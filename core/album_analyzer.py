"""
Album metadata analyzer for YT-DLP EZ-UI.
Analyzes multiple tagged files to determine consensus album information.
Uses smart heuristics to normalize albums from playlists.
"""

import logging
from typing import List, Dict, Optional, Tuple
from collections import Counter
from pathlib import Path
import re

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


class AlbumAnalyzer:
    """
    Analyzes album metadata across multiple files to find consensus values.
    Used when a playlist is marked as an album to normalize metadata.

    Features:
    - Consensus album detection with confidence scoring
    - Artist consistency validation
    - Track number normalization
    - Handles compilation albums and various artist scenarios
    - Filters out "Greatest Hits" and compilation noise
    """

    # Album types to deprioritize (usually not the main album)
    DEPRIORITIZED_ALBUM_TYPES = [
        'greatest hits', 'best of', 'compilation', 'collected',
        'anthology', 'music bank', 'box set', 'live', 'remaster',
        'deluxe', 'expanded', 'bonus', 'special edition'
    ]

    def __init__(self):
        """Initialize the album analyzer."""
        self.logger = logging.getLogger(__name__)

    def analyze_album_metadata(self, files: List[Dict]) -> Optional[str]:
        """
        Analyze tagged files to determine consensus album name using smart heuristics.

        Args:
            files: List of file dictionaries with metadata
                   Expected keys: 'path', 'title', 'artist', 'album' (optional)

        Returns:
            str: Consensus album name, or None if no consensus found
        """
        if not files:
            self.logger.warning("No files provided for album analysis")
            return None

        self.logger.info(f"Analyzing {len(files)} files for album consensus")

        # Extract all album names with their frequencies
        album_names = []
        for file_data in files:
            album = file_data.get('album', '').strip()
            if album and album.upper() not in ['UNKNOWN', 'N/A', '']:
                album_names.append(album)

        if not album_names:
            self.logger.warning("No valid album names found in tagged files")
            return None

        # Count frequency of each album name
        album_counter = Counter(album_names)
        self.logger.info(f"Found {len(album_counter)} unique album names: {dict(album_counter)}")

        # Score each album based on multiple factors
        album_scores = {}
        for album, count in album_counter.items():
            score = self._score_album(album, count, len(files))
            album_scores[album] = score
            self.logger.info(f"  '{album}': {count} occurrences, score={score:.2f}")

        # Get the highest scoring album
        if album_scores:
            best_album = max(album_scores, key=album_scores.get)
            best_score = album_scores[best_album]
            count = album_counter[best_album]
            percentage = (count / len(files)) * 100

            self.logger.info(
                f"Selected consensus album: '{best_album}' "
                f"(score={best_score:.2f}, {count}/{len(files)} files, {percentage:.1f}%)"
            )

            return best_album

        return None

    def _score_album(self, album_name: str, occurrence_count: int, total_files: int) -> float:
        """
        Score an album based on multiple heuristics.

        Args:
            album_name: Name of the album
            occurrence_count: How many files have this album
            total_files: Total number of files being analyzed

        Returns:
            float: Score (higher is better)
        """
        # Base score from frequency (0-100)
        frequency_score = (occurrence_count / total_files) * 100

        # Penalty for deprioritized album types
        album_lower = album_name.lower()
        penalty = 0
        for deprioritized_type in self.DEPRIORITIZED_ALBUM_TYPES:
            if deprioritized_type in album_lower:
                penalty += 30  # Heavy penalty for compilations, greatest hits, etc.
                self.logger.debug(f"Applied penalty to '{album_name}' for '{deprioritized_type}'")

        # Bonus for shorter album names (more likely to be studio albums)
        # Very long names often indicate compilations or special editions
        length_bonus = 0
        if len(album_name) < 30:
            length_bonus = 10
        elif len(album_name) > 50:
            penalty += 10

        # Bonus for clean album names (no special characters suggesting compilation)
        if not re.search(r'[:\(\)\[\]]', album_name):
            length_bonus += 5

        final_score = frequency_score + length_bonus - penalty
        return max(0, final_score)  # Never go below zero

    def apply_consensus_album(self, files: List[Dict], consensus_album: str) -> List[Dict]:
        """
        Apply consensus album name to ALL files in the list and normalize track numbers.
        Track numbers are assigned based on file creation time (download order).

        Args:
            files: List of file dictionaries with 'path' key
            consensus_album: Album name to apply

        Returns:
            list: Updated file dictionaries with consensus album and sequential track numbers
        """
        if not consensus_album:
            self.logger.warning("No consensus album provided")
            return files

        self.logger.info(f"Applying consensus album '{consensus_album}' to ALL {len(files)} files")

        # Sort files by creation time (oldest first = track 1)
        from pathlib import Path
        sorted_files = sorted(files, key=lambda f: Path(f['path']).stat().st_ctime)

        updated_files = []
        for track_num, file_data in enumerate(sorted_files, start=1):
            # Create a copy to avoid modifying original
            updated_file = file_data.copy()

            # ALWAYS overwrite album to consensus (this is the point!)
            old_album = updated_file.get('album', 'UNKNOWN')
            updated_file['album'] = consensus_album

            # Assign sequential track number based on download order
            updated_file['track'] = track_num

            title = updated_file.get('title', 'Unknown')
            if old_album != consensus_album:
                self.logger.info(
                    f"  Track {track_num}: '{title}' - Album '{old_album}' → '{consensus_album}'"
                )
            else:
                self.logger.info(
                    f"  Track {track_num}: '{title}'"
                )

            updated_files.append(updated_file)

        self.logger.info(f"Successfully normalized {len(updated_files)} files to album '{consensus_album}' with sequential track numbers")

        # CRITICAL: Write the updated metadata back to the actual files
        self._write_metadata_to_files(updated_files)

        return updated_files

    def _write_metadata_to_files(self, files: List[Dict]) -> None:
        """
        Write updated album and track number metadata to actual MP3/audio files.

        Args:
            files: List of file dictionaries with 'path', 'album', 'track' keys
        """
        if not MUTAGEN_AVAILABLE:
            self.logger.error("Mutagen not available - cannot write metadata to files")
            return

        self.logger.info(f"Writing updated metadata to {len(files)} files")

        for file_data in files:
            file_path = Path(file_data['path'])
            album = file_data.get('album')
            track_num = file_data.get('track')

            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                continue

            try:
                # Determine file type and use appropriate Mutagen handler
                file_ext = file_path.suffix.lower()

                if file_ext == '.mp3':
                    audio = EasyID3(str(file_path))
                elif file_ext in ['.m4a', '.mp4']:
                    audio = MP4(str(file_path))
                elif file_ext == '.flac':
                    audio = FLAC(str(file_path))
                elif file_ext in ['.ogg', '.opus']:
                    audio = OggVorbis(str(file_path))
                else:
                    self.logger.warning(f"Unsupported file format: {file_ext}")
                    continue

                # Write album name
                if album:
                    if file_ext in ['.m4a', '.mp4']:
                        audio['\xa9alb'] = [album]  # MP4 uses different tag names
                    else:
                        audio['album'] = album

                # Write track number
                if track_num:
                    if file_ext in ['.m4a', '.mp4']:
                        audio['trkn'] = [(track_num, 0)]  # MP4 format: (track, total)
                    else:
                        audio['tracknumber'] = str(track_num)

                # Save changes to file
                audio.save()
                self.logger.info(f"Updated metadata for: {file_path.name} (Album: '{album}', Track: {track_num})")

            except Exception as e:
                self.logger.error(f"Failed to write metadata to {file_path.name}: {e}")

    def get_album_statistics(self, files: List[Dict]) -> Dict[str, int]:
        """
        Get statistics about album names in the file list.

        Args:
            files: List of file dictionaries

        Returns:
            dict: Album name -> count mapping
        """
        album_names = []
        for file_data in files:
            album = file_data.get('album', '').strip()
            if album and album.upper() not in ['UNKNOWN', 'N/A', '']:
                album_names.append(album)

        return dict(Counter(album_names))

    def get_consensus_artist(self, files: List[Dict]) -> Optional[str]:
        """
        Determine the consensus artist from all files.

        Args:
            files: List of file dictionaries

        Returns:
            str: Consensus artist name, or None if no consensus
        """
        if not files:
            return None

        artist_names = []
        for file_data in files:
            artist = file_data.get('artist', '').strip()
            if artist and artist.upper() not in ['UNKNOWN', 'N/A', '', 'VARIOUS ARTISTS']:
                artist_names.append(artist)

        if not artist_names:
            self.logger.warning("No valid artist names found")
            return None

        artist_counter = Counter(artist_names)
        most_common = artist_counter.most_common(1)

        if most_common:
            consensus_artist, count = most_common[0]
            percentage = (count / len(artist_names)) * 100

            self.logger.info(
                f"Consensus artist: '{consensus_artist}' "
                f"({count}/{len(artist_names)} occurrences, {percentage:.1f}%)"
            )

            # Only return if at least 60% agreement
            if percentage >= 60:
                return consensus_artist

        return None

    def validate_album_consistency(self, files: List[Dict]) -> Tuple[bool, str]:
        """
        Validate if files appear to be from the same album.

        Args:
            files: List of file dictionaries

        Returns:
            tuple: (is_consistent, reason)
        """
        if not files:
            return False, "No files provided"

        # Check artist consistency
        artists = [f.get('artist', '').strip() for f in files if f.get('artist')]
        unique_artists = set(artists)

        if len(unique_artists) > 3:
            self.logger.warning(f"Found {len(unique_artists)} different artists - likely a compilation")
            return False, f"Too many different artists ({len(unique_artists)})"

        # Check if we have album data
        albums = [f.get('album', '').strip() for f in files if f.get('album') and f.get('album').upper() not in ['UNKNOWN', 'N/A']]

        if not albums:
            return False, "No album metadata found"

        unique_albums = set(albums)
        self.logger.info(f"Found {len(unique_albums)} unique albums across {len(files)} files")

        return True, f"Valid album data: {len(unique_albums)} unique album names"

    def apply_consensus_artist(self, files: List[Dict], consensus_artist: str) -> None:
        """
        Apply consensus artist name to ALL files in the list.
        Writes metadata directly to files using Mutagen.

        Args:
            files: List of file dictionaries with 'path' key
            consensus_artist: Artist name to apply

        v5.1: Added for folder metadata review dialog
        """
        if not consensus_artist:
            self.logger.warning("No consensus artist provided")
            return

        if not MUTAGEN_AVAILABLE:
            self.logger.error("Mutagen not available - cannot write metadata to files")
            return

        self.logger.info(f"Applying consensus artist '{consensus_artist}' to ALL {len(files)} files")

        updated_count = 0
        failed_count = 0

        for file_data in files:
            file_path = Path(file_data['path'])

            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                failed_count += 1
                continue

            try:
                # Determine file type and use appropriate Mutagen handler
                file_ext = file_path.suffix.lower()

                if file_ext == '.mp3':
                    audio = EasyID3(str(file_path))
                elif file_ext in ['.m4a', '.mp4']:
                    audio = MP4(str(file_path))
                elif file_ext == '.flac':
                    audio = FLAC(str(file_path))
                elif file_ext in ['.ogg', '.opus']:
                    audio = OggVorbis(str(file_path))
                else:
                    self.logger.warning(f"Unsupported file format: {file_ext}")
                    failed_count += 1
                    continue

                # Write artist name
                old_artist = file_data.get('artist', 'UNKNOWN')
                if file_ext in ['.m4a', '.mp4']:
                    audio['\xa9ART'] = [consensus_artist]  # MP4 uses different tag names
                else:
                    audio['artist'] = consensus_artist

                # Save changes to file
                audio.save()

                # Update file_data dictionary for consistency
                file_data['artist'] = consensus_artist

                if old_artist != consensus_artist:
                    self.logger.info(
                        f"Updated artist for {file_path.name}: '{old_artist}' → '{consensus_artist}'"
                    )
                else:
                    self.logger.info(f"Confirmed artist for {file_path.name}: '{consensus_artist}'")

                updated_count += 1

            except Exception as e:
                self.logger.error(f"Failed to write metadata to {file_path.name}: {e}")
                failed_count += 1

        self.logger.info(
            f"Successfully applied artist '{consensus_artist}' to {updated_count}/{len(files)} files "
            f"({failed_count} failed)"
        )
