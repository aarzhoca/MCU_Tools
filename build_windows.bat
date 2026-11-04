@echo off
setlocal
pushd "%~dp0"
py -3.12 -m venv .venv-package
if errorlevel 1 goto fail
set "PY=%CD%\.venv-package\Scripts\python.exe"
"%PY%" -c "import sys, struct, platform, tkinter; assert sys.platform == 'win32' and sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 and platform.machine().upper() in ('AMD64','X86_64'), 'Use Windows x64 Python 3.12'"
if errorlevel 1 goto fail
"%PY%" -m pip install -r requirements-windows-build.txt
if errorlevel 1 goto fail
"%PY%" -m pip check
if errorlevel 1 goto fail
pushd backend
"%PY%" -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
  popd
  goto fail
)
popd
pushd frontend
if exist package-lock.json (
  call npm ci
) else (
  call npm install
)
if errorlevel 1 (
  popd
  goto fail
)
call npm run build
if errorlevel 1 (
  popd
  goto fail
)
popd
"%PY%" build_windows.py
if errorlevel 1 goto fail
echo Windows pilot package built. See dist\windows.
popd
pause
exit /b 0
:fail
echo Build failed. Read the first error above. No distributor package is approved.
popd
pause
exit /b 1
