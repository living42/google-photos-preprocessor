"""Simplified file processor - crashes on any error."""

import os
import time
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple


class PhotoProcessor:
    """Simplified processor - no live photo detection, crashes on errors."""

    BATCH_SIZE = 100
    MOTIONPHOTO2_TIMEOUT = 3600

    def __init__(
        self,
        source_dir: str,
        target_dir: str,
        db,
        motionphoto2_path: str,
        scan_days: int,
        logger=None
    ):
        self.source_dir = Path(source_dir).resolve()
        self.target_dir = Path(target_dir).resolve()
        self.db = db
        self.motionphoto2_path = motionphoto2_path
        self.scan_days = scan_days
        self.logger = logger or logging.getLogger(__name__)

        if not os.path.isfile(self.motionphoto2_path):
            raise FileNotFoundError(f"motionphoto2 binary not found: {self.motionphoto2_path}")
        if not os.access(self.motionphoto2_path, os.X_OK):
            raise PermissionError(f"motionphoto2 binary is not executable: {self.motionphoto2_path}")

        self.logger.info(f"PhotoProcessor initialized: scan_days={scan_days}")

    def scan_source_directory(self) -> List[Tuple[str, str]]:
        """Scan for files and return (relative_path, full_path) for unprocessed files."""
        self.logger.info(f"Starting scan of {self.source_dir}")

        files_to_process = []

        # Common picture and video extensions
        extensions = [
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'heic', 'heif',
            'mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'm4v', '3gp', 'webm', 'mts', 'm2ts'
        ]

        # Build find command with extension filters
        # If scan_days is 0 or less, scan the whole library (no -mtime filter)
        find_cmd = [
            'find', str(self.source_dir),
            '-type', 'f',
        ]
        if self.scan_days > 0:
            find_cmd.extend(['-mtime', f'-{self.scan_days}'])

        # Add extension filters (case insensitive)
        ext_filters = []
        for ext in extensions:
            if not ext_filters:
                ext_filters.extend(['(', '-iname', f'*.{ext}'])
            else:
                ext_filters.extend(['-o', '-iname', f'*.{ext}'])
        ext_filters.append(')')

        find_cmd.extend(ext_filters)
        find_cmd.append('-print0')

        result = subprocess.run(
            find_cmd,
            capture_output=True,
            text=False,
            timeout=300
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
            raise RuntimeError(f"find command failed: {error_msg}")

        if result.stdout:
            file_paths = [path.decode("utf-8") for path in result.stdout.split(b'\x00')]
            for filepath in file_paths:
                if not filepath:
                    continue
                try:
                    relative_path = os.path.relpath(filepath, self.source_dir)
                except ValueError:
                    continue

                if not self.db.is_processed(relative_path):
                    files_to_process.append((relative_path, filepath))

        self.logger.info(f"Scan complete: {len(files_to_process)} files to process")
        return files_to_process

    def create_temp_symlinks(self, files: List[Tuple[str, str]]) -> str:
        """Create temporary directory with symlinks."""
        timestamp = int(time.time())
        temp_dir = f"/tmp/gp_processor_{timestamp}"
        os.makedirs(temp_dir, exist_ok=True)

        for relative_path, full_path in files:
            temp_subdir = os.path.join(temp_dir, os.path.dirname(relative_path))
            os.makedirs(temp_subdir, exist_ok=True)

            temp_link = os.path.join(temp_dir, relative_path)
            os.symlink(full_path, temp_link)
            self.logger.info(f"Created symlink: {full_path} -> {temp_link}")

        self.logger.debug(f"Created temp directory with {len(files)} symlinks: {temp_dir}")
        return temp_dir

    def run_motionphoto2(self, temp_dir: str) -> str:
        """Execute motionphoto2 - crashes on any error."""
        cmd = [
            self.motionphoto2_path,
            '--input-directory', temp_dir,
            '--output-directory', str(self.target_dir),
            '--exif-match',
            '--copy-unmuxed',
            '--recursive',
        ]

        self.logger.info(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.MOTIONPHOTO2_TIMEOUT
        )

        output = result.stdout + result.stderr

        if result.returncode != 0:
            raise RuntimeError(f"motionphoto2 failed with code {result.returncode}: {output}")

        self.logger.info(f"motionphoto2 completed")
        return output

    def cleanup_temp_dir(self, temp_dir: str) -> None:
        """Remove temporary directory."""
        try:
            shutil.rmtree(temp_dir)
            self.logger.debug(f"Cleaned up temp directory: {temp_dir}")
        except OSError as e:
            raise RuntimeError(f"Failed to cleanup temp directory {temp_dir}: {e}")

    def process_files(self, files: List[Tuple[str, str]]) -> int:
        """Process files in batches - crashes on any error."""
        if not files:
            return 0

        total_batches = (len(files) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        processed_count = 0
        processed_paths = []

        for batch_num in range(total_batches):
            start_idx = batch_num * self.BATCH_SIZE
            end_idx = min(start_idx + self.BATCH_SIZE, len(files))
            batch = files[start_idx:end_idx]

            self.logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} files)")

            temp_dir = self.create_temp_symlinks(batch)
            try:
                self.run_motionphoto2(temp_dir)

                for relative_path, _ in batch:
                    processed_paths.append(relative_path)
                    self.logger.info(f"Processed: {relative_path}")

                processed_count += len(batch)
                self.logger.info(f"Batch {batch_num + 1} complete")

            finally:
                self.cleanup_temp_dir(temp_dir)

        # Record all successfully processed files
        if processed_paths:
            self.db.add_processed(processed_paths)

        return processed_count
