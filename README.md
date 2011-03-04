# MBUtil

MBUtil is a utility for importing and exporting the [MBTiles](http://mbtiles.org/) format.

## Usage

Export an `mbtiles` file to files on the filesystem:

    mbutil --input World_Light.mbtiles --output adirectory

Import a directory into a `mbtiles` file

    mbutil --input directory --output World_Light.mbtiles

## Building

MBUtil requires [cmake](http://www.cmake.org/), [boost](http://www.boost.org/) and [SQLite](http://sqlite.org/) to build.

    cmake .
    make

## Metadata

MBUtil imports and exports metadata as JSON, in the root of the tile directory, as a file named `metadata.json`.

    {
        "metadata": {
            "name": "World Light",
            "description": "A Test Metadata",
            "version": "3"
        }
    }

## Authors

- Tom MacWright (tmcw)
