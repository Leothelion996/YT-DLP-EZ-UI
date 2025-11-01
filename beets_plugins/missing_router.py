"""
Missing Metadata Router Plugin for Beets.
Routes files with incomplete metadata to organized Missing Metadata folders.
"""

import json
import logging
import shutil
from pathlib import Path
from beets.plugins import BeetsPlugin
from beets import config
from beets.library import Item


class MissingRouterPlugin(BeetsPlugin):
    """
    Beets plugin to route files with missing metadata to categorized folders.
    Creates subfolders for different types of missing metadata and generates reports.
    """

    # Metadata categories
    MISSING_EVERYTHING = "Missing Everything"
    MISSING_TRACK_NAME = "Missing Track name"
    MISSING_ARTIST_NAME = "Missing Artist name"
    MISSING_ALBUM_COVER = "Missing Album cover"

    def __init__(self):
        """Initialize the missing metadata router plugin."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.register_listener('import_task_files', self.on_import_task_files)
        self.missing_files_report = []

    def on_import_task_files(self, session, task):
        """
        Hook called after import task processes files.
        Checks for missing metadata and routes accordingly.

        Args:
            session: Beets import session
            task: Current import task
        """
        if not hasattr(task, 'items'):
            return

        for item in task.items:
            missing_category = self._check_missing_metadata(item)
            if missing_category:
                self._route_to_missing_folder(item, missing_category)

    def _check_missing_metadata(self, item: Item) -> str:
        """
        Check what metadata is missing from an item.

        Args:
            item: Beets library item to check

        Returns:
            Missing category string, or None if metadata is complete
        """
        has_title = bool(item.title and item.title.strip())
        has_artist = bool(item.artist and item.artist.strip())
        has_album = bool(item.album and item.album.strip())
        has_cover = self._has_album_art(item)

        # Strictest case first: missing title AND artist
        if not has_title and not has_artist:
            return self.MISSING_EVERYTHING

        # Individual missing metadata
        if not has_title:
            return self.MISSING_TRACK_NAME

        if not has_artist:
            return self.MISSING_ARTIST_NAME

        # Has title and artist but no album cover
        if has_title and has_artist and not has_cover:
            return self.MISSING_ALBUM_COVER

        # All metadata present
        return None

    def _has_album_art(self, item: Item) -> bool:
        """
        Check if item has associated album art.

        Args:
            item: Beets library item

        Returns:
            True if album art exists, False otherwise
        """
        try:
            # Check if artpath is set and file exists
            if hasattr(item, 'artpath') and item.artpath:
                art_file = Path(item.artpath)
                return art_file.exists()
            return False
        except Exception as e:
            self.logger.warning(f"Error checking album art for {item.path}: {e}")
            return False

    def _route_to_missing_folder(self, item: Item, category: str) -> None:
        """
        Move or copy file to appropriate Missing Metadata subfolder.

        Args:
            item: Beets library item
            category: Missing metadata category
        """
        try:
            # Get library root from config
            library_path = config['directory'].as_filename()
            missing_root = Path(library_path) / "Missing Metadata" / category

            # Ensure target directory exists
            missing_root.mkdir(parents=True, exist_ok=True)

            # Get original filename
            source_path = Path(item.path)
            target_path = missing_root / source_path.name

            # Avoid overwrites with unique naming
            counter = 1
            while target_path.exists():
                stem = source_path.stem
                suffix = source_path.suffix
                target_path = missing_root / f"{stem}_{counter}{suffix}"
                counter += 1

            # Copy file to missing metadata folder
            shutil.copy2(source_path, target_path)

            # Add to report
            self.missing_files_report.append({
                "original_path": str(source_path),
                "new_path": str(target_path),
                "category": category,
                "title": item.title or "Unknown",
                "artist": item.artist or "Unknown",
                "album": item.album or "Unknown"
            })

            self.logger.info(f"Routed {source_path.name} to {category}")

        except Exception as e:
            self.logger.error(f"Failed to route {item.path} to {category}: {e}")

    def shutdown(self):
        """
        Called when beets session ends.
        Generate final report for missing metadata files.
        """
        if self.missing_files_report:
            self._generate_report()

    def _generate_report(self) -> None:
        """Generate JSON report of all missing metadata files."""
        try:
            library_path = config['directory'].as_filename()
            report_path = Path(library_path) / "Missing Metadata" / "report.json"

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_files": len(self.missing_files_report),
                    "files": self.missing_files_report
                }, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Missing metadata report saved to {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to generate missing metadata report: {e}")
