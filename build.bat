@echo off
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found in PATH!
    exit /b 1
)

pip install -r requirements.txt

pyinstaller --collect-all winrt ^
    --collect-submodules bleak ^
    --hidden-import winrt.windows.devices.bluetooth.genericattributeprofile ^
    --hidden-import winrt.windows.devices.radios ^
    --noconsole ^
    --onefile ^
    --name HR-Overlay ^
    --icon icon.ico ^
    run.py

echo Build completed successfully.
