import os
import zfspy

from .zfileinfo import ZFileInfo

SECTOR_SIZE = 512
DNODE_SIZE = 512

LABEL_OFFSET = 0
VDEV_OFFSET = LABEL_OFFSET + 16384  # 16k offset from beginning of the label
VDEV_SIZE = 114688  # 112K of NVPairs


def get_dev_size(dev):
    """Return the size of a device.

    Finds and returns the size of a device or file.

    https://stackoverflow.com/questions/2773604/query-size-of-block-device-file-in-python

    Args:
        dev: The device to find the size of.

    Returns:
        An integer representing the size of the disk in bytes.
    """

    file_ = os.open(dev, os.O_RDONLY)

    try:
        return os.lseek(file_, 0, os.SEEK_END)
    finally:
        os.close(file_)


def get_file_from_dnode(dnode):
    """Parse a ZFile from a given dnode.

    A ZFile contains both the dnode and the contents of the bonus section of
    the dnode represented as a ZNode. This function will parse the ZNode and
    return a newly created ZFile object.

    Args:
        dnode: The dnode to create a ZFile from.

    Returns:
        A ZFile object representing the given dnode.
    """

    zfsfile = zfspy.ZFile()
    zfsfile.dnode = dnode
    zfsfile.znode = zfspy.ZNode(dnode.bonus)

    return zfsfile


def get_uberblocks(disk, vdev_tree):
    """Locates valid Uberblocks.

    Given a disk and the tree representing VDevs of a ZFS pool, this function
    will locate the valid UberBlocks and return them in a dictionary indexed by
    their ub_txg (transaction group number).

    Args:
        disk: The disk to load the UberBlocks from.
        vdev_tree: The VDev information for the ZFS pool.

    Returns:
        A dictionary of UberBlock objects indexed by their ub_txg value.
    """

    spa = zfspy.SPA(vdev_tree)
    labels = spa.load_labels(disk)
    valid = {}

    for label in labels:
        for uberb in label.uberblocks:
            if not uberb.valid():
                continue

            if uberb.ub_txg in valid:
                continue
            valid[uberb.ub_txg] = uberb

    return valid


def get_vdev_info(disk):
    """Return the VDev information for a disk.

    Parses the VDev information from a given disk. The VDev information
    contains information about every VDev in a ZFS pool and the structure of
    the VDevs.

    Args:
        disk: The disk to load VDev info from.

    Returns:
        A zfspy.OODict object representing the VDev info that was parsed from
        the disk.
    """

    raw_data = zfspy.ZIO.read(disk, VDEV_OFFSET, VDEV_SIZE)
    data = zfspy.NVPair.unpack(raw_data)
    vdev_info = zfspy.NVPair.strip(data['value'])

    return vdev_info


def walk_files(pool, filehash):
    """Add all files in the given pool to the filehash.

    Walks the entire file system directory by directory creating ZFileInfo
    objects from all of the found files and adding them to the ZFileHash
    filehash.

    Args:
        pool: The loaded pool to walk.
        filehash: A ZFileHash object to add the found files to.
    """

    def _walk_dir(zdir):
        """Walk the given directory adding ZFileInfo objects to the filehash.

        Args:
            zdir: The directory to walk.
        """

        for item in zdir.entries.keys():
            path.append(item)

            zobj_id = zdir.get_child(item)
            zobj = zfs.open_obj(zobj_id)
            zobj.read()

            if isinstance(zobj, zfspy.zpl.ZDir):
                _walk_dir(zobj)
            elif isinstance(zobj, zfspy.zpl.ZFile):
                zfilename = '_'.join(path)
                zfileinfo = ZFileInfo(zobj, zfilename)
                filehash.add(zfileinfo)

            path.pop()

    path = []

    zfs = pool.dsl_dir.head_dataset.active_fs
    root = zfs.open('/')
    root.read()
    _walk_dir(root)


def dnode_scan(disk, vdev_tree, sector_map):
    """Scans for dnodes on a given disk.

    Scanning is performed on the disk given to locate ZFS dnodes. The
    sector_map provides a mapping of sectors to search (those that have not
    been set). Each bit in the sector_map cooresponds to a sector on disk. Once
    the data is read from disk it decompressed. Currently the only supported
    form of compression for dnodes is LZJB. If the decompression yeilds usable
    data dnodes are created from that data. If the dnode created is valid then
    it is added to the list of parsed dnodes. The list is then returned.

    Args:
        disk: The disk to scan for dnodes.
        vdev_tree: The VDev information for the ZFS pool.
        sector_map: A SectorMap of sectors not to scan.

    Returns:
        A list of zfspy.DNode objects that were parsed from the disk.
    """

    file_ = open(disk, 'rb')
    dnodes = []

    for sector in sector_map.unset_gen():
        offset = sector * SECTOR_SIZE
        file_.seek(offset)

        data = file_.read(1024)
        decomp_data = zfspy.compress.lzjb_decompress(data)

        if not decomp_data:
            continue

        chunks = len(decomp_data) / DNODE_SIZE

        for ii in xrange(0, chunks):

            try:
                dnode = zfspy.DNode(
                    vdev_tree,
                    zfspy.util.get_record(decomp_data, DNODE_SIZE, ii)
                    )
            except Exception:
                continue
            else:
                if dnode.type != 'DMU_OT_NONE':
                    dnodes.append(dnode)

    return dnodes
