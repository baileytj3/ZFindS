import logging
import zfspy

from .sectortracker import SectorTracker
from .zfilehash import ZFileHash
from .zfileinfo import ZFileInfo
from .utils import (
    dnode_scan,
    get_file_from_dnode,
    get_uberblocks,
    get_vdev_info,
    walk_files,
    )


class Zfinds(object):
    """Contains all objects related to data recovery.

    The Zfinds object contains all of the necessary objects to perform data
    recovery on the given ZFS file system.
    """

    def __init__(self, disk, writer):
        """Initialize Zfinds.

        Args:
            disk: The path to the disk to perform recovery.
            writer: The ZFileWriter to use for data output.
        """

        self.disk = disk
        self.writer = writer
        self.files = ZFileHash()
        self.files_uber = None
        self.files_brute = None
        self.tracker = None
        self.vdev_info = get_vdev_info(self.disk)
        self.log = logging.getLogger(__name__)

    def build_cache(self):
        """Builds a cache of files on current file system.

        Walks the current file system hashing all of the files to add to the
        ZFileHash. The cache is necessary so that current files are not
        returned as 'found' files.
        """

        self.log.info('Building file cache.')
        self.tracker = SectorTracker(zfspy.zio.ZIO.read, self.disk)
        zfspy.zio.ZIO.read = self.tracker

        pool = zfspy.ZPool(self.vdev_info)
        pool.load()
        walk_files(pool, self.files)

    def find_brute(self):
        """Perform data recovery via the brute method.

        Recovers data from the ZFS file system by attempting to locate dnodes
        of the type DMU_OT_PLAIN_FILE_CONTENTS. When a dnode of the correct
        type is found it is added to the ZFileHash.
        """

        self.log.info('Running brute method.')
        self.files_brute = ZFileHash(exclude=self.files+self.files_uber)

        dnodes = dnode_scan(self.disk, self.vdev_info.vdev_tree,
                            self.tracker.get_map())

        for dnode in dnodes:
            if dnode.type != 'DMU_OT_PLAIN_FILE_CONTENTS':
                continue

            zfile = get_file_from_dnode(dnode)
            self.files_brute.add(ZFileInfo(zfile))

    def find_uber(self):
        """Perform data recover via the uber method.

        Recovers data from the ZFS file system by checking all available
        uberblocks for a valid file system, and then scanning those file
        systems for files. When a file is found it is added to the ZFileHash.
        """

        self.log.info('Running uber method.')
        self.files_uber = ZFileHash(exclude=self.files)
        ubblocks = get_uberblocks(self.disk, self.vdev_info.vdev_tree)

        for txg in ubblocks.keys():
            pool = zfspy.ZPool(self.vdev_info)

            try:
                pool.load(txg)
                walk_files(pool, self.files_uber)
            except NotImplementedError:
                self.log.warn('Found fat ZAP in txg %s', txg)
            except Exception:
                self.log.debug('Error on txg %s', txg)
                continue

            self.log.debug('Walked txg %s', txg)

    def write_brute(self):
        """Save the files found via the brute method.

        Uses the ZFileWriter that was given to save the files that were found
        via the brute method.
        """

        self.log.info('Writing brute files.')
        self.writer.write(self.files_brute.values(), 'brute')

    def write_uber(self):
        """Save the files found via the uber method.

        Uses the ZFileWriter that was given to save the files that were found
        via the uber method.
        """

        self.log.info('Writing uber files.')
        self.writer.write(self.files_uber.values(), 'uber')
