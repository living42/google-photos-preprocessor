"""Main entry point - simplified version."""

import os
import sys
import logging
from pathlib import Path

from src.database import ProgressDatabase
from src.processor import PhotoProcessor


def main() -> int:
    config = load_config()
    logger = setup_logging(config['log_level'])
    
    run_processor(config, logger)
    
    if config['run_once']:
        logger.info("RUN_ONCE enabled, exiting")
    else:
        logger.info("SCHEDULER MODE: Not implemented in simplified version")
    
    return 0


def load_config():
    config = {
        'source_dir': os.getenv('SOURCE_DIR', '/data/source'),
        'target_dir': os.getenv('TARGET_DIR', '/data/output'),
        'db_path': os.getenv('DB_PATH', '/data/progress/progress.db'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'motionphoto2_path': os.getenv('MOTIONPHOTO2_PATH', '/usr/local/bin/motionphoto2'),
        'run_once': os.getenv('RUN_ONCE', 'true').lower() == 'true',
        'scan_days': int(os.getenv('SCAN_DAYS', '30')),
        'target_retention_days': int(os.getenv('TARGET_RETENTION_DAYS', '30')),
    }

    if not Path(config['source_dir']).exists():
        raise FileNotFoundError(f"Source directory does not exist: {config['source_dir']}")

    # If scanning entire library (SCAN_DAYS=0), disable cleanup
    if config['scan_days'] == 0:
        config['target_retention_days'] = 0
    # Validate retention days cannot exceed scan days (when scan_days > 0)
    elif config['target_retention_days'] > config['scan_days']:
        raise ValueError(
            f"TARGET_RETENTION_DAYS ({config['target_retention_days']}) "
            f"cannot exceed SCAN_DAYS ({config['scan_days']}). "
            f"This prevents cleaning files that might be re-scanned."
        )

    Path(config['target_dir']).mkdir(parents=True, exist_ok=True)
    Path(config['db_path']).parent.mkdir(parents=True, exist_ok=True)

    return config


def setup_logging(log_level: str) -> logging.Logger:
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logger = logging.getLogger('gp_preprocessor')
    logger.setLevel(level)
    return logger


def run_processor(config, logger) -> None:
    logger.info("=" * 60)
    logger.info("Google Photos Preprocessor - Starting run")
    logger.info("=" * 60)
    
    logger.info(f"Source: {config['source_dir']}")
    logger.info(f"Target: {config['target_dir']}")
    logger.info(f"Database: {config['db_path']}")
    logger.info(f"Scan window: {config['scan_days']} days")
    logger.info(f"Target retention: {config['target_retention_days']} days")
    
    db = ProgressDatabase(
        db_path=config['db_path'],
        logger=logger
    )
    
    processor = PhotoProcessor(
        source_dir=config['source_dir'],
        target_dir=config['target_dir'],
        db=db,
        motionphoto2_path=config['motionphoto2_path'],
        scan_days=config['scan_days'],
        target_retention_days=config['target_retention_days'],
        logger=logger
    )
    
    files_to_process = processor.scan_source_directory()
    
    if not files_to_process:
        logger.info("No new or modified files to process")
    else:
        logger.info(f"Processing {len(files_to_process)} files...")
        processed_count = processor.process_files(files_to_process)
        logger.info(f"Processing complete: {processed_count} files")
    
    logger.info(f"Total processed files in DB: {db.get_count()}")
    logger.info("=" * 60)
    logger.info("Run complete")
    logger.info("=" * 60)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
