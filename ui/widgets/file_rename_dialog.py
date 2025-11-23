"""
File Rename Dialog for YT-DLP EZ-UI.
Post-tagging verification dialog allowing users to rename files to match metadata (v3.0).
"""

import logging
from pathlib import Path
from typing import List, Dict, Set
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt

from .manual_metadata_dialog import ManualMetadataDialog  # v4.0

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


class FileRenameDialog(QDialog):
    """
    Modal dialog for file renaming after successful tagging.
    Displays checkboxes for each file with original name → metadata-based name.
    """

    def __init__(self, tagged_files: List[Dict], parent=None):
        """
        Initialize the file rename dialog.

        Args:
            tagged_files: List of dicts with keys: 'path' (Path), 'title' (str), 'artist' (str)
            parent: Parent widget
        """
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)
        self.tagged_files = tagged_files
        self.checkboxes = []  # Store checkbox references

        # v4.0: Track manually edited files and locked checkboxes
        self._manually_edited_files: Dict[str, Dict] = {}  # file_path -> {'title': str, 'artist': str}
        self._locked_checkboxes: Set[QCheckBox] = set()  # Checkboxes that are locked

        self._init_ui()
        self.setModal(True)  # Block interaction with parent until dismissed

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Rename Files to Match Metadata")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Header with instructions
        header_label = QLabel(
            "The following files have been tagged successfully.\n"
            "Select files to rename to match their metadata titles:"
        )
        header_label.setStyleSheet("font-weight: bold; color: #ffffff; padding: 8px;")
        header_label.setWordWrap(True)
        main_layout.addWidget(header_label)

        # Scroll area for checkbox list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background-color: #f9f9f9;
            }
        """)

        # Container for checkboxes
        checkbox_container = QWidget()
        checkbox_layout = QVBoxLayout(checkbox_container)
        checkbox_layout.setSpacing(6)
        checkbox_layout.setContentsMargins(8, 8, 8, 8)

        # Create checkbox for each file
        for file_data in self.tagged_files:
            file_path = file_data['path']
            title = file_data.get('title', 'UNKNOWN')
            artist = file_data.get('artist', 'UNKNOWN')

            # Generate new filename from metadata
            new_filename = self._generate_filename(artist, title, file_path.suffix)

            # Create checkbox with label showing original → new name
            checkbox = QCheckBox()
            original_name = file_path.name
            label_text = f"{original_name}  →  {new_filename}"

            checkbox.setText(label_text)
            checkbox.setChecked(True)  # Default to checked
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-family: 'Consolas', 'Courier New', monospace;
                    padding: 4px;
                    font-size: 11px;
                }
                QCheckBox:hover {
                    background-color: #CC5555;
                }
            """)

            # Store file data with checkbox
            checkbox.setProperty('file_data', file_data)
            checkbox.setProperty('new_filename', new_filename)

            # v4.0: Connect checkbox state change to handle manual metadata entry
            checkbox.stateChanged.connect(
                lambda state, cb=checkbox: self._on_checkbox_state_changed(cb)
            )

            checkbox_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        checkbox_layout.addStretch()
        scroll_area.setWidget(checkbox_container)
        main_layout.addWidget(scroll_area)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # Select All / Clear All toggle button
        self.toggle_button = QPushButton("Clear All")
        self.toggle_button.setMinimumWidth(120)
        self.toggle_button.clicked.connect(self._on_toggle_clicked)
        button_layout.addWidget(self.toggle_button)

        button_layout.addStretch()

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # OK button
        ok_button = QPushButton("OK - Rename Selected Files")
        ok_button.setMinimumWidth(180)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        ok_button.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

        self.logger.info(f"File rename dialog initialized with {len(self.tagged_files)} files")

    def _generate_filename(self, artist: str, title: str, extension: str) -> str:
        """
        Generate a safe filename from metadata.

        Args:
            artist: Artist name
            title: Track title
            extension: File extension (e.g., '.mp3')

        Returns:
            str: Safe filename
        """
        # Create filename: "Title.ext" (artist is in metadata only)
        if title:
            base_name = title
        else:
            base_name = "UNKNOWN"

        # Sanitize filename (remove invalid characters)
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            base_name = base_name.replace(char, '')

        # Limit length
        if len(base_name) > 200:
            base_name = base_name[:200]

        return f"{base_name}{extension}"

    def _on_toggle_clicked(self):
        """Handle Select All / Clear All button click."""
        # Check if any checkbox is currently unchecked
        any_unchecked = any(not cb.isChecked() for cb in self.checkboxes if cb not in self._locked_checkboxes)

        if any_unchecked:
            # Select all (skip locked checkboxes)
            for cb in self.checkboxes:
                if cb not in self._locked_checkboxes:
                    cb.setChecked(True)
            self.toggle_button.setText("Clear All")
            self.logger.info("Selected all files for renaming")
        else:
            # Clear all (skip locked checkboxes)
            for cb in self.checkboxes:
                if cb not in self._locked_checkboxes:
                    cb.setChecked(False)
            self.toggle_button.setText("Select All")
            self.logger.info("Cleared all file selections")

    def _on_checkbox_state_changed(self, checkbox: QCheckBox):
        """
        Handle checkbox state change (v4.0).
        When user unchecks a checkbox, show manual metadata entry dialog.

        Args:
            checkbox: The checkbox that changed state
        """
        # If checkbox is locked, block state change and keep it unchecked
        if checkbox in self._locked_checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(False)  # Force to unchecked
            checkbox.blockSignals(False)
            return

        # If user is UN-checking the checkbox (checked -> unchecked)
        if not checkbox.isChecked():
            file_data = checkbox.property('file_data')
            file_path = file_data['path']

            # Show manual metadata dialog
            dialog = ManualMetadataDialog(file_path.name, parent=self)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                # User pressed "Done" with valid data
                manual_data = dialog.get_metadata()

                # Store manual metadata
                self._manually_edited_files[str(file_path)] = manual_data

                # Lock this checkbox
                self._locked_checkboxes.add(checkbox)

                # Visual indication: gray out and disable
                checkbox.setEnabled(False)
                checkbox.setStyleSheet("""
                    QCheckBox {
                        font-family: 'Consolas', 'Courier New', monospace;
                        padding: 4px;
                        font-size: 11px;
                        color: #888888;
                    }
                """)

                self.logger.info(f"File manually edited and locked: {file_path.name}")
            else:
                # User pressed "Cancel"
                # Checkbox remains unchecked, can be toggled again
                # Do nothing - user can select/deselect again later
                self.logger.info(f"Manual metadata entry cancelled for: {file_path.name}")

    def _on_ok_clicked(self):
        """Handle OK button - perform file renaming and metadata removal for unchecked files (v4.0: + manual edits)."""
        # Collect selected files for renaming, unchecked files for metadata removal, and manually edited files
        files_to_rename = []
        files_to_remove_metadata = []
        manually_edited_files = []

        for checkbox in self.checkboxes:
            file_data = checkbox.property('file_data')
            file_path = file_data['path']

            # Check if this file was manually edited
            if str(file_path) in self._manually_edited_files:
                # v4.0: File is manually edited
                manually_edited_files.append(file_path)
            elif checkbox.isChecked():
                # File is checked - rename using fingerprinted metadata
                new_filename = checkbox.property('new_filename')
                files_to_rename.append((file_path, new_filename))
            else:
                # File is unchecked and NOT manually edited - remove metadata
                files_to_remove_metadata.append(file_path)

        # Build confirmation message
        confirm_parts = []
        if files_to_rename:
            confirm_parts.append(f"Rename {len(files_to_rename)} file(s) using fingerprinted metadata")
        if manually_edited_files:
            confirm_parts.append(f"Rename {len(manually_edited_files)} file(s) using manual metadata")
        if files_to_remove_metadata:
            confirm_parts.append(f"Remove metadata from {len(files_to_remove_metadata)} file(s)")

        if not confirm_parts:
            QMessageBox.information(
                self,
                "No Changes",
                "No changes were made."
            )
            return

        # Confirm with user
        response = QMessageBox.question(
            self,
            "Confirm Changes",
            "\n".join(confirm_parts) + "?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        # Perform renaming
        success_count = 0
        error_count = 0
        errors = []

        for old_path, new_filename in files_to_rename:
            try:
                new_path = old_path.parent / new_filename

                # Check if target file already exists
                if new_path.exists() and new_path != old_path:
                    self.logger.warning(f"Target file already exists: {new_path}")
                    errors.append(f"{old_path.name}: Target file already exists")
                    error_count += 1
                    continue

                # Rename file
                old_path.rename(new_path)
                self.logger.info(f"Renamed: {old_path.name} → {new_filename}")
                success_count += 1

            except Exception as e:
                self.logger.error(f"Failed to rename {old_path.name}: {e}")
                errors.append(f"{old_path.name}: {str(e)}")
                error_count += 1

        # v4.0: Process manually edited files
        manual_success_count = 0
        for file_path in manually_edited_files:
            try:
                manual_data = self._manually_edited_files[str(file_path)]
                self._apply_manual_metadata(file_path, manual_data)
                self.logger.info(f"Applied manual metadata to: {file_path.name}")
                manual_success_count += 1
            except Exception as e:
                self.logger.error(f"Failed to apply manual metadata to {file_path.name}: {e}")
                errors.append(f"{file_path.name}: Failed to apply manual metadata - {str(e)}")
                error_count += 1

        # Remove metadata from unchecked files
        metadata_removed_count = 0
        for file_path in files_to_remove_metadata:
            try:
                self._remove_metadata(file_path)
                self.logger.info(f"Removed metadata from: {file_path.name}")
                metadata_removed_count += 1
            except Exception as e:
                self.logger.error(f"Failed to remove metadata from {file_path.name}: {e}")
                errors.append(f"{file_path.name}: Failed to remove metadata - {str(e)}")
                error_count += 1

        # Show results
        if error_count == 0:
            result_parts = []
            if success_count > 0:
                result_parts.append(f"Successfully renamed {success_count} file(s)")
            if manual_success_count > 0:
                result_parts.append(f"Applied manual metadata to {manual_success_count} file(s)")
            if metadata_removed_count > 0:
                result_parts.append(f"Removed metadata from {metadata_removed_count} file(s)")

            QMessageBox.information(
                self,
                "Complete",
                "!\n".join(result_parts) + "!"
            )
            self.accept()  # Close dialog with success
        else:
            # Show error summary
            error_msg = ""
            if success_count > 0:
                error_msg += f"Renamed {success_count} file(s) successfully.\n"
            if manual_success_count > 0:
                error_msg += f"Applied manual metadata to {manual_success_count} file(s).\n"
            if metadata_removed_count > 0:
                error_msg += f"Removed metadata from {metadata_removed_count} file(s).\n"
            error_msg += f"\n{error_count} operation(s) failed:\n"
            error_msg += "\n".join(errors[:10])  # Show first 10 errors
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more"

            QMessageBox.warning(
                self,
                "Completed with Errors",
                error_msg
            )

            if success_count > 0 or manual_success_count > 0 or metadata_removed_count > 0:
                self.accept()  # Close if at least some succeeded
            # Otherwise stay open so user can retry

    def _apply_manual_metadata(self, file_path: Path, manual_data: Dict) -> None:
        """
        Apply manually entered metadata to a file and rename it (v4.0).

        Args:
            file_path: Path to the audio file
            manual_data: Dictionary with 'title' and 'artist' keys

        Raises:
            Exception: If metadata application or renaming fails
        """
        if not MUTAGEN_AVAILABLE:
            raise Exception("Mutagen library not available")

        try:
            title = manual_data.get('title', '').strip()
            artist = manual_data.get('artist', '').strip()

            # Load the file for metadata writing (create tags if they don't exist)
            try:
                audio = EasyID3(str(file_path))
            except Exception:
                # File has no ID3 tags, create them
                audio_file = ID3()
                audio_file.save(str(file_path))
                audio = EasyID3(str(file_path))

            # Write metadata
            if title:
                audio['title'] = title
            if artist:
                audio['artist'] = artist

            audio.save()

            # Generate new filename: Always use title as the filename
            # Title is the primary identifier - filename should match title 1-to-1
            if title:
                new_name = f"{title}{file_path.suffix}"
            elif artist:
                # Fallback: if only artist provided, use artist as filename
                new_name = f"{artist}{file_path.suffix}"
            else:
                # Should not happen due to validation, but handle gracefully
                self.logger.warning(f"No title or artist provided for {file_path.name}")
                return

            # Sanitize filename
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            for char in invalid_chars:
                new_name = new_name.replace(char, '-')

            # Rename file
            new_path = file_path.parent / new_name

            # Check if target exists
            if new_path.exists() and new_path != file_path:
                raise Exception(f"Target file already exists: {new_name}")

            file_path.rename(new_path)

            self.logger.info(f"Applied manual metadata and renamed: {file_path.name} → {new_name}")

        except Exception as e:
            self.logger.error(f"Failed to apply manual metadata: {e}")
            raise

    def _remove_metadata(self, file_path: Path) -> None:
        """
        Remove all metadata tags from an audio file.

        Args:
            file_path: Path to the audio file

        Raises:
            Exception: If metadata removal fails
        """
        if not MUTAGEN_AVAILABLE:
            raise Exception("Mutagen library not available")

        try:
            # Load the file's ID3 tags
            audio = ID3(str(file_path))

            # Delete all tags
            audio.delete()

            # Save the file without tags
            audio.save(str(file_path))

            self.logger.info(f"Successfully removed all metadata from: {file_path.name}")

        except Exception as e:
            self.logger.error(f"Failed to remove metadata: {e}")
            raise

    def get_results(self) -> Dict[str, int]:
        """
        Get rename operation results.

        Returns:
            dict: {'renamed': count, 'skipped': count}
        """
        # This could be expanded to track detailed results
        return {'renamed': 0, 'skipped': 0}
