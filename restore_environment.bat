@echo off
echo ===================================================
echo Recreating Python Virtual Environment for SQL Lineage
echo ===================================================

echo Deactivating current environment...
call deactivate 2>nul

echo Removing old environment...
rmdir /s /q sqllinege 2>nul

echo Creating new virtual environment...
python -m venv sqllinege

echo Activating new environment...
call sqllinege\Scripts\activate

echo Installing required packages...
pip install -r requirements.txt

echo Checking installation...
python -c "import streamlit; import blinker; from blinker import Signal; print('OK: blinker.Signal available'); import cachetools; from cachetools import TTLCache; print('OK: cachetools.TTLCache available'); print('All dependencies installed successfully!')"

echo.
echo ===================================================
echo Environment restored!
echo.
echo To use the environment:
echo 1. Activate: sqllinege\Scripts\activate
echo 2. Run: streamlit run streamlit_app.py
echo =================================================== 