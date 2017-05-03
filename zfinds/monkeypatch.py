import zfspy

from zfspy import StreamUnpacker
from zfspy.compress import lzjb_decompress
from zfspy.dmu import OBJSet
from zfspy.dsl import DSL_Dir
from zfspy.nvpair import DATA_TYPE, NVPair
from zfspy.spa import UBERBLOCK_SIZE, BlockPtr, UberBlock
from zfspy.util import debug, get_record, split_records
from zfspy.zap import ZAP, ZBT_MICRO
from zfspy.zio import ZIO


def monkeypatch_method(cls, clsmethod=False):
    """
    Function to monkeypatch a method of a given class.

    Given a class this decorator will either add or replace the method within
    the class with the function that is decorated by this decorator.

    Arguments:
        cls (class): The class to add/replace the method in.
    """
    def decorator(func):
        """Decorated function"""

        if clsmethod:
            setattr(cls, func.__name__, classmethod(func))
        else:
            setattr(cls, func.__name__, func)
        return func

    return decorator

#
# Monkeypatch NVPair
#

# Fix error where pair['type'] was not set on DATA_TYPE_BOOLEAN's.
@monkeypatch_method(zfspy.nvpair.NVPair)
def _single_pair_decode(self):
    # Get name, type, elements number
    pair = {}
    pair['encoded_sz'], pair['decoded_sz'] = self.su.repeat('uint32', 2)
    pair['name'] = self.su.string()

    type, n = self.su.repeat('uint32', 2)
    type = DATA_TYPE[type]
    pair['type'] = type
    # Adjust the elments number, only array type has more than one elements.
    # We did not check malformed file format here
    if type == 'DATA_TYPE_BOOLEAN':
        n = 0
        pair['value'] = None
        return pair

    pair['elements_n'] = n
    value = []
    # It's wired thinking of nvlistarray, in memory I know how it looks like,
    # but what about in a file? How to store nvlist's data?
    # Parse all the elements
    for i in range(n):
        value.append(self._elements_decode(type))
    # If it's not a array, we should not return a list
    if 'ARRAY' not in type:
        value = value[0]
    pair['value'] = value
    return pair

#
# Monkeypatch VDevLabel
#

# Modify the ununsed variable self.uberblocks to be a list. All of the
# UberBlocks that are found when parsing the VDevLabel will be added to the
# array for retrieval later.
@monkeypatch_method(zfspy.spa.VDevLabel)
def __init__(self, data=None):
    self.boot_header = None
    self.nvlist = {}
    self.uberblocks = []
    self.data = ''
    self.ub_array = None
    if data:
        self._from_data(data)

# Add method call to append the found UberBlock to the self.uberblocks array.
@monkeypatch_method(zfspy.spa.VDevLabel)
def _from_data(self, data):
    self.boot_header = data[8 << 10: 16 << 10]
    self.nvlist = NVPair.unpack(data[16 << 10: 128 << 10])
    self.data = NVPair.strip(self.nvlist['value'])

    # find the active uberblock
    self.ub_array = data[128 << 10:]
    ubbest = None
    i = 0
    for data in split_records(self.ub_array, UBERBLOCK_SIZE):
        ub = UberBlock(data, self)
        ub.index = i
        i = i + 1

        self.uberblocks.append(ub)

        if not ub.valid():
            continue
        if ub.better_than(ubbest):
            ubbest = ub

    self.ubbest = ubbest
    self.ubbest.load_rootbp()

#
# Monkeypatch SPA
#

# Add method to load a particular txg instead of loading the UberBlock with the
# highest txg.
@monkeypatch_method(zfspy.spa.SPA)
def vdev_ubtxg_load(self, vdev, txg):
    """
    Find an UberBlock with the given txg number and load it.
    """
    if 'children' in vdev:
        for node in vdev.children:
            self.vdev_ubtxg_load(node, txg)
        return

    for label in self.load_labels(vdev.path):
        for ub in label.uberblocks:
            if ub.ub_txg == txg:
                self.ubbest = ub
                self.labelbest = label
                self.ubbest.load_rootbp()

# Save builtin open call
builtin_open = open

# Add txg as a keyword argument to open(). This will allow a given transaction
# group to be loaded from the ZFS pool.
@monkeypatch_method(zfspy.spa.SPA)
def open(self, txg=None):
    if txg:
        self.vdev_ubtxg_load(self.vdev, txg)
    else:
        self.vdev_ubbest_load(self.vdev)

# Restore builtin open call
open = builtin_open

#
# Monkeypatch UberBlock
#

# Store the label that the Uberblock was loaded from so that the root block
# pointer can be lazily loaded.
@monkeypatch_method(zfspy.spa.UberBlock)
def __init__(self, data, label=None):
    if data:
        su = StreamUnpacker(data)
        self.ub_magic, self.ub_version, self.ub_txg, self.ub_guid_sum, self.ub_timestamp = su.repeat('uint64', 5)
        self.label = label


# Add method to be able to lazily load a root block pointer from a UberBlock.
@monkeypatch_method(zfspy.spa.UberBlock)
def load_rootbp(self):
    data = get_record(self.label.ub_array, UBERBLOCK_SIZE, self.index)
    self.ub_rootbp = BlockPtr(data[40: 168])

#
# Monkeypatch ZAP
#

# Instead of printing output when a fat ZAP is encountered, raise an error.
@monkeypatch_method(zfspy.zpool.ZAP)
def __init__(self, data):
    self.type = StreamUnpacker(data[:8]).uint64()
    if self.type == ZBT_MICRO:
        debug('mzap init')
        self._mzap(data)
    else:
        raise NotImplementedError('Unable to parse fat ZAP\'s')

#
# Monkeypatch ZPool
#

# Add txg keyword argument to load(). This argument will tell the ZPool to load
# a particular txg from the ZFS pool.
@monkeypatch_method(zfspy.zpool.ZPool)
def load(self, txg=None):
    """
    Load root dataset from disks

    object_directory is the second element(index 1) in mos, it's a zap
    object, contains:
        root_dataset DMU_OT_DSL_DIR
        config DMU_OT_PACKED_NVLIST
        sync_bplist DMU_OT_SYNC_BPLIST
    """
    self.spa.open(txg)
    vdev = self.spa.labelbest.data.vdev_tree
    data = ZIO.read_blk(vdev, self.spa.ubbest.ub_rootbp)
    self.mos = OBJSet(vdev, data)
    self.object_directory = ZAP.from_dnode(self.mos, 1)

    # get config, sync_bplist  here

    # get root_dataset
    self.dsl_dir = DSL_Dir(self.mos, self.object_directory.entries.root_dataset)
