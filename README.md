# IR Auto Proxy Tray (Windows x64)

- System Tray app with a duck icon 🦆
- Finds + tests proxies from many sources, applies to **Windows** or **Chrome**.
- Auto-switch if proxy dies; menu includes Add Source, Show Sources, Remove Proxy, Switch Now.

## Local build (standalone EXE)
Double click `build_exe.bat` (or run these commands in PowerShell):
```
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=duck_icon.png --name ir_auto_proxy_tray ir_auto_proxy_tray_single.py
```
Output: `dist/ir_auto_proxy_tray.exe`

## GitHub Actions build
1. Create a new empty repo and upload all files (including `.github/workflows/build.yml`).
2. Go to **Actions** tab → run **Build EXE (Windows x64)**.
3. After it finishes, download the artifact **IR-Proxy-Tray-EXE** → `ir_auto_proxy_tray.exe`.

> امضای دیجیتال واقعی اضافه نشده. برای حذف کامل هشدار SmartScreen باید فایل خروجی را با گواهی خودتان امضا کنید.
