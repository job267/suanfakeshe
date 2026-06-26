@echo off
setlocal

cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=gui"

if /I "%MODE%"=="gui" (
    conda run --no-capture-output -n suanfa python main.py --gui
) else if /I "%MODE%"=="console" (
    conda run --no-capture-output -n suanfa python main.py --console --strategy Greedy
) else if /I "%MODE%"=="compare" (
    conda run --no-capture-output -n suanfa python main.py --compare
) else if /I "%MODE%"=="local" (
    conda run --no-capture-output -n suanfa python main.py --local-greedy
) else if /I "%MODE%"=="batch" (
    conda run --no-capture-output -n suanfa python main.py --batch
) else if /I "%MODE%"=="batch-all" (
    conda run --no-capture-output -n suanfa python main.py --batch --batch-all
) else if /I "%MODE%"=="preview" (
    conda run --no-capture-output -n suanfa python main.py --preview
) else if /I "%MODE%"=="evaluate" (
    conda run --no-capture-output -n suanfa python main.py --evaluate
) else if /I "%MODE%"=="report" (
    conda run --no-capture-output -n suanfa python main.py --export-report
) else if /I "%MODE%"=="qlearn" (
    conda run --no-capture-output -n suanfa python main.py --qlearn
) else if /I "%MODE%"=="clean" (
    call clean_cache.bat
) else (
    echo Unknown mode: %MODE%
    echo Usage:
    echo   run_ai_player.bat
    echo   run_ai_player.bat gui
    echo   run_ai_player.bat console
    echo   run_ai_player.bat compare
    echo   run_ai_player.bat local
    echo   run_ai_player.bat batch
    echo   run_ai_player.bat batch-all
    echo   run_ai_player.bat preview
    echo   run_ai_player.bat evaluate
    echo   run_ai_player.bat report
    echo   run_ai_player.bat qlearn
    echo   run_ai_player.bat clean
    exit /b 1
)

endlocal
