@echo off
rem Ingestion pipeline entry point for Windows. Same commands as bin/pipeline.
setlocal
set "ROOT=%~dp0.."
if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo no virtualenv at %ROOT%\.venv - see the Windows setup in README.md 1>&2
  exit /b 1
)
rem Run from the repo root so the pipeline package is importable.
pushd "%ROOT%"
".venv\Scripts\python.exe" -m pipeline.cli %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
