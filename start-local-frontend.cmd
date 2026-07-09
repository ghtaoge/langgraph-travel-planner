@echo off
cd /d "%~dp0frontend"
npm run dev -- --host 127.0.0.1 >> "%~dp0frontend-local.log" 2>> "%~dp0frontend-local.err.log"
