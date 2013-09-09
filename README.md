# MBUtil

MBUtil is a utility for importing and exporting the [MBTiles](http://mbtiles.org/) format,
typically created with [MapBox](http://mapbox.com/) [TileMill](http://mapbox.com/tilemill/).

Before exporting tiles to disk, see if there's a [MapBox Hosting plan](http://mapbox.com/plans/)
or an open source [MBTiles server implementation](https://github.com/mapbox/mbtiles-spec/wiki/Implementations)
that works for you - tiles on disk are notoriously difficult to manage.

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

    $ mb-util -h
    Usage: mb-util [options] input output

        Examples:
        Export an mbtiles file to a directory of files:

        $ mb-util world.mbtiles tiles # tiles must not already exist

        Import a directory of tiles into an mbtiles file:
        $ mb-util tiles world.mbtiles # mbtiles file must not already exist

    Options:
      -h, --help       show this help message and exit
      --scheme=SCHEME  Tiling scheme of the tiles. Default is "xyz" (z/x/y),
                       other options are "tms" which is also z/x/y
                       but uses a flipped y coordinate, and "wms" which replicates
                       the MapServer WMS TileCache directory structure "z/000/000/x/000/000/y.png"''',

    Export an `mbtiles` file to files on the filesystem:

        mb-util World_Light.mbtiles adirectory

    Import a directory into a `mbtiles` file

        mb-util directory World_Light.mbtiles

## Requirements

* Python `>= 2.6`

## Metadata

MBUtil imports and exports metadata as JSON, in the root of the tile directory, as a file named `metadata.json`.

```javascript
{
    "name": "World Light",
    "description": "A Test Metadata",
    "version": "3"
}
```

## Testing

This project uses [nosetests](http://readthedocs.org/docs/nose/en/latest/) for testing. Install nosetests
and run

    nosetests

## See Also

* [node-mbtiles provides mbpipe](https://github.com/mapbox/node-mbtiles/wiki/Post-processing-MBTiles-with-MBPipe), a useful utility.

## License

BSD - see LICENSE.md

## Authors

- Tom MacWright (tmcw)
- Dane Springmeyer (springmeyer)
- Mathieu Leplatre (leplatrem)
