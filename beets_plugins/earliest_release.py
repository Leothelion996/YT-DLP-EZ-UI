"""
Earliest Release Selection Plugin for Beets.
Selects the earliest official release when multiple releases exist for a recording.
"""

import logging
from datetime import datetime
from beets.plugins import BeetsPlugin
from beets.autotag.hooks import AlbumInfo


class EarliestReleasePlugin(BeetsPlugin):
    """
    Beets plugin to prefer the earliest official release from MusicBrainz.
    When multiple releases exist for a recording, selects based on:
    1. Official releases over bootlegs/promos
    2. Earliest release date (year, then month/day)
    3. Most complete tracklist if dates are identical
    """

    def __init__(self):
        """Initialize the earliest release plugin."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.register_listener('album_candidates', self.on_album_candidates)

    def on_album_candidates(self, session, task):
        """
        Hook called when album candidates are available.
        Re-orders candidates to prefer earliest official release.

        Args:
            session: Beets import session
            task: Current import task with candidates
        """
        if not task.candidates:
            return

        try:
            # Sort candidates by release preference
            task.candidates.sort(key=lambda c: self._get_release_score(c.info))
            self.logger.debug(f"Sorted {len(task.candidates)} candidates by earliest release")
        except Exception as e:
            self.logger.error(f"Error sorting album candidates: {e}")

    def _get_release_score(self, album_info: AlbumInfo) -> tuple:
        """
        Calculate a score tuple for sorting releases.
        Lower scores are preferred (earliest, official releases first).

        Args:
            album_info: MusicBrainz album information

        Returns:
            Tuple for sorting (official_score, date_score, tracklist_completeness)
        """
        # Score 1: Official releases (0) before bootlegs/promos (1)
        official_score = 0 if self._is_official_release(album_info) else 1

        # Score 2: Release date (earlier is better)
        date_score = self._parse_release_date(album_info)

        # Score 3: Tracklist completeness (more tracks is better, so negate)
        tracklist_score = -len(album_info.tracks) if album_info.tracks else 0

        return (official_score, date_score, tracklist_score)

    def _is_official_release(self, album_info: AlbumInfo) -> bool:
        """
        Determine if this is an official release.

        Args:
            album_info: MusicBrainz album information

        Returns:
            True if official release, False otherwise
        """
        # Check MusicBrainz release status
        status = getattr(album_info, 'albumstatus', '').lower()
        if status in ['official', 'promotion']:
            return True

        # Check for bootleg indicators
        album_type = getattr(album_info, 'albumtype', '').lower()
        if 'bootleg' in album_type:
            return False

        # Default to True if unknown (prefer inclusion)
        return True

    def _parse_release_date(self, album_info: AlbumInfo) -> int:
        """
        Parse release date into sortable integer.
        Earlier dates return lower numbers.

        Args:
            album_info: MusicBrainz album information

        Returns:
            Integer timestamp (0 if no date available)
        """
        try:
            # Get year, month, day from album info
            year = getattr(album_info, 'year', None)
            month = getattr(album_info, 'month', 1)
            day = getattr(album_info, 'day', 1)

            if year:
                # Create datetime and convert to timestamp
                release_date = datetime(year, month or 1, day or 1)
                return int(release_date.timestamp())
            else:
                # No date: assign very high value (sort to end)
                return 9999999999
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Invalid release date for {album_info.album}: {e}")
            return 9999999999
