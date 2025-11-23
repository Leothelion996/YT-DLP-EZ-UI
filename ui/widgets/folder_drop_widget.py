"""
Folder drop widget for YT-DLP EZ-UI (v4.0).
Allows users to drag and drop folders for processing through fingerprinting.
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent


class FolderDropWidget(QWidget):
    """
    Widget for dragging and dropping folders to process existing audio files.
    Shows dropped folder path and provides processing options.
    """

    folder_dropped = pyqtSignal(Path)  # Emits folder path when dropped
    process_clicked = pyqtSignal(Path)  # Emits folder path when process button clicked

    def __init__(self, parent=None):
        """
        Initialize the folder drop widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.current_folder = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        # Group box
        group_box = QGroupBox("Process Existing Folder")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(group_box)

        # Inner layout
        layout = QVBoxLayout(group_box)

        # Instruction label
        instruction_label = QLabel(
            "Drag and drop a folder here to process audio files through fingerprinting,\n"
            "or click 'Browse' to select a folder."
        )
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("color: #888; font-size: 10pt;")
        layout.addWidget(instruction_label)

        # Drop zone
        self.drop_zone = QLabel("Drop Folder Here")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setMinimumHeight(80)
        self.drop_zone.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 8px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 12pt;
                font-weight: bold;
            }
        """)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.dragEnterEvent = self._on_drag_enter
        self.drop_zone.dropEvent = self._on_drop
        self.drop_zone.dragLeaveEvent = self._on_drag_leave
        layout.addWidget(self.drop_zone)

        # Folder path display
        folder_path_layout = QHBoxLayout()
        folder_path_label = QLabel("Selected Folder:")
        folder_path_label.setStyleSheet("font-weight: bold;")
        folder_path_layout.addWidget(folder_path_label)

        self.folder_path_display = QLabel("None")
        self.folder_path_display.setStyleSheet("color: #666;")
        self.folder_path_display.setWordWrap(True)
        folder_path_layout.addWidget(self.folder_path_display, 1)

        layout.addLayout(folder_path_layout)

        # Buttons
        button_layout = QHBoxLayout()

        # Browse button
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setMinimumWidth(100)
        self.browse_button.clicked.connect(self._on_browse_clicked)
        button_layout.addWidget(self.browse_button)

        button_layout.addStretch()

        # Process button
        self.process_button = QPushButton("Process Folder")
        self.process_button.setMinimumWidth(150)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
        """)
        self.process_button.clicked.connect(self._on_process_clicked)
        button_layout.addWidget(self.process_button)

        layout.addLayout(button_layout)

        self.logger.info("Folder drop widget initialized")

    def _on_drag_enter(self, event: QDragEnterEvent):
        """
        Handle drag enter event.

        Args:
            event: Drag enter event
        """
        if event.mimeData().hasUrls():
            # Check if any URL is a directory
            urls = event.mimeData().urls()
            if urls and Path(urls[0].toLocalFile()).is_dir():
                event.acceptProposedAction()
                # Highlight drop zone
                self.drop_zone.setStyleSheet("""
                    QLabel {
                        border: 2px dashed #4CAF50;
                        border-radius: 8px;
                        background-color: #e8f5e9;
                        color: #2E7D32;
                        font-size: 12pt;
                        font-weight: bold;
                    }
                """)
        else:
            event.ignore()

    def _on_drag_leave(self, event):
        """
        Handle drag leave event (reset drop zone appearance).

        Args:
            event: Drag leave event
        """
        # Reset drop zone style
        self.drop_zone.setStyleSheet("""
            QLabel {
                border: 2px dashed #888;
                border-radius: 8px;
                background-color: #f5f5f5;
                color: #666;
                font-size: 12pt;
                font-weight: bold;
            }
        """)

    def _on_drop(self, event: QDropEvent):
        """
        Handle drop event.

        Args:
            event: Drop event
        """
        urls = event.mimeData().urls()
        if urls:
            folder_path = Path(urls[0].toLocalFile())
            if folder_path.is_dir():
                self.set_folder(folder_path)
                self.folder_dropped.emit(folder_path)
            else:
                self.logger.warning(f"Dropped item is not a folder: {folder_path}")

        # Reset drop zone style
        self._on_drag_leave(None)

    def _on_browse_clicked(self):
        """Handle browse button click."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Process",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if folder_path:
            folder_path = Path(folder_path)
            self.set_folder(folder_path)
            self.folder_dropped.emit(folder_path)

    def _on_process_clicked(self):
        """Handle process button click."""
        if self.current_folder:
            self.logger.info(f"Processing folder: {self.current_folder}")
            self.process_clicked.emit(self.current_folder)

    def set_folder(self, folder_path: Path):
        """
        Set the current folder path.

        Args:
            folder_path: Path to folder
        """
        self.current_folder = folder_path
        self.folder_path_display.setText(str(folder_path))
        self.process_button.setEnabled(True)
        self.logger.info(f"Folder selected: {folder_path}")

    def clear_folder(self):
        """Clear the current folder selection."""
        self.current_folder = None
        self.folder_path_display.setText("None")
        self.process_button.setEnabled(False)
        self.logger.info("Folder selection cleared")

    def set_processing(self, is_processing: bool):
        """
        Enable/disable widget during processing.

        Args:
            is_processing: True if processing is active
        """
        self.process_button.setEnabled(not is_processing and self.current_folder is not None)
        self.browse_button.setEnabled(not is_processing)
        self.drop_zone.setEnabled(not is_processing)
