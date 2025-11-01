"""
Main window for YT-DLP EZ-UI.
Central application window that orchestrates all UI components.
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStatusBar, QMessageBox
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

from core.downloader import DownloadManager
from core.queue_manager import QueueManager
from core.beets_manager import BeetsManager
from core.metadata import MetadataHandler
from core.acoustid_tagger import AcoustIDTagger


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
    beets_complete_signal = pyqtSignal(bool, str)  # success, error_msg

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.settings = SettingsManager()
        self.download_manager = DownloadManager()
        self.queue_manager = QueueManager()
        self.beets_manager = BeetsManager()
        self.metadata_handler = MetadataHandler()

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
        self.link_list = LinkListWidget(self.queue_manager)
        main_layout.addWidget(self.link_list)

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
            self._last_logged_playlist_video = 0  # Reset last logged video

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

        # Update progress signal
        self.download_progress_signal.emit(
            self._download_index + 1,
            self._download_total,
            url
        )

        # Thread-safe callbacks that emit signals
        def on_complete():
            self.download_complete_signal.emit()

        def on_error(error_msg):
            self.download_error_signal.emit(error_msg)

        def on_progress(progress_dict):
            """Handle progress updates from yt-dlp."""
            # Extract playlist information if available
            playlist_index = progress_dict.get('playlist_index')
            playlist_count = progress_dict.get('playlist_count')

            if playlist_index and playlist_count:
                # It's a playlist - track total count
                if self._playlist_videos_total == 0:
                    self._playlist_videos_total = playlist_count
                    # Emit signal to log to UI
                    self.playlist_progress_signal.emit(f"Starting playlist download: {playlist_count} videos total")

                # Check status
                status = progress_dict.get('status', '')

                # Try to get video title from multiple possible sources
                video_title = None
                if 'info_dict' in progress_dict:
                    video_title = progress_dict['info_dict'].get('title')
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
                    # Track completed playlist videos
                    self._playlist_videos_completed += 1
                    finish_msg = f"[Playlist {playlist_index}/{playlist_count}] Completed: {video_title}"
                    self.playlist_progress_signal.emit(finish_msg)

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

        Args:
            message: Progress message from beets
        """
        self.log_viewer.append_log(f"[Beets] {message}")

    def _on_beets_complete_safe(self, success: bool, error_msg: str):
        """
        Handle beets completion safely in main thread.

        Args:
            success: True if processing succeeded
            error_msg: Error message if failed (empty string if success)
        """
        if success:
            self.log_viewer.append_log("[Beets] Processing complete!")
            self.status_bar.showMessage("Music tagging complete", 5000)
        else:
            self.log_viewer.append_log(f"[Beets] ERROR: {error_msg}")
            self.status_bar.showMessage("Music tagging failed", 5000)
            QMessageBox.warning(
                self,
                "Beets Processing Failed",
                f"Music fingerprinting encountered an error:\n\n{error_msg}"
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

        # Log to viewer
        self.log_viewer.append_log(f"[{current}/{total}] Starting download: {url}")

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
            # Some downloads failed - show error summary
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

        # Hide cancel and progress widget after user dismisses dialog
        self.cancel_button.hide()
        self.progress_widget.hide_widget()

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

            def on_complete(success: bool, error_msg: Optional[str]):
                self.beets_complete_signal.emit(success, error_msg or "")

            # Start tagging
            success = tagger.tag_directory(
                directory=download_dir,
                progress_callback=on_progress,
                completion_callback=on_complete
            )

            if not success:
                self.logger.warning("Failed to start fingerprinting")

        except Exception as e:
            self.logger.error(f"Error running fingerprinting: {e}")
            self.log_viewer.append_log(f"[Tagging] ERROR: {e}")

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
