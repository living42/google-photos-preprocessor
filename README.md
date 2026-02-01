# Google Photos Preprocessor

A solution to sync iPhone Live Photos to Google Photos via a Pixel phone.

## The Problem

iPhone Live Photos are incompatible with Google Photos. When uploaded directly, they split into separate photo and video files, breaking the Live Photo experience.

## The Solution

This tool converts iPhone Live Photos into a format that Google Photos recognizes, allowing seamless syncing through a Pixel phone.

## Workflow

```
iPhone → NAS → Preprocessor → Pixel Phone → Google Photos
```

1. **iPhone uploads to NAS**: Use PhotoSync or similar to auto-upload Live Photos to your NAS
2. **Preprocessor runs**: Converts Live Photos to Google Photos-compatible format, and places files in another directory so your library is not modified
3. **Pixel Phone downloads files**: Downloads processed photos/videos from the output folder
4. **Google Photos uploads**: Pixel automatically uploads everything to your library

## Quick Start

> **Note:** Steps 1 and 2 can be skipped if you already have your iPhone and Pixel sync set up and working.

### 1. Configure iPhone PhotoSync

Set up PhotoSync to auto-upload to `/path/to/nas/photos` on your NAS.

### 2. Configure Pixel Sync

Install **FolderSync** on your Pixel and configure it to sync `/path/to/nas/pixel/sync` folder to your phone's local storage.

### 3. Create docker-compose.yml

```yaml
services:
  preprocessor:
    image: ghcr.io/living42/google-photos-preprocessor:latest
    volumes:
      - /path/to/nas/photos:/data/source:ro     # iPhone uploads here
      - /path/to/nas/pixel/sync:/data/output:rw     # Pixel reads from here
      - ./data:/data/progress:rw                # Database
    environment:
      - SOURCE_DIR=/data/source
      - TARGET_DIR=/data/output
      - DB_PATH=/data/progress/progress.db
      - RUN_ONCE=false                          # Run continuously
      - SCHEDULE_TIME=02:00                     # Process at 2 AM
```

#### Environment Variables

All configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_DIR` | `/data/source` | Directory containing iPhone photos to process |
| `TARGET_DIR` | `/data/output` | Directory where processed photos are saved |
| `DB_PATH` | `/data/progress/progress.db` | SQLite database path for tracking processed files |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `RUN_ONCE` | `true` | Exit after single run if `true`, otherwise runs continuously |
| `SCAN_DAYS` | `30` | Number of days to look back when scanning for new files. Set to `0` to scan the entire library |
| `TARGET_RETENTION_DAYS` | `30` | Days to keep processed files in target directory. Files older than this are deleted. Disabled when `SCAN_DAYS=0`. Must be ≤ `SCAN_DAYS` |

### 4. Start the Preprocessor

#### Initial Setup: Process Your Entire Library

For the first run, you may want to process your entire photo library (not just recent files). Use this command to scan and convert all photos:

```bash
docker compose run --rm -e RUN_ONCE=true -e SCAN_DAYS=0 preprocessor /entrypoint.sh
```

This will:
- Scan your entire photo library (`SCAN_DAYS=0`)
- Run once and exit (`RUN_ONCE=true`)
- Process all Live Photos found in the source directory

#### Run Continuously

After the initial run, start the service to automatically process new photos on a schedule:

```bash
docker compose up -d
```

## What It Does

- **Converts Live Photos**: Combines iPhone photo + video into Google Photos-compatible format
- **Preserves metadata**: Keeps timestamps, location data, and other photo info
- **Skips duplicates**: Won't re-process already handled photos
- **Runs automatically**: Scheduled daily processing

## Requirements

- NAS with Docker support
- iPhone with auto-upload app (PhotoSync)
- Pixel phone with FolderSync and Google Photos installed

## Credits

This project uses [MotionPhoto2](https://github.com/PetrVys/MotionPhoto2) by PetrVys to convert iPhone Live Photos to Google Photos-compatible format.
