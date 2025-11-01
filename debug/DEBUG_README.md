# YT-DLP EZ-UI Debugging Guide

This directory contains debugging tools and documentation for troubleshooting issues in YT-DLP EZ-UI.

## Logging System

### Overview
The application uses a comprehensive multi-level logging system to track operations and diagnose issues.

### Log File Locations

All logs are stored in: `%APPDATA%\YT-DLP EZ-UI\`

On Windows, this typically resolves to:
```
C:\Users\[YourUsername]\AppData\Roaming\YT-DLP EZ-UI\
```

#### Main Application Logs
- **`app.log`** - General application logs
  - Location: `%APPDATA%\YT-DLP EZ-UI\app.log`
  - Contains: Application startup, errors, warnings, info messages
  - Rotation: 10MB max size, keeps 5 backup files

#### Fingerprinting Logs
Located in: `%APPDATA%\YT-DLP EZ-UI\fingerprint_logs\`

1. **`fingerprint_detailed.log`** - Step-by-step fingerprinting process
   - Every file being processed
   - Fingerprint generation details
   - AcoustID API queries and responses
   - Metadata extraction steps
   - Tag writing operations
   - File modification times

2. **`fingerprint_summary.log`** - High-level results
   - Total files found vs. recent files
   - Success/failure counts
   - Final metadata applied

3. **`fingerprint_errors.log`** - Errors only
   - AcoustID API errors
   - Fingerprint generation failures
   - Database lookup failures
   - Tag writing errors

## Common Debugging Scenarios

### Issue: Downloaded files have no metadata

**Steps to diagnose:**
1. Check `fingerprint_detailed.log` for:
   - Was fpcalc.exe found? Look for "Chromaprint (fpcalc) found at:"
   - Were files detected as recent? Look for "Recent files to fingerprint:"
   - Did fingerprint generation succeed? Look for "Duration:" and "Fingerprint length:"

2. Check `fingerprint_errors.log` for:
   - API errors: "AcoustID API ERROR"
   - No matches: "No match found in AcoustID database"

**Common causes:**
- Wrong API key type (should be AcoustID Application API key, not User API key)
- Files not in AcoustID/MusicBrainz database
- fpcalc.exe not installed/found
- Audio quality too poor for fingerprinting

### Issue: Fingerprinting all files in directory instead of just new downloads

**Check:**
- Look at `fingerprint_detailed.log` for modification times
- Files should be modified within the last 300 seconds (5 minutes)
- If files are older, they won't be fingerprinted

**The system filters by:**
```
max_age_seconds = 300  # Only process files modified in last 5 minutes
```

### Issue: AcoustID API errors

**Common API errors:**
1. **"Invalid API key"** - Using wrong key type
   - Solution: Get Application API key from https://acoustid.org/new-application
   - NOT the user API key

2. **"Rate limit exceeded"** - Too many requests
   - Solution: Wait a few minutes and try again
   - Consider adding delays between requests

3. **"No match found"** - Song not in database
   - This is normal for rare/obscure tracks
   - The fingerprint worked, just no database match

## Manual Debugging

### Test fpcalc manually
```bash
cd "D:\Coding Projects\YT-DLP EZ-UI\bin"
fpcalc.exe "path\to\audio\file.mp3"
```

Should output:
```
DURATION=390
FINGERPRINT=AQADt...
```

### Check AcoustID API key
```python
import keyring
api_key = keyring.get_password("YT-DLP_EZ-UI_Beets", "acoustid")
print(api_key)
```

### View recent file modifications
```python
from pathlib import Path
import time

download_dir = Path(r"C:\Users\YourName\Downloads\YT-DLP LH Added Scripts")
current_time = time.time()

for file in download_dir.rglob("*.mp3"):
    mod_time = file.stat().st_mtime
    age = current_time - mod_time
    print(f"{file.name}: {age:.1f} seconds ago")
```

## Log Rotation

Logs automatically rotate to prevent disk space issues:
- Main app log: 10MB max, 5 backup files
- Fingerprint logs: Append mode (manually clean if needed)

## Debug Scripts

Place debugging scripts in this directory. Examples:

### test_acoustid.py
Test AcoustID fingerprinting on a specific file

### check_metadata.py
Check what metadata is currently on downloaded files

### verify_setup.py
Verify all dependencies are installed correctly

## Getting Help

When reporting issues, include:
1. Relevant sections from `fingerprint_detailed.log`
2. Error messages from `fingerprint_errors.log`
3. App version and OS
4. Steps to reproduce

## Configuration

### Adjusting fingerprint age filter
Edit `core/acoustid_tagger.py`:
```python
def _find_audio_files(self, directory: str, max_age_seconds: int = 300)
```
Change `300` to adjust how many seconds back to look for files.

### Increasing log verbosity
Edit `config/constants.py`:
```python
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
```

Set logging level in main.py:
```python
logging.basicConfig(level=logging.DEBUG)  # Most verbose
```

## Useful Commands

### Clear all logs
```bash
cd "%APPDATA%\YT-DLP EZ-UI"
del /Q *.log
del /Q fingerprint_logs\*.log
```

### View logs in real-time (PowerShell)
```powershell
Get-Content "$env:APPDATA\YT-DLP EZ-UI\fingerprint_logs\fingerprint_detailed.log" -Wait
```

### Check chromaprint installation
```python
from utils.chromaprint_installer import ChromaprintInstaller
installer = ChromaprintInstaller()
print(f"Installed: {installer.is_installed()}")
print(f"Path: {installer.get_fpcalc_path()}")
```

## Tips

1. **Always check fingerprint_detailed.log first** - It shows everything
2. **Look for API errors** - These are usually the root cause
3. **Verify file ages** - Old files won't be processed
4. **Check fpcalc path** - Must be found for fingerprinting to work
5. **Validate API key** - Common issue is wrong key type
