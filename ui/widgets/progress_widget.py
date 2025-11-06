"""
Progress widget for YT-DLP EZ-UI.
Shows download progress with a progress bar and "More Info" button.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, Qt


class ProgressWidget(QWidget):
    """
    Widget displaying download progress.
    Shows progress bar and "More Info" button to toggle log viewer.
    """

    more_info_clicked = pyqtSignal(bool)  # Emits True/False for show/hide

    def __init__(self, parent=None):
        """
        Initialize the progress widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self._log_viewer_visible = False

        self._init_ui()
        self.hide()  # Hidden by default

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 8)
        main_layout.setSpacing(4)

        # Progress info row
        info_layout = QHBoxLayout()

        self.status_label = QLabel("Downloading...")
        self.status_label.setStyleSheet("color: #3e3f40; font-weight: bold;")
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()

        # More Info button
        self.more_info_button = QPushButton("More Info")
        self.more_info_button.setFixedWidth(100)
        self.more_info_button.clicked.connect(self._on_more_info_clicked)
        info_layout.addWidget(self.more_info_button)

        main_layout.addLayout(info_layout)

        # Main progress bar row (URL-level progress)
        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.progress_bar)

        main_layout.addLayout(progress_layout)

        # v3.0: Playlist progress bar (hidden by default, shows only for playlists)
        playlist_layout = QVBoxLayout()
        playlist_layout.setSpacing(2)

        self.playlist_label = QLabel("Playlist Progress:")
        self.playlist_label.setStyleSheet("color: #6c757d; font-size: 11px;")

        self.playlist_progress_bar = QProgressBar()
        self.playlist_progress_bar.setMinimum(0)
        self.playlist_progress_bar.setMaximum(100)
        self.playlist_progress_bar.setValue(0)
        self.playlist_progress_bar.setTextVisible(True)
        self.playlist_progress_bar.setMinimumHeight(20)

        playlist_layout.addWidget(self.playlist_label)
        playlist_layout.addWidget(self.playlist_progress_bar)

        main_layout.addLayout(playlist_layout)

        # Hide playlist progress by default
        self.playlist_label.hide()
        self.playlist_progress_bar.hide()

    def _on_more_info_clicked(self):
        """Handle More Info button click."""
        self._log_viewer_visible = not self._log_viewer_visible

        # Update button text
        if self._log_viewer_visible:
            self.more_info_button.setText("Hide Info")
        else:
            self.more_info_button.setText("More Info")

        # Emit signal
        self.more_info_clicked.emit(self._log_viewer_visible)
        self.logger.info(f"Log viewer visibility toggled: {self._log_viewer_visible}")

    def set_progress(self, current: int, total: int, url: str = ""):
        """
        Update progress display.

        Args:
            current: Current download number (1-indexed)
            total: Total number of downloads
            url: Current URL being downloaded (optional)
        """
        # Calculate percentage based on completed downloads
        # When starting download 1 of 3, show 0% (0 completed)
        # When starting download 2 of 3, show 33% (1 completed)
        # When starting download 3 of 3, show 66% (2 completed)
        # Only shows 100% when all are done via set_complete()
        if total > 0:
            completed = current - 1  # Downloads completed so far
            percentage = int((completed / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{completed}/{total} completed - {percentage}%")

        # Update status label
        if url:
            # Truncate long URLs
            display_url = url if len(url) < 60 else url[:57] + "..."
            self.status_label.setText(f"Downloading {current} of {total}: {display_url}")
        else:
            self.status_label.setText(f"Downloading {current} of {total}")

        self.logger.info(f"Progress updated: {current}/{total}, {completed}/{total} completed")

    def set_complete(self):
        """Set progress to completed state."""
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Complete")
        self.status_label.setText("All downloads completed!")
        self.logger.info("Progress set to complete")

    def set_playlist_progress(self, current: int, total: int):
        """
        Update playlist progress (v3.0).
        Shows playlist progress bar and updates it.

        Args:
            current: Current video number in playlist
            total: Total videos in playlist
        """
        # Show playlist progress elements if hidden
        if not self.playlist_progress_bar.isVisible():
            self.playlist_label.show()
            self.playlist_progress_bar.show()

        # Calculate percentage
        if total > 0:
            percentage = int((current / total) * 100)
            self.playlist_progress_bar.setValue(percentage)
            self.playlist_progress_bar.setFormat(f"{current}/{total} videos - {percentage}%")
        else:
            self.playlist_progress_bar.setValue(0)
            self.playlist_progress_bar.setFormat("0%")

        self.logger.info(f"Playlist progress updated: {current}/{total}")

    def hide_playlist_progress(self):
        """Hide the playlist progress bar (v3.0)."""
        self.playlist_label.hide()
        self.playlist_progress_bar.hide()

    def reset(self):
        """Reset progress to initial state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.status_label.setText("Downloading...")
        self._log_viewer_visible = False
        self.more_info_button.setText("More Info")
        # v3.0: Also reset playlist progress
        self.hide_playlist_progress()
        self.playlist_progress_bar.setValue(0)
        self.logger.info("Progress reset")

    def show_widget(self):
        """Show the progress widget."""
        self.reset()
        self.show()

    def hide_widget(self):
        """Hide the progress widget."""
        self.hide()
        self._log_viewer_visible = False
        self.more_info_clicked.emit(False)  # Ensure log viewer is also hidden
