@echo off
REM ============================================================
REM  Apply the Chinese UI patch to VisoMaster Fusion.
REM  Put this repo folder next to VisoMaster-Fusion (inside the
REM  portable install folder), then double-click this file.
REM  Safe to run repeatedly: every patcher rebuilds from the
REM  pristine *.orig snapshots, so it cannot double-translate.
REM  Run it again after any "Update from Git" in the launcher.
REM
REM  This .bat stays pure ASCII on purpose -- cmd reads .bat as
REM  the OEM codepage, so Chinese literals here would show as
REM  mojibake. All Chinese output comes from the Python scripts.
REM ============================================================
setlocal
chcp 65001 >nul
set "I=%~dp0"
set "PY=%I%..\..\portable-files\python\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo === 1/3  right panel: parameter labels + hover tooltips ===
"%PY%" "%I%apply_ast.py" "%I%strings.json" apply || goto :fail

echo.
echo === 2/3  window title, docks, menu skeleton ===
"%PY%" "%I%apply_mainwindow.py" "%I%ui_strings.json" apply || goto :fail

echo.
echo === 3/3  hardcoded menus and buttons ===
"%PY%" "%I%apply_hardcoded.py" "%I%ui_strings.json" apply || goto :fail

echo.
echo === verifying every patched file still parses ===
"%PY%" "%I%verify_patch.py" || goto :fail

echo.
echo Done. Start VisoMaster with Start_Portable.bat
echo The launcher will warn "Tracked files changed" -- that is
echo this patch, not a fault. Do NOT use "Repair Installation",
echo it restores English.
goto :end

:fail
echo.
echo [ERROR] a step failed, see the message above. Run revert_en.bat to go back to English.

:end
echo.
pause
endlocal
