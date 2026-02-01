#!/usr/bin/env bash
set -xeu

cd "$(dirname "${BASH_SOURCE[0]}")/.."

SOURCE_DIR=${SOURCE_DIR:-./samples}

rm -rf ./output
mkdir ./output

docker run --rm \
    -v "${SOURCE_DIR}":/data/input:ro \
    -v ./output:/data/output:rw \
    -v ./data/progress:/data/progress:rw \
    -e SOURCE_DIR=/data/input \
    -e TARGET_DIR=/data/output \
    -e DB_PATH=/data/progress/progress.db \
    -e RUN_ONCE=true \
    -e LOG_LEVEL=DEBUG \
    google-photos-preprocessor:latest
