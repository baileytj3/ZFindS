import copy
import math

from functools import wraps

from .sectormap import SectorMap
from .utils import get_dev_size

SECTOR_SIZE = 512


class SectorTracker(object):
    """Tracks access sectors on a disk.

    The SectorTracker is used to replace the callable function
    zfspy.zio.ZIO.read. Upon the function being called SectorTracker calculates
    the sector(s) on disk that is being read from and marks it as used in the
    SectorMap. This class was originally written to keep track of the used
    sectors on a ZFS disk during a data walk. These sectors could then be
    skipped during a scan of the disk for inactive dnodes. This is utilized to
    speed up the brute force method of finding dnodes.
    """

    def __init__(self, func, dev):
        """Initialize SectorTracker.

        Args:
            func: The function that is being decorated.
            dev: The device to track.
        """
        self.dev = dev
        self.dev_size = get_dev_size(dev)
        self.dev_sectors = self.dev_size / SECTOR_SIZE
        self.func = func
        self.sector_map = SectorMap(self.dev_sectors)
        self.track = False
        wraps(func)(self)

    def __call__(self, dev, offset, size, *args, **kwargs):
        """Calculate the sector(s) and call the decorated function.

        When the object is called, the sectors that are being access is
        calculated and the SectorMap is updated accordingly. Once the SectorMap
        is updated the decorated function is called.

        Args:
            dev: The device to read from.
            offset: The offset to start reading from the device at.
            size: The size of data to read.

        Returns:
            The data read by the decorated function.
        """

        # If offset if negative then the reference point on the disk is the
        # end, not the beginning like with a positive offset. Make sure
        # reference point is the beginning of the disk.
        if offset < 0:
            true_offset = self.dev_size + offset
        else:
            true_offset = offset

        sector = true_offset / SECTOR_SIZE
        count = int(math.ceil(size / SECTOR_SIZE))

        sectors = []
        for ii in xrange(0, count):
            sectors.append(sector+ii)
            self.sector_map.set(sector + ii)

        return self.func(dev, offset, size, *args, **kwargs)

    def get_map(self):
        """Retrieve the SectorMap.

        Creates a copy of the SectorMap and returns it. Since the sector_map is
        an Object it is possible that if not copied, it could be modified
        outside of the SectorTracker object, which would affect the sector_map
        object that is currently in use. Therefore a deep copy of the SectorMap
        object is made before returning.

        Returns:
            A SectorMap object representing the sectors that have been
                accessed.
        """

        return copy.deepcopy(self.sector_map)

    def reset(self):
        """Reset the SectorMap.

        Creates a new SectorMap for tracking used sectors.
        """

        self.sector_map = SectorMap(self.sector_map.size())
