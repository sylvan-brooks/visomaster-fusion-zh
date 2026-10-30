@echo off
REM ============================================================
REM  Restore the original English UI of VisoMaster Fusion
REM  from the *.orig snapshots written by apply_zh.bat.
REM  Pure ASCII on purpose, see apply_zh.bat.
REM ============================================================
setlocal
chcp 65001 >nul
set "I=%~dp0"
set "PY=%I%..\..\portable-files\python\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo === 1/3  right panel ===
"%PY%" "%I%apply_ast.py" "%I%strings.json" revert

echo.
echo === 2/3  window title, docks, menu skeleton ===
"%PY%" "%I%apply_mainwindow.py" "%I%ui_strings.json" revert

echo.
echo === 3/3  hardcoded menus and buttons ===
"%PY%" "%I%apply_hardcoded.py" "%I%ui_strings.json" revert

echo.
echo === verifying every restored file still parses ===
"%PY%" "%I%verify_patch.py"

echo.
echo Done. English UI restored.
echo.
pause
endlocal
