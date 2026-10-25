"""Read-only preflight and scoped migration for the Windows startup installer.

Never imports app.main, seeds the database, prints secrets, or kills by image name.
"""
import argparse
from contextlib import closing, contextmanager
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def tunnel_settings(root):
    values = {}
    for line in (root / "tunnel_sozlama.txt").read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip().upper()] = value.strip().strip('"\'')
    token = values.get("TOKEN", "")
    url = next((values[key] for key in ("MANZIL", "URL", "HOSTNAME") if values.get(key)), "")
    if url and "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if not token or token.lower() in {"token", "your_token", "paste_token_here"}:
        raise RuntimeError("Cloudflare TOKEN sozlanmagan. tunnel_sozlama.txt ni tekshiring.")
    if (parts.scheme != "https" or parts.netloc.lower() != "dunyochoyxona.uz"
            or parts.path not in ("", "/") or parts.query or parts.fragment):
        raise RuntimeError("MANZIL https://dunyochoyxona.uz bo'lishi kerak; mavjud sozlama o'zgartirilmadi.")
    return "https://dunyochoyxona.uz"


def database_path(root):
    from dotenv import dotenv_values
    from sqlalchemy.engine import make_url
    values = dotenv_values(root / "backend" / ".env")
    url = make_url(os.environ.get("DATABASE_URL") or values.get("DATABASE_URL")
                   or "sqlite+aiosqlite:///./restaron.db")
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        raise RuntimeError("Bu o'rnatuvchi diskdagi SQLite bazasi uchun tayyorlangan. Baza turi mos emas.")
    path = Path(url.database)
    return path.resolve() if path.is_absolute() else (root / "backend" / path).resolve()


@contextmanager
def read_database(path):
    if not path.is_file():
        raise RuntimeError("Ishchi baza topilmadi; bo'sh baza yaratilmadi.")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        conn.execute("PRAGMA query_only=ON")
        yield conn
    finally:
        conn.close()


def preflight(root=ROOT, prepare=False):
    required = ("server_manager.py", "frontend_build.py", "cloudflared.exe",
                "backend/.venv/Scripts/python.exe", "backend/.env", "backend/app/main.py")
    for name in required:
        if not (root / name).is_file():
            raise RuntimeError(f"Kerakli fayl topilmadi: {name}")
    for module in ("fastapi", "uvicorn", "sqlalchemy", "aiosqlite", "dotenv", "psutil", "win32print", "win32job"):
        if importlib.util.find_spec(module) is None:
            raise RuntimeError(f"Python kutubxonasi yetishmayapti: {module}. 1_BIRINCHI_ORNATISH.bat ni bajaring.")
    domain = tunnel_settings(root)
    db = database_path(root)
    with read_database(db) as conn:
        for table in ("orders", "tables", "print_jobs"):
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                raise RuntimeError("Ishchi bazaning tuzilishi mos emas; o'rnatish to'xtatildi.")
    from frontend_build import build_is_current, ensure_frontend_build
    if prepare:
        ensure_frontend_build(root)
    if not build_is_current(root / "frontend"):
        raise RuntimeError("Frontend build eskirgan. O'rnatish rejimi buildni xavfsiz yangilaydi.")
    print(json.dumps({"preflight": "ok", "domain": domain, "frontend_current": True,
                      "database_exists": True}, ensure_ascii=True))


def process_role(command, cwd, root=ROOT):
    """Exact checkout matching; an unrelated Python/tunnel must never be selected."""
    if not command:
        return None
    root = root.resolve()
    if Path(command[0]).name.lower() not in {"python.exe", "pythonw.exe", "python", "python3"}:
        return None
    for index, argument in enumerate(command[1:-1], 1):
        if Path(argument).name != "server_manager.py" or command[index + 1] != "serve":
            continue
        script = Path(argument)
        if not script.is_absolute():
            script = Path(cwd) / script
        if script.resolve() == root / "server_manager.py":
            return "supervisor"
    if command[1:4] == ["-m", "uvicorn", "app.main:app"] and Path(cwd).resolve() == root / "backend":
        try:
            if command[command.index("--port") + 1] == "8000":
                return "backend"
        except (ValueError, IndexError):
            pass
    return None


def project_processes(root=ROOT):
    import psutil
    supervisors, backends, children = {}, {}, {}
    for proc in psutil.process_iter():
        try:
            role = process_role(proc.cmdline(), proc.cwd(), root)
            if role == "supervisor":
                supervisors[proc.pid] = proc
            elif role == "backend":
                backends[proc.pid] = proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    for proc in list(supervisors.values()):
        try:
            for child in proc.children(recursive=True):
                children[child.pid] = child
        except psutil.NoSuchProcess:
            continue
    return supervisors, backends, children


def check_port(root=ROOT):
    import psutil
    supervisors, backends, children = project_processes(root)
    known = set(supervisors) | set(backends) | set(children)
    listeners = [c for c in psutil.net_connections(kind="tcp")
                 if c.status == psutil.CONN_LISTEN and c.laddr.port == 8000]
    if any(c.pid is None or c.pid not in known for c in listeners):
        raise RuntimeError("8000-port boshqa yoki aniqlanmagan jarayonga tegishli; unga tegilmadi.")
    return supervisors, backends, children


def wait_print_idle(db, timeout=45):
    deadline = time.monotonic() + timeout
    while True:
        with read_database(db) as conn:
            count = conn.execute("SELECT count(*) FROM print_jobs WHERE status='printing'").fetchone()[0]
        if count == 0:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("Printer chek chiqarishni tugatmadi. Server to'xtatilmadi; keyinroq qayta urining.")
        time.sleep(1)


def stop_project(root=ROOT):
    """The installer disables its scheduled task first, preventing a restart race."""
    import psutil
    check_port(root)  # Refuse to interfere with another application.
    db = database_path(root)
    wait_print_idle(db)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = root / "backups" / "autostart" / (stamp + ".db")
    backup.parent.mkdir(parents=True, exist_ok=True)
    with read_database(db) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Zaxira tekshiruvi o'tmadi; server to'xtatilmadi.")
    wait_print_idle(db)
    supervisors, backends, children = check_port(root)
    # Stop supervisors first so they cannot spawn a replacement during migration.
    for group in (supervisors, {**children, **backends}):
        running = []
        for proc in group.values():
            try:
                proc.terminate()
                running.append(proc)
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(running, timeout=10)
        for proc in alive:
            proc.kill()
        _, alive = psutil.wait_procs(alive, timeout=5)
        if alive:
            raise RuntimeError("RestAron jarayoni to'xtamadi; yangi nusxa ishga tushirilmadi.")
    if any(c.status == psutil.CONN_LISTEN and c.laddr.port == 8000
           for c in psutil.net_connections(kind="tcp")):
        raise RuntimeError("8000-port bo'shamadi; yangi nusxa ishga tushirilmadi.")
    print(json.dumps({"stopped": True, "backup": str(backup)}, ensure_ascii=True))


def health(url, timeout=4):
    try:
        req = Request(url.rstrip("/") + "/health", headers={"User-Agent": "Mozilla/5.0 RestAronStartupCheck"})
        with urlopen(req, timeout=timeout) as response:
            data = json.load(response)
            return response.status == 200 and data.get("status") == "healthy"
    except Exception:
        return False


def wait_ready(timeout=120):
    deadline = time.monotonic() + timeout
    local = public = False
    while time.monotonic() < deadline:
        local = health("http://127.0.0.1:8000", timeout=2)
        public = local and health("https://dunyochoyxona.uz", timeout=4)
        if local and public:
            print("TAYYOR: lokal server va https://dunyochoyxona.uz javob bermoqda.")
            return 0
        time.sleep(2)
    if local:
        print("Lokal server ishlayapti. Domen hali javob bermadi: internet/Cloudflare ulanishini tekshiring. Tunnel qayta urinadi.")
        return 2
    print("XATO: lokal server tayyor bo'lmadi. server.log va uvicorn.log ni tekshiring; vazifa qayta urinadi.")
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "prepare", "stop", "wait", "health"))
    args = parser.parse_args()
    try:
        if args.action in ("check", "prepare"):
            preflight(prepare=args.action == "prepare")
            check_port()
        elif args.action == "stop":
            stop_project()
        elif args.action == "health":
            local = health("http://127.0.0.1:8000")
            public = health("https://dunyochoyxona.uz")
            print(json.dumps({"local_healthy": local, "domain_healthy": public}))
            return 0 if local and public else 2
        else:
            return wait_ready()
    except Exception as exc:
        # Do not echo arbitrary library errors; a parser error could contain a URL secret.
        if isinstance(exc, RuntimeError):
            print("XATO: " + str(exc))
        else:
            print("XATO: tekshiruv bajarilmadi (" + type(exc).__name__ + "). Sozlamalar o'zgartirilmadi.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
