@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install Pillow==11.1.0
if errorlevel 1 (echo Failed to install Pillow& pause& exit /b 1)
py -3 scripts\collect_281_photos.py
py -3 scripts\verify_and_pack.py --package
if errorlevel 1 (
  echo Incomplete: review PHOTO_VERIFICATION_REPORT.md and PHOTO_DOWNLOAD_REPORT.json.
) else (
  echo Complete: JAPAN_ATLAS_281_REAL_PHOTOS_FINAL.zip created next to project folder.
)
pause
