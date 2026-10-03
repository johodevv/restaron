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

# Doimiy (o'zgarmaydigan) internet manzili sozlamasi.
# Bo'sh bo'lsa — bepul trycloudflare ishlatiladi va manzil har safar o'zgaradi.
TUNNEL_CONFIG = BASE_DIR / "tunnel_sozlama.txt"
URL_FILE = BASE_DIR / "SERVER_ONLINE_URL.txt"
PID_FILE = BASE_DIR / "server_pids.json"
LOG_FILE = BASE_DIR / "server.log"
UVICORN_LOG = BASE_DIR / "uvicorn.log"
STATUS_FILE = BASE_DIR / "server_status.json"

PORT = 8000


MAX_LOG_BYTES = 2 * 1024 * 1024   # 2 MB


def _trim_log(path, max_bytes=MAX_LOG_BYTES):
    """
    Jurnal fayli juda kattalashib ketmasligi uchun eski qismini kesadi.
    Server restoranda yillab ishlaydi -- cheklovsiz jurnal diskni to'ldiradi.
    """
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            data = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(data[-(max_bytes // 2):], encoding="utf-8")
    except Exception:
        pass


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        _trim_log(LOG_FILE)
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
    """
    Backend TAYYOR bolishini kutadi.

    Faqat portni tekshirish yetarli emas: uvicorn portni ochadi, lekin
    jadvallar yaratilishi va seed tugaguncha sorovlar xato qaytaradi.
    Shuning uchun /health endpointi javob berishini kutamiz.
    """
    from urllib.request import urlopen

    start = time.time()
    while time.time() - start < timeout:
        try:
            with urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
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
        cf_flags = 0x08000000  # CREATE_NO_WINDOW

    uvicorn_proc = subprocess.Popen(
        uvicorn_cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
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

        cf_token, cf_fixed_url = read_tunnel_config()
        if cf_token:
            log("  Doimiy tunnel rejimi (manzil o'zgarmaydi)")
            cf_cmd = [
                str(CLOUDFLARED_EXE), "tunnel", "--no-autoupdate",
                "run", "--token", cf_token,
            ]
        else:
            cf_cmd = [
                str(CLOUDFLARED_EXE),
                "tunnel",
                "--url", f"http://localhost:{PORT}",
                "--no-autoupdate",
            ]

        # cloudflared for URL capture — start with PIPE (not detached) first
        # so we can read its stdout/stderr to find the tunnel URL.
        # cloudflared will keep running independently; it doesn't die when we close PIPE.
        cf_proc = subprocess.Popen(
            cf_cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            # creationflags faqat Windows da qollab-quvvatlanadi — Linux/Mac da
            # nolga teng bolmagan qiymat ValueError beradi.
            creationflags=cf_flags,  # CREATE_NO_WINDOW only (no DETACHED so PIPE works)
        )

        cf_pid = cf_proc.pid
        log(f"  cloudflared PID: {cf_pid}")

        url_found = threading.Event()
        cf_url_result = {"url": ""}

        def read_cf_output(stream):
            # api.trycloudflare.com -- cloudflared'ning o'z API manzili, tunnel manzili EMAS
            url_pattern = re.compile(r"https://(?!api\.)[a-z0-9\-]+\.trycloudflare\.com")
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

        if cf_token:
            # Doimiy rejimda manzil sozlamadan olinadi — cloudflared uni
            # chop etmaydi, chunki u Cloudflare panelida belgilangan.
            public_url = cf_fixed_url
            if public_url:
                log(f"  Doimiy internet manzili: {public_url}")
            else:
                log("  OGOHLANTIRISH: tunnel_sozlama.txt da MANZIL yozilmagan")
        elif url_found.wait(timeout=40):
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




def read_tunnel_config():
    """Doimiy tunnel sozlamasini o'qish.

    tunnel_sozlama.txt ikki qatordan iborat:
        TOKEN=eyJhIjoi...
        MANZIL=https://restoran.mening-domenim.uz

    TOKEN — Cloudflare Zero Trust panelida tunnel yaratilganda beriladi.
    MANZIL — o'sha tunnelga biriktirilgan doimiy manzil.

    Qaytaradi: (token, manzil). Sozlama bo'lmasa (None, None) —
    u holda bepul trycloudflare ishlatiladi (manzil har safar o'zgaradi).
    """
    if not TUNNEL_CONFIG.exists():
        return None, None
    token = url = ""
    try:
        for raw in TUNNEL_CONFIG.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip().upper()
            val = val.strip().strip('"').strip("'")
            if key == "TOKEN":
                token = val
            elif key in ("MANZIL", "URL", "HOSTNAME"):
                url = val
    except Exception as e:
        log(f"  tunnel_sozlama.txt o'qilmadi: {e}")
        return None, None

    if not token:
        return None, None
    if url and not url.startswith("http"):
        url = "https://" + url
    return token, url.rstrip("/")


def _tunnel_supervisor(stop_event):
    """
    Cloudflare Tunnel ni fonda ushlab turadi (alohida oqimda).

    tunnel_sozlama.txt da TOKEN bo'lsa — DOIMIY manzil ishlatiladi
    (har safar bir xil, stollardagi QR kodlar buzilmaydi).
    Bo'lmasa — bepul trycloudflare: manzil har safar o'zgaradi.

    Tunnel ishga tushgach internet manzilini SERVER_ONLINE_URL.txt ga
    yozadi. Tunnel uzilsa qayta ko'taradi.
    """
    if not CLOUDFLARED_EXE.exists():
        log("  cloudflared.exe topilmadi - faqat lokal Wi-Fi rejimi")
        return

    token, fixed_url = read_tunnel_config()
    named = bool(token)

    if named:
        cf_cmd = [str(CLOUDFLARED_EXE), "tunnel", "--no-autoupdate",
                  "run", "--token", token]
        log("  Doimiy tunnel rejimi (manzil o'zgarmaydi)")
        if fixed_url:
            # Doimiy manzil oldindan ma'lum — stollardagi QR kodlar
            # shu manzilga ishora qiladi va hech qachon buzilmaydi.
            try:
                URL_FILE.write_text(fixed_url, encoding="utf-8")
                log(f"  INTERNET MANZILI (doimiy): {fixed_url}")
            except Exception:
                pass
        else:
            log("  OGOHLANTIRISH: tunnel_sozlama.txt da MANZIL yozilmagan — "
                "QR kodlar lokal manzilda qoladi")
    else:
        cf_cmd = [str(CLOUDFLARED_EXE), "tunnel", "--url",
                  f"http://localhost:{PORT}", "--no-autoupdate"]

    # api.trycloudflare.com -- cloudflared API manzili, tunnel manzili EMAS
    url_pattern = re.compile(r"https://(?!api\.)[a-z0-9\-]+\.trycloudflare\.com")
    flags = 0x08000000 if sys.platform == "win32" else 0

    while not stop_event.is_set():
        try:
            cf = subprocess.Popen(
                cf_cmd,
                cwd=str(BASE_DIR),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace",
                creationflags=flags,
            )
        except Exception as e:
            log(f"  Tunnel ishga tushmadi: {e}")
            time.sleep(20)
            continue

        log(f"  cloudflared PID {cf.pid} - internet manzili kutilmoqda...")
        found = False
        try:
            for line in cf.stdout:
                if stop_event.is_set():
                    break
                if named:
                    # Doimiy rejimda manzil sozlamadan olinadi, cloudflared
                    # uni chop etmaydi. Shunchaki jurnal uchun o'qiymiz.
                    continue
                m = url_pattern.search(line or "")
                if m and not found:
                    found = True
                    url = m.group(0)
                    try:
                        URL_FILE.write_text(url, encoding="utf-8")
                    except Exception:
                        pass
                    log(f"  INTERNET MANZILI: {url}")
        except Exception:
            pass

        cf.wait()
        if stop_event.is_set():
            break
        log("  Tunnel uzildi, 10 sekunddan keyin qayta ulanadi...")
        time.sleep(10)


def serve_forever():
    """
    Nazoratchi rejim (Windows Scheduled Task shu rejimda ishga tushiradi).

    Uvicorn ni ishga tushiradi va u qandaydir sababga ko'ra to'xtab qolsa
    avtomatik qayta ko'taradi. Shunday qilib server kompyuter yonib
    turgan paytda doimiy ishlaydi va "qotib qolish" holatidan o'zi chiqadi.

    Jurnal: server.log
    """
    log("=" * 60)
    log("RestAron nazoratchi rejimi ishga tushdi (serve)")
    log(f"  Python: {VENV_PYTHON}")
    log(f"  Papka:  {BACKEND_DIR}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(BACKEND_DIR)

    cmd = [
        str(VENV_PYTHON), "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", str(PORT), "--no-access-log",
    ]

    # Internet orqali kirish uchun Cloudflare Tunnel ni ham fonda ushlaymiz.
    # Shunday qilib avtomatik ishga tushadigan xizmat ham lokal Wi-Fi'da,
    # ham internetda (4G) ishlaydi.
    stop_event = threading.Event()
    local_ip = get_local_ip()
    try:
        URL_FILE.write_text(f"http://{local_ip}:{PORT}", encoding="utf-8")
    except Exception:
        pass
    threading.Thread(target=_tunnel_supervisor, args=(stop_event,), daemon=True).start()

    flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
    restarts = 0

    while True:
        started_at = time.time()

        # Port band bo'lsa -- uvicorn "address already in use" bilan darhol
        # qulaydi. Buni oldindan aniqlab, aniq xabar beramiz (aks holda
        # cheksiz qayta urinish bo'lib ko'rinadi).
        try:
            chk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            chk.settimeout(1.0)
            busy = chk.connect_ex(("127.0.0.1", PORT)) == 0
            chk.close()
        except Exception:
            busy = False
        if busy:
            log(f"  DIQQAT: {PORT}-port allaqachon band (boshqa RestAron nusxasi ishlayaptimi?).")
            log(f"  Serverni to'xtatish: RESTARON_XIZMATNI_TOXTATISH.bat")
            time.sleep(20)
            continue

        # MUHIM: uvicorn chiqishi ilgari DEVNULL ga yuborilardi, shuning uchun
        # u qulab tushsa SABABINI bilish imkoni yo'q edi. Endi alohida
        # faylga yoziladi va xato bo'lsa jurnalga ko'chiriladi.
        try:
            uvicorn_log = open(UVICORN_LOG, "w", encoding="utf-8", errors="replace")
        except Exception:
            uvicorn_log = subprocess.DEVNULL

        try:
            proc = subprocess.Popen(
                cmd, cwd=str(BACKEND_DIR), env=env,
                stdout=uvicorn_log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=flags,
            )
        except Exception as e:
            log(f"XATO: uvicorn ishga tushmadi: {e}")
            time.sleep(15)
            continue

        log(f"  uvicorn PID {proc.pid} — port {PORT}")
        save_pids(proc.pid, 0)
        save_status("running", "", get_local_ip())

        code = proc.wait()          # jarayon tugaguncha kutamiz
        uptime = time.time() - started_at
        restarts += 1
        try:
            if uvicorn_log is not subprocess.DEVNULL:
                uvicorn_log.close()
        except Exception:
            pass

        log(f"  uvicorn to'xtadi (kod {code}, {uptime:.0f} sek ishladi). Qayta ishga tushirilmoqda...")

        # Tez qulagan bo'lsa -- sababini jurnalga ko'chiramiz
        if code != 0 and uptime < 30:
            try:
                tail = open(UVICORN_LOG, encoding="utf-8", errors="replace").read().strip().split("\n")
                tail = [ln for ln in tail if ln.strip()][-15:]
                if tail:
                    log("  --- uvicorn xato xabari ---")
                    for ln in tail:
                        log("  | " + ln[:200])
                    log("  --- (to'liq matn: uvicorn.log) ---")
            except Exception:
                pass

        # Juda tez-tez qulab tushsa, loglarni to'ldirmaslik uchun kutib turamiz
        delay = 5 if uptime > 60 else min(60, 5 * restarts)
        time.sleep(delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RestAron Server Manager")
    parser.add_argument(
        "action",
        nargs="?",
        default="start",
        choices=["start", "stop", "status", "url", "restart", "serve"],
        help="Amal: start | stop | status | url | restart | serve",
    )
    args = parser.parse_args()

    if args.action == "serve":
        serve_forever()
    elif args.action == "start":
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
