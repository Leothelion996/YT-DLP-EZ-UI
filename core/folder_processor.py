"""
Folder processor for YT-DLP EZ-UI (v4.0).
Processes existing audio files through fingerprinting without downloading.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Callable
from threading import Thread, Lock
from PyQt6.QtCore import QObject, pyqtSignal

from core.acoustid_tagger import AcoustIDTagger


class FolderProcessor(QObject):
    """
    Processes folders of existing audio files through AcoustID fingerprinting.
    Copies approved files to user-selected output location.
    """

    # Signals
    processing_complete_signal = pyqtSignal(bool, str, object)  # success, error_msg, results
    processing_progress_signal = pyqtSignal(str)  # progress message

    def __init__(self):
        """Initialize the folder processor."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()
        self._is_processing = False
        self.current_folder: Optional[Path] = None  # v5.0: Track current folder for metadata editor loading

    def process_folder(
        self,
        folder_path: Path,
        api_key: str,
        progress_callback: Optional[Callable] = None
    ) -> None:
        """
        Process a folder of audio files (fingerprint and tag).
        Runs in background thread.

        Args:
            folder_path: Path to folder containing audio files
            api_key: AcoustID API key for fingerprinting
            progress_callback: Optional callback for progress updates
        """
        with self._lock:
            if self._is_processing:
                self.logger.warning("Already processing a folder")
                self.processing_complete_signal.emit(
                    False,
                    "Already processing another folder",
                    None
                )
                return

            self._is_processing = True
            self.current_folder = folder_path  # v5.0: Store current folder for metadata editor

        # Start processing in background thread
        thread = Thread(
            target=self._process_worker,
            args=(folder_path, api_key, progress_callback),
            daemon=True
        )
        thread.start()

    def _process_worker(
        self,
        folder_path: Path,
        api_key: str,
        progress_callback: Optional[Callable]
    ) -> None:
        """
        Worker thread for processing folder.

        Args:
            folder_path: Path to folder
            api_key: AcoustID API key
            progress_callback: Progress callback
        """
        try:
            self.logger.info(f"Starting folder processing: {folder_path}")

            # Validate folder exists
            if not folder_path.exists() or not folder_path.is_dir():
                raise Exception(f"Invalid folder path: {folder_path}")

            # Create AcoustID tagger
            tagger = AcoustIDTagger(api_key)

            # Process with fingerprinting callback
            def fingerprint_progress(msg: str):
                self.logger.debug(f"Fingerprint progress: {msg}")
                if progress_callback:
                    progress_callback(msg)
                self.processing_progress_signal.emit(msg)

            # Tag the folder (uses folder_list mode, no time filtering)
            success = tagger.tag_directory(
                directory=str(folder_path.parent),
                folder_list=[folder_path],
                progress_callback=fingerprint_progress,
                completion_callback=self._on_fingerprint_complete
            )

            if not success:
                raise Exception("Fingerprinting failed to start")

        except Exception as e:
            self.logger.error(f"Error processing folder: {e}")
            with self._lock:
                self._is_processing = False
            self.processing_complete_signal.emit(False, str(e), None)

    def _on_fingerprint_complete(
        self,
        success: bool,
        error_msg: Optional[str],
        results: Optional[List[Dict]]
    ) -> None:
        """
        Handle fingerprinting completion.

        Args:
            success: Whether fingerprinting succeeded
            error_msg: Error message if failed
            results: List of tagging results
        """
        with self._lock:
            self._is_processing = False

        if success:
            self.logger.info(f"Folder processing complete: {len(results) if results else 0} results")
            self.processing_complete_signal.emit(True, "", results)
        else:
            self.logger.error(f"Folder processing failed: {error_msg}")
            self.processing_complete_signal.emit(False, error_msg or "Unknown error", None)

    def copy_approved_files(
        self,
        files: List[Path],
        output_dir: Path,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """
        Copy approved files to output directory.

        Args:
            files: List of file paths to copy
            output_dir: Destination directory
            progress_callback: Optional callback for progress updates

        Returns:
            dict: {'copied': count, 'failed': count}
        """
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        failed = 0

        for file_path in files:
            try:
                dest_path = output_dir / file_path.name

                # Handle name conflicts
                if dest_path.exists():
                    # Add number suffix
                    counter = 1
                    stem = file_path.stem
                    suffix = file_path.suffix
                    while dest_path.exists():
                        dest_path = output_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                # Copy file
                shutil.copy2(file_path, dest_path)
                self.logger.info(f"Copied: {file_path.name} → {dest_path}")
                copied += 1

                if progress_callback:
                    progress_callback(f"Copied: {file_path.name}")

            except Exception as e:
                self.logger.error(f"Failed to copy {file_path.name}: {e}")
                failed += 1

                if progress_callback:
                    progress_callback(f"Failed to copy: {file_path.name}")

        return {'copied': copied, 'failed': failed}

    def is_processing(self) -> bool:
        """
        Check if currently processing.

        Returns:
            bool: True if processing
        """
        with self._lock:
            return self._is_processing
