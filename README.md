# YT-DLP EZ-UI

A professional, user-friendly Windows desktop application for downloading YouTube videos and playlists using yt-dlp, with advanced AcoustID-based music fingerprinting and tagging.

## Features

- **Easy-to-Use GUI**: Clean, modern interface built with PyQt6
- **Flexible Input**: Add single links or batch paste multiple URLs (CSV, line-by-line, or space-separated)
- **Smart Quality Selection**: Context-aware quality options (video resolutions or audio bitrates)
- **Download Queue**: Manage multiple downloads with edit and delete capabilities
- **AcoustID Fingerprinting**: Automatic acoustic fingerprinting for accurate music metadata
- **In-Place Tagging**: Downloaded files are tagged directly (no library import needed)
- **Automatic Track Numbering**: Sets track numbers based on file creation time
- **Smart File Renaming**: Optional post-download file renaming to match metadata
- **Selective Metadata Management**: Choose which files to rename or remove metadata from
- **Secure API Key Storage**: Windows Credential Manager integration
- **Multi-Tier Logging**: Comprehensive logging system for debugging and monitoring
- **Persistent Settings**: Remembers your preferences across sessions
- **Robust Error Handling**: Skips unavailable/private videos, continues with available content

## Requirements

- Python 3.10 or higher
- FFmpeg (for audio extraction and format conversion)
- Windows 11 (primary target platform)
- AcoustID Application API Key (for music fingerprinting - [Get one here](https://acoustid.org/new-application))

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg:**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add to system PATH or place in the same directory as the application

4. **Set up AcoustID (for music tagging):**
   - Get an Application API key from [acoustid.org/new-application](https://acoustid.org/new-application)
   - Enter the key in the application's setup wizard on first run
   - Chromaprint (fpcalc.exe) will be downloaded automatically

## Usage

### Running the Application

```bash
python main.py
```

### Using the Application

1. **Select Output Directory**: Choose where downloaded files will be saved
2. **Choose Format**: Select Video or Audio Only
3. **Select Quality**: Choose resolution (for videos) or bitrate (for audio)
4. **Add Links**:
   - Paste a single YouTube URL and click "+"
   - Or paste multiple URLs (comma/newline/space-separated)
5. **Manage Queue**: Right-click on items to delete them
6. **Start Download**: Click "Start Download" to begin

### Supported URL Formats

- Individual videos: `https://www.youtube.com/watch?v=...`
- Short links: `https://youtu.be/...`
- Playlists: `https://www.youtube.com/playlist?list=...`
- Videos in playlists: `https://www.youtube.com/watch?v=...&list=...`

## Project Structure

```
YT-DLP EZ-UI/
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── config/
│   ├── settings.py                  # Settings management
│   ├── constants.py                 # Application constants
│   └── user_profile.py              # User setup state tracking
├── ui/
│   ├── main_window.py               # Main window
│   ├── styles.py                    # UI styling
│   └── widgets/
│       ├── link_input.py            # Link input widget
│       ├── link_list.py             # Queue display widget
│       ├── options.py               # Format/quality options
│       ├── output_select.py         # Output directory selector
│       ├── progress_widget.py       # Download progress display
│       ├── log_viewer.py            # Download details/logs viewer
│       └── file_rename_dialog.py    # Post-download file renaming dialog
├── core/
│   ├── downloader.py                # yt-dlp wrapper
│   ├── acoustid_tagger.py           # AcoustID fingerprinting (primary tagging)
│   └── beets_manager.py             # Beets integration (legacy/optional)
├── utils/
│   ├── validators.py                # Input validation
│   ├── file_utils.py                # File operations
│   ├── logger.py                    # Logging system
│   ├── chromaprint_installer.py     # Auto-downloads fpcalc.exe
│   ├── track_numberer.py            # Automatic track number assignment
│   └── cover_art_fetcher.py         # Cover art download utility
├── beets_plugins/                   # Custom Beets plugins
│   ├── keyring_auth.py              # Keyring integration
│   ├── earliest_release.py          # Release selection
│   └── missing_router.py            # Metadata routing
├── beets_config/                    # Beets configuration templates
├── debug/                           # Debugging tools and documentation
│   └── DEBUG_README.md              # Comprehensive debugging guide
└── tests/
    ├── test_downloader.py
    ├── test_beets_manager.py
    └── test_acoustid_tagger.py
```

## Architecture

This application follows **SOLID principles** and maintains a **modular architecture**:

- **Separation of Concerns**: UI, business logic, and data handling are separated
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Components receive dependencies rather than creating them
- **Thread Safety**: Download operations don't block the UI
- **NASA-Level Quality**: Robust error handling and logging throughout

## Configuration

Settings are automatically saved to:
```
%APPDATA%\YT-DLP EZ-UI\settings.json
%APPDATA%\YT-DLP EZ-UI\user_profile.json
```

Logs are saved to:
```
%APPDATA%\YT-DLP EZ-UI\app.log
%APPDATA%\YT-DLP EZ-UI\fingerprint_logs\
```

See [debug/DEBUG_README.md](debug/DEBUG_README.md) for detailed logging information.

## Testing

Run all tests:
```bash
python -m unittest discover tests
```

Run specific test files:
```bash
python -m unittest tests.test_beets_manager
python -m unittest tests.test_downloader
python -m unittest tests.test_acoustid_tagger
```

## Development

### Code Quality Standards

- **Naming**: PascalCase for classes, snake_case for functions, UPPER_SNAKE_CASE for constants
- **Documentation**: Docstrings for all modules, classes, and public functions
- **Error Handling**: Try-except blocks with proper logging
- **Type Hints**: Used throughout for better code clarity

### Adding New Features

1. Create new module in appropriate package (core, ui, utils)
2. Follow existing patterns for consistency
3. Add appropriate tests
4. Update this README if user-facing changes

## License

This project is provided as-is for educational and personal use.

## Credits

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- GUI framework: [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- Metadata handling: [Mutagen](https://mutagen.readthedocs.io/)

---

## Current Development Status

**Version**: 3.1.0
**Phase**: Active Development & Testing
**Next Version**: v3.2.0 (planning phase)

### v3.1.0 Features Complete
- ✅ AcoustID fingerprinting with in-place tagging
- ✅ Multi-tier logging system (detailed, summary, errors)
- ✅ Chromaprint auto-installation
- ✅ Secure API key storage via Windows Credential Manager
- ✅ Progress tracking and UI updates
- ✅ Per-video folder organization
- ✅ Thread-safe download operations
- ✅ Automatic track numbering based on file creation time
- ✅ Post-download file renaming dialog
- ✅ Selective metadata removal for unchecked files
- ✅ Improved playlist error handling (skips unavailable videos)
- ✅ Fixed progress bar accuracy (shows completed vs total)
- ✅ Enhanced multi-playlist progress tracking

### Recent Improvements (v3.1.0)
- **Smart Error Handling**: Downloads continue even when individual videos fail
- **Track Numbering**: Automatically numbers tracks in playlists by creation order
- **File Renaming**: Optional post-tagging dialog to rename files to match metadata
- **Metadata Management**: Choose to keep or remove metadata on a per-file basis
- **Progress Accuracy**: Fixed queue progress bar to show actual completion percentage
- **Multi-Playlist Support**: Improved handling of multiple playlists in queue

### Known Limitations
- AcoustID fingerprinting requires audio files in their database
- File age filtering (5 minutes) may need adjustment for very slow downloads
- Windows 11 primary target (other Windows versions untested)
- Playlist error handling skips unavailable videos (by design)

---

**Author**: YT-DLP EZ-UI Team
**License**: Educational and Personal Use
