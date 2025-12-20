"""
CSV processor dialog for BatchRipTagger YT (v5.0).
Allows users to import YouTube links from CSV files.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from utils.csv_validator import CSVValidator


class CSVProcessorDialog(QDialog):
    """
    Dialog for processing CSV files and extracting YouTube links.
    Validates links and shows preview before adding to queue.
    """

    links_validated = pyqtSignal(list)  # Emits list of validated URLs

    def __init__(self, parent=None):
        """
        Initialize the CSV processor dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.validator = CSVValidator()

        self.valid_links = []
        self.rejected_items = []

        self.setWindowTitle("Import CSV Links")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        self._init_ui()

        self.logger.debug("CSV processor dialog initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel(
            "<b>Import YouTube Links from CSV</b><br>"
            "Select a CSV file containing YouTube links. The validator will extract "
            "valid YouTube URLs and filter out invalid entries."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background-color: #e8f4ff; border-radius: 4px;")
        main_layout.addWidget(instructions)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("CSV File:"))

        self.file_path_label = QLabel("<i>No file selected</i>")
        self.file_path_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_path_label, 1)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        file_layout.addWidget(self.browse_button)

        main_layout.addLayout(file_layout)

        # Summary
        self.summary_label = QLabel("Summary: No file processed")
        self.summary_label.setStyleSheet("font-weight: bold; padding: 5px;")
        main_layout.addWidget(self.summary_label)

        # Valid links preview
        valid_group = QGroupBox("Valid YouTube Links")
        valid_layout = QVBoxLayout(valid_group)

        self.valid_links_text = QTextEdit()
        self.valid_links_text.setReadOnly(True)
        self.valid_links_text.setPlaceholderText("Valid YouTube links will appear here...")
        self.valid_links_text.setMaximumHeight(200)
        valid_layout.addWidget(self.valid_links_text)

        main_layout.addWidget(valid_group)

        # Rejected items preview (collapsible)
        rejected_group = QGroupBox("Rejected Items (Click to expand)")
        rejected_group.setCheckable(True)
        rejected_group.setChecked(False)
        rejected_layout = QVBoxLayout(rejected_group)

        self.rejected_items_text = QTextEdit()
        self.rejected_items_text.setReadOnly(True)
        self.rejected_items_text.setPlaceholderText("Rejected items will appear here...")
        self.rejected_items_text.setMaximumHeight(150)
        rejected_layout.addWidget(self.rejected_items_text)

        main_layout.addWidget(rejected_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        self.add_button = QPushButton("Add to Queue")
        self.add_button.setEnabled(False)
        self.add_button.setDefault(True)
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)

        main_layout.addLayout(button_layout)

    def _on_browse_clicked(self):
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )

        if file_path:
            self._process_csv(Path(file_path))

    def _process_csv(self, file_path: Path):
        """
        Process the CSV file and extract links.

        Args:
            file_path: Path to the CSV file
        """
        self.logger.info(f"Processing CSV file: {file_path}")
        self.file_path_label.setText(str(file_path))

        try:
            # Extract and validate links
            self.valid_links, self.rejected_items = self.validator.extract_links_from_csv(file_path)

            # Update summary
            self.summary_label.setText(
                f"Summary: <span style='color: green;'>{len(self.valid_links)} valid links</span>, "
                f"<span style='color: red;'>{len(self.rejected_items)} rejected items</span>"
            )

            # Update valid links preview
            if self.valid_links:
                self.valid_links_text.setPlainText('\n'.join(self.valid_links))
                self.add_button.setEnabled(True)
            else:
                self.valid_links_text.setPlainText("No valid YouTube links found in the CSV file.")
                self.add_button.setEnabled(False)

            # Update rejected items preview
            if self.rejected_items:
                self.rejected_items_text.setPlainText('\n'.join(self.rejected_items))
            else:
                self.rejected_items_text.setPlainText("All items were valid!")

            self.logger.info(f"CSV processing complete: {len(self.valid_links)} valid, {len(self.rejected_items)} rejected")

        except Exception as e:
            self.logger.error(f"Error processing CSV: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to process CSV file:\n{e}"
            )

    def _on_add_clicked(self):
        """Handle add to queue button click."""
        if self.valid_links:
            self.logger.info(f"Adding {len(self.valid_links)} links to queue")
            self.links_validated.emit(self.valid_links)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "No Links",
                "No valid links to add to the queue."
            )
