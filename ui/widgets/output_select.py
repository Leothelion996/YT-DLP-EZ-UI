"""
Output directory selection widget for YT-DLP EZ-UI.
Allows users to select where downloaded files will be saved.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from config.settings import SettingsManager
from utils.file_utils import FileUtils


class OutputSelectWidget(QWidget):
    """
    Widget for selecting output directory.
    Displays current directory and provides button to change it.
    """

    directory_changed = pyqtSignal(str)  # Emits new directory path

    def __init__(self, settings: SettingsManager, parent=None):
        """
        Initialize the output selector widget.

        Args:
            settings: Settings manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.settings = settings

        self._init_ui()
        self._load_saved_directory()

    def _init_ui(self):
        """Initialize the user interface."""
        # Group box
        group_box = QGroupBox("Output Directory")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(group_box)

        # Inner layout
        layout = QHBoxLayout(group_box)

        # Directory display
        self.directory_edit = QLineEdit()
        self.directory_edit.setReadOnly(True)
        self.directory_edit.setPlaceholderText("Select output directory...")
        layout.addWidget(self.directory_edit, stretch=1)

        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        layout.addWidget(self.browse_button)

    def _load_saved_directory(self):
        """Load the saved directory from settings."""
        saved_dir = self.settings.download_directory
        if saved_dir and FileUtils.is_valid_directory(saved_dir):
            self.directory_edit.setText(saved_dir)
        else:
            # Use default Downloads folder
            from config.constants import DOWNLOADS_DIR
            self.directory_edit.setText(str(DOWNLOADS_DIR))
            self.settings.download_directory = str(DOWNLOADS_DIR)

    def _on_browse_clicked(self):
        """Handle browse button click."""
        current_dir = self.directory_edit.text() or str(Path.home())

        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if selected_dir:
            self.set_directory(selected_dir)

    def set_directory(self, directory: str):
        """
        Set the output directory.

        Args:
            directory: Directory path to set
        """
        if FileUtils.is_valid_directory(directory):
            self.directory_edit.setText(directory)
            self.settings.download_directory = directory
            self.directory_changed.emit(directory)
            self.logger.info(f"Output directory changed to: {directory}")
        else:
            self.logger.warning(f"Invalid directory: {directory}")

    def get_selected_directory(self) -> str:
        """
        Get the currently selected directory.

        Returns:
            str: Selected directory path
        """
        return self.directory_edit.text()
