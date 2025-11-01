"""
Options widget for YT-DLP EZ-UI.
Provides context-aware format and quality selection.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QComboBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from config.settings import SettingsManager
from config.constants import VIDEO_RESOLUTIONS, AUDIO_BITRATES, FILE_FORMATS


class OptionsWidget(QWidget):
    """
    Widget for selecting download format and quality.
    Quality options change dynamically based on format selection.
    """

    format_changed = pyqtSignal(str)  # Emits 'video' or 'audio'
    quality_changed = pyqtSignal(str)  # Emits quality string

    def __init__(self, settings: SettingsManager, parent=None):
        """
        Initialize the options widget.

        Args:
            settings: Settings manager instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.settings = settings

        self._init_ui()
        self._load_saved_settings()
        self._connect_signals()

    def _init_ui(self):
        """Initialize the user interface."""
        # Group box
        group_box = QGroupBox("Download Options")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(group_box)

        # Inner layout
        layout = QHBoxLayout(group_box)

        # File format selection
        format_layout = QVBoxLayout()
        format_label = QLabel("Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(list(FILE_FORMATS.keys()))
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Quality selection
        quality_layout = QVBoxLayout()
        self.quality_label = QLabel("Quality:")
        self.quality_combo = QComboBox()
        quality_layout.addWidget(self.quality_label)
        quality_layout.addWidget(self.quality_combo)
        layout.addLayout(quality_layout)

        layout.addStretch()

    def _connect_signals(self):
        """Connect signals and slots."""
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)

    def _load_saved_settings(self):
        """Load saved format and quality settings."""
        # Load file format
        saved_format = self.settings.file_format
        if saved_format == 'video':
            self.format_combo.setCurrentText("Video")
        else:
            self.format_combo.setCurrentText("Audio Only")

        # Update quality options based on format
        self._update_quality_options()

        # Load quality setting
        if saved_format == 'video':
            saved_quality = self.settings.video_quality
            if saved_quality in VIDEO_RESOLUTIONS:
                self.quality_combo.setCurrentText(saved_quality)
        else:
            saved_quality = self.settings.audio_quality
            if saved_quality in AUDIO_BITRATES:
                self.quality_combo.setCurrentText(saved_quality)

    def _on_format_changed(self, format_text: str):
        """
        Handle format change - update quality options accordingly.

        Args:
            format_text: The selected format text ("Video" or "Audio Only")
        """
        self._update_quality_options()

        # Save to settings
        file_format = FILE_FORMATS.get(format_text, 'video')
        self.settings.file_format = file_format

        # Emit signal
        self.format_changed.emit(file_format)

        self.logger.info(f"Format changed to: {file_format}")

    def _on_quality_changed(self, quality: str):
        """
        Handle quality change.

        Args:
            quality: The selected quality string
        """
        # Save to appropriate settings
        file_format = self.get_file_format()
        if file_format == 'video':
            self.settings.video_quality = quality
        else:
            self.settings.audio_quality = quality

        # Emit signal
        self.quality_changed.emit(quality)

        self.logger.info(f"Quality changed to: {quality}")

    def _update_quality_options(self):
        """Update quality combo box based on current format selection."""
        current_format = self.format_combo.currentText()

        # Clear current options
        self.quality_combo.clear()

        # Add appropriate options
        if current_format == "Video":
            self.quality_label.setText("Resolution:")
            self.quality_combo.addItems(VIDEO_RESOLUTIONS)
        else:  # Audio Only
            self.quality_label.setText("Bitrate:")
            self.quality_combo.addItems(AUDIO_BITRATES)

    def get_file_format(self) -> str:
        """
        Get the current file format.

        Returns:
            str: 'video' or 'audio'
        """
        format_text = self.format_combo.currentText()
        return FILE_FORMATS.get(format_text, 'video')

    def get_quality(self) -> str:
        """
        Get the current quality selection.

        Returns:
            str: Quality string (e.g., '1080p', '320kbps')
        """
        return self.quality_combo.currentText()
