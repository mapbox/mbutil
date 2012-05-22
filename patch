#!/usr/bin/env bash

# Usage:
#
# $ patch [source] [dest]
#
# Inserts all tiles from [source] into [dest], replacing any old tiles
# in [dest].

SOURCE=$1
DEST=$2

if [ -z "$SOURCE" ] || [ -z "$DEST" ]; then
    echo "Usage: merge [source] [dest]"
    exit 1
fi

if [ ! -f $SOURCE ]; then
    echo "File '$SOURCE' does not exist."
    exit 1
fi

if [ ! -f $DEST ]; then
    echo "File '$DEST' does not exist."
    exit 1
fi

echo "Patch $SOURCE => $DEST ..."

echo "
PRAGMA journal_mode=PERSIST;
PRAGMA page_size=80000;
PRAGMA synchronous=OFF;
ATTACH DATABASE '$1' AS source;
REPLACE INTO map SELECT * FROM source.map;
REPLACE INTO images SELECT * FROM source.images;"\
| sqlite3 $2
