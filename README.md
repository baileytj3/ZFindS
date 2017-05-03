# ZFindS

ZFindS is a command line tool that can be used to attempt to recover previous
versions of files on disk, or files that have been deleted but yet still remain
on disk.

## Supported recovery methods

uber
------
The uber recovery method scans through all available UberBlocks that
are not the active UberBlock for files that may have been altered or
deleted.

brute
-----
The brute recovery method scans all unused blocks on the disk and
attempts to parse DNodes from them in an attempt to locate files that
may have been altered or deleted.

all
-----
The all recovery method performs both the uber and brute recovery
methods. When the all recovery method is used the output of the brute
method will not include the files that were found with the uber
recovery method.

## Output

The files that are found by either recovery method are saved to a default
location, unless overridden by the -d flag. The files found by the uber method
will have a file name that corresponds to their original path with the postfix
of the access time in seconds since epoch and the text 'uber'. Files recovered
by the brute method will have file names starting with 1 and incrementing for
each found file.  They will also have a postfix of the access time in seconds
since epoch and the text 'brute'. Files found via either method will have their
access and modify times updated to what they were on the file system that is
being scanned.

# Installation

## Dependancies

Install ZFSpy dependancy.

    git clone https://github.com/nkchenz/zfspy
    python zfspy/setup.py install

## Install ZFindS

Clone the github repository.
Install the package via pip.

    git clone https://github.com/baileytj3/ZFindS
    python ZFindS/setup.py install
