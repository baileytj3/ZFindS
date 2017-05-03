import hashlib
import logging


class ZFileHash(dict):
    """Dictionary that creates keys based on contents of the ZFile.

    A ZFileHash stores ZFiles in a dictionary with a key that is based off of a
    sha256 hash of the ZFile data. A ZFileHash also prevents multiple files
    with the same data from being added into the dictionary.
    """

    def __init__(self, exclude=None):
        """Initialize ZFileHash.

        Args:
            exclude: ZFileHash of objects not to exclude from this ZFileHash.
        """

        super(ZFileHash, self).__init__()
        self.exclude = exclude
        self.log = logging.getLogger(__name__)

    def __add__(self, other):
        """Overwrite + operator.

        Takes two ZFileHashes and returns a new ZFileHash that represents a
        combination of them both.

        Args:
            other: The other ZFileHash to add to this one.

        Returns:
            A new ZFileHash that is a combination of self, and other.
        """

        fhash = ZFileHash()
        fhash.update(self)

        if other is not None:
            fhash.update(other)

        return fhash

    def add(self, zfile):
        """Add a ZFile to the dictionary.

        Before adding the file to the dictionary, the ZFile contents are read
        and hashed to generate a key. The dictionary is then checked to make
        sure the key does not already exist before adding the ZFile.

        Args:
            zfile: The ZFile object to add to the dictionary.
        """

        zfile_hash = hashlib.sha256()
        zfile_hash.update(zfile.read())
        digest = zfile_hash.hexdigest()

        self.log.debug('Digest: %s - Attempting to add file', digest[:6])

        if digest in self:
            self.log.debug('Digest: %s - File exists in self', digest[:6])
        else:
            if self.exclude:
                if digest in self.exclude:
                    self.log.debug('Digest: %s - File exists in excludes',
                                   digest[:6])
                else:
                    self.log.debug('Digest: %s - Added file', digest[:6])
                    self[digest] = zfile
            else:
                self.log.debug('Digest: %s - Added file', digest[:6])
                self[digest] = zfile
