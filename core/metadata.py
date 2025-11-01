"""
Metadata handler for YT-DLP EZ-UI.
Extracts and applies metadata to downloaded audio and video files.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TCON
import yt_dlp


class MetadataHandler:
    """
    Handles metadata extraction and application.
    Supports both video (MP4) and audio (MP3) files.
    """

    def __init__(self):
        """Initialize the metadata handler."""
        self.logger = logging.getLogger(__name__)

    def extract_metadata_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from a YouTube URL without downloading.

        Args:
            url: YouTube URL

        Returns:
            dict or None: Metadata dictionary, None on error
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                metadata = {
                    'title': info.get('title', ''),
                    'artist': info.get('uploader', ''),
                    'channel': info.get('channel', ''),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'duration': info.get('duration', 0),
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'view_count': info.get('view_count', 0),
                }

                self.logger.info(f"Extracted metadata for: {metadata.get('title')}")
                return metadata

        except Exception as e:
            self.logger.error(f"Failed to extract metadata from URL '{url}': {e}")
            return None

    def apply_metadata_to_mp3(
        self,
        file_path: str,
        title: str = None,
        artist: str = None,
        album: str = None,
        year: str = None,
        genre: str = None,
        track_number: str = None
    ) -> bool:
        """
        Apply ID3 metadata tags to an MP3 file.

        Args:
            file_path: Path to MP3 file
            title: Track title
            artist: Artist name
            album: Album name
            year: Release year
            genre: Genre
            track_number: Track number

        Returns:
            bool: True if successful
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                return False

            # Try to load existing tags, create new if doesn't exist
            try:
                audio = MP3(str(file_path), ID3=EasyID3)
            except:
                audio = MP3(str(file_path))
                audio.add_tags()

            # Apply tags
            if title:
                audio['title'] = title
            if artist:
                audio['artist'] = artist
            if album:
                audio['album'] = album
            if year:
                audio['date'] = year
            if genre:
                audio['genre'] = genre
            if track_number:
                audio['tracknumber'] = track_number

            audio.save()
            self.logger.info(f"Applied metadata to MP3: {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply MP3 metadata to '{file_path}': {e}")
            return False

    def apply_metadata_to_mp4(
        self,
        file_path: str,
        title: str = None,
        artist: str = None,
        year: str = None,
        comment: str = None
    ) -> bool:
        """
        Apply metadata tags to an MP4 file.

        Args:
            file_path: Path to MP4 file
            title: Video title
            artist: Channel/uploader name
            year: Upload year
            comment: Description or comment

        Returns:
            bool: True if successful
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                return False

            video = MP4(str(file_path))

            # Apply tags (MP4 uses different tag names)
            if title:
                video['\xa9nam'] = [title]  # Title
            if artist:
                video['\xa9ART'] = [artist]  # Artist
            if year:
                video['\xa9day'] = [year]  # Year
            if comment:
                video['\xa9cmt'] = [comment]  # Comment

            video.save()
            self.logger.info(f"Applied metadata to MP4: {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply MP4 metadata to '{file_path}': {e}")
            return False

    def apply_youtube_metadata(self, file_path: str, url: str) -> bool:
        """
        Extract metadata from YouTube URL and apply to file.
        Automatically detects file type (MP3 or MP4).

        Args:
            file_path: Path to downloaded file
            url: YouTube URL

        Returns:
            bool: True if successful
        """
        try:
            # Extract metadata from URL
            metadata = self.extract_metadata_from_url(url)
            if not metadata:
                self.logger.warning(f"No metadata extracted for {url}")
                return False

            file_path = Path(file_path)
            file_extension = file_path.suffix.lower()

            # Apply based on file type
            if file_extension == '.mp3':
                return self.apply_metadata_to_mp3(
                    str(file_path),
                    title=metadata.get('title'),
                    artist=metadata.get('uploader'),
                    year=self._format_year(metadata.get('upload_date'))
                )
            elif file_extension == '.mp4':
                return self.apply_metadata_to_mp4(
                    str(file_path),
                    title=metadata.get('title'),
                    artist=metadata.get('uploader'),
                    year=self._format_year(metadata.get('upload_date')),
                    comment=metadata.get('description')
                )
            else:
                self.logger.warning(f"Unsupported file type: {file_extension}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to apply YouTube metadata: {e}")
            return False

    def _format_year(self, upload_date: str) -> Optional[str]:
        """
        Extract year from upload_date string (format: YYYYMMDD).

        Args:
            upload_date: Upload date string

        Returns:
            str or None: Year as string
        """
        if upload_date and len(upload_date) >= 4:
            return upload_date[:4]
        return None

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read existing metadata from a file.

        Args:
            file_path: Path to audio/video file

        Returns:
            dict or None: Metadata dictionary
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return None

            file_extension = file_path.suffix.lower()

            if file_extension == '.mp3':
                audio = MP3(str(file_path), ID3=EasyID3)
                return {
                    'title': audio.get('title', [''])[0],
                    'artist': audio.get('artist', [''])[0],
                    'album': audio.get('album', [''])[0],
                    'year': audio.get('date', [''])[0],
                    'genre': audio.get('genre', [''])[0],
                }
            elif file_extension == '.mp4':
                video = MP4(str(file_path))
                return {
                    'title': video.get('\xa9nam', [''])[0],
                    'artist': video.get('\xa9ART', [''])[0],
                    'year': video.get('\xa9day', [''])[0],
                    'comment': video.get('\xa9cmt', [''])[0],
                }

            return None

        except Exception as e:
            self.logger.error(f"Failed to read metadata from '{file_path}': {e}")
            return None
