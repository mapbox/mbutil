# MBUtil

MBUtil is a utility for importing and exporting the [MBTiles](http://mbtiles.org/) format.

## Building

MBUtil requires [boost](http://www.boost.org/) and [SQLite](http://sqlite.org/).

    make

## Usage

Export an `mbtiles` file to files on the filesystem:

    mbutil --input World_Light.mbtiles --output adirectory

Import a directory into a `mbtiles` file

    mbutil --input directory --output World_Light.mbtiles

## Authors

- Tom MacWright (tmcw)
