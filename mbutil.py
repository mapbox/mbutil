#!/usr/bin/env python

# MBUtil: a tool for MBTiles files
# Supports importing, exporting, and more
# 
# (c) Development Seed 2011
# Licensed under BSD

import sqlite3, uuid, sys, logging, time, os, json
from optparse import OptionParser

logging.basicConfig(level=logging.DEBUG)

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
        print "Could not connect to database"
        print e
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
    print 'analyzing db'
    cur.execute("""ANALYZE;""")
    print 'cleaning db'
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
        print "select: %s" % (time.time() - start)
        rows = cur.fetchall()
        for r in rows:
            total = total + 1
            if r[3] in files:
                overlapping = overlapping + 1
                start = time.time()
                query = """insert into map 
                    (zoom_level, tile_column, tile_row, tile_id) 
                    values (?, ?, ?, ?)"""
                print "insert: %s" % (time.time() - start)
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
                print "insert into images: %s" % (time.time() - start)
                start = time.time()
                query = """insert into map 
                    (zoom_level, tile_column, tile_row, tile_id) 
                    values (?, ?, ?, ?)"""
                cur.execute(query, (r[0], r[1], r[2], id))
                print "insert into map: %s" % (time.time() - start)
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
    print "Importing disk to MBTiles"
    print "%s --> %s" % (directory_path, mbtiles_file)
    con = mbtiles_connect(mbtiles_file)
    cur = con.cursor()
    optimize_connection(cur)
    mbtiles_setup(cur)
    try:
        metadata = json.load(open('%s/metadata.json' % directory_path, 'r'))
        for name, value in metadata.items():
            cur.execute('insert into metadata (name, value) values (?, ?)',
                    (name, value))
        print 'metadata from metadata.json restored'
    except Exception, e:
        print e
        print 'metadata.json not found'

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
                                tile_row, tile_column, tile_data) values
                                (?, ?, ?, ?);""",
                                (z, x, y, sqlite3.Binary(f.read())))
                            f.close()
                            count = count + 1
                            if (count % 100) == 0:
                                for c in msg: sys.stdout.write(chr(8))
                                msg = "%s tiles inserted (%d tiles/sec)" % (count, count / (time.time() - start_time))
                                sys.stdout.write(msg)
    print 'tiles inserted.'
    optimize_database(con)

def mbtiles_to_disk(mbtiles_file, directory_path):
    print "Exporting MBTiles to disk"
    print "%s --> %s" % (mbtiles_file, directory_path)
    con = mbtiles_connect(mbtiles_file)
    cur = con.cursor()
    os.mkdir("%s" % directory_path)
    metadata = dict(con.execute('select name, value from metadata;').fetchall())
    json.dump(metadata, open('%s/metadata.json' % directory_path, 'w'))
    count = con.execute('select count(zoom_level) from tiles;').fetchone()[0]
    done = 0
    msg ='' 
    tiles = con.execute('select zoom_level, tile_row, tile_column, tile_data from tiles;')
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
        msg = '%s / %s tiles exported' % (done, count)
        sys.stdout.write(msg)
        t = tiles.fetchone()

if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [options] input output")
    parser.add_option('-w', '--window', dest='window',
        help='compression window size. larger values faster, dangerouser',
        type='int',
        default=2000)

    (options, args) = parser.parse_args()

    # Transfer operations
    if len(args) == 2:
        if os.path.isfile(args[0]) and not os.path.exists(args[1]):
            mbtiles_file, directory_path = args
            mbtiles_to_disk(mbtiles_file, directory_path)
        if os.path.isfile(args[0]) and os.path.exists(args[1]):
            sys.stderr.write('To export MBTiles to disk, specify a directory that does not yet exist\n')
            sys.exit(1)
        if os.path.isdir(args[0]) and not os.path.isfile(args[0]):
            directory_path, mbtiles_file = args
            disk_to_mbtiles(directory_path, mbtiles_file)
        if os.path.isdir(args[0]) and os.path.isfile(args[1]):
            sys.stderr.write('Importing tiles into already-existing MBTiles is not yet supported\n')
            sys.exit(1)
    else:
        parser.print_help()
