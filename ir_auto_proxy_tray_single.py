# -*- coding: utf-8 -*-
"""
IR Auto Proxy Tray - single file
"""
import os, sys, re, time, json, random, queue, threading, subprocess, base64, io
from urllib.parse import urlparse

import requests
from PIL import Image
import pystray
from pystray import MenuItem as item
from plyer import notification

DUCK_ICON_B64 = """iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAACCklEQVR4nO1b23HDIBCETApJikgHaSoVpDgXkXRCvuRghsdx7D08sF+asQW7yx0cEooppbAzXqwJWOMYYE3AGscAawLWOAZYE7DGMcCagDVeVXv7jfSy8y1FQSZ3RPFSeEZ0C4JmyBiAEN0C2AysAZLCS4CMwE2CmuKB/WEM0BYP7HctBayE18BMCX4EeBIfApsPzwBv4i8weM0b4FX8hUl+upUgE/H9/zr9gNuemgSVRz8XXmJoBHFSpKeA99AvQeRLM8BAfG/0Kb+HEEi8t98Ojw14ttAvMeDvNgJGkxxqNXBrgBb6y6CT8IfUAY1l8SkKIXTxkwOfAt/wFkXRTgFu+LcM+GK1hkUlDfRSoGaMA1Ns5wAHpvibBJVN8WfAFhHwadJrFXoGUEXfsusPCSKPkDEgD+Nb819jXPcKGoGvA3K0xPcEce6holIHyBlQCuEIQLSRo2KAzG4QRby8byWdGmgbgHoLuzpqqPxv6MFHgMQsnrcDjoLtH4j0DVA6piKOjo4TAdYErDE2YDYNJCaslYl1wF8+AlZNEFj7c9AMWImCEPgiVgsqAm/Zt8OWewHioM2fEUKZMAMh8SFoPA+4yHOMUHgewDslht4p5hDY8fXAPybn5LXZAxiVK38Z9FYmM/lgzgpbRsPiQGAKIatoAPSLqwS1TQD1d74XOF+MaH49vuU3Q87xB3eDxOqKRf6pAAAAAElFTkSuQmCC"""

APP_NAME = "IR Auto Proxy Tray"
ICON_FILE = "_duck_icon_embedded.png"
SOURCES_FILE = "sources.txt"
STATE_FILE = "state.json"

ON_WINDOWS = (os.name == "nt")
if ON_WINDOWS:
    import winreg

DEFAULT_SOURCES = [
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=5000",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxy-list.download/api/v1/get?type=socks4",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://www.proxyscan.io/download?type=http",
    "https://www.proxyscan.io/download?type=https",
    "https://www.proxyscan.io/download?type=socks4",
    "https://www.proxyscan.io/download?type=socks5",
]

CHECK_URLS = [
    "http://example.com",
    "http://detectportal.firefox.com/success.txt",
    "http://httpbin.org/ip"
]
HEADERS = {"User-Agent": "Mozilla/5.0"}

healthy_proxies = set()
dead_proxies = set()
source_list = []
current_proxy = None
apply_mode = None
stop_event = threading.Event()
proxy_queue = queue.Queue()

def notify(title, message, timeout=5):
    try:
        notification.notify(title=title, message=message, timeout=timeout)
    except Exception:
        pass

def ensure_icon_file():
    if not os.path.exists(ICON_FILE):
        try:
            raw = base64.b64decode(DUCK_ICON_B64.encode("ascii"))
            with open(ICON_FILE, "wb") as f:
                f.write(raw)
        except Exception:
            from PIL import Image
            img = Image.new("RGBA", (64,64), (255,223,0,255))
            img.save(ICON_FILE, "PNG")

def create_icon():
    ensure_icon_file()
    try:
        return Image.open(ICON_FILE)
    except Exception:
        from PIL import Image
        return Image.new("RGBA", (64,64), (255,223,0,255))

def load_sources():
    global source_list
    urls = list(DEFAULT_SOURCES)
    if os.path.exists(SOURCES_FILE):
        try:
            with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                extra = [ln.strip() for ln in f if ln.strip()]
                urls.extend(extra)
        except Exception:
            pass
    seen = set(); ded = []
    for u in urls:
        try:
            key = (urlparse(u).netloc, urlparse(u).path)
            if key not in seen:
                seen.add(key); ded.append(u)
        except Exception:
            continue
    source_list = ded

def save_state():
    st = {
        "healthy_count": len(healthy_proxies),
        "dead_count": len(dead_proxies),
        "current_proxy": current_proxy,
        "apply_mode": apply_mode
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def valid_proxy_line(line):
    return bool(re.match(r"^(\\S+@\\S+:\\d+|\\d{1,3}(?:\\.\\d{1,3}){3}:\\d{2,5}|[^/\\s:@]+:[^/\\s:@]+@\\d{1,3}(?:\\.\\d{1,3}){3}:\\d{2,5})$", line.strip()))

def fetch_from_source(url, timeout=7):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception:
        return ""
    return ""

def parse_proxies(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and valid_proxy_line(line):
            out.append(line)
    return out

def test_proxy(proxy, timeout=4):
    scheme_proxy = f"http://{{proxy}}" if not proxy.startswith("http") else proxy
    proxies = {"http": scheme_proxy, "https": scheme_proxy}
    for url in CHECK_URLS:
        try:
            r = requests.get(url, proxies=proxies, headers=HEADERS, timeout=timeout, allow_redirects=False)
            if r.status_code in (200, 204, 301, 302):
                return True
        except Exception:
            continue
    return False

def set_windows_proxy(proxy):
    if not ON_WINDOWS:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings", 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy)
        winreg.CloseKey(key)
        try:
            import ctypes
            INTERNET_OPTION_SETTINGS_CHANGED = 39
            INTERNET_OPTION_REFRESH = 37
            ctypes.windll.Wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
        except Exception:
            pass
        return True
    except Exception:
        return False

def disable_windows_proxy():
    if not ON_WINDOWS:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings", 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def find_chrome_path():
    if not ON_WINDOWS:
        return None
    candidates = [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Users\\{{}}\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe".format(os.getenv("USERNAME",""))
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def launch_chrome_with_proxy(proxy):
    chrome = find_chrome_path()
    if not chrome:
        notify(APP_NAME, "Chrome پیدا نشد. روی ویندوز ست می‌کنم.", 5)
        return set_windows_proxy(proxy)
    try:
        subprocess.Popen([chrome, f"--proxy-server=http://{{proxy}}", "--new-window", "https://httpbin.org/ip"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def choose_apply_mode(proxy):
    global apply_mode
    if apply_mode in ("windows", "chrome"):
        return set_windows_proxy(proxy) if apply_mode=="windows" else launch_chrome_with_proxy(proxy)
    notify(APP_NAME, "پروکسی سالم پیدا شد. از منو محل اعمال را انتخاب کن: ویندوز یا کروم.", 6)
    return set_windows_proxy(proxy)

def fetch_loop():
    while not stop_event.is_set():
        load_sources()
        random.shuffle(source_list)
        for url in list(source_list):
            if stop_event.is_set(): break
            text = fetch_from_source(url)
            if not text: 
                continue
            for p in parse_proxies(text):
                if p in healthy_proxies or p in dead_proxies: 
                    continue
                proxy_queue.put(p)
        time.sleep(60)

def tester_loop():
    global current_proxy
    while not stop_event.is_set():
        try:
            proxy = proxy_queue.get(timeout=2)
        except queue.Empty:
            time.sleep(1); continue
        if test_proxy(proxy):
            healthy_proxies.add(proxy)
            if current_proxy is None:
                if choose_apply_mode(proxy):
                    current_proxy = proxy
                    notify(APP_NAME, f"پروکسی وصل شد: {{proxy}}", 5)
        else:
            dead_proxies.add(proxy)
        save_state()

def monitor_loop():
    global current_proxy
    while not stop_event.is_set():
        time.sleep(10)
        if current_proxy and not test_proxy(current_proxy):
            notify(APP_NAME, "پروکسی فعلی قطع شد. در حال تعویض...", 5)
            current_proxy = None
            for hp in list(healthy_proxies):
                if choose_apply_mode(hp):
                    current_proxy = hp
                    notify(APP_NAME, f"پروکسی جدید فعال شد: {{hp}}", 5)
                    break
        save_state()

def add_source_action(icon, _item):
    with open("ADD_SOURCE_URL.txt", "w", encoding="utf-8") as f:
        f.write("URL منبع را در خط اول وارد کن و ذخیره کن.\n")
    notify(APP_NAME, "فایل ADD_SOURCE_URL.txt ساخته شد. بعد از نوشتن URL، از منو «ثبت منبع جدید از فایل» را بزن.", 8)

def commit_new_source(icon, _item):
    try:
        with open("ADD_SOURCE_URL.txt", "r", encoding="utf-8") as f:
            url = f.readline().strip()
        if not url.startswith("http"):
            notify(APP_NAME, "URL معتبر نبود.", 5); return
        text = fetch_from_source(url)
        if not text or not parse_proxies(text):
            notify(APP_NAME, "منبع جواب نداد یا لیست خالی بود.", 6); return
        with open(SOURCES_FILE, "a", encoding="utf-8") as f:
            f.write("\n" + url)
        notify(APP_NAME, "منبع جدید اضافه شد.", 5)
    except Exception:
        notify(APP_NAME, "ثبت منبع ناموفق بود.", 5)

def show_sources(icon, _item):
    load_sources()
    with open("CURRENT_SOURCES.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(source_list) if source_list else "(خالی)")
    notify(APP_NAME, "فایل CURRENT_SOURCES.txt ذخیره شد.", 5)

def remove_proxy_action(icon, _item):
    if ON_WINDOWS:
        if disable_windows_proxy():
            notify(APP_NAME, "تنظیمات پروکسی سیستم حذف شد.", 5)
        else:
            notify(APP_NAME, "حذف پروکسی سیستم ناموفق بود.", 5)
    else:
        notify(APP_NAME, "این قابلیت فقط در ویندوز فعال است.", 6)

def set_mode_windows(icon, _item):
    global apply_mode, current_proxy
    apply_mode = "windows"
    notify(APP_NAME, "حالت اعمال: ویندوز", 4)
    if current_proxy:
        set_windows_proxy(current_proxy)

def set_mode_chrome(icon, _item):
    global apply_mode, current_proxy
    apply_mode = "chrome"
    notify(APP_NAME, "حالت اعمال: فقط کروم", 4)
    if current_proxy:
        launch_chrome_with_proxy(current_proxy)

def switch_proxy_now(icon, _item):
    global current_proxy
    for hp in list(healthy_proxies):
        if hp != current_proxy and test_proxy(hp):
            if choose_apply_mode(hp):
                current_proxy = hp
                notify(APP_NAME, f"پروکسی تعویض شد: {{hp}}", 5)
                return
    notify(APP_NAME, "پروکسی سالم دیگری پیدا نشد.", 5)

def on_quit(icon, _item):
    stop_event.set()
    icon.visible = False
    icon.stop()

def run_tray():
    icon_img = create_icon()
    menu = (
        item("افزودن منبع جدید (ایجاد فایل)", add_source_action),
        item("ثبت منبع جدید از فایل", commit_new_source),
        item("نمایش لیست منابع", show_sources),
        item("حذف تنظیم پروکسی سیستم", remove_proxy_action),
        item("حالت اعمال → ویندوز", set_mode_windows),
        item("حالت اعمال → فقط کروم", set_mode_chrome),
        item("تعویض دستی پروکسی فعال", switch_proxy_now),
        item("خروج", on_quit),
    )
    ic = pystray.Icon("ir_auto_proxy_tray", icon_img, APP_NAME, menu)
    threading.Thread(target=fetch_loop, daemon=True).start()
    threading.Thread(target=tester_loop, daemon=True).start()
    threading.Thread(target=monitor_loop, daemon=True).start()
    ic.run()

if __name__ == "__main__":
    ensure_icon_file()
    run_tray()
