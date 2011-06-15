# MBUtil

MBUtil is a utility for importing and exporting the [MBTiles](http://mbtiles.org/) format.

## Installation

Git checkout (requires git)

    git clone git://github.com/mapbox/mbutil.git
    cd mbutil
    ./mb-util -h

    # then to install the mb-util command globally:
    sudo python setup.py install
    # then you can run:
    mb-util

Python installation (requires easy_install)

    easy_install mbutil
    mb-util -h

## Usage

Export an `mbtiles` file to files on the filesystem:

    mb-util World_Light.mbtiles adirectory

Import a directory into a `mbtiles` file

    mb-util directory World_Light.mbtiles

## Requirements

* Python `>= 2.6`

## Metadata

MBUtil imports and exports metadata as JSON, in the root of the tile directory, as a file named `metadata.json`.

    {
        "name": "World Light",
        "description": "A Test Metadata",
        "version": "3"
    }

## Authors

- Tom MacWright (tmcw)
- Dane Springmeyer (springmeyer)
- Mathieu Leplatre (leplatrem)
