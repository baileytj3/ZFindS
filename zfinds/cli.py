import logging
import click

from .zfinds import Zfinds
from .zfilewriter import ZFileWriter

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS, options_metavar='<options>')
@click.argument('method', metavar='<method>',
                type=click.Choice(['all', 'brute', 'uber']))
@click.argument('disk', metavar='<path to disk>')
@click.option('-d', '--destination', default='/tmp/zfinds', metavar='<dest>',
              show_default=True, help='location to save recovered files',
              type=click.Path(file_okay=False, writable=True,
                              resolve_path=True))
@click.option('--cache/--no-cache', default=True, show_default=True,
              help='If True, enables creating a cache of existing files '
              'before running recovery to prevent them from being found')
@click.option('-v', '--log-level', default='WARN',
              type=click.Choice(['DEBUG', 'INFO', 'WARN', 'ERROR']),
              show_default=True, help='logging level to use')
def cli(disk, method, destination, cache, log_level):
    """
    ZFindS is a command line tool that can be used to attempt to recover
    previous versions of files on disk, or files that have been deleted but yet
    still remain on disk.

    Supported recovery methods:

        \b
        uber
            The uber recovery method scans through all
            available UberBlocks that are not the active
            UberBlock for files that may have been
            altered or deleted.

        \b
        brute
            The brute recovery method scans all unused
            blocks on the disk and attempts to parse
            DNodes from them in an attempt to locate
            files that may have been altered or deleted.

        \b
        all
            The all recovery method performs both the
            uber and brute recovery methods. When the
            all recovery method is used the output of
            the brute method will not include the files
            that were found with the uber recovery method.

    Output:

        \b
        The files that are found by either recovery method
        are saved to a default location, unless overridden
        by the -d flag. The files found by the uber method
        will have a file name that corresponds to their
        original path with the postfix of the access time in
        seconds since epoch and the text 'uber'. Files
        recovered by the brute method will have file names
        starting with 1 and incrementing for each found file.
        They will also have a postfix of the access time in
        seconds since epoch and the text 'brute'. Files
        found via either method will have their access and
        modify times updated to what they were on the file
        system that is being scanned.
    """

    # Set root logging configuration
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)

    zfilewriter = ZFileWriter(destination)
    zfinds = Zfinds(disk, zfilewriter)

    if cache:
        zfinds.build_cache()

    if method == 'uber' or method == 'all':
        zfinds.find_uber()
        zfinds.write_uber()

    if method == 'brute' or method == 'all':
        zfinds.find_brute()
        zfinds.write_brute()
