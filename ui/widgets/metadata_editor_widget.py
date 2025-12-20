"""
Metadata Editor Widget for BatchRipTagger YT (v5.0).
Allows viewing and editing metadata for audio files in a folder.
"""

import logging
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMenu, QInputDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


class MetadataEditorWidget(QWidget):
    """
    Widget for editing metadata of audio files in a folder.

    Features:
    - View all audio files in a table
    - Edit metadata inline (title, artist, album, track #)
    - Right-click context menu
    - F2 to rename files
    - Bulk album setting from folder
    """

    # Signals
    files_loaded = pyqtSignal(int)  # Emits count of files loaded
    metadata_saved = pyqtSignal(str)  # Emits file path when metadata is saved

    def __init__(self, parent=None):
        """
        Initialize the metadata editor widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.current_folder: Optional[Path] = None
        self.audio_files: List[Path] = []

        self._init_ui()
        self.logger.debug("Metadata editor widget initialized")

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Info label
        self.info_label = QLabel("No folder loaded. Use 'Process Existing Folder' to load files.")
        self.info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        main_layout.addWidget(self.info_label)

        # Table for file list
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(6)
        self.file_table.setHorizontalHeaderLabels([
            "Filename", "Title", "Artist", "Album", "Track #", "Path"
        ])

        # Configure table
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked |
                                       QTableWidget.EditTrigger.EditKeyPressed)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)

        # Hide path column (used internally)
        self.file_table.setColumnHidden(5, True)

        # Resize columns
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # Connect signals
        self.file_table.itemChanged.connect(self._on_item_changed)
        self.file_table.installEventFilter(self)

        main_layout.addWidget(self.file_table)

        # Button bar
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Reload files from current folder")
        self.refresh_button.clicked.connect(self.refresh)
        button_layout.addWidget(self.refresh_button)

        self.set_album_button = QPushButton("Set Album for All")
        self.set_album_button.setToolTip("Set the same album name for all files")
        self.set_album_button.clicked.connect(self._set_album_for_all)
        button_layout.addWidget(self.set_album_button)

        self.set_album_from_folder_button = QPushButton("Album from Folder")
        self.set_album_from_folder_button.setToolTip("Use folder name as album for all files")
        self.set_album_from_folder_button.clicked.connect(self._set_album_from_folder)
        button_layout.addWidget(self.set_album_from_folder_button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def eventFilter(self, obj, event):
        """Handle F2 key press for rename."""
        if obj == self.file_table and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_F2:
                self._rename_selected_file()
                return True
        return super().eventFilter(obj, event)

    def load_folder(self, folder_path: Path):
        """
        Load all audio files from a folder.

        Args:
            folder_path: Path to folder containing audio files
        """
        self.logger.info(f"Loading folder: {folder_path}")
        self.current_folder = folder_path
        self.audio_files.clear()
        self.file_table.setRowCount(0)

        if not folder_path.exists():
            self.info_label.setText(f"Folder does not exist: {folder_path}")
            return

        # Find all audio files
        audio_extensions = {'.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.wma'}
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                self.audio_files.append(file_path)

        # Sort by filename
        self.audio_files.sort(key=lambda p: p.name.lower())

        # Load into table
        self._populate_table()

        self.info_label.setText(f"Loaded {len(self.audio_files)} file(s) from: {folder_path.name}")
        self.files_loaded.emit(len(self.audio_files))

    def refresh(self):
        """Reload files from current folder."""
        if self.current_folder:
            self.load_folder(self.current_folder)

    def _populate_table(self):
        """Populate table with audio files and their metadata."""
        self.file_table.blockSignals(True)  # Prevent itemChanged from firing during population

        self.file_table.setRowCount(len(self.audio_files))

        for row, file_path in enumerate(self.audio_files):
            # Filename
            filename_item = QTableWidgetItem(file_path.name)
            filename_item.setFlags(filename_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Read-only
            self.file_table.setItem(row, 0, filename_item)

            # Load metadata
            metadata = self._read_metadata(file_path)

            # Title
            title_item = QTableWidgetItem(metadata.get('title', ''))
            self.file_table.setItem(row, 1, title_item)

            # Artist
            artist_item = QTableWidgetItem(metadata.get('artist', ''))
            self.file_table.setItem(row, 2, artist_item)

            # Album
            album_item = QTableWidgetItem(metadata.get('album', ''))
            self.file_table.setItem(row, 3, album_item)

            # Track #
            track_item = QTableWidgetItem(metadata.get('tracknumber', ''))
            self.file_table.setItem(row, 4, track_item)

            # Path (hidden)
            path_item = QTableWidgetItem(str(file_path))
            self.file_table.setItem(row, 5, path_item)

        self.file_table.blockSignals(False)

    def _read_metadata(self, file_path: Path) -> dict:
        """
        Read metadata from an audio file.

        Args:
            file_path: Path to audio file

        Returns:
            dict: Metadata dictionary
        """
        if not MUTAGEN_AVAILABLE:
            return {}

        try:
            # Try EasyID3 first (works for MP3)
            try:
                audio = EasyID3(str(file_path))
                return {
                    'title': audio.get('title', [''])[0],
                    'artist': audio.get('artist', [''])[0],
                    'album': audio.get('album', [''])[0],
                    'tracknumber': audio.get('tracknumber', [''])[0]
                }
            except:
                pass

            # Try other formats
            if file_path.suffix.lower() == '.flac':
                audio = FLAC(str(file_path))
            elif file_path.suffix.lower() in {'.m4a', '.mp4'}:
                audio = MP4(str(file_path))
            else:
                return {}

            return {
                'title': audio.get('title', [''])[0] if 'title' in audio else '',
                'artist': audio.get('artist', [''])[0] if 'artist' in audio else '',
                'album': audio.get('album', [''])[0] if 'album' in audio else '',
                'tracknumber': audio.get('tracknumber', [''])[0] if 'tracknumber' in audio else ''
            }
        except Exception as e:
            self.logger.warning(f"Failed to read metadata from {file_path.name}: {e}")
            return {}

    def _on_item_changed(self, item: QTableWidgetItem):
        """
        Handle item change - save metadata to file.

        Args:
            item: Changed table item
        """
        row = item.row()
        column = item.column()

        # Only handle metadata columns
        if column not in {1, 2, 3, 4}:
            return

        # Get file path
        path_item = self.file_table.item(row, 5)
        if not path_item:
            return

        file_path = Path(path_item.text())

        # Get all metadata from table
        metadata = {
            'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
            'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
            'album': self.file_table.item(row, 3).text() if self.file_table.item(row, 3) else '',
            'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
        }

        # Save metadata
        try:
            self._write_metadata(file_path, metadata)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save metadata for {file_path.name}:\n{e}"
            )

    def _write_metadata(self, file_path: Path, metadata: dict):
        """
        Write metadata to an audio file.

        Args:
            file_path: Path to audio file
            metadata: Metadata dictionary
        """
        if not MUTAGEN_AVAILABLE:
            self.logger.error("Mutagen not available - cannot write metadata")
            raise Exception("Mutagen library not available")

        try:
            # Try EasyID3 first
            try:
                audio = EasyID3(str(file_path))
            except:
                # Create ID3 tags if they don't exist
                audio_file = ID3()
                audio_file.save(str(file_path))
                audio = EasyID3(str(file_path))

            # Update metadata - always set fields even if empty to ensure they're written
            # v5.1 FIX: Use 'in metadata' instead of 'get' to ensure empty values are written
            if 'title' in metadata:
                audio['title'] = metadata['title'] if metadata['title'] else ''
            if 'artist' in metadata:
                audio['artist'] = metadata['artist'] if metadata['artist'] else ''
            if 'album' in metadata:
                audio['album'] = metadata['album'] if metadata['album'] else ''
            if 'tracknumber' in metadata:
                # Ensure tracknumber is always written (important for track numbering feature)
                audio['tracknumber'] = metadata['tracknumber']

            audio.save()
            self.logger.debug(f"Saved metadata for: {file_path.name} (track: {metadata.get('tracknumber', 'N/A')})")
            self.metadata_saved.emit(str(file_path))

        except Exception as e:
            self.logger.error(f"Failed to write metadata to {file_path.name}: {e}")
            raise  # Re-raise so caller knows it failed

    def _show_context_menu(self, position):
        """Show right-click context menu."""
        # Get selected rows
        selected_rows = set(item.row() for item in self.file_table.selectedItems())
        if not selected_rows:
            return

        # Determine which column was clicked
        item = self.file_table.itemAt(position)
        clicked_column = item.column() if item else None

        menu = QMenu(self)

        # Rename action (only if single file selected)
        if len(selected_rows) == 1:
            rename_action = QAction("Rename File (F2)", self)
            rename_action.triggered.connect(self._rename_selected_file)
            menu.addAction(rename_action)
            menu.addSeparator()

        # Column-specific actions
        if clicked_column == 1:  # Title column
            title_from_filename_action = QAction("Use Filename as Title", self)
            title_from_filename_action.triggered.connect(self._set_title_from_filename)
            menu.addAction(title_from_filename_action)
            menu.addSeparator()

        if clicked_column == 2:  # Artist column
            artist_from_options_action = QAction("Select Artist from Available Options", self)
            artist_from_options_action.triggered.connect(self._select_artist_from_options)
            menu.addAction(artist_from_options_action)
            menu.addSeparator()

        # Set album action (with dropdown if album column clicked)
        if clicked_column == 3:  # Album column
            set_album_from_options_action = QAction("Set Album from Available Options", self)
            set_album_from_options_action.triggered.connect(self._set_album_from_options)
            menu.addAction(set_album_from_options_action)
        else:
            set_album_action = QAction("Set Album for Selected", self)
            set_album_action.triggered.connect(self._set_album_for_selected)
            menu.addAction(set_album_action)

        # Track # column actions
        if clicked_column == 4:  # Track # column
            number_by_date_action = QAction("Number Tracks by Creation Date", self)
            number_by_date_action.triggered.connect(self._number_tracks_by_creation_date)
            menu.addAction(number_by_date_action)
            menu.addSeparator()

        # Clear metadata action
        clear_action = QAction("Clear Metadata for Selected", self)
        clear_action.triggered.connect(self._clear_metadata_for_selected)
        menu.addAction(clear_action)

        menu.addSeparator()

        # Show in explorer
        show_action = QAction("Show in File Explorer", self)
        show_action.triggered.connect(self._show_in_explorer)
        menu.addAction(show_action)

        menu.exec(self.file_table.viewport().mapToGlobal(position))

    def _rename_selected_file(self):
        """Rename the selected file (F2 functionality)."""
        selected_rows = set(item.row() for item in self.file_table.selectedItems())
        if len(selected_rows) != 1:
            return

        row = list(selected_rows)[0]
        path_item = self.file_table.item(row, 5)
        if not path_item:
            return

        old_path = Path(path_item.text())
        old_name = old_path.stem
        extension = old_path.suffix

        # Show input dialog
        new_name, ok = QInputDialog.getText(
            self,
            "Rename File",
            "Enter new filename (without extension):",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            new_path = old_path.parent / f"{new_name}{extension}"

            # Check if file exists
            if new_path.exists():
                QMessageBox.warning(
                    self,
                    "File Exists",
                    f"A file named '{new_path.name}' already exists."
                )
                return

            try:
                old_path.rename(new_path)
                self.logger.info(f"Renamed: {old_path.name} → {new_path.name}")

                # Update table
                self.file_table.item(row, 0).setText(new_path.name)
                self.file_table.item(row, 5).setText(str(new_path))

                # Update internal list
                self.audio_files[row] = new_path

            except Exception as e:
                self.logger.error(f"Failed to rename file: {e}")
                QMessageBox.critical(
                    self,
                    "Rename Error",
                    f"Failed to rename file:\n{e}"
                )

    def _set_album_for_selected(self):
        """Set album for selected files."""
        selected_rows = sorted(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            return

        # Get album name from user
        album_name, ok = QInputDialog.getText(
            self,
            "Set Album",
            f"Enter album name for {len(selected_rows)} selected file(s):"
        )

        if ok and album_name:
            self.file_table.blockSignals(True)

            for row in selected_rows:
                # Update table
                album_item = self.file_table.item(row, 3)
                if album_item:
                    album_item.setText(album_name)

                # Get file path and save
                path_item = self.file_table.item(row, 5)
                if path_item:
                    file_path = Path(path_item.text())
                    metadata = {
                        'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
                        'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
                        'album': album_name,
                        'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
                    }
                    self._write_metadata(file_path, metadata)

            self.file_table.blockSignals(False)
            self.logger.info(f"Set album '{album_name}' for {len(selected_rows)} file(s)")

    def _set_album_for_all(self):
        """Set album for all files in the list."""
        if self.file_table.rowCount() == 0:
            return

        # Get album name from user
        album_name, ok = QInputDialog.getText(
            self,
            "Set Album for All",
            f"Enter album name for all {self.file_table.rowCount()} file(s):"
        )

        if ok and album_name:
            self.file_table.blockSignals(True)

            for row in range(self.file_table.rowCount()):
                # Update table
                album_item = self.file_table.item(row, 3)
                if album_item:
                    album_item.setText(album_name)

                # Get file path and save
                path_item = self.file_table.item(row, 5)
                if path_item:
                    file_path = Path(path_item.text())
                    metadata = {
                        'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
                        'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
                        'album': album_name,
                        'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
                    }
                    self._write_metadata(file_path, metadata)

            self.file_table.blockSignals(False)
            self.logger.info(f"Set album '{album_name}' for all {self.file_table.rowCount()} file(s)")

    def _set_album_from_folder(self):
        """Use folder name as album for all files."""
        if not self.current_folder or self.file_table.rowCount() == 0:
            return

        album_name = self.current_folder.name

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Set Album from Folder",
            f"Set album to '{album_name}' for all {self.file_table.rowCount()} file(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.file_table.blockSignals(True)

            for row in range(self.file_table.rowCount()):
                # Update table
                album_item = self.file_table.item(row, 3)
                if album_item:
                    album_item.setText(album_name)

                # Get file path and save
                path_item = self.file_table.item(row, 5)
                if path_item:
                    file_path = Path(path_item.text())
                    metadata = {
                        'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
                        'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
                        'album': album_name,
                        'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
                    }
                    self._write_metadata(file_path, metadata)

            self.file_table.blockSignals(False)
            self.logger.info(f"Set album from folder '{album_name}' for all {self.file_table.rowCount()} file(s)")

    def _clear_metadata_for_selected(self):
        """Clear metadata for selected files."""
        selected_rows = sorted(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            return

        reply = QMessageBox.question(
            self,
            "Clear Metadata",
            f"Clear all metadata for {len(selected_rows)} selected file(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.file_table.blockSignals(True)

            for row in selected_rows:
                # Clear table
                for col in [1, 2, 3, 4]:  # Title, Artist, Album, Track #
                    item = self.file_table.item(row, col)
                    if item:
                        item.setText('')

                # Clear file metadata
                path_item = self.file_table.item(row, 5)
                if path_item:
                    file_path = Path(path_item.text())
                    metadata = {'title': '', 'artist': '', 'album': '', 'tracknumber': ''}
                    self._write_metadata(file_path, metadata)

            self.file_table.blockSignals(False)
            self.logger.info(f"Cleared metadata for {len(selected_rows)} file(s)")

    def _show_in_explorer(self):
        """Show selected file in file explorer."""
        selected_rows = set(item.row() for item in self.file_table.selectedItems())
        if not selected_rows:
            return

        row = list(selected_rows)[0]
        path_item = self.file_table.item(row, 5)
        if not path_item:
            return

        file_path = Path(path_item.text())

        # Open file explorer (Windows specific)
        import subprocess
        import sys

        if sys.platform == 'win32':
            subprocess.run(['explorer', '/select,', str(file_path)])
        else:
            # For other platforms, just open the folder
            subprocess.run(['xdg-open', str(file_path.parent)])

    def _set_title_from_filename(self):
        """
        Set title from filename (without extension) for selected files.
        v5.1: Context menu action for Title column.
        """
        selected_rows = sorted(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            return

        self.file_table.blockSignals(True)

        for row in selected_rows:
            # Get filename without extension
            path_item = self.file_table.item(row, 5)
            if not path_item:
                continue

            file_path = Path(path_item.text())
            title = file_path.stem  # Filename without extension

            # Update table
            title_item = self.file_table.item(row, 1)
            if title_item:
                title_item.setText(title)

            # Save to file
            metadata = {
                'title': title,
                'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
                'album': self.file_table.item(row, 3).text() if self.file_table.item(row, 3) else '',
                'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
            }
            self._write_metadata(file_path, metadata)

        self.file_table.blockSignals(False)
        self.logger.info(f"Set title from filename for {len(selected_rows)} file(s)")

    def _get_available_albums(self) -> List[str]:
        """
        Get list of unique album names from all files in the table.
        v5.1: Helper for album dropdown selection.

        Returns:
            List of unique album names (excluding empty strings)
        """
        albums = set()
        for row in range(self.file_table.rowCount()):
            album_item = self.file_table.item(row, 3)
            if album_item and album_item.text().strip():
                albums.add(album_item.text().strip())

        return sorted(list(albums))

    def _get_available_artists(self) -> List[str]:
        """
        Get list of unique artist names from all files in the table.
        v5.1: Helper for artist dropdown selection.

        Returns:
            List of unique artist names (excluding empty strings)
        """
        artists = set()
        for row in range(self.file_table.rowCount()):
            artist_item = self.file_table.item(row, 2)
            if artist_item and artist_item.text().strip():
                artists.add(artist_item.text().strip())

        return sorted(list(artists))

    def _set_album_from_options(self):
        """
        Set album for selected files from available options in folder.
        v5.1: Context menu action with dropdown of existing albums.
        """
        selected_rows = sorted(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            return

        # Get available albums
        available_albums = self._get_available_albums()

        if not available_albums:
            # No albums available, fall back to manual input
            QMessageBox.information(
                self,
                "No Albums Found",
                "No album metadata found in this folder. Use 'Set Album for Selected' to enter manually."
            )
            return

        # Add "Custom..." option at the end
        available_albums.append("--- Enter Custom Album ---")

        # Show selection dialog
        from PyQt6.QtWidgets import QInputDialog
        album_name, ok = QInputDialog.getItem(
            self,
            "Select Album",
            f"Choose album for {len(selected_rows)} selected file(s):",
            available_albums,
            0,
            False  # Not editable in dropdown
        )

        if not ok:
            return

        # If "Custom..." was selected, show text input
        if album_name == "--- Enter Custom Album ---":
            album_name, ok = QInputDialog.getText(
                self,
                "Enter Custom Album",
                f"Enter album name for {len(selected_rows)} selected file(s):"
            )
            if not ok or not album_name:
                return

        # Apply the album
        self.file_table.blockSignals(True)

        for row in selected_rows:
            # Update table
            album_item = self.file_table.item(row, 3)
            if album_item:
                album_item.setText(album_name)

            # Get file path and save
            path_item = self.file_table.item(row, 5)
            if path_item:
                file_path = Path(path_item.text())
                metadata = {
                    'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
                    'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
                    'album': album_name,
                    'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
                }
                self._write_metadata(file_path, metadata)

        self.file_table.blockSignals(False)
        self.logger.info(f"Set album '{album_name}' for {len(selected_rows)} file(s) from options")

    def _select_artist_from_options(self):
        """
        Select artist for selected files from available options in folder.
        v5.1: Context menu action with dropdown of existing artists.
        """
        selected_rows = sorted(set(item.row() for item in self.file_table.selectedItems()))
        if not selected_rows:
            return

        # Get available artists
        available_artists = self._get_available_artists()

        if not available_artists:
            # No artists available, fall back to manual input
            QMessageBox.information(
                self,
                "No Artists Found",
                "No artist metadata found in this folder. Double-click to edit manually."
            )
            return

        # Add "Custom..." option at the end
        available_artists.append("--- Enter Custom Artist ---")

        # Show selection dialog
        from PyQt6.QtWidgets import QInputDialog
        artist_name, ok = QInputDialog.getItem(
            self,
            "Select Artist",
            f"Choose artist for {len(selected_rows)} selected file(s):",
            available_artists,
            0,
            False  # Not editable in dropdown
        )

        if not ok:
            return

        # If "Custom..." was selected, show text input
        if artist_name == "--- Enter Custom Artist ---":
            artist_name, ok = QInputDialog.getText(
                self,
                "Enter Custom Artist",
                f"Enter artist name for {len(selected_rows)} selected file(s):"
            )
            if not ok or not artist_name:
                return

        # Apply the artist
        self.file_table.blockSignals(True)

        for row in selected_rows:
            # Update table
            artist_item = self.file_table.item(row, 2)
            if artist_item:
                artist_item.setText(artist_name)

            # Get file path and save
            path_item = self.file_table.item(row, 5)
            if path_item:
                file_path = Path(path_item.text())
                metadata = {
                    'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
                    'artist': artist_name,
                    'album': self.file_table.item(row, 3).text() if self.file_table.item(row, 3) else '',
                    'tracknumber': self.file_table.item(row, 4).text() if self.file_table.item(row, 4) else ''
                }
                self._write_metadata(file_path, metadata)

        self.file_table.blockSignals(False)
        self.logger.info(f"Set artist '{artist_name}' for {len(selected_rows)} file(s) from options")

    def _number_tracks_by_creation_date(self):
        """
        Number tracks based on file creation date (oldest = track 1).
        v5.1: Context menu action for Track # column.
        """
        if self.file_table.rowCount() == 0:
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Number Tracks by Creation Date",
            f"Number all {self.file_table.rowCount()} tracks by creation date?\n\n"
            "Oldest file will be track 1, newest will be the last track.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Get all files with their creation times
        file_data = []
        for row in range(self.file_table.rowCount()):
            path_item = self.file_table.item(row, 5)
            if not path_item:
                continue

            file_path = Path(path_item.text())
            if file_path.exists():
                # Get creation time (or modification time as fallback)
                try:
                    creation_time = file_path.stat().st_ctime
                except:
                    creation_time = file_path.stat().st_mtime

                file_data.append({
                    'row': row,
                    'path': file_path,
                    'creation_time': creation_time
                })

        if not file_data:
            QMessageBox.warning(
                self,
                "No Files Found",
                "Could not find any valid files to number."
            )
            return

        # Sort by creation time (oldest first)
        file_data.sort(key=lambda x: x['creation_time'])

        # Apply track numbers
        self.file_table.blockSignals(True)

        success_count = 0
        failed_files = []

        for track_num, data in enumerate(file_data, start=1):
            row = data['row']
            file_path = data['path']

            try:
                # Update table
                track_item = self.file_table.item(row, 4)
                if track_item:
                    track_item.setText(str(track_num))
                else:
                    # Create track item if it doesn't exist
                    track_item = QTableWidgetItem(str(track_num))
                    self.file_table.setItem(row, 4, track_item)

                # Save to file
                metadata = {
                    'title': self.file_table.item(row, 1).text() if self.file_table.item(row, 1) else '',
                    'artist': self.file_table.item(row, 2).text() if self.file_table.item(row, 2) else '',
                    'album': self.file_table.item(row, 3).text() if self.file_table.item(row, 3) else '',
                    'tracknumber': str(track_num)
                }

                self.logger.debug(f"Setting track {track_num} for {file_path.name}")
                self._write_metadata(file_path, metadata)
                success_count += 1

            except Exception as e:
                self.logger.error(f"Failed to set track number {track_num} for {file_path.name}: {e}")
                failed_files.append(f"{file_path.name} (track {track_num})")

        self.file_table.blockSignals(False)
        self.logger.info(f"Numbered {success_count}/{len(file_data)} tracks by creation date")

        # Show success message (or warnings if there were failures)
        if failed_files:
            QMessageBox.warning(
                self,
                "Track Numbering Complete (with errors)",
                f"Successfully numbered {success_count}/{len(file_data)} tracks by creation date.\n\n"
                f"Failed to number {len(failed_files)} file(s):\n" + "\n".join(failed_files[:5]) +
                ("\n..." if len(failed_files) > 5 else "")
            )
        else:
            QMessageBox.information(
                self,
                "Tracks Numbered",
                f"Successfully numbered {len(file_data)} tracks by creation date.\n\n"
                "Oldest file is track 1, newest is the last track."
            )
