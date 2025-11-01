"""
Download manager module for YT-DLP EZ-UI.
Wrapper around yt-dlp for downloading YouTube videos with progress tracking.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from threading import Thread, Lock, Event
import yt_dlp
from utils.file_utils import FileUtils


class YtDlpLogger:
    """
    Custom logger for yt-dlp to capture progress messages.
    """

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize the logger.

        Args:
            progress_callback: Callback to receive progress messages
        """
        self.progress_callback = progress_callback

    def debug(self, msg):
        """Capture debug messages from yt-dlp."""
        if self.progress_callback and msg:
            # Parse playlist progress messages
            # Example: "[download] Downloading video 5 of 20"
            match = re.search(r'\[download\].*?(\d+)\s+of\s+(\d+)', msg)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                self.progress_callback({'playlist_index': current, 'playlist_count': total, 'status': 'downloading', 'msg': msg})

    def warning(self, msg):
        """Capture warning messages."""
        pass

    def error(self, msg):
        """Capture error messages."""
        pass


class DownloadManager:
    """
    Manages YouTube downloads using yt-dlp.
    Handles single videos, playlists, and provides progress callbacks.
    """

    def __init__(self):
        """Initialize the download manager."""
        self.logger = logging.getLogger(__name__)
        self._active_downloads: Dict[str, bool] = {}
        self._lock = Lock()
        self._cancel_event = Event()  # Thread-safe cancellation flag

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch video metadata without downloading.

        Args:
            url: YouTube video or playlist URL

        Returns:
            dict or None: Video information, None on error
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                # Handle playlist vs single video
                if 'entries' in info:
                    # It's a playlist
                    return {
                        'type': 'playlist',
                        'title': info.get('title', 'Unknown Playlist'),
                        'uploader': info.get('uploader', 'Unknown'),
                        'video_count': len(info['entries']),
                        'entries': info['entries']
                    }
                else:
                    # Single video
                    return {
                        'type': 'video',
                        'title': info.get('title', 'Unknown Title'),
                        'uploader': info.get('uploader', 'Unknown Channel'),
                        'duration': info.get('duration', 0),
                        'upload_date': info.get('upload_date', ''),
                        'description': info.get('description', ''),
                        'thumbnail': info.get('thumbnail', '')
                    }

        except Exception as e:
            self.logger.error(f"Failed to fetch video info for '{url}': {e}")
            return None

    def _build_ydl_opts(
        self,
        output_dir: str,
        file_format: str,
        quality: str,
        progress_callback: Optional[Callable] = None,
        folder_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build yt-dlp options dictionary based on user preferences.

        Args:
            output_dir: Output directory path
            file_format: 'video' or 'audio'
            quality: Quality string (e.g., '1080p', '320kbps', 'Best Available')
            progress_callback: Optional callback for progress updates
            folder_name: Optional folder name to organize downloads

        Returns:
            dict: yt-dlp options
        """
        # Build output template with folder structure
        if folder_name:
            # Create folder per video/playlist: output_dir/FolderName/filename.ext
            from utils.file_utils import FileUtils
            safe_folder = FileUtils.get_safe_filename(folder_name)
            output_template = os.path.join(output_dir, safe_folder, '%(title)s.%(ext)s')
        else:
            # Fallback to flat structure with auto folder creation based on title
            output_template = os.path.join(output_dir, '%(title)s', '%(title)s.%(ext)s')

        # Base options
        opts = {
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
        }

        # Progress hook
        if progress_callback:
            opts['progress_hooks'] = [progress_callback]
            # Add custom logger to capture playlist progress
            opts['logger'] = YtDlpLogger(progress_callback)

        # Format selection based on file type and quality
        if file_format == 'audio':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }]

            # Set audio quality
            if quality != 'Best Available':
                # Extract bitrate number (e.g., '320kbps' -> '320')
                bitrate = quality.replace('kbps', '').strip()
                opts['postprocessors'][0]['preferredquality'] = bitrate

        else:  # video
            if quality == 'Best Available':
                opts['format'] = 'bestvideo+bestaudio/best'
            else:
                # Map quality to format selection
                height = quality.replace('p', '').replace('K', '2160')
                if height == '4':
                    height = '2160'

                opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'

            # Merge to mp4
            opts['merge_output_format'] = 'mp4'

        return opts

    def download(
        self,
        url: str,
        output_dir: str,
        file_format: str = 'video',
        quality: str = 'Best Available',
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> bool:
        """
        Download a YouTube video or playlist.

        Args:
            url: YouTube URL
            output_dir: Output directory
            file_format: 'video' or 'audio'
            quality: Quality string
            progress_callback: Callback for progress updates (dict with progress info)
            completion_callback: Callback on successful completion
            error_callback: Callback on error (receives error message)

        Returns:
            bool: True if download started successfully
        """
        # Check for cancellation before starting
        if self.is_cancelled():
            error_msg = "Download cancelled before start"
            self.logger.warning(error_msg)
            if error_callback:
                error_callback(error_msg)
            return False

        # Validate output directory
        if not FileUtils.is_valid_directory(output_dir):
            error_msg = f"Invalid output directory: {output_dir}"
            self.logger.error(error_msg)
            if error_callback:
                error_callback(error_msg)
            return False

        if not FileUtils.is_writable_directory(output_dir):
            error_msg = f"Output directory is not writable: {output_dir}"
            self.logger.error(error_msg)
            if error_callback:
                error_callback(error_msg)
            return False

        # Fetch metadata first to get video/playlist title for folder name
        try:
            video_info = self.get_video_info(url)
            folder_name = None

            if video_info:
                if video_info['type'] == 'playlist':
                    folder_name = video_info['title']
                    self.logger.info(f"Creating folder for playlist: {folder_name}")
                else:
                    folder_name = video_info['title']
                    self.logger.info(f"Creating folder for video: {folder_name}")

            # Wrap progress callback to check for cancellation
            def cancellable_progress_callback(progress_dict):
                # Check cancellation flag
                if self.is_cancelled():
                    self.logger.warning(f"Download cancelled by user: {url}")
                    raise Exception("Download cancelled by user")

                # Call original callback if provided
                if progress_callback:
                    progress_callback(progress_dict)

            # Build yt-dlp options with folder structure
            ydl_opts = self._build_ydl_opts(
                output_dir,
                file_format,
                quality,
                cancellable_progress_callback,
                folder_name
            )

            # Mark as active download
            with self._lock:
                self._active_downloads[url] = True

            # Perform download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info(f"Starting download: {url}")
                ydl.download([url])
                self.logger.info(f"Download completed: {url}")

                # Mark as completed
                with self._lock:
                    self._active_downloads[url] = False

                # Check if cancelled after completion (shouldn't call completion callback)
                if self.is_cancelled():
                    self.logger.warning(f"Download cancelled after completion: {url}")
                    return False

                if completion_callback:
                    completion_callback()

                return True

        except Exception as e:
            error_msg = f"Download failed for '{url}': {str(e)}"

            # Different logging for cancellation vs errors
            if "cancelled by user" in str(e).lower():
                self.logger.warning(error_msg)
            else:
                self.logger.error(error_msg)

            with self._lock:
                self._active_downloads[url] = False

            if error_callback:
                error_callback(error_msg)

            return False

    def download_async(
        self,
        url: str,
        output_dir: str,
        file_format: str = 'video',
        quality: str = 'Best Available',
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None
    ) -> Thread:
        """
        Download asynchronously in a separate thread.

        Args:
            url: YouTube URL
            output_dir: Output directory
            file_format: 'video' or 'audio'
            quality: Quality string
            progress_callback: Callback for progress updates
            completion_callback: Callback on completion
            error_callback: Callback on error

        Returns:
            Thread: The download thread
        """
        thread = Thread(
            target=self.download,
            args=(url, output_dir, file_format, quality),
            kwargs={
                'progress_callback': progress_callback,
                'completion_callback': completion_callback,
                'error_callback': error_callback
            },
            daemon=True
        )
        thread.start()
        return thread

    def is_downloading(self, url: str) -> bool:
        """
        Check if a URL is currently being downloaded.

        Args:
            url: YouTube URL

        Returns:
            bool: True if currently downloading
        """
        with self._lock:
            return self._active_downloads.get(url, False)

    def get_active_downloads_count(self) -> int:
        """
        Get the number of active downloads.

        Returns:
            int: Number of active downloads
        """
        with self._lock:
            return sum(1 for active in self._active_downloads.values() if active)

    def cancel_all(self):
        """
        Cancel all active downloads.
        Sets the cancellation flag which will be checked by running downloads.
        """
        self.logger.warning("Cancellation requested - setting cancel flag")
        self._cancel_event.set()

    def reset_cancel(self):
        """
        Reset the cancellation flag for new download sessions.
        """
        self._cancel_event.clear()

    def is_cancelled(self) -> bool:
        """
        Check if cancellation has been requested.

        Returns:
            bool: True if cancellation is requested
        """
        return self._cancel_event.is_set()
