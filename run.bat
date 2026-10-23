@echo off
setlocal
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python sync.py %*
) else (
    where py >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        py -3 sync.py %*
    ) else (
        echo [ERROR] Python 3 was not found in PATH.
        echo Please install Python 3 from https://www.python.org/
        pause
        exit /b 1
    )
)
if %ERRORLEVEL% neq 0 (
    echo.
    echo Script finished with error code %ERRORLEVEL%.
    pause
)
