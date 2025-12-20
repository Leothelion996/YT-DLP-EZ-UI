"""
Downloader view for BatchRipTagger YT (v5.0).
Contains all widgets related to downloading YouTube videos/playlists.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QSize, pyqtSignal

from ui.widgets import (
    OutputSelectWidget, OptionsWidget, BeetsOptionsWidget,
    LinkInputWidget, LinkListWidget,
    ProgressWidget, LogViewer
)


class DownloaderView(QWidget):
    """
    View containing all download-related UI components.
    This is the default view showing YouTube download functionality.
    """

    # Signals to communicate with main window
    download_requested = pyqtSignal()  # Download button clicked
    cancel_requested = pyqtSignal()  # Cancel button clicked
    format_changed = pyqtSignal(str)  # Format changed
    beets_enabled_changed = pyqtSignal(bool)  # Beets enabled/disabled

    def __init__(
        self,
        settings_manager,
        queue_manager,
        beets_manager,
        parent=None
    ):
        """
        Initialize the downloader view.

        Args:
            settings_manager: Settings manager instance
            queue_manager: Queue manager instance
            beets_manager: Beets manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.settings = settings_manager
        self.queue_manager = queue_manager
        self.beets_manager = beets_manager

        self._init_ui()
        self.logger.debug("Downloader view initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(0, 0, 0, 0)

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
        self.link_list = LinkListWidget(self.queue_manager, self.settings)
        main_layout.addWidget(self.link_list)

        # Progress widget (hidden by default)
        self.progress_widget = ProgressWidget()
        main_layout.addWidget(self.progress_widget)

        # Log viewer widget (hidden by default)
        self.log_viewer = LogViewer()
        main_layout.addWidget(self.log_viewer)

        # Download button and controls
        from PyQt6.QtWidgets import QPushButton
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
        self.download_button.clicked.connect(self.download_requested.emit)
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
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        controls_layout.addWidget(self.cancel_button)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)


    def connect_internal_signals(self):
        """Connect internal widget signals."""
        # Options widget signals
        self.options_widget.format_changed.connect(self.format_changed.emit)

        # Beets options widget signals
        self.beets_options_widget.beets_enabled_changed.connect(self.beets_enabled_changed.emit)

        # Progress widget signals
        self.progress_widget.more_info_clicked.connect(self.log_viewer.toggle_visibility)

        # Set initial beets options visibility based on current format
        current_format = self.options_widget.get_file_format()
        self.beets_options_widget.set_format_visibility(current_format)
