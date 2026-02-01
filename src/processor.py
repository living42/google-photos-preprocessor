"""Simplified file processor - crashes on any error."""

import os
import time
import shutil
import subprocess
import logging
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple


class PhotoProcessor:
    """Photo processor with Live Photo pair detection and batching."""

    BATCH_SIZE = 100
    MOTIONPHOTO2_TIMEOUT = 3600

    def __init__(
        self,
        source_dir: str,
        target_dir: str,
        db,
        motionphoto2_path: str,
        scan_days: int,
        target_retention_days: int,
        logger=None
    ):
        self.source_dir = Path(source_dir).resolve()
        self.target_dir = Path(target_dir).resolve()
        self.db = db
        self.motionphoto2_path = motionphoto2_path
        self.scan_days = scan_days
        self.target_retention_days = target_retention_days
        self.logger = logger or logging.getLogger(__name__)

        if not os.path.isfile(self.motionphoto2_path):
            raise FileNotFoundError(f"motionphoto2 binary not found: {self.motionphoto2_path}")
        if not os.access(self.motionphoto2_path, os.X_OK):
            raise PermissionError(f"motionphoto2 binary is not executable: {self.motionphoto2_path}")

        self.logger.info(
            f"PhotoProcessor initialized: scan_days={scan_days}, "
            f"target_retention_days={target_retention_days}"
        )

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
            self.logger.debug(f"Created symlink: {full_path} -> {temp_link}")

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
        """Process files in batches, keeping Live Photo pairs together."""
        if not files:
            return 0

        # Photo extensions and video extensions for Live Photo detection
        photo_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif'}
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp', '.webm', '.mts', '.m2ts'}

        # Group files by basename (filename without extension)
        basename_groups = defaultdict(list)
        for relative_path, full_path in files:
            # Get basename without extension
            path_obj = Path(relative_path)
            basename = path_obj.stem.lower()  # e.g., "IMG_9647" from "IMG_9647.HEIC"
            ext = path_obj.suffix.lower()
            basename_groups[basename].append((relative_path, full_path, ext))

        # Identify Live Photo pairs and single files
        pairs = []  # List of (photo_path, video_path) tuples
        singles = []  # List of (relative_path, full_path) for unpaired files

        for basename, group in basename_groups.items():
            if len(group) == 2:
                # Check if it's a photo+video pair
                ext1, ext2 = group[0][2], group[1][2]
                is_pair = (ext1 in photo_exts and ext2 in video_exts) or (ext1 in video_exts and ext2 in photo_exts)
                if is_pair:
                    # Sort so photo comes first
                    if ext1 in video_exts:
                        group[0], group[1] = group[1], group[0]
                    pairs.append(((group[0][0], group[0][1]), (group[1][0], group[1][1])))
                else:
                    # Same type, treat as singles
                    for item in group:
                        singles.append((item[0], item[1]))
            else:
                # Single file or more than 2 files with same basename
                for item in group:
                    singles.append((item[0], item[1]))

        self.logger.info(f"Found {len(pairs)} Live Photo pairs and {len(singles)} single files")

        # Create batches treating pairs as atomic units
        batches = []
        current_batch = []
        current_batch_count = 0  # Count pairs as 1 unit, singles as 1 unit

        # Add pairs first (process pairs together)
        for photo, video in pairs:
            if current_batch_count >= self.BATCH_SIZE:
                batches.append(current_batch)
                current_batch = []
                current_batch_count = 0
            current_batch.extend([photo, video])
            current_batch_count += 1  # Pair counts as 1 unit

        # Add singles
        for single in singles:
            if current_batch_count >= self.BATCH_SIZE:
                batches.append(current_batch)
                current_batch = []
                current_batch_count = 0
            current_batch.append(single)
            current_batch_count += 1

        # Don't forget the last batch
        if current_batch:
            batches.append(current_batch)

        # Process batches
        processed_count = 0
        total_batches = len(batches)

        for batch_num, batch in enumerate(batches):
            self.logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} files)")

            temp_dir = self.create_temp_symlinks(batch)
            try:
                self.run_motionphoto2(temp_dir)

                batch_paths = []
                for relative_path, _ in batch:
                    batch_paths.append(relative_path)
                    self.logger.info(f"Processed: {relative_path}")

                processed_count += len(batch)
                self.logger.info(f"Batch {batch_num + 1} complete")

                # Record batch to database immediately
                if batch_paths:
                    self.db.add_processed(batch_paths)

            finally:
                self.cleanup_temp_dir(temp_dir)

        # Clean up old target files
        self.cleanup_old_targets()

        return processed_count

    def cleanup_old_targets(self) -> int:
        """Clean up target files and DB records older than retention period.

        For Live Photos, the video file (MOV) won't exist as a separate target
        file since it was merged into the photo. We skip deletion for these.

        Returns number of files cleaned up.
        """
        if self.target_retention_days <= 0:
            self.logger.debug("Target retention disabled (target_retention_days=0)")
            return 0

        self.logger.info(
            f"Cleaning up targets older than {self.target_retention_days} days"
        )

        old_records = self.db.get_old_records(self.target_retention_days)
        if not old_records:
            self.logger.info("No old records to clean up")
            return 0

        self.logger.info(f"Found {len(old_records)} old records to clean up")

        cleaned_paths = []
        deleted_count = 0
        skipped_count = 0

        for relative_path, processed_at in old_records:
            target_path = self.target_dir / relative_path

            if target_path.exists():
                try:
                    target_path.unlink()
                    self.logger.debug(f"Deleted old target file: {target_path}")
                    deleted_count += 1
                except OSError as e:
                    self.logger.warning(
                        f"Failed to delete {target_path}: {e}"
                    )
                    continue
            else:
                # Target doesn't exist - this is expected for Live Photo video files
                # (MOV files get merged into the photo file)
                self.logger.debug(
                    f"Target file not found (may be Live Photo video): {target_path}"
                )
                skipped_count += 1

            cleaned_paths.append(relative_path)

        # Remove records from database
        if cleaned_paths:
            self.db.remove_records(cleaned_paths)

        self.logger.info(
            f"Cleanup complete: {deleted_count} files deleted, "
            f"{skipped_count} skipped (not found), "
            f"{len(cleaned_paths)} records removed from DB"
        )

        return len(cleaned_paths)
