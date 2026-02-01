#!/bin/bash
set -e

# Ensure directories exist
mkdir -p "$TARGET_DIR"
mkdir -p "$(dirname "$DB_PATH")"

# Validate source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "ERROR: Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

# Run the processor
exec python3 -m src.main
