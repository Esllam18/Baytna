@echo off
cd /d %~dp0\backend
python ..\scripts\worker.py
