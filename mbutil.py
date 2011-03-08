#!/usr/bin/env python
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

def optimize_connection(con):
    con.execute("""PRAGMA synchronous=0""")
    con.execute("""PRAGMA locking_mode=EXCLUSIVE""")
    con.execute("""PRAGMA journal_mode=TRUNCATE""")

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
    con.commit()

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

def compression_finalize(cur, con):
    cur.execute("""drop table tiles;""")
    con.commit()
    cur.execute("""create view tiles as
        select map.zoom_level as zoom_level,
        map.tile_column as tile_column,
        map.tile_row as tile_row,
        images.tile_data as tile_data FROM
        map JOIN images on images.tile_id = map.tile_id;""")
    con.commit()
    cur.execute("""
          CREATE UNIQUE INDEX map_index on map 
            (zoom_level, tile_column, tile_row);""")
    cur.execute("""
          CREATE UNIQUE INDEX images_id on images 
            (tile_id);""")
    cur.execute("""vacuum;""")
    cur.execute("""analyze;""")
    con.commit()

def disk_to_mbtiles(directory_path, mbtiles_file):
    con = mbtiles_connect(mbtiles_file)
    mbtiles_setup(con.cursor())
    con.commit()
    try:
        metadata = json.load(open('%s/metadata.json' % directory_path, 'r'))
        for name, value in metadata.items():
            con.execute('insert into metadata (name, value) values (?, ?)',
                    (name, value))
        con.commit()
    except Exception, e:
        print e
        print 'Metadata file not found. Not inserting metadata'

    # for root, dirs, files in os.walk(directory_path):

def mbtiles_to_disk(mbtiles_file, directory_path):
    con = mbtiles_connect(mbtiles_file)
    cur = con.cursor()
    os.mkdir("%s" % directory_path)
    metadata = dict(con.execute('select name, value from metadata;').fetchall())
    json.dump(metadata, open('%s/metadata.json' % directory_path, 'w'))
    count = con.execute('select count(zoom_level) from tiles;').fetchone()[0]
    chunk = count / 80
    done = 0
    tiles = con.execute('select zoom_level, tile_row, tile_column, tile_data from tiles;')
    t = tiles.fetchone()
    while t:
        if not os.path.isdir("%s/%s/%s/" % (directory_path, t[0], t[1])):
            os.makedirs("%s/%s/%s/" % (directory_path, t[0], t[1]))
        f = open('%s/%s/%s/%s.%s' %
                (directory_path, t[0], t[1], t[2], metadata.get('format', 'png')), 'wb')
        f.write(t[3])
        f.close()
        t = tiles.fetchone()

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-w", "--window", dest="window",
        help="compression window size. larger values faster, dangerouser",
        type="int",
        default=2000)

    (options, args) = parser.parse_args()

    # Transfer operations
    if len(args) == 2:
        if os.path.isfile(args[0]) and not os.path.isdir(args[1]):
            mbtiles_file, directory_path = args
            mbtiles_to_disk(mbtiles_file, directory_path)
        if os.path.isdir(args[0]) and not os.path.isfile(args[0]):
            directory_path, mbtiles_file = args
            disk_to_mbtiles(directory_path, mbtiles_file)
