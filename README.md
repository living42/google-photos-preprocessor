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
2. **Preprocessor runs**: Converts Live Photos to Google Photos-compatible format
3. **Pixel Phone download files**: Downloads processed photos/videos from the output folder
4. **Google Photos uploads**: Pixel automatically uploads everything to your library

## Quick Start

### 1. Create docker-compose.yml

```yaml
services:
  preprocessor:
    image: ghcr.io/living42/google-photos-preprocessor:latest
    volumes:
      - /path/to/nas/photos:/data/source:ro     # iPhone uploads here
      - /path/to/pixel/sync:/data/output:rw     # Pixel reads from here
      - ./data:/data/progress:rw                # Database
    environment:
      - SOURCE_DIR=/data/source
      - TARGET_DIR=/data/output
      - DB_PATH=/data/progress/progress.db
      - RUN_ONCE=false                          # Run continuously
      - SCHEDULE_TIME=02:00                     # Process at 2 AM
```

### 2. Configure iPhone PhotoSync

Set up PhotoSync to auto-upload to `/path/to/nas/photos` on your NAS.

### 3. Configure Pixel Sync

Install **FolderSync** on your Pixel and configure it to sync `/path/to/pixel/sync` folder to your phone's local storage.

### 4. Start

```bash
docker-compose up -d
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
