"""
Preferences dialog for BatchRipTagger YT (v5.0).
Allows users to set default values for UI options.
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QCheckBox, QPushButton, QGroupBox,
    QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt

from config.ui_preferences import UIPreferencesManager
from config.constants import VIDEO_RESOLUTIONS, AUDIO_BITRATES


class PreferencesDialog(QDialog):
    """
    Dialog for configuring UI preferences.
    Allows users to set default values for download options.
    """

    def __init__(self, parent=None):
        """
        Initialize the preferences dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.preferences = UIPreferencesManager()

        self.setWindowTitle("Preferences")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self._init_ui()
        self._load_current_preferences()

        self.logger.debug("Preferences dialog initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)

        # Tab widget for different preference categories
        self.tab_widget = QTabWidget()

        # Download Settings Tab
        download_tab = self._create_download_tab()
        self.tab_widget.addTab(download_tab, "Download Settings")

        # Metadata Settings Tab
        metadata_tab = self._create_metadata_tab()
        self.tab_widget.addTab(metadata_tab, "Metadata Settings")

        main_layout.addWidget(self.tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Restore Defaults button
        restore_button = QPushButton("Restore Defaults")
        restore_button.clicked.connect(self._on_restore_defaults)
        button_layout.addWidget(restore_button)

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # Save button
        save_button = QPushButton("Save")
        save_button.setDefault(True)
        save_button.clicked.connect(self._on_save)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

    def _create_download_tab(self) -> QWidget:
        """Create the download settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # File Format Group
        format_group = QGroupBox("Default File Format")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["Video", "Audio Only"])
        format_layout.addRow("File Format:", self.format_combo)

        layout.addWidget(format_group)

        # Quality Settings Group
        quality_group = QGroupBox("Default Quality Settings")
        quality_layout = QFormLayout(quality_group)

        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(VIDEO_RESOLUTIONS)
        quality_layout.addRow("Video Quality:", self.video_quality_combo)

        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(AUDIO_BITRATES)
        quality_layout.addRow("Audio Quality:", self.audio_quality_combo)

        layout.addWidget(quality_group)

        # Feature Defaults Group
        features_group = QGroupBox("Feature Defaults")
        features_layout = QVBoxLayout(features_group)

        self.album_checkbox = QCheckBox("Show 'Album?' checkbox by default")
        self.album_checkbox.setToolTip("Controls whether the album checkbox appears in the link queue")
        features_layout.addWidget(self.album_checkbox)

        self.beets_enabled_checkbox = QCheckBox("Enable automatic tagging by default")
        self.beets_enabled_checkbox.setToolTip("Automatically enable AcoustID fingerprinting for new sessions")
        features_layout.addWidget(self.beets_enabled_checkbox)

        self.remember_output_checkbox = QCheckBox("Remember last output directory")
        self.remember_output_checkbox.setToolTip("Restore the last used output directory on startup")
        features_layout.addWidget(self.remember_output_checkbox)

        layout.addWidget(features_group)

        # Info label
        info_label = QLabel(
            "<i>Note: These preferences set the default state for UI options. "
            "You can still change individual settings during each session.</i>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        return tab

    def _create_metadata_tab(self) -> QWidget:
        """Create the metadata settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Display Settings Group
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout(display_group)

        self.show_extensions_checkbox = QCheckBox("Show file extensions in metadata view")
        self.show_extensions_checkbox.setToolTip("Display file extensions when viewing metadata")
        display_layout.addWidget(self.show_extensions_checkbox)

        self.auto_refresh_checkbox = QCheckBox("Auto-refresh on folder change")
        self.auto_refresh_checkbox.setToolTip("Automatically reload metadata when changing folders")
        display_layout.addWidget(self.auto_refresh_checkbox)

        layout.addWidget(display_group)

        # Placeholder for future metadata preferences
        placeholder_label = QLabel(
            "<i>Additional metadata processing preferences will be added "
            "as more features are implemented.</i>"
        )
        placeholder_label.setWordWrap(True)
        placeholder_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(placeholder_label)

        layout.addStretch()
        return tab

    def _load_current_preferences(self):
        """Load current preferences into UI controls."""
        # Download settings
        file_format = self.preferences.get("default_file_format", "audio")
        self.format_combo.setCurrentText("Audio Only" if file_format == "audio" else "Video")

        video_quality = self.preferences.get("default_video_quality", "Best Available")
        self.video_quality_combo.setCurrentText(video_quality)

        audio_quality = self.preferences.get("default_audio_quality", "Best Available")
        self.audio_quality_combo.setCurrentText(audio_quality)

        self.album_checkbox.setChecked(self.preferences.get("default_album_checkbox", True))
        self.beets_enabled_checkbox.setChecked(self.preferences.get("default_beets_enabled", False))
        self.remember_output_checkbox.setChecked(self.preferences.get("remember_output_directory", True))

        # Metadata settings
        self.show_extensions_checkbox.setChecked(self.preferences.get("show_file_extensions", True))
        self.auto_refresh_checkbox.setChecked(self.preferences.get("auto_refresh_on_folder_change", True))

    def _on_save(self):
        """Save preferences and close dialog."""
        try:
            # Download settings
            file_format = "audio" if self.format_combo.currentText() == "Audio Only" else "video"
            self.preferences.set("default_file_format", file_format, save=False)
            self.preferences.set("default_video_quality", self.video_quality_combo.currentText(), save=False)
            self.preferences.set("default_audio_quality", self.audio_quality_combo.currentText(), save=False)
            self.preferences.set("default_album_checkbox", self.album_checkbox.isChecked(), save=False)
            self.preferences.set("default_beets_enabled", self.beets_enabled_checkbox.isChecked(), save=False)
            self.preferences.set("remember_output_directory", self.remember_output_checkbox.isChecked(), save=False)

            # Metadata settings
            self.preferences.set("show_file_extensions", self.show_extensions_checkbox.isChecked(), save=False)
            self.preferences.set("auto_refresh_on_folder_change", self.auto_refresh_checkbox.isChecked(), save=True)

            self.logger.info("Preferences saved successfully")
            QMessageBox.information(
                self,
                "Preferences Saved",
                "Your preferences have been saved successfully.\n\n"
                "New defaults will be applied the next time you start the application."
            )
            self.accept()
        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save preferences:\n{e}"
            )

    def _on_restore_defaults(self):
        """Restore all preferences to default values."""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore all preferences to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.preferences.reset_to_defaults()
            self._load_current_preferences()
            self.logger.info("Preferences restored to defaults")
            QMessageBox.information(
                self,
                "Defaults Restored",
                "All preferences have been restored to their default values."
            )
