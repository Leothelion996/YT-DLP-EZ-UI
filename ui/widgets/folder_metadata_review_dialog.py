"""
Folder Metadata Review Dialog for YT-DLP EZ-UI (v5.1).
Post-processing dialog for reviewing and correcting AcoustID metadata using majority voting.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt

from core.album_analyzer import AlbumAnalyzer


class FolderMetadataReviewDialog(QDialog):
    """
    Post-processing dialog that analyzes AcoustID results for a folder
    and suggests corrections based on majority voting.

    Allows users to fix metadata inconsistencies with 2 clicks:
    1. Click "Apply to All" for Album
    2. Click "Apply to All" for Artist

    Uses AlbumAnalyzer for smart metadata analysis and file writing.
    """

    def __init__(self, acoustid_results: List[Dict], parent=None):
        """
        Initialize the folder metadata review dialog.

        Args:
            acoustid_results: List of AcoustID tagging results with structure:
                [
                    {
                        'file': '/path/to/file.mp3',
                        'success': True,
                        'title': 'Song Title',
                        'artist': 'Artist Name',
                        'album': 'Album Name'
                    },
                    ...
                ]
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        # Store results and analyzer
        self.results = acoustid_results
        self.analyzer = AlbumAnalyzer()

        # Extract file data for analysis
        self.files = self._extract_file_data(acoustid_results)

        # Analysis results
        self.album_stats = {}
        self.artist_stats = {}
        self.consensus_album = None
        self.consensus_artist = None

        # User selections
        self.selected_album = None
        self.selected_artist = None
        self.changes_applied = False

        self._init_ui()
        self._analyze_metadata()
        self._populate_ui()

        self.logger.info(f"Metadata review dialog initialized with {len(self.files)} files")

    def _extract_file_data(self, results: List[Dict]) -> List[Dict]:
        """
        Extract file data from AcoustID results for analysis.

        Args:
            results: AcoustID results list

        Returns:
            List of file dictionaries with path, title, artist, album
        """
        files = []
        for result in results:
            if result.get('success', False):
                files.append({
                    'path': Path(result['file']),
                    'title': result.get('title', 'UNKNOWN'),
                    'artist': result.get('artist', 'UNKNOWN'),
                    'album': result.get('album', 'UNKNOWN')
                })
        return files

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Review Folder Metadata")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # Header
        header_label = QLabel(
            f"<b>Metadata Review</b><br>"
            f"Found {len(self.files)} files with metadata from AcoustID.<br>"
            f"Review and correct any inconsistencies below."
        )
        header_label.setWordWrap(True)
        header_label.setStyleSheet("font-size: 11pt; color: #0078d4; padding: 10px;")
        main_layout.addWidget(header_label)

        # Album section
        album_group = QGroupBox("Album Selection")
        album_layout = QVBoxLayout(album_group)

        self.album_info_label = QLabel("Analyzing...")
        self.album_info_label.setWordWrap(True)
        album_layout.addWidget(self.album_info_label)

        album_control_layout = QHBoxLayout()
        self.album_combo = QComboBox()
        self.album_combo.setMinimumWidth(300)
        album_control_layout.addWidget(self.album_combo)

        self.album_apply_button = QPushButton("Apply to All Files")
        self.album_apply_button.setMinimumWidth(150)
        self.album_apply_button.clicked.connect(self._on_apply_album_clicked)
        self.album_apply_button.setStyleSheet("""
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
        album_control_layout.addWidget(self.album_apply_button)

        album_layout.addLayout(album_control_layout)
        main_layout.addWidget(album_group)

        # Artist section
        artist_group = QGroupBox("Artist Selection")
        artist_layout = QVBoxLayout(artist_group)

        self.artist_info_label = QLabel("Analyzing...")
        self.artist_info_label.setWordWrap(True)
        artist_layout.addWidget(self.artist_info_label)

        artist_control_layout = QHBoxLayout()
        self.artist_combo = QComboBox()
        self.artist_combo.setMinimumWidth(300)
        artist_control_layout.addWidget(self.artist_combo)

        self.artist_apply_button = QPushButton("Apply to All Files")
        self.artist_apply_button.setMinimumWidth(150)
        self.artist_apply_button.clicked.connect(self._on_apply_artist_clicked)
        self.artist_apply_button.setStyleSheet("""
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
        artist_control_layout.addWidget(self.artist_apply_button)

        artist_layout.addLayout(artist_control_layout)
        main_layout.addWidget(artist_group)

        # Statistics section
        stats_group = QGroupBox("Metadata Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("Loading statistics...")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-family: monospace; font-size: 9pt;")
        stats_layout.addWidget(self.stats_label)

        main_layout.addWidget(stats_group)

        # Bottom buttons
        main_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        skip_button = QPushButton("Skip (No Changes)")
        skip_button.setMinimumWidth(150)
        skip_button.clicked.connect(self.reject)
        button_layout.addWidget(skip_button)

        done_button = QPushButton("Done")
        done_button.setMinimumWidth(150)
        done_button.clicked.connect(self.accept)
        done_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        button_layout.addWidget(done_button)

        main_layout.addLayout(button_layout)

    def _analyze_metadata(self):
        """Analyze metadata using AlbumAnalyzer to find consensus values."""
        if not self.files:
            self.logger.warning("No files to analyze")
            return

        # Get album statistics
        self.album_stats = self.analyzer.get_album_statistics(self.files)
        self.consensus_album = self.analyzer.analyze_album_metadata(self.files)

        # Get artist statistics
        artist_names = []
        for file_data in self.files:
            artist = file_data.get('artist', '').strip()
            if artist and artist.upper() not in ['UNKNOWN', 'N/A', '', 'VARIOUS ARTISTS']:
                artist_names.append(artist)

        if artist_names:
            self.artist_stats = dict(Counter(artist_names))
            self.consensus_artist = self.analyzer.get_consensus_artist(self.files)

        self.logger.info(f"Analysis complete - Album consensus: {self.consensus_album}, Artist consensus: {self.consensus_artist}")
        self.logger.info(f"Album stats: {self.album_stats}")
        self.logger.info(f"Artist stats: {self.artist_stats}")

    def _populate_ui(self):
        """Populate UI with analysis results."""
        # Populate album section
        if self.album_stats:
            # Sort albums by count (most common first)
            sorted_albums = sorted(self.album_stats.items(), key=lambda x: x[1], reverse=True)

            # Build info label with statistics
            total_files = len(self.files)
            most_common_album, most_common_count = sorted_albums[0]

            info_text = f"<b>Most common:</b> {most_common_album} ({most_common_count}/{total_files} files)"
            if len(sorted_albums) > 1:
                info_text += "<br><b>Other albums found:</b><br>"
                for album, count in sorted_albums[1:]:
                    info_text += f"  • {album} ({count} file{'s' if count > 1 else ''})<br>"

            self.album_info_label.setText(info_text)

            # Populate combo box
            for album, count in sorted_albums:
                self.album_combo.addItem(f"{album} ({count} files)", album)

            # Select consensus album by default
            if self.consensus_album:
                index = self.album_combo.findData(self.consensus_album)
                if index >= 0:
                    self.album_combo.setCurrentIndex(index)
        else:
            self.album_info_label.setText("No album metadata found")
            self.album_apply_button.setEnabled(False)

        # Populate artist section
        if self.artist_stats:
            # Sort artists by count (most common first)
            sorted_artists = sorted(self.artist_stats.items(), key=lambda x: x[1], reverse=True)

            # Build info label with statistics
            total_files = len(self.files)
            most_common_artist, most_common_count = sorted_artists[0]

            info_text = f"<b>Most common:</b> {most_common_artist} ({most_common_count}/{total_files} files)"
            if len(sorted_artists) > 1:
                info_text += "<br><b>Other artists found:</b><br>"
                for artist, count in sorted_artists[1:]:
                    info_text += f"  • {artist} ({count} file{'s' if count > 1 else ''})<br>"

            self.artist_info_label.setText(info_text)

            # Populate combo box
            for artist, count in sorted_artists:
                self.artist_combo.addItem(f"{artist} ({count} files)", artist)

            # Select consensus artist by default
            if self.consensus_artist:
                index = self.artist_combo.findData(self.consensus_artist)
                if index >= 0:
                    self.artist_combo.setCurrentIndex(index)
        else:
            self.artist_info_label.setText("No artist metadata found")
            self.artist_apply_button.setEnabled(False)

        # Populate statistics section
        stats_text = "<b>Detailed Statistics:</b><br><br>"

        if self.album_stats:
            stats_text += "<b>Albums:</b><br>"
            for album, count in sorted(self.album_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(self.files)) * 100
                stats_text += f"  {album}: {count} files ({percentage:.0f}%)<br>"

        if self.artist_stats:
            stats_text += "<br><b>Artists:</b><br>"
            for artist, count in sorted(self.artist_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(self.files)) * 100
                stats_text += f"  {artist}: {count} files ({percentage:.0f}%)<br>"

        self.stats_label.setText(stats_text)

    def _on_apply_album_clicked(self):
        """Handle Apply to All button click for album."""
        selected_album = self.album_combo.currentData()
        if not selected_album:
            self.logger.warning("No album selected")
            return

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Confirm Album Change",
            f"Apply album '{selected_album}' to all {len(self.files)} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info(f"Applying album '{selected_album}' to all files")

            # Apply consensus album using AlbumAnalyzer
            updated_files = self.analyzer.apply_consensus_album(self.files, selected_album)

            # Update internal file list
            self.files = updated_files
            self.selected_album = selected_album
            self.changes_applied = True

            QMessageBox.information(
                self,
                "Album Applied",
                f"Successfully applied album '{selected_album}' to all {len(self.files)} files."
            )

            self.logger.info(f"Album '{selected_album}' applied successfully")

    def _on_apply_artist_clicked(self):
        """Handle Apply to All button click for artist."""
        selected_artist = self.artist_combo.currentData()
        if not selected_artist:
            self.logger.warning("No artist selected")
            return

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Confirm Artist Change",
            f"Apply artist '{selected_artist}' to all {len(self.files)} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info(f"Applying artist '{selected_artist}' to all files")

            # Apply consensus artist using AlbumAnalyzer
            self.analyzer.apply_consensus_artist(self.files, selected_artist)

            self.selected_artist = selected_artist
            self.changes_applied = True

            QMessageBox.information(
                self,
                "Artist Applied",
                f"Successfully applied artist '{selected_artist}' to all {len(self.files)} files."
            )

            self.logger.info(f"Artist '{selected_artist}' applied successfully")

    def get_changes_applied(self) -> bool:
        """
        Check if any changes were applied.

        Returns:
            bool: True if changes were applied
        """
        return self.changes_applied
