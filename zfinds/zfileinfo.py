class ZFileInfo(object):
    """Container for ZFile and its metadata.

    ZFS stores the ZFile object separate from certain metadata, like the ZFile
    name. A ZFileInfo object stores a ZFile and its name attribute for
    convenience.

    Attributes:
        zfile: The ZFile object.
        name: The name of the ZFile.
    """

    def __init__(self, zfile, name=None):
        """Initialize ZFileInfo.

        Args:
            zfile: The ZFile object.
            name: The name associated with the ZFile object.
        """

        self.zfile = zfile
        self.name = name

    def read(self):
        """Read the contents of the ZFile.

        Returns:
            The contents of the ZFile.
        """

        return self.zfile.read()
