import logging
import os


class ZFileWriter(object):
    """Writes ZFiles out to file system.

    Class to write the list of found ZFiles to a given location. Once the file
    is written to the file system the access and modify times of the file are
    updated to reflect the access and modify times on the ZFile.
    """

    def __init__(self, base_path):
        """Initialize ZFileWriter.

        Args:
            base_path: path to where files should be saved.
        """

        self.base_path = os.path.abspath(base_path)
        self.log = logging.getLogger(__name__)

        if os.path.exists(self.base_path):
            if not os.path.isdir(self.base_path):
                raise IOError('Base path is not a directory')
        else:
            os.mkdir(self.base_path)

    def write(self, zfiles, postfix):
        """Write the ZFiles to the file system.

        Writes the ZFile data to the file system in the location specified by
        base_path. After the ZFile data has been written the access and modify
        times are updated to match that of the original ZFile.

        Args:
            zfiles: List of ZFileInfo objects to write.
            postfix: String to append to the end of the file name.
        """

        self.log.info('Writing files')
        file_count = 0

        for zfileinfo in zfiles:
            atime = zfileinfo.zfile.znode.atime[0]
            mtime = zfileinfo.zfile.znode.mtime[0]

            if zfileinfo.name:
                file_name = '{0}-{1}-{2}'.format(
                    zfileinfo.name, mtime, postfix)
            else:
                file_count += 1
                file_name = '{0:05}-{1}-{2}'.format(file_count, mtime, postfix)

            self.log.info('Found file: %s', file_name)

            file_path = os.path.join(self.base_path, file_name)
            zfile = zfileinfo.zfile

            file_ = open(file_path, 'w')
            file_.write(zfile.read())
            file_.close()

            os.utime(file_path, (atime, mtime))
