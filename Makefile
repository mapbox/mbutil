test/tmp:
	mkdir test/tmp

test/data:
	mkdir test/data
	wget http://mapbox-tilesets.s3.amazonaws.com/mbtiles/World_Glass_1.1.mbtiles.zip -o test/data/World_Glass_1.1.mbtiles.zip
	unzip test/data/World_Glass_1.1.mbtiles.zip
	mv World_Glass_1.1.mbtiles test/data

test/tmp/world_glass:
	time ./mb-util test/data/World_Glass_1.1.mbtiles test/tmp/world_glass

test/tmp/world_glass_out.mbtiles:
	time ./mb-util test/tmp/world_glass test/tmp/world_glass_out.mbtiles

test: test/data test/tmp test/tmp/world_glass test/tmp/world_glass_out.mbtiles
