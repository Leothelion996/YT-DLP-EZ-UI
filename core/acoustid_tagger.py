"""
AcoustID fingerprint-based music tagger.
Tags files in-place using acoustic fingerprinting without moving them.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from threading import Thread
from datetime import datetime

try:
    import acoustid
    ACOUSTID_AVAILABLE = True
except ImportError:
    ACOUSTID_AVAILABLE = False

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

from utils.chromaprint_installer import ChromaprintInstaller
from config.constants import (
    FINGERPRINT_LOG_DIR,
    FINGERPRINT_DETAILED_LOG,
    FINGERPRINT_SUMMARY_LOG,
    FINGERPRINT_ERROR_LOG
)


class FingerprintLogger:
    """
    Dedicated logger for fingerprinting operations.
    Writes to multiple log files for comprehensive tracking.
    """

    def __init__(self):
        """Initialize fingerprint logger with multiple log files."""
        # Ensure log directory exists
        FINGERPRINT_LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Create separate loggers for different purposes
        self.detailed_logger = self._setup_logger('fingerprint_detailed', FINGERPRINT_DETAILED_LOG)
        self.summary_logger = self._setup_logger('fingerprint_summary', FINGERPRINT_SUMMARY_LOG)
        self.error_logger = self._setup_logger('fingerprint_error', FINGERPRINT_ERROR_LOG)

        # Start new session
        self._log_session_start()

    def _setup_logger(self, name: str, log_file: Path) -> logging.Logger:
        """Setup individual logger with file handler."""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()  # Clear any existing handlers

        # File handler
        handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        handler.setLevel(logging.DEBUG)

        # Detailed format with timestamp
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _log_session_start(self):
        """Log the start of a new fingerprinting session."""
        separator = "=" * 80
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for logger in [self.detailed_logger, self.summary_logger, self.error_logger]:
            logger.info(separator)
            logger.info(f"NEW FINGERPRINTING SESSION STARTED: {timestamp}")
            logger.info(separator)

    def detailed(self, message: str):
        """Log detailed step-by-step information."""
        self.detailed_logger.info(message)

    def summary(self, message: str):
        """Log high-level summary information."""
        self.summary_logger.info(message)
        self.detailed_logger.info(f"[SUMMARY] {message}")

    def error(self, message: str):
        """Log error information."""
        self.error_logger.error(message)
        self.detailed_logger.error(f"[ERROR] {message}")

    def section(self, title: str):
        """Log a section separator."""
        separator = "-" * 60
        self.detailed_logger.info(separator)
        self.detailed_logger.info(f"  {title}")
        self.detailed_logger.info(separator)


class AcoustIDTagger:
    """
    Tags audio files in-place using AcoustID fingerprinting.
    Does NOT move files - applies metadata where they are.
    """

    def __init__(self, api_key: str):
        """
        Initialize the tagger.

        Args:
            api_key: AcoustID API key
        """
        self.logger = logging.getLogger(__name__)
        self.fp_logger = FingerprintLogger()
        self.api_key = api_key

        self.fp_logger.section("INITIALIZING ACOUSTID TAGGER")
        self.fp_logger.detailed(f"AcoustID API Key configured: {api_key[:4]}...{api_key[-4:]}")

        # Get chromaprint path
        installer = ChromaprintInstaller()
        self.fpcalc_path = installer.get_fpcalc_path()

        if self.fpcalc_path:
            self.fp_logger.detailed(f"Chromaprint (fpcalc) found at: {self.fpcalc_path}")
            # Set environment variable for acoustid library
            os.environ['FPCALC'] = self.fpcalc_path
            self.fp_logger.detailed(f"Set FPCALC environment variable: {self.fpcalc_path}")
        else:
            self.fp_logger.error("WARNING: Chromaprint (fpcalc) NOT FOUND!")
            self.fp_logger.error("Fingerprinting will fail without fpcalc")

    def is_available(self) -> bool:
        """Check if all dependencies are available."""
        available = ACOUSTID_AVAILABLE and MUTAGEN_AVAILABLE and (self.fpcalc_path is not None)

        self.fp_logger.detailed(f"Dependency Check:")
        self.fp_logger.detailed(f"  - acoustid library: {ACOUSTID_AVAILABLE}")
        self.fp_logger.detailed(f"  - mutagen library: {MUTAGEN_AVAILABLE}")
        self.fp_logger.detailed(f"  - fpcalc executable: {self.fpcalc_path is not None}")
        self.fp_logger.detailed(f"  - Overall availability: {available}")

        return available

    def tag_directory(
        self,
        directory: str,
        progress_callback: Optional[Callable[[str], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> bool:
        """
        Tag all audio files in a directory using fingerprinting.

        Args:
            directory: Path to directory containing audio files
            progress_callback: Callback for progress updates
            completion_callback: Callback on completion

        Returns:
            bool: True if tagging started successfully
        """
        self.fp_logger.section(f"STARTING DIRECTORY TAGGING")
        self.fp_logger.detailed(f"Target directory: {directory}")

        if not self.is_available():
            error = "AcoustID, Mutagen, or Chromaprint not available"
            self.fp_logger.error(error)
            if completion_callback:
                completion_callback(False, error)
            return False

        # Find audio files
        self.fp_logger.detailed("Searching for audio files...")
        audio_files = self._find_audio_files(directory)

        if not audio_files:
            error = f"No audio files found in {directory}"
            self.fp_logger.error(error)
            if completion_callback:
                completion_callback(False, error)
            return False

        self.fp_logger.summary(f"Found {len(audio_files)} audio files to fingerprint")
        for i, file_path in enumerate(audio_files, 1):
            self.fp_logger.detailed(f"  [{i}] {file_path.name}")

        # Start tagging in background thread
        thread = Thread(
            target=self._tag_worker,
            args=(audio_files, progress_callback, completion_callback),
            daemon=True
        )
        thread.start()

        self.fp_logger.detailed("Background tagging thread started")
        return True

    def _find_audio_files(self, directory: str, max_age_seconds: int = 300) -> List[Path]:
        """
        Find recently created audio files in directory.

        Args:
            directory: Directory to search
            max_age_seconds: Only include files created/modified within this many seconds (default: 5 minutes)

        Returns:
            List of audio file paths
        """
        import time
        audio_extensions = ['.mp3', '.m4a', '.flac', '.ogg', '.opus']
        directory_path = Path(directory)

        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        self.fp_logger.detailed(f"Searching for audio files modified in last {max_age_seconds} seconds")
        self.fp_logger.detailed(f"Current time: {current_time}")
        self.fp_logger.detailed(f"Cutoff time: {cutoff_time}")

        audio_files = []
        all_files_count = 0

        for ext in audio_extensions:
            found = list(directory_path.rglob(f'*{ext}'))
            all_files_count += len(found)

            # Filter by modification time
            recent_files = [f for f in found if f.stat().st_mtime >= cutoff_time]

            if recent_files:
                self.fp_logger.detailed(f"Found {len(recent_files)} recent {ext} files (out of {len(found)} total)")
                for f in recent_files:
                    mod_time = f.stat().st_mtime
                    age = current_time - mod_time
                    self.fp_logger.detailed(f"  - {f.name} (modified {age:.1f} seconds ago)")
                audio_files.extend(recent_files)

        self.fp_logger.summary(f"Total files in directory: {all_files_count}")
        self.fp_logger.summary(f"Recent files to fingerprint: {len(audio_files)}")

        return audio_files

    def _tag_worker(
        self,
        files: List[Path],
        progress_callback: Optional[Callable[[str], None]],
        completion_callback: Optional[Callable[[bool, Optional[str]], None]]
    ):
        """Worker thread to tag files."""
        self.fp_logger.section("WORKER THREAD STARTED")

        try:
            total = len(files)
            successful = 0
            failed = 0
            results = []

            for i, file_path in enumerate(files, 1):
                self.fp_logger.section(f"PROCESSING FILE {i}/{total}")
                self.fp_logger.detailed(f"File: {file_path}")
                self.fp_logger.detailed(f"Size: {file_path.stat().st_size / 1024:.2f} KB")

                if progress_callback:
                    progress_callback(f"Fingerprinting {i}/{total}: {file_path.name}")

                try:
                    # Fingerprint and tag the file
                    result = self._tag_file(file_path)

                    if result['success']:
                        successful += 1
                        self.fp_logger.summary(f"[{i}/{total}] SUCCESS: {file_path.name}")
                        self.fp_logger.summary(f"           Tagged as: {result.get('artist', '?')} - {result.get('title', '?')}")
                    else:
                        failed += 1
                        self.fp_logger.error(f"[{i}/{total}] FAILED: {file_path.name}")
                        self.fp_logger.error(f"          Reason: {result.get('error', 'Unknown')}")

                    results.append(result)

                except Exception as e:
                    failed += 1
                    self.fp_logger.error(f"[{i}/{total}] EXCEPTION: {file_path.name}")
                    self.fp_logger.error(f"          Exception: {str(e)}")
                    results.append({
                        'success': False,
                        'file': str(file_path),
                        'error': str(e)
                    })

            # Complete
            self.fp_logger.section("TAGGING SESSION COMPLETE")
            self.fp_logger.summary(f"Total files: {total}")
            self.fp_logger.summary(f"Successful: {successful}")
            self.fp_logger.summary(f"Failed: {failed}")
            self.fp_logger.summary(f"Success rate: {(successful/total*100):.1f}%")

            summary = f"Tagged {successful} files successfully, {failed} failed"

            if progress_callback:
                progress_callback(summary)

            if completion_callback:
                completion_callback(True, None)

        except Exception as e:
            error_msg = f"Tagging failed: {e}"
            self.fp_logger.error(f"CRITICAL ERROR: {error_msg}")
            if completion_callback:
                completion_callback(False, error_msg)

    def _tag_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Fingerprint and tag a single file.

        Args:
            file_path: Path to audio file

        Returns:
            dict: Result with success status and metadata
        """
        result = {
            'success': False,
            'file': str(file_path),
            'error': None
        }

        try:
            self.fp_logger.detailed("STEP 1: Generating acoustic fingerprint")
            self.fp_logger.detailed(f"  Using fpcalc at: {self.fpcalc_path}")

            # Get fingerprint - explicitly set fpcalc path
            try:
                duration, fingerprint = acoustid.fingerprint_file(
                    str(file_path),
                    force_fpcalc=self.fpcalc_path if self.fpcalc_path else None
                )
                self.fp_logger.detailed(f"  Duration: {duration} seconds")
                self.fp_logger.detailed(f"  Fingerprint length: {len(fingerprint)} chars")
                self.fp_logger.detailed(f"  Fingerprint: {fingerprint[:100]}...")
            except Exception as fp_error:
                self.fp_logger.error(f"  Fingerprint generation FAILED: {fp_error}")
                result['error'] = f"Fingerprint failed: {fp_error}"
                return result

            self.fp_logger.detailed("STEP 2: Querying AcoustID database")
            self.fp_logger.detailed(f"  API Key: {self.api_key[:4]}...{self.api_key[-4:]}")

            # Look up in AcoustID
            try:
                lookup_results = acoustid.lookup(
                    self.api_key,
                    fingerprint,
                    duration,
                    meta='recordings releasegroups'
                )
                self.fp_logger.detailed(f"  AcoustID response received")
                self.fp_logger.detailed(f"  Response keys: {list(lookup_results.keys())}")

                # Check for API error in response
                if 'error' in lookup_results:
                    error_msg = lookup_results.get('error', {}).get('message', 'Unknown error')
                    self.fp_logger.error(f"  AcoustID API ERROR: {error_msg}")
                    self.fp_logger.error(f"  Full error response: {lookup_results['error']}")
                    result['error'] = f"AcoustID API error: {error_msg}"
                    return result

            except Exception as lookup_error:
                self.fp_logger.error(f"  AcoustID lookup FAILED: {lookup_error}")
                result['error'] = f"AcoustID lookup failed: {lookup_error}"
                return result

            if not lookup_results or 'results' not in lookup_results or not lookup_results['results']:
                self.fp_logger.error(f"  No match found in AcoustID database")
                self.fp_logger.error(f"  This could mean:")
                self.fp_logger.error(f"    - The audio is not in the AcoustID/MusicBrainz database")
                self.fp_logger.error(f"    - The audio quality is too poor for fingerprinting")
                self.fp_logger.error(f"    - The fingerprint didn't match any known recordings")
                result['error'] = "No match found"
                return result

            self.fp_logger.detailed(f"  Found {len(lookup_results['results'])} matches")

            # Get best match
            match = lookup_results['results'][0]
            match_score = match.get('score', 0)
            self.fp_logger.detailed(f"  Best match score: {match_score}")

            if 'recordings' not in match or not match['recordings']:
                self.fp_logger.error(f"  No recordings in match")
                result['error'] = "No recordings found"
                return result

            recording = match['recordings'][0]
            self.fp_logger.detailed(f"  Recording ID: {recording.get('id', 'unknown')}")

            self.fp_logger.detailed("STEP 3: Extracting metadata")

            # Extract metadata
            title = recording.get('title', '')
            self.fp_logger.detailed(f"  Title: {title}")

            artist = recording['artists'][0]['name'] if 'artists' in recording and recording['artists'] else ''
            self.fp_logger.detailed(f"  Artist: {artist}")

            # Get album info from release groups
            album = ''
            year = ''
            if 'releasegroups' in recording and recording['releasegroups']:
                release_group = recording['releasegroups'][0]
                album = release_group.get('title', '')
                self.fp_logger.detailed(f"  Album: {album}")

                if 'first-release-date' in release_group:
                    year = release_group['first-release-date'][:4]
                    self.fp_logger.detailed(f"  Year: {year}")

            self.fp_logger.detailed("STEP 4: Writing metadata tags to file")

            # Apply tags
            self._write_tags(file_path, title, artist, album, year)

            self.fp_logger.detailed("  Tags written successfully")

            result['success'] = True
            result['title'] = title
            result['artist'] = artist
            result['album'] = album
            result['year'] = year

            return result

        except Exception as e:
            self.fp_logger.error(f"EXCEPTION in _tag_file: {e}")
            result['error'] = str(e)
            return result

    def _write_tags(self, file_path: Path, title: str, artist: str, album: str, year: str):
        """
        Write ID3 tags to audio file.

        Args:
            file_path: Path to audio file
            title: Track title
            artist: Artist name
            album: Album name
            year: Release year
        """
        try:
            self.fp_logger.detailed(f"  Opening file with Mutagen")
            audio = MutagenFile(str(file_path), easy=True)

            if audio is None:
                self.fp_logger.error(f"  Could not open file for tagging")
                return

            # Set tags
            if title:
                audio['title'] = title
                self.fp_logger.detailed(f"  Set title: {title}")
            if artist:
                audio['artist'] = artist
                self.fp_logger.detailed(f"  Set artist: {artist}")
            if album:
                audio['album'] = album
                self.fp_logger.detailed(f"  Set album: {album}")
            if year:
                audio['date'] = year
                self.fp_logger.detailed(f"  Set year: {year}")

            audio.save()
            self.fp_logger.detailed(f"  File saved with new tags")

        except Exception as e:
            self.fp_logger.error(f"  Failed to write tags: {e}")
