"""
Cover Art Fetcher for YT-DLP EZ-UI.
Fetches album artwork from MusicBrainz Cover Art Archive and embeds it in audio files.
"""

import logging
from pathlib import Path
from typing import Optional
import requests
from mutagen.id3 import ID3, APIC
from mutagen import File as MutagenFile
import time


class CoverArtFetcher:
    """
    Fetches album artwork from MusicBrainz Cover Art Archive.
    Embeds artwork in audio files and saves as cover.jpg.
    """

    def __init__(self):
        """Initialize the cover art fetcher."""
        self.logger = logging.getLogger(__name__)
        self.cover_art_api_base = "https://coverartarchive.org/release-group"
        self.timeout = 10  # seconds
        self.max_retries = 2  # Retry on connection failures
        self.retry_delay = 1.5  # Seconds between retries

    def fetch_cover_art(self, release_group_id: str) -> Optional[bytes]:
        """
        Fetch album artwork from MusicBrainz Cover Art Archive with retry logic.

        Args:
            release_group_id: MusicBrainz Release Group ID (RGID)

        Returns:
            bytes: Image data, or None if not found/error
        """
        if not release_group_id:
            self.logger.warning("No release group ID provided")
            return None

        url = f"{self.cover_art_api_base}/{release_group_id}/front"
        self.logger.info(f"Fetching cover art from: {url}")

        # Retry loop for connection failures
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers={'User-Agent': 'YT-DLP-EZ-UI/4.0'}  # Identify ourselves
                )

                if response.status_code == 200:
                    self.logger.info(f"Cover art fetched successfully ({len(response.content)} bytes)")
                    return response.content
                elif response.status_code == 404:
                    self.logger.warning(f"No cover art found for release group {release_group_id}")
                    return None
                elif response.status_code == 503:
                    # Service unavailable - retry
                    if attempt < self.max_retries:
                        self.logger.warning(f"Service unavailable, retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        self.logger.error("Cover art service unavailable after retries")
                        return None
                else:
                    self.logger.error(f"Cover art fetch failed with status {response.status_code}")
                    return None

            except requests.Timeout:
                if attempt < self.max_retries:
                    self.logger.warning(f"Timeout, retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    self.logger.error(f"Cover art fetch timed out after {self.max_retries} retries")
                    return None

            except (requests.ConnectionError, ConnectionResetError) as e:
                if attempt < self.max_retries:
                    self.logger.warning(f"Connection failed, retrying in {self.retry_delay}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    self.logger.error(f"Cover art fetch failed after {self.max_retries} retries: Connection error")
                    return None

            except requests.RequestException as e:
                self.logger.error(f"Cover art fetch failed: {e}")
                return None

            except Exception as e:
                self.logger.error(f"Unexpected error fetching cover art: {e}")
                return None

        return None

    def save_cover_jpg(self, image_bytes: bytes, directory: Path) -> Optional[Path]:
        """
        Save cover art as cover.jpg in the specified directory.

        Args:
            image_bytes: Image data
            directory: Directory to save cover.jpg

        Returns:
            Path: Path to saved cover.jpg, or None on error
        """
        if not image_bytes:
            self.logger.warning("No image data provided")
            return None

        try:
            cover_path = directory / "cover.jpg"

            with open(cover_path, 'wb') as f:
                f.write(image_bytes)

            self.logger.info(f"Cover art saved to: {cover_path}")
            return cover_path

        except IOError as e:
            self.logger.error(f"Failed to save cover.jpg: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error saving cover art: {e}")
            return None

    def embed_cover_art(self, audio_file: Path, image_bytes: bytes) -> bool:
        """
        Embed album artwork into audio file using Mutagen.

        Args:
            audio_file: Path to audio file
            image_bytes: Image data to embed

        Returns:
            bool: True if successful, False otherwise
        """
        if not image_bytes:
            self.logger.warning("No image data provided for embedding")
            return False

        if not audio_file.exists():
            self.logger.error(f"Audio file does not exist: {audio_file}")
            return False

        try:
            # Determine MIME type based on image header
            mime_type = self._get_mime_type(image_bytes)

            # Load audio file
            audio = MutagenFile(str(audio_file))

            if audio is None:
                self.logger.error(f"Could not load audio file: {audio_file}")
                return False

            # Handle different audio formats
            file_ext = audio_file.suffix.lower()

            if file_ext in ['.mp3']:
                # MP3 uses ID3 tags
                return self._embed_id3(audio_file, image_bytes, mime_type)
            elif file_ext in ['.m4a', '.mp4']:
                # M4A uses different tag format
                return self._embed_mp4(audio, image_bytes)
            elif file_ext in ['.flac']:
                # FLAC uses VorbisComment
                return self._embed_flac(audio, image_bytes, mime_type)
            elif file_ext in ['.ogg', '.opus']:
                # Ogg/Opus uses VorbisComment
                return self._embed_vorbis(audio, image_bytes, mime_type)
            else:
                self.logger.warning(f"Unsupported audio format for embedding: {file_ext}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to embed cover art: {e}")
            return False

    def _get_mime_type(self, image_bytes: bytes) -> str:
        """
        Determine MIME type from image header.

        Args:
            image_bytes: Image data

        Returns:
            str: MIME type string
        """
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif image_bytes.startswith(b'\x89PNG'):
            return 'image/png'
        else:
            # Default to JPEG if unknown
            return 'image/jpeg'

    def _embed_id3(self, audio_file: Path, image_bytes: bytes, mime_type: str) -> bool:
        """
        Embed cover art in MP3 file using ID3 tags.

        Args:
            audio_file: Path to MP3 file
            image_bytes: Image data
            mime_type: MIME type of image

        Returns:
            bool: True if successful
        """
        try:
            # Load or create ID3 tags
            try:
                audio = ID3(str(audio_file))
            except:
                audio = ID3()

            # Add album artwork (APIC frame)
            audio.add(APIC(
                encoding=3,  # UTF-8
                mime=mime_type,
                type=3,  # Cover (front)
                desc='Cover',
                data=image_bytes
            ))

            audio.save(str(audio_file))
            self.logger.info(f"Cover art embedded in ID3 tags: {audio_file.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to embed ID3 cover art: {e}")
            return False

    def _embed_mp4(self, audio, image_bytes: bytes) -> bool:
        """
        Embed cover art in M4A/MP4 file.

        Args:
            audio: Mutagen audio object
            image_bytes: Image data

        Returns:
            bool: True if successful
        """
        try:
            from mutagen.mp4 import MP4Cover, MP4

            # Determine format
            if image_bytes.startswith(b'\xff\xd8\xff'):
                cover_format = MP4Cover.FORMAT_JPEG
            elif image_bytes.startswith(b'\x89PNG'):
                cover_format = MP4Cover.FORMAT_PNG
            else:
                cover_format = MP4Cover.FORMAT_JPEG

            audio['covr'] = [MP4Cover(image_bytes, imageformat=cover_format)]
            audio.save()
            self.logger.info("Cover art embedded in MP4 tags")
            return True

        except Exception as e:
            self.logger.error(f"Failed to embed MP4 cover art: {e}")
            return False

    def _embed_flac(self, audio, image_bytes: bytes, mime_type: str) -> bool:
        """
        Embed cover art in FLAC file.

        Args:
            audio: Mutagen audio object
            image_bytes: Image data
            mime_type: MIME type of image

        Returns:
            bool: True if successful
        """
        try:
            from mutagen.flac import Picture
            import base64

            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = mime_type
            picture.desc = 'Cover'
            picture.data = image_bytes

            audio.clear_pictures()
            audio.add_picture(picture)
            audio.save()
            self.logger.info("Cover art embedded in FLAC")
            return True

        except Exception as e:
            self.logger.error(f"Failed to embed FLAC cover art: {e}")
            return False

    def _embed_vorbis(self, audio, image_bytes: bytes, mime_type: str) -> bool:
        """
        Embed cover art in Ogg/Opus file using VorbisComment.

        Args:
            audio: Mutagen audio object
            image_bytes: Image data
            mime_type: MIME type of image

        Returns:
            bool: True if successful
        """
        try:
            from mutagen.flac import Picture
            import base64

            picture = Picture()
            picture.type = 3  # Cover (front)
            picture.mime = mime_type
            picture.desc = 'Cover'
            picture.data = image_bytes

            # Encode picture to base64 for VorbisComment
            picture_data = base64.b64encode(picture.write()).decode('ascii')
            audio['metadata_block_picture'] = [picture_data]

            audio.save()
            self.logger.info("Cover art embedded in Vorbis tags")
            return True

        except Exception as e:
            self.logger.error(f"Failed to embed Vorbis cover art: {e}")
            return False
