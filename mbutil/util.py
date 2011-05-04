#!/usr/bin/env python

# MBUtil: a tool for MBTiles files
# Supports importing, exporting, and more
# 
# (c) Development Seed 2011
# Licensed under BSD

import sqlite3, uuid, sys, logging, time, os, json

logger = logging.getLogger(__name__)


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
    cur.execute("""create unique index name on metadata (name);""")
    cur.execute("""create unique index tile_index on tiles 
        (zoom_level, tile_column, tile_row);""")

def mbtiles_connect(mbtiles_file):
    try:
        con = sqlite3.connect(mbtiles_file)
        return con
    except Exception, e:
        logger.error("Could not connect to database")
        logger.exception(e)
        sys.exit(1)

def optimize_connection(cur):
    cur.execute("""PRAGMA synchronous=0""")
    cur.execute("""PRAGMA locking_mode=EXCLUSIVE""")
    cur.execute("""PRAGMA journal_mode=TRUNCATE""")

def compression_prepare(cur, con):
    cur.execute("""
      CREATE TABLE if not exists images (
        tile_data blob,
        tile_id VARCHAR(256));
    """)
    cur.execute("""
      CREATE TABLE if not exists map (
        zoom_level integer, 
        tile_column integer, 
        tile_row integer, 
        tile_id VARCHAR(256));
    """)

def optimize_database(cur):
    logger.debug('analyzing db')
    cur.execute("""ANALYZE;""")
    logger.debug('cleaning db')
    cur.execute("""VACUUM;""")

def compression_do(cur, con, chunk):
    overlapping = 0
    unique = 0
    total = 0
    cur.execute("select count(zoom_level) from tiles")
    res = cur.fetchone()
    total_tiles = res[0]
    logging.debug("%d total tiles to fetch" % total_tiles)
    for i in range(total_tiles / chunk):
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
                id = str(uuid.uuid4())
    
                ids.append(id)
                files.append(r[3])

                start = time.time()
                query = """insert into images 
                    (tile_id, tile_data) 
                    values (?, ?)"""
                cur.execute(query, (str(id), sqlite3.Binary(r[3])))
                logger.debug("insert into images: %s" % (time.time() - start))
                start = time.time()
                query = """insert into map 
                    (zoom_level, tile_column, tile_row, tile_id) 
                    values (?, ?, ?, ?)"""
                cur.execute(query, (r[0], r[1], r[2], id))
                logger.debug("insert into map: %s" % (time.time() - start))
        con.commit()

def compression_finalize(cur):
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

def disk_to_mbtiles(directory_path, mbtiles_file):
    logger.info("Importing disk to MBTiles")
    logger.debug("%s --> %s" % (directory_path, mbtiles_file))
    con = mbtiles_connect(mbtiles_file)
    cur = con.cursor()
    optimize_connection(cur)
    mbtiles_setup(cur)
    try:
        metadata = json.load(open('%s/metadata.json' % directory_path, 'r'))
        for name, value in metadata.items():
            cur.execute('insert into metadata (name, value) values (?, ?)',
                    (name, value))
        logger.info('metadata from metadata.json restored')
    except IOError, e:
        logger.warning('metadata.json not found')

    count = 0
    start_time = time.time()
    msg = ""
    for r1, zs, ignore in os.walk(directory_path):
        for z in zs:
            for r2, xs, ignore in os.walk(os.path.join(r1, z)):
                for x in xs:
                    for r2, ignore, ys in os.walk(os.path.join(r1, z, x)):
                        for y in ys:
                            f = open(os.path.join(r1, z, x, y), 'rb')
                            cur.execute("""insert into tiles (zoom_level,
                                tile_column, tile_row, tile_data) values
                                (?, ?, ?, ?);""",
                                (z, x, y.split('.')[0], sqlite3.Binary(f.read())))
                            f.close()
                            count = count + 1
                            if (count % 100) == 0:
                                for c in msg: sys.stdout.write(chr(8))
                                msg = "%s tiles inserted (%d tiles/sec)" % (count, count / (time.time() - start_time))
                                sys.stdout.write(msg)
    logger.debug('tiles inserted.')
    optimize_database(con)

def mbtiles_to_disk(mbtiles_file, directory_path):
    logger.debug("Exporting MBTiles to disk")
    logger.debug("%s --> %s" % (mbtiles_file, directory_path))
    con = mbtiles_connect(mbtiles_file)
    cur = con.cursor()
    os.mkdir("%s" % directory_path)
    metadata = dict(con.execute('select name, value from metadata;').fetchall())
    json.dump(metadata, open('%s/metadata.json' % directory_path, 'w'))
    count = con.execute('select count(zoom_level) from tiles;').fetchone()[0]
    done = 0
    msg ='' 
    tiles = con.execute('select zoom_level, tile_column, tile_row, tile_data from tiles;')
    t = tiles.fetchone()
    while t:
        if not os.path.isdir("%s/%s/%s/" % (directory_path, t[0], t[1])):
            os.makedirs("%s/%s/%s/" % (directory_path, t[0], t[1]))
        f = open('%s/%s/%s/%s.%s' %
                (directory_path, t[0], t[1], t[2], metadata.get('format', 'png')), 'wb')
        f.write(t[3])
        f.close()
        done = done + 1
        for c in msg: sys.stdout.write(chr(8))
        logger.info('%s / %s tiles exported' % (done, count))
        t = tiles.fetchone()

