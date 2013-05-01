import os, shutil
from nose import with_setup
from mbutil import mbtiles_to_disk, disk_to_mbtiles

def clear_data():
    try: shutil.rmtree('test/output')
    except Exception: pass

    try: os.path.mkdir('test/output')
    except Exception: pass

@with_setup(clear_data, clear_data)
def test_mbtiles_to_disk():
    mbtiles_to_disk('test/data/one_tile.mbtiles', 'test/output')
    assert os.path.exists('test/output/0/0/0.png')
    assert os.path.exists('test/output/metadata.json')

@with_setup(clear_data, clear_data)
def test_mbtiles_to_disk_and_back():
    mbtiles_to_disk('test/data/one_tile.mbtiles', 'test/output')
    assert os.path.exists('test/output/0/0/0.png')
    disk_to_mbtiles('test/output/', 'test/output/one.mbtiles')
    assert os.path.exists('test/output/one.mbtiles')

@with_setup(clear_data, clear_data)
def test_utf8grid_mbtiles_to_disk():
    mbtiles_to_disk('test/data/utf8grid.mbtiles', 'test/output')
    assert os.path.exists('test/output/0/0/0.grid.json')
    assert os.path.exists('test/output/0/0/0.png')
    assert os.path.exists('test/output/metadata.json')
