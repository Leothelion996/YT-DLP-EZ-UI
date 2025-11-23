"""
Folder processing options dialog for YT-DLP EZ-UI (v4.0).
Allows users to select processing options for dropped folders.
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QPushButton, QGroupBox
)
from PyQt6.QtCore import Qt


class FolderProcessingOptionsDialog(QDialog):
    """
    Dialog for selecting folder processing options.
    Shown before processing a dropped folder.
    """

    def __init__(self, parent=None):
        """
        Initialize the folder processing options dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Folder Processing Options")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(
            "Select the processing options for the audio files in this folder:"
        )
        header_label.setWordWrap(True)
        header_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(header_label)

        # Options group
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)

        # Checkbox options
        self.clean_file_names_checkbox = QCheckBox("Clean file names (remove special characters)")
        self.clean_file_names_checkbox.setChecked(True)
        self.clean_file_names_checkbox.setToolTip("Remove special characters from file names")
        options_layout.addWidget(self.clean_file_names_checkbox)

        self.clean_folder_names_checkbox = QCheckBox("Clean folder names (album names only)")
        self.clean_folder_names_checkbox.setChecked(True)
        self.clean_folder_names_checkbox.setToolTip("Simplify folder names to album names")
        options_layout.addWidget(self.clean_folder_names_checkbox)

        self.update_track_checkbox = QCheckBox("Update track metadata")
        self.update_track_checkbox.setChecked(True)
        self.update_track_checkbox.setToolTip("Update track title metadata")
        options_layout.addWidget(self.update_track_checkbox)

        self.update_artist_checkbox = QCheckBox("Update artist metadata")
        self.update_artist_checkbox.setChecked(True)
        self.update_artist_checkbox.setToolTip("Update artist metadata")
        options_layout.addWidget(self.update_artist_checkbox)

        self.update_album_checkbox = QCheckBox("Update album metadata")
        self.update_album_checkbox.setChecked(True)
        self.update_album_checkbox.setToolTip("Update album metadata")
        options_layout.addWidget(self.update_album_checkbox)

        layout.addWidget(options_group)

        # Note
        note_label = QLabel(
            "Note: Original files will remain unchanged. "
            "Only approved files with changes will be copied to the selected output location."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666; font-size: 9pt; padding: 8px; background-color: #f0f0f0; border-radius: 4px;")
        layout.addWidget(note_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        process_button = QPushButton("Process")
        process_button.setMinimumWidth(100)
        process_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        process_button.clicked.connect(self.accept)
        button_layout.addWidget(process_button)

        layout.addLayout(button_layout)

    def get_options(self) -> dict:
        """
        Get the selected processing options.

        Returns:
            dict: Processing options
        """
        return {
            'clean_file_names': self.clean_file_names_checkbox.isChecked(),
            'clean_folder_names': self.clean_folder_names_checkbox.isChecked(),
            'update_track': self.update_track_checkbox.isChecked(),
            'update_artist': self.update_artist_checkbox.isChecked(),
            'update_album': self.update_album_checkbox.isChecked()
        }
