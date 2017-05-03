#!/usr/bin/env python

# MBUtil: a tool for MBTiles files
# Supports importing, exporting, and more
#
# (c) Development Seed 2012
# Licensed under BSD

# for additional reference on schema see:
# https://github.com/mapbox/node-mbtiles/blob/master/lib/schema.sql

import sqlite3, sys, logging, time, os, json, zlib, re

logger = logging.getLogger(__name__)

def flip_y(zoom, y):
    return (2**zoom-1) - y

def mbtiles_setup(cur):
    cur.execute("""
        create table tiles (
            zoom_level integer,
            tile_column integer,
            tile_row integer,
            tile_data blob);
            """)
    cur.execute("""create table metadata
        (name text, value text);""")
    cur.execute("""CREATE TABLE grids (zoom_level integer, tile_column integer,
    tile_row integer, grid blob);""")
    cur.execute("""CREATE TABLE grid_data (zoom_level integer, tile_column
    integer, tile_row integer, key_name text, key_json text);""")
    cur.execute("""create unique index name on metadata (name);""")
    cur.execute("""create unique index tile_index on tiles
        (zoom_level, tile_column, tile_row);""")

def mbtiles_connect(mbtiles_file, silent):
    try:
        con = sqlite3.connect(mbtiles_file)
        return con
    except Exception as e:
        if not silent:
            logger.error("Could not connect to database")
            logger.exception(e)
        sys.exit(1)

def optimize_connection(cur):
    cur.execute("""PRAGMA synchronous=0""")
    cur.execute("""PRAGMA locking_mode=EXCLUSIVE""")
    cur.execute("""PRAGMA journal_mode=DELETE""")

def compression_prepare(cur, silent):
    if not silent: 
        logger.debug('Prepare database compression.')
    cur.execute("""
      CREATE TABLE if not exists images (
        tile_data blob,
        tile_id integer);
    """)
    cur.execute("""
      CREATE TABLE if not exists map (
        zoom_level integer,
        tile_column integer,
        tile_row integer,
        tile_id integer);
    """)

def optimize_database(cur, silent):
    if not silent: 
        logger.debug('analyzing db')
    cur.execute("""ANALYZE;""")
    if not silent: 
        logger.debug('cleaning db')

    # Workaround for python>=3.6.0,python<3.6.2
    # https://bugs.python.org/issue28518
    cur.isolation_level = None
    cur.execute("""VACUUM;""")
    cur.isolation_level = ''  # reset default value of isolation_level


def compression_do(cur, con, chunk, silent):
    if not silent:
        logger.debug('Making database compression.')
    overlapping = 0
    unique = 0
    total = 0
    cur.execute("select count(zoom_level) from tiles")
    res = cur.fetchone()
    total_tiles = res[0]
    last_id = 0
    logging.debug("%d total tiles to fetch" % total_tiles)
    for i in range(total_tiles // chunk + 1):
        logging.debug("%d / %d rounds done" % (i, (total_tiles / chunk)))
        ids = []
        files = []
        start = time.time()
        cur.execute("""select zoom_level, tile_column, tile_row, tile_data
            from tiles where rowid > ? and rowid <= ?""", ((i * chunk), ((i + 1) * chunk)))
        logger.debug("select: %s" % (time.time() - start))
        rows = cur.fetchall()
        for r in rows:
            total = total + 1
            if r[3] in files:
                overlapping = overlapping + 1
                start = time.time()
                query = """insert into map
                    (zoom_level, tile_column, tile_row, tile_id)
                    values (?, ?, ?, ?)"""
                logger.debug("insert: %s" % (time.time() - start))
                cur.execute(query, (r[0], r[1], r[2], ids[files.index(r[3])]))
            else:
                unique = unique + 1
                last_id += 1

                ids.append(last_id)
                files.append(r[3])

                start = time.time()
                query = """insert into images
                    (tile_id, tile_data)
                    values (?, ?)"""
                cur.execute(query, (str(last_id), sqlite3.Binary(r[3])))
                logger.debug("insert into images: %s" % (time.time() - start))
                start = time.time()
                query = """insert into map
                    (zoom_level, tile_column, tile_row, tile_id)
                    values (?, ?, ?, ?)"""
                cur.execute(query, (r[0], r[1], r[2], last_id))
                logger.debug("insert into map: %s" % (time.time() - start))
        con.commit()

def compression_finalize(cur):
    logger.debug('Finalizing database compression.')
    cur.execute("""drop table tiles;""")
    cur.execute("""create view tiles as
        select map.zoom_level as zoom_level,
        map.tile_column as tile_column,
        map.tile_row as tile_row,
        images.tile_data as tile_data FROM
        map JOIN images on images.tile_id = map.tile_id;""")
    cur.execute("""
          CREATE UNIQUE INDEX map_index on map
            (zoom_level, tile_column, tile_row);""")
    cur.execute("""
          CREATE UNIQUE INDEX images_id on images
            (tile_id);""")
    cur.execute("""vacuum;""")
    cur.execute("""analyze;""")

def get_dirs(path):
    return [name for name in os.listdir(path)
        if os.path.isdir(os.path.join(path, name))]

def disk_to_mbtiles(directory_path, mbtiles_file, **kwargs):

    silent = kwargs.get('silent')

    if not silent:
        logger.info("Importing disk to MBTiles")
        logger.debug("%s --> %s" % (directory_path, mbtiles_file))

    con = mbtiles_connect(mbtiles_file, silent)
    cur = con.cursor()
    optimize_connection(cur)
    mbtiles_setup(cur)
    #~ image_format = 'png'
    image_format = kwargs.get('format', 'png')

    try:
        metadata = json.load(open(os.path.join(directory_path, 'metadata.json'), 'r'))
        image_format = kwargs.get('format')
        for name, value in metadata.items():
            cur.execute('insert into metadata (name, value) values (?, ?)',
                (name, value))
        if not silent: 
            logger.info('metadata from metadata.json restored')
    except IOError:
        if not silent: 
            logger.warning('metadata.json not found')

    count = 0
    start_time = time.time()
    msg = ""

    for zoom_dir in get_dirs(directory_path):
        if kwargs.get("scheme") == 'ags':
            if not "L" in zoom_dir:
                if not silent: 
                    logger.warning("You appear to be using an ags scheme on an non-arcgis Server cache.")
            z = int(zoom_dir.replace("L", ""))
        elif kwargs.get("scheme") == 'gwc':
            z=int(zoom_dir[-2:])
        else:
            if "L" in zoom_dir:
                if not silent: 
                    logger.warning("You appear to be using a %s scheme on an arcgis Server cache. Try using --scheme=ags instead" % kwargs.get("scheme"))
            z = int(zoom_dir)
        for row_dir in get_dirs(os.path.join(directory_path, zoom_dir)):
            if kwargs.get("scheme") == 'ags':
                y = flip_y(z, int(row_dir.replace("R", ""), 16))
            elif kwargs.get("scheme") == 'gwc':
                pass
            else:
                x = int(row_dir)
            for current_file in os.listdir(os.path.join(directory_path, zoom_dir, row_dir)):
                if current_file == ".DS_Store" and not silent:
                    logger.warning("Your OS is MacOS,and the .DS_Store file will be ignored.")
                else:
                    file_name, ext = current_file.split('.',1)
                    f = open(os.path.join(directory_path, zoom_dir, row_dir, current_file), 'rb')
                    file_content = f.read()
                    f.close()
                    if kwargs.get('scheme') == 'xyz':
                        y = flip_y(int(z), int(file_name))
                    elif kwargs.get("scheme") == 'ags':
                        x = int(file_name.replace("C", ""), 16)
                    elif kwargs.get("scheme") == 'gwc':
                        x, y = file_name.split('_')
                        x = int(x)
                        y = int(y)
                    else:
                        y = int(file_name)

                    if (ext == image_format):
                        if not silent:
                            logger.debug(' Read tile from Zoom (z): %i\tCol (x): %i\tRow (y): %i' % (z, x, y))
                        cur.execute("""insert into tiles (zoom_level,
                            tile_column, tile_row, tile_data) values
                            (?, ?, ?, ?);""",
                            (z, x, y, sqlite3.Binary(file_content)))
                        count = count + 1
                        if (count % 100) == 0:
                            for c in msg: sys.stdout.write(chr(8))
                            msg = "%s tiles inserted (%d tiles/sec)" % (count, count / (time.time() - start_time))
                            sys.stdout.write(msg)
                    elif (ext == 'grid.json'):
                        if not silent:
                            logger.debug(' Read grid from Zoom (z): %i\tCol (x): %i\tRow (y): %i' % (z, x, y))
                        # Remove potential callback with regex
                        file_content = file_content.decode('utf-8')
                        has_callback = re.match(r'[\w\s=+-/]+\(({(.|\n)*})\);?', file_content)
                        if has_callback:
                            file_content = has_callback.group(1)
                        utfgrid = json.loads(file_content)

                        data = utfgrid.pop('data')
                        compressed = zlib.compress(json.dumps(utfgrid).encode())
                        cur.execute("""insert into grids (zoom_level, tile_column, tile_row, grid) values (?, ?, ?, ?) """, (z, x, y, sqlite3.Binary(compressed)))
                        grid_keys = [k for k in utfgrid['keys'] if k != ""]
                        for key_name in grid_keys:
                            key_json = data[key_name]
                            cur.execute("""insert into grid_data (zoom_level, tile_column, tile_row, key_name, key_json) values (?, ?, ?, ?, ?);""", (z, x, y, key_name, json.dumps(key_json)))
    
    if not silent:
        logger.debug('tiles (and grids) inserted.')

    if kwargs.get('compression', False):
        compression_prepare(cur)
        compression_do(cur, con, 256, silent)
        compression_finalize(cur)

    optimize_database(con, silent)

def mbtiles_metadata_to_disk(mbtiles_file, **kwargs):
    silent = kwargs.get('silent')
    if not silent:
        logger.debug("Exporting MBTiles metatdata from %s" % (mbtiles_file))
    con = mbtiles_connect(mbtiles_file, silent)
    metadata = dict(con.execute('select name, value from metadata;').fetchall())
    if not silent:
        logger.debug(json.dumps(metadata, indent=2))

def mbtiles_to_disk(mbtiles_file, directory_path, **kwargs):
    silent = kwargs.get('silent')
    if not silent:
        logger.debug("Exporting MBTiles to disk")
        logger.debug("%s --> %s" % (mbtiles_file, directory_path))
    con = mbtiles_connect(mbtiles_file, silent)
    os.mkdir("%s" % directory_path)
    metadata = dict(con.execute('select name, value from metadata;').fetchall())
    json.dump(metadata, open(os.path.join(directory_path, 'metadata.json'), 'w'), indent=4)
    count = con.execute('select count(zoom_level) from tiles;').fetchone()[0]
    done = 0
    msg = ''
    base_path = directory_path
    if not os.path.isdir(base_path):
        os.makedirs(base_path)

    # if interactivity
    formatter = metadata.get('formatter')
    if formatter:
        layer_json = os.path.join(base_path, 'layer.json')
        formatter_json = {"formatter":formatter}
        open(layer_json, 'w').write(json.dumps(formatter_json))

    tiles = con.execute('select zoom_level, tile_column, tile_row, tile_data from tiles;')
    t = tiles.fetchone()
    while t:
        z = t[0]
        x = t[1]
        y = t[2]
        if kwargs.get('scheme') == 'xyz':
            y = flip_y(z,y)
            if not silent:
                logger.debug('flipping')
            tile_dir = os.path.join(base_path, str(z), str(x))
        elif kwargs.get('scheme') == 'wms':
            tile_dir = os.path.join(base_path,
                "%02d" % (z),
                "%03d" % (int(x) / 1000000),
                "%03d" % ((int(x) / 1000) % 1000),
                "%03d" % (int(x) % 1000),
                "%03d" % (int(y) / 1000000),
                "%03d" % ((int(y) / 1000) % 1000))
        else:
            tile_dir = os.path.join(base_path, str(z), str(x))
        if not os.path.isdir(tile_dir):
            os.makedirs(tile_dir)
        if kwargs.get('scheme') == 'wms':
            tile = os.path.join(tile_dir,'%03d.%s' % (int(y) % 1000, kwargs.get('format', 'png')))
        else:
            tile = os.path.join(tile_dir,'%s.%s' % (y, kwargs.get('format', 'png')))
        f = open(tile, 'wb')
        f.write(t[3])
        f.close()
        done = done + 1
        for c in msg: sys.stdout.write(chr(8))
        if not silent:
            logger.info('%s / %s tiles exported' % (done, count))
        t = tiles.fetchone()

    # grids
    callback = kwargs.get('callback')
    done = 0
    msg = ''
    try:
        count = con.execute('select count(zoom_level) from grids;').fetchone()[0]
        grids = con.execute('select zoom_level, tile_column, tile_row, grid from grids;')
        g = grids.fetchone()
    except sqlite3.OperationalError:
        g = None # no grids table
    while g:
        zoom_level = g[0] # z
        tile_column = g[1] # x
        y = g[2] # y
        grid_data_cursor = con.execute('''select key_name, key_json FROM
            grid_data WHERE
            zoom_level = %(zoom_level)d and
            tile_column = %(tile_column)d and
            tile_row = %(y)d;''' % locals() )
        if kwargs.get('scheme') == 'xyz':
            y = flip_y(zoom_level,y)
        grid_dir = os.path.join(base_path, str(zoom_level), str(tile_column))
        if not os.path.isdir(grid_dir):
            os.makedirs(grid_dir)
        grid = os.path.join(grid_dir,'%s.grid.json' % (y))
        f = open(grid, 'w')
        grid_json = json.loads(zlib.decompress(g[3]).decode('utf-8'))
        # join up with the grid 'data' which is in pieces when stored in mbtiles file
        grid_data = grid_data_cursor.fetchone()
        data = {}
        while grid_data:
            data[grid_data[0]] = json.loads(grid_data[1])
            grid_data = grid_data_cursor.fetchone()
        grid_json['data'] = data
        if callback in (None, "", "false", "null"):
            f.write(json.dumps(grid_json))
        else:
            f.write('%s(%s);' % (callback, json.dumps(grid_json)))
        f.close()
        done = done + 1
        for c in msg: sys.stdout.write(chr(8))
        if not silent:
            logger.info('%s / %s grids exported' % (done, count))
        g = grids.fetchone()
