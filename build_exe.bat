@echo off
setlocal
python -V || (echo Python not found & pause & exit /b 1)
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=duck_icon.png --name ir_auto_proxy_tray ir_auto_proxy_tray_single.py
echo.
echo Built EXE at .\dist\ir_auto_proxy_tray.exe
pause
