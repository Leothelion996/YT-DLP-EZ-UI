"""
Link input widget for YT-DLP EZ-UI.
Provides URL input with add button and batch parsing support.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from utils.validators import URLValidator


class LinkInputWidget(QWidget):
    """
    Widget for inputting YouTube links.
    Supports single link addition and batch link parsing.
    """

    link_added = pyqtSignal(str)  # Emits single URL
    batch_links_added = pyqtSignal(list)  # Emits list of URLs

    def __init__(self, parent=None):
        """
        Initialize the link input widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.validator = URLValidator()

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        # Group box
        group_box = QGroupBox("Add YouTube Links")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(group_box)

        # Inner layout
        layout = QVBoxLayout(group_box)

        # Input row
        input_layout = QHBoxLayout()

        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here (single or multiple)...")
        input_layout.addWidget(self.url_input, stretch=1)

        # Add button
        self.add_button = QPushButton("+")
        self.add_button.setObjectName("addButton")
        self.add_button.setToolTip("Add link to queue")
        input_layout.addWidget(self.add_button)

        layout.addLayout(input_layout)

        # Help text
        help_label = QLabel(
            "Tip: Paste multiple links separated by commas, newlines, or spaces"
        )
        help_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(help_label)

    def _connect_signals(self):
        """Connect signals and slots."""
        self.add_button.clicked.connect(self._on_add_clicked)
        self.url_input.returnPressed.connect(self._on_add_clicked)

    def _on_add_clicked(self):
        """Handle add button click."""
        text = self.url_input.text().strip()

        if not text:
            return

        # Try to parse as batch first
        urls = self.validator.parse_batch_urls(text)

        if len(urls) == 0:
            # No valid URLs found - provide specific error feedback
            from PyQt6.QtWidgets import QMessageBox

            # Check if it looks like a YouTube URL but is malformed
            if 'youtube.com' in text.lower() or 'youtu.be' in text.lower():
                error_msg = (
                    "Invalid YouTube URL format detected.\n\n"
                    "Common issues:\n"
                    "• Malformed video ID (must be exactly 11 alphanumeric characters)\n"
                    "• Extra characters or slashes in the URL\n"
                    "• Incomplete or corrupted URL\n\n"
                    "Please verify the URL is complete and correctly formatted."
                )
            else:
                error_msg = (
                    "No valid YouTube URLs found in the input.\n\n"
                    "Please enter a valid YouTube video or playlist URL."
                )

            QMessageBox.warning(
                self,
                "Invalid URL",
                error_msg
            )

            self.logger.warning(f"No valid URLs found in input: {text}")
            self.url_input.selectAll()
            return

        elif len(urls) == 1:
            # Single URL
            self.link_added.emit(urls[0])
            self.logger.info(f"Single link added: {urls[0]}")

        else:
            # Multiple URLs
            self.batch_links_added.emit(urls)
            self.logger.info(f"Batch of {len(urls)} links added")

        # Clear input
        self.url_input.clear()

    def get_current_text(self) -> str:
        """
        Get the current input text.

        Returns:
            str: Current input text
        """
        return self.url_input.text()

    def clear(self):
        """Clear the input field."""
        self.url_input.clear()
