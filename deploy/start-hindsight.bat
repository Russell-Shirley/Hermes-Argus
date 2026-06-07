@echo off
REM Start Hindsight local MCP server (detached, with stdio captured to log files)
REM Uses pg0 on port 15432 to avoid conflict with existing Postgres on 5432
REM LLM: Ollama gemma3:4b (free, local — Bun/claude-code provider crashes in scheduled task context)
REM API: http://localhost:8888

set HINDSIGHT_API_LLM_PROVIDER=ollama
set HINDSIGHT_API_LLM_MODEL=gemma3:4b
set HINDSIGHT_API_DATABASE_URL=pg0://hindsight-mcp:15432
set PYTHONIOENCODING=utf-8

REM Ensure FFmpeg shared DLLs are on PATH for torchcodec (also copied into torchcodec dir, but belt-and-suspenders)
set PATH=C:\ffmpeg-shared\bin;%PATH%

REM Redirect stdout/stderr to log files so Python has real file handles
REM (when launched via scheduled task with no console, Python crashes on missing stdout)
set LOGDIR=%USERPROFILE%\.hermes\logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set LOG=%LOGDIR%\hindsight-daemon.log
set ERR=%LOGDIR%\hindsight-daemon.err.log

REM Timestamp marker for log rotation visibility
echo. >> "%LOG%"
echo === Hindsight daemon starting at %DATE% %TIME% === >> "%LOG%"

"C:\Users\Russell\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python3.13.exe" -c "from hindsight_api.mcp_local import main; main()" >> "%LOG%" 2>> "%ERR%"
