@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" padel_stats_mcp.py
) else (
  python padel_stats_mcp.py
)
