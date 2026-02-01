# AGENTS.md - Guidelines for AI Coding Agents

## Build Commands

```bash
# Build Docker image
./scripts/build.sh

# Run full test (via Docker)
./scripts/test.sh

# Manual Docker build
docker build -t google-photos-preprocessor:latest .

# Run application (via Docker)
docker run --rm \
    -v ./samples:/data/samples:ro \
    -v ./output:/data/output:rw \
    -v ./data/progress:/data/progress:rw \
    -e SOURCE_DIR=/data/samples \
    -e TARGET_DIR=/data/output \
    -e DB_PATH=/data/progress/progress.db \
    -e RUN_ONCE=true \
    google-photos-preprocessor:latest
```

## Test Commands

There is no formal test suite in this project. Testing is done via Docker:

```bash
# build before run test
./scripts/build.sh
# Run integration test (processes sample files)
./scripts/test.sh

# Clean output directory before testing
rm -rf ./output && mkdir ./output && ./scripts/test.sh
```

## Lint Commands

No linting tools configured. Follow the code style guidelines below.

## Code Style Guidelines

### Python Conventions

- **Python Version**: Python 3.x (Ubuntu 24.04 base)
- **Line Length**: ~100 characters max
- **Indentation**: 4 spaces (no tabs)

## Project Structure

```
src/
  __init__.py          # Package root with version
  main.py              # Entry point and config
  database.py          # SQLite progress tracking
  processor.py         # File processing logic
  scheduler.py         # Daily execution schedule
scripts/
  build.sh             # Docker build script
  test.sh              # Integration test script
docker/
  entrypoint.sh        # Container entrypoint
samples/               # Test input files
output/                # Test output (gitignored)
data/                  # Progress database (gitignored)
```

## Environment Variables

Configuration is via environment variables (see `load_config()` in main.py):

- `SOURCE_DIR` - Source photos directory (default: /data/source)
- `TARGET_DIR` - Output directory (default: /data/output)
- `DB_PATH` - SQLite database path (default: /data/progress/progress.db)
- `SCHEDULE_TIME` - Daily run time, HH:MM (default: 01:00)
- `LOG_LEVEL` - Logging level (default: INFO)
- `RUN_ONCE` - Exit after single run if true (default: false)
- `SCAN_DAYS` - Days to look back when scanning (default: 30, set to 0 to scan entire library)
- `DB_RETENTION_DAYS` - Days to keep DB records (default: 90)
