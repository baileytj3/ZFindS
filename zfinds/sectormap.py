import bitmap


class SectorMap(object):
    """Maps bits in a bitmap to sectors on a disk.

    Used to keep track of use of sectors on a disk. Bits in the bitmap
    represents a sector on disk. Can be used as a boolean flag for disk
    sectors.
    """

    def __init__(self, size):
        """Initialize SectorMap.

        Args:
            size: The number of sectors to account for.
        """
        self.map_size = size
        self.map = bitmap.BitMap(size)

    def get(self, sector):
        """Retrieve a sectors status.

        Args:
            sector: The sector position to get.

        Returns:
            The value of the sector at the given position.
        """

        return self.get(sector)

    def set(self, sector):
        """Set a sectors status.

        Sets the sector flag at the given sector position.

        Args:
            sector: The sector position to set.
        """
        self.map.set(sector)

    def size(self):
        """Retrieve the size of the SectorMap.

        Returns:
            The size of the sector map as an integer.
        """

        return self.map_size

    def unset_gen(self):
        """A generator that yields unset sectors.

        Loops over all of the sectors in the map and yields the unset ones.

        Yields:
            Unset sectors in the map.
        """

        for sector in xrange(self.map_size):
            if not self.map.test(sector):
                yield sector

    def set_gen(self):
        """A generator that yields set sectors.

        Loops over all of the sectors in the map and yields the set ones.

        Yields:
            Set sectors in the map.
        """

        for sector in xrange(self.map_size):
            if self.map.test(sector):
                yield sector
