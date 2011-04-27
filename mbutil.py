#!/usr/bin/env python
# MBUtil: a tool for MBTiles files
# Supports importing, exporting, and more
# 
# (c) Development Seed 2011
# Licensed under BSD
import logging
import os, sys
from optparse import OptionParser

from mbutil import mbtiles_to_disk, disk_to_mbtiles, mbtiles_update_mbtiles


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    parser = OptionParser(usage="usage: %prog [options] input output")
    parser.add_option('-w', '--window', dest='window',
        help='compression window size. larger values faster, dangerouser',
        type='int',
        default=2000)
    parser.add_option('-m', '--merge', dest='merge', action="store_true",
        help='Merge the first tileset into the second one, overwriting files if necessary')

    (options, args) = parser.parse_args()

    # Transfer operations
    if len(args) == 2:
        if (options.merge): # TODO: SAFETY CHECKS
            mbtiles_file_in, mbtiles_file_out = args
            mbtiles_update_mbtiles(mbtiles_file_in, mbtiles_file_out)
        if os.path.isfile(args[1]) and os.path.exists(args[1]) and not (options.merge):
            sys.stderr.write('To export MBTiles to disk, specify a directory that does not yet exist\n')
            sys.exit(1)
        if os.path.isfile(args[0]) and not os.path.exists(args[1]):
            mbtiles_file, directory_path = args
            mbtiles_to_disk(mbtiles_file, directory_path)
        if os.path.isdir(args[0]) and os.path.isfile(args[1]):
            sys.stderr.write('Importing tiles into already-existing MBTiles is not yet supported\n')
            sys.exit(1)
        if os.path.isdir(args[0]) and not os.path.isfile(args[0]):
            directory_path, mbtiles_file = args
            disk_to_mbtiles(directory_path, mbtiles_file)
    else:
        parser.print_help()
