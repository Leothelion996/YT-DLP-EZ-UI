"""
Metadata Processor view for BatchRipTagger YT (v5.0).
Contains all widgets related to processing and editing metadata of existing files.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from ui.widgets import OutputSelectWidget, FolderDropWidget, ProgressWidget, LogViewer, MetadataEditorWidget


class MetadataProcessorView(QWidget):
    """
    View containing metadata processing and editing UI components.
    Focuses on working with existing audio files without downloading.
    """

    # Signals to communicate with main window
    folder_process_requested = pyqtSignal(object)  # Folder process clicked (Path)

    def __init__(
        self,
        settings_manager,
        parent=None
    ):
        """
        Initialize the metadata processor view.

        Args:
            settings_manager: Settings manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager

        self._init_ui()
        self.logger.debug("Metadata processor view initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Info label
        info_label = QLabel(
            "<b>Metadata Processor</b><br>"
            "Process and edit metadata for existing audio files in a folder."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 12pt; padding: 10px; color: #0078d4;")
        main_layout.addWidget(info_label)

        # Output directory selector (shared with downloader view)
        self.output_selector = OutputSelectWidget(self.settings)
        main_layout.addWidget(self.output_selector)

        # Folder drop widget for processing existing files
        self.folder_drop_widget = FolderDropWidget()
        main_layout.addWidget(self.folder_drop_widget)

        # Progress widget (hidden by default) - v5.0: Added for fingerprinting progress
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)

        # Log viewer widget (hidden by default) - v5.0: Added for fingerprinting logs
        self.log_viewer = LogViewer()
        main_layout.addWidget(self.log_viewer)

        # Metadata editor widget - v5.0: For viewing and editing file metadata
        self.metadata_editor = MetadataEditorWidget()
        main_layout.addWidget(self.metadata_editor)

    def connect_internal_signals(self):
        """Connect internal widget signals."""
        # Folder drop widget signals
        self.folder_drop_widget.process_clicked.connect(self.folder_process_requested.emit)

        # Progress widget signals - v5.0: Added for log viewer toggle
        self.progress_widget.more_info_clicked.connect(self.log_viewer.toggle_visibility)
