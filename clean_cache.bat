@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root=(Resolve-Path '.').Path; " ^
  "$targets=@(); " ^
  "$targets += Get-ChildItem -LiteralPath $root -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue; " ^
  "$targets += Get-ChildItem -LiteralPath $root -Directory -Filter 'pytest-cache-files-*' -ErrorAction SilentlyContinue; " ^
  "$extra=@('.pytest_cache','outputs\mpl_cache','outputs\test_reports'); " ^
  "foreach($item in $extra){ $path=Join-Path $root $item; if(Test-Path -LiteralPath $path){ $targets += Get-Item -LiteralPath $path } }; " ^
  "foreach($target in $targets){ $resolved=(Resolve-Path -LiteralPath $target.FullName).Path; if($resolved.StartsWith($root)){ Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue; if(Test-Path -LiteralPath $resolved){ Write-Host ('warning: still exists ' + $resolved) } else { Write-Host ('removed ' + $resolved) } } }"
endlocal
