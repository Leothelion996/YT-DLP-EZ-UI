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

        # Progress bar row
        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.progress_bar)

        main_layout.addLayout(progress_layout)

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
        # Calculate percentage
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"{current}/{total} - {percentage}%")

        # Update status label
        if url:
            # Truncate long URLs
            display_url = url if len(url) < 60 else url[:57] + "..."
            self.status_label.setText(f"Downloading {current} of {total}: {display_url}")
        else:
            self.status_label.setText(f"Downloading {current} of {total}")

        self.logger.info(f"Progress updated: {current}/{total}")

    def set_complete(self):
        """Set progress to completed state."""
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Complete")
        self.status_label.setText("All downloads completed!")
        self.logger.info("Progress set to complete")

    def reset(self):
        """Reset progress to initial state."""
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0%")
        self.status_label.setText("Downloading...")
        self._log_viewer_visible = False
        self.more_info_button.setText("More Info")
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
