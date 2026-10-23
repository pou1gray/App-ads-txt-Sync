@echo off
python sync.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo Script finished with error code %ERRORLEVEL%.
    pause
)
