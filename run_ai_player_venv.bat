@echo off
setlocal

cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "VENV_DIR=.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [venv] Creating virtual environment: %VENV_DIR%
    py -3 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        python -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (
        echo [venv] Failed to create virtual environment.
        echo Please make sure Python is installed and available as "py" or "python".
        exit /b 1
    )

    echo [venv] Installing dependencies from requirements.txt
    "%PYTHON_EXE%" -m pip install --upgrade pip
    if errorlevel 1 exit /b 1
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b 1
)

set "MODE=%~1"
if "%MODE%"=="" set "MODE=gui"

if /I "%MODE%"=="gui" (
    "%PYTHON_EXE%" main.py --gui
) else if /I "%MODE%"=="console" (
    "%PYTHON_EXE%" main.py --console --strategy Greedy
) else if /I "%MODE%"=="compare" (
    "%PYTHON_EXE%" main.py --compare
) else if /I "%MODE%"=="local" (
    "%PYTHON_EXE%" main.py --local-greedy
) else if /I "%MODE%"=="batch" (
    "%PYTHON_EXE%" main.py --batch
) else if /I "%MODE%"=="batch-all" (
    "%PYTHON_EXE%" main.py --batch --batch-all
) else if /I "%MODE%"=="preview" (
    "%PYTHON_EXE%" main.py --preview
) else if /I "%MODE%"=="evaluate" (
    "%PYTHON_EXE%" main.py --evaluate
) else if /I "%MODE%"=="report" (
    "%PYTHON_EXE%" main.py --export-report
) else if /I "%MODE%"=="qlearn" (
    "%PYTHON_EXE%" main.py --qlearn
) else if /I "%MODE%"=="clean" (
    call clean_cache.bat
) else (
    echo Unknown mode: %MODE%
    echo Usage:
    echo   run_ai_player_venv.bat
    echo   run_ai_player_venv.bat gui
    echo   run_ai_player_venv.bat console
    echo   run_ai_player_venv.bat compare
    echo   run_ai_player_venv.bat local
    echo   run_ai_player_venv.bat batch
    echo   run_ai_player_venv.bat batch-all
    echo   run_ai_player_venv.bat preview
    echo   run_ai_player_venv.bat evaluate
    echo   run_ai_player_venv.bat report
    echo   run_ai_player_venv.bat qlearn
    echo   run_ai_player_venv.bat clean
    exit /b 1
)

endlocal
