"""
RestAron Server Manager
=======================
Bu skript:
  1. FastAPI (uvicorn) ni background da ishga tushiradi
  2. Cloudflare Tunnel ni ishga tushiradi
  3. Tunnel URL ni SERVER_ONLINE_URL.txt ga saqlaydi
  4. Admin panel orqali URL korish mumkin boladi

Ishlatish:
  python server_manager.py start    # Serverni ishga tushirish
  python server_manager.py stop     # Serverni toxtatish
  python server_manager.py status   # Holat korish
  python server_manager.py url      # Internet URL korish
"""

import os
import sys
import re
import time
import json
import signal
import socket
import subprocess
import threading
import argparse
from pathlib import Path
from datetime import datetime

# Yollar
BASE_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = BASE_DIR / "backend"
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

CLOUDFLARED_EXE = BASE_DIR / "cloudflared.exe"
URL_FILE = BASE_DIR / "SERVER_ONLINE_URL.txt"
PID_FILE = BASE_DIR / "server_pids.json"
LOG_FILE = BASE_DIR / "server.log"
STATUS_FILE = BASE_DIR / "server_status.json"

PORT = 8000


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def save_pids(uvicorn_pid: int, cloudflared_pid: int):
    data = {
        "uvicorn_pid": uvicorn_pid,
        "cloudflared_pid": cloudflared_pid,
        "started_at": datetime.now().isoformat(),
    }
    with open(PID_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_pids() -> dict:
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_status(status: str, public_url: str = "", local_ip: str = ""):
    data = {
        "status": status,
        "public_url": public_url,
        "local_url": f"http://{local_ip}:{PORT}" if local_ip else "",
        "local_ip": local_ip,
        "updated_at": datetime.now().isoformat(),
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def kill_pid(pid: int, name: str = ""):
    if pid <= 0:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        log(f"  OK {name} (PID {pid}) toxtatildi")
    except Exception as e:
        log(f"  ! {name} (PID {pid}) toxtatib bolmadi: {e}")


def wait_for_backend(timeout=60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=2)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


def start_server():
    pids = load_pids()
    if pids.get("uvicorn_pid") and is_pid_running(pids["uvicorn_pid"]):
        log("Server allaqachon ishlamoqda!")
        if URL_FILE.exists():
            url = URL_FILE.read_text(encoding="utf-8").strip()
            log(f"Internet URL: {url}")
        return

    log("RestAron Server ishga tushmoqda...")
    log(f"  Backend: {BACKEND_DIR}")
    log(f"  Python:  {VENV_PYTHON}")

    local_ip = get_local_ip()
    log(f"  Lokal IP: {local_ip}")

    if URL_FILE.exists():
        URL_FILE.unlink()

    save_status("starting", "", local_ip)

    log("FastAPI serveri ishga tushmoqda (port 8000)...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(BACKEND_DIR)

    uvicorn_cmd = [
        str(VENV_PYTHON), "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--no-access-log",
    ]

    cf_flags = 0
    if sys.platform == "win32":
        cf_flags = subprocess.CREATE_NO_WINDOW

    uvicorn_proc = subprocess.Popen(
        uvicorn_cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=cf_flags,
    )

    log(f"  uvicorn PID: {uvicorn_proc.pid}")
    log("  Backend tayyor bolishi kutilmoqda...")

    if not wait_for_backend(timeout=60):
        log("XATO: Backend ishga tushmadi (60 sekund kutildi).")
        uvicorn_proc.terminate()
        save_status("error", "", local_ip)
        return

    log(f"  Backend tayyor: http://localhost:{PORT}")

    public_url = ""

    if CLOUDFLARED_EXE.exists():
        log("Cloudflare Tunnel ishga tushmoqda...")

        cf_cmd = [
            str(CLOUDFLARED_EXE),
            "tunnel",
            "--url", f"http://localhost:{PORT}",
            "--no-autoupdate",
        ]

        cf_proc = subprocess.Popen(
            cf_cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=cf_flags,
        )

        cf_pid = cf_proc.pid
        log(f"  cloudflared PID: {cf_pid}")

        url_found = threading.Event()
        cf_url_result = {"url": ""}

        def read_cf_output(stream):
            url_pattern = re.compile(r"https://[a-z0-9\-]+\.trycloudflare\.com")
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                m = url_pattern.search(line)
                if m:
                    cf_url_result["url"] = m.group(0)
                    url_found.set()

        t_out = threading.Thread(target=read_cf_output, args=(cf_proc.stdout,), daemon=True)
        t_err = threading.Thread(target=read_cf_output, args=(cf_proc.stderr,), daemon=True)
        t_out.start()
        t_err.start()

        if url_found.wait(timeout=40):
            public_url = cf_url_result["url"]
            log(f"  Cloudflare URL: {public_url}")
        else:
            log("  OGOHLANTIRISH: Cloudflare URL topilmadi (40 sekund kutildi)")
            log("  Lokal Wi-Fi rejimida davom etiladi")

        save_pids(uvicorn_proc.pid, cf_pid)
    else:
        log("  cloudflared.exe topilmadi - faqat lokal Wi-Fi rejimi")
        save_pids(uvicorn_proc.pid, -1)

    effective_url = public_url if public_url else f"http://{local_ip}:{PORT}"
    URL_FILE.write_text(effective_url, encoding="utf-8")
    save_status("running", public_url, local_ip)

    log("")
    log("=" * 60)
    log("RestAron Server TAYYOR!")
    log("=" * 60)
    if public_url:
        log(f"  Internet (4G/Wi-Fi):  {public_url}")
    log(f"  Lokal Wi-Fi:          http://{local_ip}:{PORT}")
    log(f"  Lokal:                http://localhost:{PORT}")
    log("")
    log("  Ofitsianlarga bering: " + (public_url or f"http://{local_ip}:{PORT}"))
    log("  Admin panel: /login")
    log("=" * 60)
    log("  Serverni toxtatish: python server_manager.py stop")
    log("=" * 60)


def stop_server():
    log("Server toxtatilmoqda...")
    pids = load_pids()

    uv_pid = pids.get("uvicorn_pid", -1)
    cf_pid = pids.get("cloudflared_pid", -1)

    kill_pid(cf_pid, "cloudflared")
    kill_pid(uv_pid, "uvicorn")

    if sys.platform == "win32":
        for proc_name in ["uvicorn.exe", "cloudflared.exe"]:
            subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True)

    for f in [URL_FILE, PID_FILE]:
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass

    save_status("stopped")
    log("Server toxtatildi.")


def show_status():
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                st = json.load(f)
            status = st.get("status", "unknown")
            pub = st.get("public_url", "")
            loc = st.get("local_url", "")
            updated = st.get("updated_at", "")

            print(f"\n{'='*50}")
            print(f"RestAron Server Holati")
            print(f"{'='*50}")
            print(f"Holat:       {status.upper()}")
            if pub:
                print(f"Internet:    {pub}")
            if loc:
                print(f"Lokal:       {loc}")
            if updated:
                print(f"Yangilangan: {updated[:19]}")
            print(f"{'='*50}\n")
            return
        except Exception:
            pass

    pids = load_pids()
    uv_pid = pids.get("uvicorn_pid", -1)
    cf_pid = pids.get("cloudflared_pid", -1)
    uv_running = is_pid_running(uv_pid) if uv_pid > 0 else False
    cf_running = is_pid_running(cf_pid) if cf_pid > 0 else False

    if not uv_running and not cf_running:
        print("Server ishlamayapti. Ishga tushirish: python server_manager.py start")
        return

    print(f"\n{'='*50}")
    print(f"FastAPI: {'Ishlayapti' if uv_running else 'Toxtatilgan'} (PID: {uv_pid})")
    print(f"Cloudflare: {'Ishlayapti' if cf_running else 'Toxtatilgan'} (PID: {cf_pid})")
    if URL_FILE.exists():
        url = URL_FILE.read_text(encoding="utf-8").strip()
        print(f"Server URL: {url}")
    print(f"{'='*50}\n")


def show_url():
    if URL_FILE.exists():
        url = URL_FILE.read_text(encoding="utf-8").strip()
        print(url)
    else:
        local_ip = get_local_ip()
        print(f"http://{local_ip}:{PORT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RestAron Server Manager")
    parser.add_argument(
        "action",
        nargs="?",
        default="start",
        choices=["start", "stop", "status", "url", "restart"],
        help="Amal: start | stop | status | url | restart",
    )
    args = parser.parse_args()

    if args.action == "start":
        start_server()
    elif args.action == "stop":
        stop_server()
    elif args.action == "status":
        show_status()
    elif args.action == "url":
        show_url()
    elif args.action == "restart":
        stop_server()
        time.sleep(3)
        start_server()
