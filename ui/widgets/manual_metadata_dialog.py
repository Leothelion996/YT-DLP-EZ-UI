"""
Manual metadata entry dialog for YT-DLP EZ-UI.
Allows users to manually enter title and artist for files with incorrect metadata.
"""

import logging
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt


class ManualMetadataDialog(QDialog):
    """
    Dialog for manually entering file metadata (title and artist).
    Appears when user unchecks a file in the rename dialog.
    """

    def __init__(self, original_filename: str, parent=None):
        """
        Initialize the manual metadata dialog.

        Args:
            original_filename: The original filename to display
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.original_filename = original_filename
        self.title_input = None
        self.artist_input = None
        self.done_button = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Manual Metadata Entry")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Original filename section (selectable and copyable)
        filename_label = QLabel("Original Filename:")
        filename_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(filename_label)

        self.filename_display = QLabel(self.original_filename)
        self.filename_display.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.filename_display.setWordWrap(True)
        self.filename_display.setStyleSheet(
            "padding: 8px; "
            "background-color: #f0f0f0; "
            "border: 1px solid #ccc; "
            "border-radius: 0px; "
            "color: #000000;"
        )
        layout.addWidget(self.filename_display)

        # Instruction text
        instruction_label = QLabel(
            "Enter the correct metadata for this file. "
            "You can highlight and copy text from the filename above."
        )
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(instruction_label)

        # Title input
        title_label = QLabel("Title:")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter song title...")
        self.title_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                color: #000000;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.title_input)

        # Artist input
        artist_label = QLabel("Artist:")
        artist_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(artist_label)

        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Enter artist name...")
        self.artist_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                color: #000000;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.artist_input)

        # Add spacer
        layout.addSpacing(10)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        button_layout.addWidget(self.cancel_button)

        self.done_button = QPushButton("Done")
        self.done_button.setMinimumWidth(100)
        self.done_button.setEnabled(False)  # Initially disabled
        self.done_button.setStyleSheet(
            "QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        button_layout.addWidget(self.done_button)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect signals and slots."""
        # Monitor text changes to enable/disable Done button
        self.title_input.textChanged.connect(self._on_text_changed)
        self.artist_input.textChanged.connect(self._on_text_changed)

        # Button clicks
        self.cancel_button.clicked.connect(self.reject)
        self.done_button.clicked.connect(self._on_done_clicked)

    def _on_text_changed(self):
        """
        Handle text input changes.
        Enable Done button only if at least one field has text.
        """
        title_text = self.title_input.text().strip()
        artist_text = self.artist_input.text().strip()

        # Enable Done button if at least one field has content
        has_content = len(title_text) > 0 or len(artist_text) > 0
        self.done_button.setEnabled(has_content)

    def _on_done_clicked(self):
        """
        Handle Done button click.
        Validate and sanitize input before accepting.
        """
        try:
            # Get input values
            title = self.title_input.text().strip()
            artist = self.artist_input.text().strip()

            # Track if any replacements were made
            replacements_made = False
            original_title = title
            original_artist = artist

            # Sanitize title (replace invalid filename characters)
            if title:
                title, title_replaced = self._sanitize_filename(title)
                if title_replaced:
                    replacements_made = True

            # Sanitize artist (replace invalid filename characters)
            if artist:
                artist, artist_replaced = self._sanitize_filename(artist)
                if artist_replaced:
                    replacements_made = True

            # Show warning if replacements were made
            if replacements_made:
                QMessageBox.warning(
                    self,
                    "Invalid Characters Replaced",
                    f"Some invalid filename characters were replaced with dashes:\n\n"
                    f"Original Title: {original_title}\n"
                    f"Sanitized Title: {title}\n\n"
                    f"Original Artist: {original_artist}\n"
                    f"Sanitized Artist: {artist}\n\n"
                    f"The sanitized values will be used.",
                    QMessageBox.StandardButton.Ok
                )

            # Store the sanitized values
            self.title_input.setText(title)
            self.artist_input.setText(artist)

            # Accept the dialog
            self.accept()
            self.logger.info(f"Manual metadata entered - Title: '{title}', Artist: '{artist}'")

        except Exception as e:
            self.logger.error(f"Error processing manual metadata: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while processing the metadata:\n{str(e)}\n\n"
                "Please try again or contact support if the problem persists."
            )

    def _sanitize_filename(self, text: str) -> tuple[str, bool]:
        """
        Sanitize text for use in filenames by replacing invalid characters.

        Args:
            text: Input text to sanitize

        Returns:
            tuple: (sanitized_text, replacements_made)
        """
        # Invalid filename characters: < > : " / \ | ? *
        invalid_chars_pattern = r'[<>:"/\\|?*]'

        # Check if any invalid characters exist
        replacements_made = bool(re.search(invalid_chars_pattern, text))

        # Replace invalid characters with dash
        sanitized = re.sub(invalid_chars_pattern, '-', text)

        return sanitized, replacements_made

    def get_metadata(self) -> dict:
        """
        Get the entered metadata.

        Returns:
            dict: {'title': str, 'artist': str}
        """
        return {
            'title': self.title_input.text().strip(),
            'artist': self.artist_input.text().strip()
        }
