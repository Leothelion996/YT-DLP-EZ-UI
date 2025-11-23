"""
Main window for YT-DLP EZ-UI.
Central application window that orchestrates all UI components.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStatusBar, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QIcon

from config.settings import SettingsManager
from config.constants import (
    APP_NAME, APP_VERSION,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT
)
from .styles import MAIN_STYLESHEET
from .widgets.link_input import LinkInputWidget
from .widgets.link_list import LinkListWidget
from .widgets.options import OptionsWidget
from .widgets.output_select import OutputSelectWidget
from .widgets.progress_widget import ProgressWidget
from .widgets.log_viewer import LogViewer
from .widgets.beets_options import BeetsOptionsWidget
from .widgets.file_rename_dialog import FileRenameDialog  # v3.0
from .widgets.folder_drop_widget import FolderDropWidget  # v4.0
from .widgets.folder_processing_options_dialog import FolderProcessingOptionsDialog  # v4.0

from core.downloader import DownloadManager
from core.queue_manager import QueueManager
from core.beets_manager import BeetsManager
from core.metadata import MetadataHandler
from core.acoustid_tagger import AcoustIDTagger
from core.album_analyzer import AlbumAnalyzer
from core.folder_processor import FolderProcessor  # v4.0
from utils.track_numberer import TrackNumberer


class MainWindow(QMainWindow):
    """
    Main application window for YT-DLP EZ-UI.
    Manages the overall layout and coordinates between widgets.
    """

    # Thread-safe signals for download events
    download_complete_signal = pyqtSignal()
    download_error_signal = pyqtSignal(str)
    download_progress_signal = pyqtSignal(int, int, str)  # current, total, url
    playlist_progress_signal = pyqtSignal(str)  # playlist progress message
    all_downloads_complete_signal = pyqtSignal(int)  # total count

    # Thread-safe signals for beets processing
    beets_progress_signal = pyqtSignal(str)  # progress message
    beets_complete_signal = pyqtSignal(bool, str, object)  # success, error_msg, results (v3.0: added results)

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.settings = SettingsManager()
        self.download_manager = DownloadManager()
        self.queue_manager = QueueManager()
        self.beets_manager = BeetsManager()
        self.metadata_handler = MetadataHandler()
        self.album_analyzer = AlbumAnalyzer()
        self.folder_processor = FolderProcessor()  # v4.0

        # Track downloaded files for post-processing
        self._downloaded_files = []

        # Download state tracking
        self._current_downloads = []
        self._download_index = 0
        self._download_total = 0
        self._download_errors = []  # Track failed downloads
        self._download_successes = 0  # Track successful downloads
        self._user_cancelled = False  # Track if user requested cancellation
        self._playlist_videos_completed = 0  # Track individual playlist videos completed
        self._playlist_videos_total = 0  # Track total playlist videos expected
        self._last_logged_playlist_video = 0  # Track last logged video to avoid spam
        self._download_session_folders = []  # Track folders created during download session (v3.0)
        self._all_processes_complete = False  # Track if downloads and fingerprinting are fully complete
        self._current_url_is_album = False  # Track if current download is marked as album (v4.0)

        self._init_ui()
        self._connect_signals()
        self._restore_window_state()

        self.logger.info("Main window initialized successfully")

    def _init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        # Apply stylesheet
        self.setStyleSheet(MAIN_STYLESHEET)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title_label = QLabel(f"{APP_NAME}")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #0078d4;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Output directory selector
        self.output_selector = OutputSelectWidget(self.settings)
        main_layout.addWidget(self.output_selector)

        # Options widget (format and quality)
        self.options_widget = OptionsWidget(self.settings)
        main_layout.addWidget(self.options_widget)

        # Beets options widget (music tagging)
        self.beets_options_widget = BeetsOptionsWidget(self.settings, self.beets_manager)
        main_layout.addWidget(self.beets_options_widget)

        # Link input widget
        self.link_input = LinkInputWidget()
        main_layout.addWidget(self.link_input)

        # Link list/queue widget
        self.link_list = LinkListWidget(self.queue_manager, self.settings)
        main_layout.addWidget(self.link_list)

        # v4.0: Folder drop widget for processing existing files
        self.folder_drop_widget = FolderDropWidget()
        main_layout.addWidget(self.folder_drop_widget)

        # Progress widget (hidden by default)
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)

        # Log viewer widget (hidden by default)
        self.log_viewer = LogViewer()
        main_layout.addWidget(self.log_viewer)

        # Download button and controls
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        self.download_button = QPushButton("Start Download")
        self.download_button.setMinimumSize(QSize(150, 40))
        self.download_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 24px;
            }
        """)
        controls_layout.addWidget(self.download_button)

        # Cancel button (hidden by default)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumSize(QSize(100, 40))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                background-color: #d13438;
            }
            QPushButton:hover {
                background-color: #b02a2e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.cancel_button.hide()  # Hidden by default
        controls_layout.addWidget(self.cancel_button)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _connect_signals(self):
        """Connect signals and slots."""
        # Link input signals
        self.link_input.link_added.connect(self._on_link_added)
        self.link_input.batch_links_added.connect(self._on_batch_links_added)

        # Download button
        self.download_button.clicked.connect(self._on_download_clicked)

        # Cancel button
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        # Options widget signals
        self.options_widget.format_changed.connect(self._on_format_changed)

        # Beets options widget signals
        self.beets_options_widget.beets_enabled_changed.connect(self._on_beets_enabled_changed)

        # v4.0: Folder drop widget signals
        self.folder_drop_widget.process_clicked.connect(self._on_folder_process_clicked)

        # v4.0: Folder processor signals
        self.folder_processor.processing_complete_signal.connect(self._on_folder_processing_complete_safe)
        self.folder_processor.processing_progress_signal.connect(self._on_folder_processing_progress_safe)

        # Set initial beets options visibility based on current format
        current_format = self.options_widget.get_file_format()
        self.beets_options_widget.set_format_visibility(current_format)

        # Thread-safe download signals
        self.download_complete_signal.connect(self._on_download_complete_safe)
        self.download_error_signal.connect(self._on_download_error_safe)
        self.download_progress_signal.connect(self._on_download_progress_safe)
        self.playlist_progress_signal.connect(self._on_playlist_progress_safe)
        self.all_downloads_complete_signal.connect(self._on_all_downloads_complete_safe)

        # Thread-safe beets signals
        self.beets_progress_signal.connect(self._on_beets_progress_safe)
        self.beets_complete_signal.connect(self._on_beets_complete_safe)

        # Progress widget signals
        self.progress_widget.more_info_clicked.connect(self.log_viewer.toggle_visibility)

    def _on_link_added(self, url: str):
        """
        Handle single link addition.

        Args:
            url: The YouTube URL to add
        """
        try:
            success = self.queue_manager.add_url(url)
            if success:
                self.link_list.refresh()
                self.status_bar.showMessage(f"Added: {url}", 3000)
                self.logger.info(f"Link added to queue: {url}")
            else:
                self.status_bar.showMessage("Invalid YouTube URL", 3000)
                QMessageBox.warning(
                    self,
                    "Invalid URL",
                    "The provided URL is not a valid YouTube link."
                )
        except Exception as e:
            self.logger.error(f"Error adding link: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add link: {str(e)}")

    def _on_batch_links_added(self, urls: list):
        """
        Handle batch link addition.

        Args:
            urls: List of YouTube URLs
        """
        try:
            added_count = 0
            for url in urls:
                if self.queue_manager.add_url(url):
                    added_count += 1

            self.link_list.refresh()
            self.status_bar.showMessage(f"Added {added_count} link(s)", 3000)
            self.logger.info(f"Batch added {added_count} links")

            if added_count < len(urls):
                QMessageBox.warning(
                    self,
                    "Partial Success",
                    f"Added {added_count} out of {len(urls)} links.\n"
                    f"{len(urls) - added_count} invalid URLs were skipped."
                )
        except Exception as e:
            self.logger.error(f"Error adding batch links: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add links: {str(e)}")

    def _on_download_clicked(self):
        """Handle download button click."""
        # Check if queue is empty
        if self.queue_manager.is_empty():
            QMessageBox.information(
                self,
                "No Links",
                "Please add at least one YouTube link to download."
            )
            return

        # Get settings
        output_dir = self.output_selector.get_selected_directory()
        file_format = self.options_widget.get_file_format()
        quality = self.options_widget.get_quality()

        # Start downloads
        self._start_downloads(output_dir, file_format, quality)

    def _start_downloads(self, output_dir: str, file_format: str, quality: str):
        """
        Start downloading all queued links.

        Args:
            output_dir: Output directory path
            file_format: 'video' or 'audio'
            quality: Quality string
        """
        try:
            urls = self.queue_manager.get_all_urls()

            # Store download state
            self._current_downloads = [(url, output_dir, file_format, quality) for url in urls]
            self._download_index = 0
            self._download_total = len(urls)
            self._download_errors = []  # Reset error tracking
            self._download_successes = 0  # Reset success count
            self._user_cancelled = False  # Reset cancellation flag
            self._playlist_videos_completed = 0  # Reset playlist video counter
            self._playlist_videos_total = 0  # Reset playlist total
            self._all_processes_complete = False  # Reset completion flag for new session
            self._last_logged_playlist_video = 0  # Reset last logged video
            self._download_session_folders = []  # Reset folder tracking for new session (v3.0)

            # Reset download manager cancellation flag
            self.download_manager.reset_cancel()

            self.download_button.setEnabled(False)
            self.cancel_button.show()  # Show cancel button
            self.cancel_button.setEnabled(True)  # Enable cancel
            self.status_bar.showMessage(f"Downloading {len(urls)} item(s)...")

            # Show progress widget
            self.progress_widget.show_widget()
            self.log_viewer.clear_log()
            self.log_viewer.append_log(f"Starting download of {len(urls)} item(s)...")

            # Start first download (will chain to others via signals)
            self._download_next()

        except Exception as e:
            self.logger.error(f"Error starting downloads: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start downloads: {str(e)}")
            self.download_button.setEnabled(True)

    def _download_next(self):
        """
        Download the next URL in the queue (called from main thread).
        """
        # Check if user cancelled - stop processing queue
        if self._user_cancelled:
            self.logger.info("User cancelled - stopping download queue")
            self.all_downloads_complete_signal.emit(self._download_total)
            return

        if self._download_index >= len(self._current_downloads):
            # All downloads complete - emit signal
            self.all_downloads_complete_signal.emit(self._download_total)
            return

        url, output_dir, file_format, quality = self._current_downloads[self._download_index]

        # v4.0: Check if this URL is marked as an album
        self._current_url_is_album = self.queue_manager.get_album_status(url)
        if self._current_url_is_album:
            self.logger.info(f"URL marked as album: {url}")

        # Update progress signal
        self.download_progress_signal.emit(
            self._download_index + 1,
            self._download_total,
            url
        )

        # Thread-safe callbacks that emit signals
        def on_complete(folder_path):
            """Handle download completion and track created folder path."""
            # Track the folder created during this download (v3.0)
            if folder_path and folder_path not in self._download_session_folders:
                self._download_session_folders.append(folder_path)
                self.logger.info(f"Tracked folder for fingerprinting: {folder_path}")

            self.download_complete_signal.emit()

        def on_error(error_msg):
            self.download_error_signal.emit(error_msg)

        # Track if we've logged the start of this download
        download_started_logged = {'logged': False}

        def on_progress(progress_dict):
            """Handle progress updates from yt-dlp."""
            # Log when download actually starts (first progress callback)
            if not download_started_logged['logged']:
                download_started_logged['logged'] = True
                self.playlist_progress_signal.emit(f"[{self._download_index + 1}/{self._download_total}] Starting download: {url}")

            # Extract playlist information if available
            # yt-dlp provides playlist data in info_dict (primary source)
            info_dict = progress_dict.get('info_dict', {})
            playlist_index = info_dict.get('playlist_index')
            playlist_count = info_dict.get('n_entries') or info_dict.get('playlist_count')

            # Fallback to top-level keys (from YtDlpLogger synthetic dict)
            if not playlist_index:
                playlist_index = progress_dict.get('playlist_index')
            if not playlist_count:
                playlist_count = progress_dict.get('playlist_count')

            # Debug logging when playlist data is missing
            if not (playlist_index and playlist_count):
                available_keys = list(progress_dict.keys())
                info_dict_keys = list(info_dict.keys()) if info_dict else []
                self.logger.debug(f"Playlist data not found. progress_dict keys: {available_keys}, info_dict keys: {info_dict_keys}")

            if playlist_index and playlist_count:
                # It's a playlist - track total count
                if self._playlist_videos_total == 0:
                    self._playlist_videos_total = playlist_count
                    # Reset the counter for this new playlist
                    self._last_logged_playlist_video = 0
                    # Emit signal to log to UI
                    self.playlist_progress_signal.emit(f"Starting playlist download: {playlist_count} videos total")
                elif playlist_count != self._playlist_videos_total:
                    # Different playlist detected (count changed), reset counter
                    self._playlist_videos_total = playlist_count
                    self._last_logged_playlist_video = 0
                    self.playlist_progress_signal.emit(f"Starting playlist download: {playlist_count} videos total")

                # v3.0: Update playlist progress bar
                self.progress_widget.set_playlist_progress(playlist_index, playlist_count)

                # Check status
                status = progress_dict.get('status', '')

                # Try to get video title from multiple possible sources
                video_title = info_dict.get('title') if info_dict else None
                if not video_title:
                    filename = progress_dict.get('filename', '')
                    if filename:
                        video_title = Path(filename).stem
                if not video_title:
                    video_title = f"Video {playlist_index}"

                if status == 'downloading':
                    # Only log when a NEW video starts (avoid spam from progress updates)
                    if playlist_index > self._last_logged_playlist_video:
                        self._last_logged_playlist_video = playlist_index
                        msg = f"[Playlist {playlist_index}/{playlist_count}] Downloading: {video_title}"
                        self.playlist_progress_signal.emit(msg)
                elif status == 'finished':
                    # NOTE: 'finished' means download finished, but FFmpeg post-processing may still be running
                    # Don't log "Completed" here - it's premature and confusing
                    # Just update the progress bar silently
                    self._playlist_videos_completed += 1
                    # v3.0: Update playlist progress bar on completion too
                    self.progress_widget.set_playlist_progress(playlist_index, playlist_count)

        # Start async download
        self.download_manager.download_async(
            url=url,
            output_dir=output_dir,
            file_format=file_format,
            quality=quality,
            progress_callback=on_progress,
            completion_callback=on_complete,
            error_callback=on_error
        )

    def _on_format_changed(self, file_format: str):
        """
        Handle file format change.

        Args:
            file_format: New file format ('video' or 'audio')
        """
        self.logger.info(f"File format changed to: {file_format}")

        # Show/hide beets options based on format (only show for audio)
        self.beets_options_widget.set_format_visibility(file_format)

        # Refresh link list to show/hide album checkboxes based on format
        self.link_list.refresh()

    def _on_beets_enabled_changed(self, enabled: bool):
        """
        Handle beets tagging enable/disable.

        Args:
            enabled: True if beets is enabled, False otherwise
        """
        self.logger.info(f"Beets music tagging {'enabled' if enabled else 'disabled'}")

    def _on_beets_progress_safe(self, message: str):
        """
        Handle beets progress update safely in main thread.
        Also updates the fingerprinting progress bar.

        Args:
            message: Progress message from beets (format: "Fingerprinting {i}/{total}: {filename}")
        """
        self.log_viewer.append_log(f"[Beets] {message}")

        # Parse progress message to update fingerprint progress bar
        # Message format: "Fingerprinting 1/10: filename.mp3"
        if message.startswith("Fingerprinting "):
            try:
                # Extract "1/10" from "Fingerprinting 1/10: filename.mp3"
                parts = message.split(":")
                if len(parts) >= 2:
                    progress_part = parts[0].replace("Fingerprinting ", "").strip()
                    if "/" in progress_part:
                        current, total = progress_part.split("/")
                        self.progress_widget.set_fingerprint_progress(int(current), int(total))
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Failed to parse fingerprint progress: {message}, error: {e}")

    def _on_beets_complete_safe(self, success: bool, error_msg: str, results: Optional[List[Dict]] = None):
        """
        Handle beets completion safely in main thread.
        v3.0: Now shows file rename dialog after successful tagging.
        v3.1: Sets track numbers based on creation time after tagging.

        Args:
            success: True if processing succeeded
            error_msg: Error message if failed (empty string if success)
            results: List of tagging results (v3.0)
        """
        # Mark fingerprinting as complete in progress bar
        self.progress_widget.set_fingerprint_complete()

        # Mark all processes as complete (downloads + fingerprinting done)
        self._all_processes_complete = True

        if success:
            self.log_viewer.append_log("[Beets] Processing complete!")
            self.status_bar.showMessage("Music tagging complete", 5000)

            # v3.1: Set track numbers for each downloaded folder
            if self._download_session_folders:
                self.log_viewer.append_log("\n=== Setting track numbers based on creation time ===")
                self._set_track_numbers_for_session_folders()

            # v3.0: Show file rename dialog if we have successful results
            if results:
                # Filter successful results only, AND exclude files with missing metadata
                successful_files = [
                    {
                        'path': Path(r['file']),
                        'title': r.get('title', 'UNKNOWN'),
                        'artist': r.get('artist', 'UNKNOWN'),
                        'album': r.get('album', 'UNKNOWN')
                    }
                    for r in results
                    if r.get('success', False)
                    and r.get('title')
                    and r.get('title') not in ['UNKNOWN', 'Unknown', '']
                ]

                # v4.0: Apply album consensus metadata if marked as album
                if successful_files and self._current_url_is_album:
                    self.log_viewer.append_log("\n=== Analyzing album metadata ===")
                    consensus_album = self.album_analyzer.analyze_album_metadata(successful_files)

                    if consensus_album:
                        self.log_viewer.append_log(f"[Album] Consensus album name: '{consensus_album}'")
                        # Apply consensus album to all files
                        successful_files = self.album_analyzer.apply_consensus_album(successful_files, consensus_album)
                        self.log_viewer.append_log(f"[Album] Applied consensus album to {len(successful_files)} files")
                    else:
                        self.log_viewer.append_log("[Album] No consensus album found")

                if successful_files:
                    self.logger.info(f"Showing rename dialog for {len(successful_files)} successfully tagged files")
                    self._show_rename_dialog(successful_files)
                else:
                    self.logger.info("No successfully tagged files to rename")
            else:
                self.logger.info("No results provided from tagging")

        else:
            self.log_viewer.append_log(f"[Beets] ERROR: {error_msg}")
            self.status_bar.showMessage("Music tagging failed", 5000)
            QMessageBox.warning(
                self,
                "Beets Processing Failed",
                f"Music fingerprinting encountered an error:\n\n{error_msg}"
            )

    def _set_track_numbers_for_session_folders(self) -> None:
        """
        Set track numbers for all folders downloaded in this session (v3.1).
        Track numbers are set based on file creation time (oldest = track 1).
        """
        try:
            track_numberer = TrackNumberer()

            if not track_numberer.is_available():
                self.logger.warning("TrackNumberer not available (Mutagen missing)")
                self.log_viewer.append_log("[Track Numbers] Skipping - Mutagen not available")
                return

            total_updated = 0
            total_failed = 0

            for folder in self._download_session_folders:
                self.log_viewer.append_log(f"[Track Numbers] Processing folder: {folder.name}")

                result = track_numberer.number_tracks(
                    folder=folder,
                    progress_callback=lambda msg: self.log_viewer.append_log(f"[Track Numbers] {msg}")
                )

                if result['success']:
                    total_updated += result['updated']
                    total_failed += result['failed']
                    self.log_viewer.append_log(
                        f"[Track Numbers] {folder.name}: {result['updated']} updated, {result['failed']} failed"
                    )
                else:
                    error = result.get('error', 'Unknown error')
                    self.log_viewer.append_log(f"[Track Numbers] ERROR in {folder.name}: {error}")

            # Summary
            if total_updated > 0:
                self.log_viewer.append_log(
                    f"[Track Numbers] Complete: {total_updated} files updated across {len(self._download_session_folders)} folder(s)"
                )
                self.logger.info(f"Track numbers set: {total_updated} files updated, {total_failed} failed")
            else:
                self.log_viewer.append_log("[Track Numbers] No track numbers were set")

        except Exception as e:
            self.logger.error(f"Error setting track numbers: {e}")
            self.log_viewer.append_log(f"[Track Numbers] ERROR: {e}")

    def _show_rename_dialog(self, tagged_files: List[Dict]):
        """
        Show file rename dialog after successful tagging (v3.0).

        Args:
            tagged_files: List of dicts with 'path', 'title', 'artist' keys
        """
        try:
            dialog = FileRenameDialog(tagged_files, parent=self)
            dialog.exec()  # Show as modal dialog
            self.logger.info("Rename dialog closed")
        except Exception as e:
            self.logger.error(f"Error showing rename dialog: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to show file rename dialog:\n\n{str(e)}"
            )

    # v4.0: Folder processing methods

    def _on_folder_process_clicked(self, folder_path: Path):
        """
        Handle folder process button click (v4.0).

        Args:
            folder_path: Path to folder to process
        """
        try:
            # Show processing options dialog
            options_dialog = FolderProcessingOptionsDialog(parent=self)
            result = options_dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                # Get selected options
                options = options_dialog.get_options()
                self.logger.info(f"Processing folder with options: {options}")

                # Get API key from beets manager
                api_key = self.beets_manager.get_acoustid_key()
                if not api_key:
                    QMessageBox.warning(
                        self,
                        "API Key Missing",
                        "AcoustID API key not configured. Please configure it in Beets Options."
                    )
                    return

                # Start processing
                self.log_viewer.append_log(f"\n=== Processing Folder: {folder_path.name} ===")
                self.folder_drop_widget.set_processing(True)

                # Process folder
                self.folder_processor.process_folder(
                    folder_path=folder_path,
                    api_key=api_key,
                    progress_callback=lambda msg: self.log_viewer.append_log(f"[Folder] {msg}")
                )

        except Exception as e:
            self.logger.error(f"Error processing folder: {e}")
            QMessageBox.critical(
                self,
                "Processing Error",
                f"Failed to process folder:\n\n{str(e)}"
            )
            self.folder_drop_widget.set_processing(False)

    def _on_folder_processing_progress_safe(self, message: str):
        """
        Handle folder processing progress updates (v4.0).

        Args:
            message: Progress message
        """
        self.log_viewer.append_log(f"[Folder] {message}")

    def _on_folder_processing_complete_safe(
        self,
        success: bool,
        error_msg: str,
        results: Optional[List[Dict]]
    ):
        """
        Handle folder processing completion (v4.0).

        Args:
            success: Whether processing succeeded
            error_msg: Error message if failed
            results: List of tagging results
        """
        self.folder_drop_widget.set_processing(False)

        if success:
            self.log_viewer.append_log("[Folder] Processing complete!")

            # Show rename dialog if we have results
            if results:
                # Filter successful results
                successful_files = [
                    {
                        'path': Path(r['file']),
                        'title': r.get('title', 'UNKNOWN'),
                        'artist': r.get('artist', 'UNKNOWN'),
                        'album': r.get('album', 'UNKNOWN')
                    }
                    for r in results
                    if r.get('success', False)
                    and r.get('title')
                    and r.get('title') not in ['UNKNOWN', 'Unknown', '']
                ]

                if successful_files:
                    self.logger.info(f"Showing rename dialog for {len(successful_files)} files")
                    self._show_rename_dialog(successful_files)
                else:
                    self.logger.info("No successfully tagged files to rename")
                    QMessageBox.information(
                        self,
                        "No Results",
                        "No files were successfully tagged. No metadata changes available."
                    )
            else:
                self.logger.info("No results from folder processing")
                QMessageBox.information(
                    self,
                    "No Results",
                    "No results were returned from processing."
                )

        else:
            self.log_viewer.append_log(f"[Folder] ERROR: {error_msg}")
            QMessageBox.warning(
                self,
                "Processing Failed",
                f"Folder processing encountered an error:\n\n{error_msg}"
            )

    # Thread-safe slot methods (called in main thread via signals)

    def _on_download_complete_safe(self):
        """
        Handle download completion safely in main thread.
        """
        self.logger.info(f"Download {self._download_index + 1} completed")

        # Track success
        self._download_successes += 1

        # Log success
        self.log_viewer.append_log(f"[{self._download_index + 1}/{self._download_total}] Download completed successfully!")

        # Reset playlist counters for next download
        self._playlist_videos_total = 0
        self._last_logged_playlist_video = 0
        self._playlist_videos_completed = 0

        self._download_index += 1
        # Continue with next download
        self._download_next()

    def _on_download_error_safe(self, error_msg: str):
        """
        Handle download error safely in main thread.

        Args:
            error_msg: Error message from download
        """
        self.logger.error(f"Download {self._download_index + 1} failed: {error_msg}")

        # Track error
        if self._download_index < len(self._current_downloads):
            url = self._current_downloads[self._download_index][0]
            self._download_errors.append((url, error_msg))

        # Log error
        self.log_viewer.append_log(f"[{self._download_index + 1}/{self._download_total}] ERROR: {error_msg}")

        self._download_index += 1
        # Continue with next download even if this one failed
        self._download_next()

    def _on_download_progress_safe(self, current: int, total: int, url: str):
        """
        Handle download progress update safely in main thread.

        Args:
            current: Current download number
            total: Total downloads
            url: Current URL being downloaded
        """
        self.status_bar.showMessage(f"Downloading {current}/{total}: {url}")
        self.logger.info(f"Progress: {current}/{total} - {url}")

        # Update progress widget
        self.progress_widget.set_progress(current, total, url)

        # Highlight current download in queue list
        self.link_list.highlight_url(url)

        # Note: Don't log "Starting download" here - it will be logged by yt-dlp progress callback
        # when the download actually begins

    def _on_playlist_progress_safe(self, message: str):
        """
        Handle playlist progress update safely in main thread.

        Args:
            message: Playlist progress message
        """
        # Log playlist progress
        self.log_viewer.append_log(message)

    def _on_all_downloads_complete_safe(self, total: int):
        """
        Handle all downloads completion safely in main thread.

        Args:
            total: Total number of downloads completed
        """
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)  # Disable cancel (downloads done)
        self.cancel_button.setText("Cancel")  # Reset text

        # Check if user cancelled
        if self._user_cancelled:
            self.status_bar.showMessage("Downloads cancelled by user", 5000)
            self.log_viewer.append_log(f"\n=== Downloads cancelled - {self._download_successes} succeeded before cancellation ===")
        else:
            self.status_bar.showMessage("All downloads completed!", 5000)

        self.queue_manager.clear()
        self.link_list.refresh()

        # Update progress widget
        self.progress_widget.set_complete()

        # Check if there were any errors
        error_count = len(self._download_errors)
        success_count = self._download_successes

        # Handle different completion scenarios
        if self._user_cancelled:
            # User cancelled - build appropriate message
            if self._playlist_videos_total > 0:
                # Was downloading a playlist
                msg = (f"Downloads cancelled by user.\n\n"
                       f"{success_count} URL(s) completed before cancellation.\n"
                       f"{self._playlist_videos_completed} out of {self._playlist_videos_total} playlist videos downloaded.")
            else:
                # Regular downloads
                msg = f"Downloads cancelled by user.\n\n{success_count} item(s) completed before cancellation."

            QMessageBox.information(
                self,
                "Cancelled",
                msg
            )
        elif error_count > 0:
            # Some downloads failed - but still process successful ones
            self.log_viewer.append_log(f"\n=== Downloads completed with {error_count} error(s), {success_count} succeeded ===")

            # Apply basic metadata and fingerprinting for successfully downloaded files
            file_format = self.settings.get("file_format", "video")
            if file_format == "audio" and success_count > 0:
                self.log_viewer.append_log("\n=== Applying basic metadata from YouTube ===")
                self._apply_basic_metadata()

                # Trigger beets processing if enabled and format is audio
                if self._should_run_beets_processing():
                    self.log_viewer.append_log("\n=== Beets is enabled, starting advanced tagging ===")
                    self._run_beets_processing()
                elif self.beets_options_widget.beets_checkbox.isChecked():
                    # Checkbox is checked but not configured
                    self.log_viewer.append_log("\n[Info] Beets checkbox is checked but AcoustID API key not configured. Only basic metadata applied.")

            # Show error summary after processing
            self._show_error_summary(total, success_count, error_count)
        else:
            # All successful
            self.log_viewer.append_log(f"\n=== All {total} downloads completed successfully! ===")

            # Apply basic metadata for audio files (always runs)
            file_format = self.settings.get("file_format", "video")
            if file_format == "audio":
                self.log_viewer.append_log("\n=== Applying basic metadata from YouTube ===")
                self._apply_basic_metadata()

            # Trigger beets processing if enabled and format is audio
            if self._should_run_beets_processing():
                self.log_viewer.append_log("\n=== Beets is enabled, starting advanced tagging ===")
                self._run_beets_processing()
            elif self.beets_options_widget.beets_checkbox.isChecked() and file_format == "audio":
                # Checkbox is checked but not configured
                self.log_viewer.append_log("\n[Info] Beets checkbox is checked but AcoustID API key not configured. Only basic metadata applied.")

            QMessageBox.information(
                self,
                "Success",
                f"Downloaded {total} item(s) successfully!"
            )

        # Hide cancel button after user dismisses dialog
        # Keep progress widget visible for fingerprinting progress
        self.cancel_button.hide()

        # If beets is not running, mark all processes as complete
        if not self._should_run_beets_processing():
            self._all_processes_complete = True

        self.logger.info(f"Downloads complete: {success_count} succeeded, {error_count} failed, cancelled: {self._user_cancelled}")

    def _show_error_summary(self, total: int, success_count: int, error_count: int):
        """
        Show error summary dialog with scrollable error details.

        Args:
            total: Total downloads attempted
            success_count: Number of successful downloads
            error_count: Number of failed downloads
        """
        from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QPushButton, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Download Summary")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout(dialog)

        # Summary label
        summary_label = QLabel(f"Completed: {success_count}/{total} successful, {error_count}/{total} failed")
        summary_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        layout.addWidget(summary_label)

        # Error details header
        error_header = QLabel("Failed Downloads:")
        error_header.setStyleSheet("font-size: 12px; font-weight: bold; color: #ff6b6b; margin-top: 10px;")
        layout.addWidget(error_header)

        # Scrollable error details
        error_text = QTextEdit()
        error_text.setReadOnly(True)
        error_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)

        # Build error message
        error_details = ""
        for idx, (url, error_msg) in enumerate(self._download_errors, 1):
            error_details += f"[{idx}] {url}\n"
            error_details += f"    ERROR: {error_msg}\n\n"

        error_text.setPlainText(error_details)
        layout.addWidget(error_text)

        # OK button
        ok_button = QPushButton("OK")
        ok_button.setMinimumHeight(35)
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        dialog.exec()

    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        self.logger.warning("Cancel requested by user")

        # Set cancellation flags
        self._user_cancelled = True
        self.download_manager.cancel_all()

        # Update UI immediately
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.status_bar.showMessage("Cancelling downloads...")
        self.log_viewer.append_log("\n=== CANCELLATION REQUESTED BY USER ===")

        # The current download will abort via the cancellable_progress_callback
        # and the _download_next will skip remaining downloads

    def _restore_window_state(self):
        """Restore window size and position from settings."""
        try:
            window_size = self.settings.get("last_window_size")
            if window_size and len(window_size) == 2:
                self.resize(window_size[0], window_size[1])

            window_pos = self.settings.get("last_window_position")
            if window_pos and len(window_pos) == 2:
                self.move(window_pos[0], window_pos[1])
        except Exception as e:
            self.logger.warning(f"Could not restore window state: {e}")

    def _apply_basic_metadata(self) -> None:
        """
        Apply basic YouTube metadata to downloaded audio files.
        This runs for ALL audio downloads, independent of Beets.

        NOTE: This is a simplified implementation that applies basic YouTube metadata.
        For playlists, yt-dlp already embeds basic metadata during download.
        This method is primarily a fallback and should not re-process all files.
        """
        try:
            # yt-dlp now configured with FFmpegMetadata postprocessor
            # Metadata (title, artist, album) is embedded during download automatically
            # For enhanced metadata (MusicBrainz, album art, etc.), Beets processing runs separately
            self.log_viewer.append_log("[Metadata] YouTube metadata embedded by yt-dlp during download")
            self.logger.info("Basic metadata handled by yt-dlp FFmpegMetadata postprocessor")
            return

        except Exception as e:
            self.logger.error(f"Error in metadata processing: {e}")

    def _should_run_beets_processing(self) -> bool:
        """
        Check if beets processing should run after downloads.

        Returns:
            bool: True if beets should process downloaded files
        """
        # Only run if beets is enabled
        if not self.beets_options_widget.is_enabled():
            return False

        # Only run for audio downloads
        file_format = self.settings.get("file_format", "video")
        if file_format != "audio":
            self.logger.info("Skipping beets processing (not audio format)")
            return False

        return True

    def _run_beets_processing(self) -> None:
        """
        Run in-place fingerprinting and tagging on downloaded audio files.
        Tags files directly in the download folder - does NOT move them.
        v3.0: Now uses folder tracking instead of time-based filtering.
        """
        try:
            # Get download directory
            download_dir = self.settings.get("download_directory")
            if not download_dir:
                self.logger.warning("No download directory set")
                return

            # Get API key from beets manager
            api_key = self.beets_manager.get_acoustid_key()
            if not api_key:
                self.logger.error("No AcoustID API key found")
                self.log_viewer.append_log("[Tagging] ERROR: AcoustID API key not configured")
                return

            self.log_viewer.append_log("\n=== Starting music fingerprinting and tagging ===")

            # v3.0: Log folder tracking information
            if self._download_session_folders:
                self.log_viewer.append_log(f"[Tagging] Processing {len(self._download_session_folders)} folder(s) from this session")
                for folder in self._download_session_folders:
                    self.log_viewer.append_log(f"  - {folder.name}")
            else:
                self.log_viewer.append_log("[Tagging] No folders tracked, processing entire download directory")

            self.log_viewer.append_log("[Tagging] Tagging files IN-PLACE in download folder")
            self.status_bar.showMessage("Fingerprinting and tagging audio files...")

            # Create in-place tagger
            tagger = AcoustIDTagger(api_key)

            if not tagger.is_available():
                error = "AcoustID or Mutagen not installed"
                self.logger.error(error)
                self.log_viewer.append_log(f"[Tagging] ERROR: {error}")
                return

            # Define callbacks that emit signals (thread-safe)
            def on_progress(message: str):
                self.beets_progress_signal.emit(message)

            def on_complete(success: bool, error_msg: Optional[str], results: Optional[List[Dict]] = None):
                """v3.0: Now includes results for rename dialog."""
                self.beets_complete_signal.emit(success, error_msg or "", results)

            # Start tagging with folder list (v3.0)
            # If folders are tracked, process only those; otherwise fall back to directory scan
            success = tagger.tag_directory(
                directory=download_dir,
                progress_callback=on_progress,
                completion_callback=on_complete,
                folder_list=self._download_session_folders if self._download_session_folders else None
            )

            if not success:
                self.logger.warning("Failed to start fingerprinting")

        except Exception as e:
            self.logger.error(f"Error running fingerprinting: {e}")
            self.log_viewer.append_log(f"[Tagging] ERROR: {e}")

    def mousePressEvent(self, event):
        """
        Handle mouse press events on the main window.
        Hides progress widget after all processes complete when user clicks anywhere.

        Args:
            event: Mouse press event
        """
        # If all processes are complete and progress widget is visible, hide it
        if self._all_processes_complete and self.progress_widget.isVisible():
            self.progress_widget.hide_widget()
            self._all_processes_complete = False  # Reset flag for next download session
            self.logger.info("Progress widget hidden after completion (user clicked)")

        # Call parent implementation to ensure normal event handling
        super().mousePressEvent(event)

    def closeEvent(self, event):
        """
        Handle window close event.

        Args:
            event: Close event
        """
        try:
            # Save window state
            self.settings.set("last_window_size", [self.width(), self.height()], save=False)
            self.settings.set("last_window_position", [self.x(), self.y()], save=True)

            self.logger.info("Application closing")
            event.accept()
        except Exception as e:
            self.logger.error(f"Error during close: {e}")
            event.accept()
