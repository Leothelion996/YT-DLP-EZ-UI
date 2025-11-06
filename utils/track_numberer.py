"""
Track number utility for YT-DLP EZ-UI.
Sets track numbers for audio files based on creation time (oldest = track 1).
"""

import logging
from pathlib import Path
from typing import List, Optional, Callable

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


class TrackNumberer:
    """
    Sets track numbers for audio files based on creation time.
    Oldest file → Track 1, Newest file → Last track number.
    """

    def __init__(self):
        """Initialize the track numberer."""
        self.logger = logging.getLogger(__name__)

    def is_available(self) -> bool:
        """
        Check if Mutagen is available.

        Returns:
            bool: True if Mutagen is available
        """
        return MUTAGEN_AVAILABLE

    def number_tracks(
        self,
        folder: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> dict:
        """
        Set track numbers for all MP3 files in a folder based on creation time.

        Args:
            folder: Path to folder containing audio files
            progress_callback: Optional callback for progress updates

        Returns:
            dict: Results with 'success', 'total', 'updated', 'failed' keys
        """
        if not MUTAGEN_AVAILABLE:
            error = "Mutagen library not available"
            self.logger.error(error)
            return {
                'success': False,
                'error': error,
                'total': 0,
                'updated': 0,
                'failed': 0
            }

        if not folder.exists() or not folder.is_dir():
            error = f"Folder does not exist: {folder}"
            self.logger.error(error)
            return {
                'success': False,
                'error': error,
                'total': 0,
                'updated': 0,
                'failed': 0
            }

        # Find all MP3 files
        audio_extensions = ['.mp3', '.m4a', '.flac', '.ogg', '.opus']
        files = []

        for ext in audio_extensions:
            found = list(folder.glob(f'*{ext}'))
            files.extend(found)

        if not files:
            msg = f"No audio files found in {folder.name}"
            self.logger.info(msg)
            if progress_callback:
                progress_callback(msg)
            return {
                'success': True,
                'total': 0,
                'updated': 0,
                'failed': 0
            }

        # Sort files by creation time (oldest first)
        files.sort(key=lambda f: f.stat().st_ctime)

        self.logger.info(f"Found {len(files)} audio files in {folder.name}, setting track numbers...")

        updated_count = 0
        failed_count = 0

        for idx, file_path in enumerate(files, start=1):
            try:
                # Report progress
                if progress_callback:
                    progress_callback(f"Setting track {idx}/{len(files)}: {file_path.name}")

                # Set track number
                success = self._set_track_number(file_path, idx)

                if success:
                    updated_count += 1
                    self.logger.info(f"Track {idx:02d}: {file_path.name}")
                else:
                    failed_count += 1
                    self.logger.warning(f"Failed to set track number for: {file_path.name}")

            except Exception as e:
                failed_count += 1
                self.logger.error(f"Error setting track number for {file_path.name}: {e}")

        # Summary
        self.logger.info(f"Track numbering complete: {updated_count} updated, {failed_count} failed")

        if progress_callback:
            progress_callback(f"Track numbering complete: {updated_count}/{len(files)} updated")

        return {
            'success': True,
            'total': len(files),
            'updated': updated_count,
            'failed': failed_count
        }

    def _set_track_number(self, file_path: Path, track_num: int) -> bool:
        """
        Set track number for a single audio file.

        Args:
            file_path: Path to audio file
            track_num: Track number to set

        Returns:
            bool: True if successful
        """
        try:
            # Handle different file types
            if file_path.suffix.lower() == '.mp3':
                # Use EasyID3 for MP3 files
                try:
                    tags = EasyID3(file_path)
                except ID3NoHeaderError:
                    # Create new tags if file has no ID3 header
                    tags = EasyID3()

                tags['tracknumber'] = str(track_num)
                tags.save(file_path)
                return True

            else:
                # For other formats, use generic Mutagen
                from mutagen import File as MutagenFile

                audio = MutagenFile(file_path)
                if audio is None:
                    return False

                # Set track number (format depends on file type)
                if hasattr(audio, 'tags'):
                    if audio.tags is None:
                        audio.add_tags()

                    # Try different tag formats
                    try:
                        audio.tags['tracknumber'] = str(track_num)
                    except:
                        try:
                            audio.tags['TRCK'] = str(track_num)
                        except:
                            pass

                    audio.save()
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Failed to set track number for {file_path.name}: {e}")
            return False
