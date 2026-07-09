@echo off
cd /d "%~dp0backend"
python run_backend.py >> "%~dp0backend-local.log" 2>> "%~dp0backend-local.err.log"
