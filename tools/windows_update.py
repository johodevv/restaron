"""Staged Windows update. Standard library only in the coordinating process.

The running checkout is changed only after download, dependency and build checks.
Runtime data is never copied from Git, reset, cleaned, or restored automatically.
"""
import argparse
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import time
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UPDATER_PROTOCOL = 1
BOOTSTRAP_FILES = {'tools/windows_update.py', 'tools/windows_update.ps1', 'RESTARON_YANGILASH.bat'}
CODE_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.css', '.html', '.json', '.toml', '.yaml', '.yml', '.bat', '.ps1'}
DEPLOY_FILES = {'tools/windows_update.py', 'tools/windows_update.ps1', 'tools/windows_autostart.py',
                'tools/windows_autostart.ps1', 'RESTARON_YANGILASH.bat', 'RESTARON_AVTO_SERVER.bat'}


class UpdateError(RuntimeError):
    pass


def protected(name, extra=()):
    path = PurePosixPath(str(name).replace('\\', '/').lower())
    parts = path.parts
    if not parts or '..' in parts or path.is_absolute() or ':' in str(path):
        return True
    if any(part in {'.git', 'node_modules', 'dist', 'dist-ssr', 'uploads', 'receipts_archive',
                    'backups', 'zaxira', 'scratch', '__pycache__', 'env', 'venv'}
           or part.startswith('.venv') for part in parts):
        return True
    leaf = parts[-1]
    if (leaf == '.env' or leaf.startswith('.env.') or leaf.endswith(('.env', '.db', '.db-wal', '.db-shm',
            '.sqlite', '.sqlite3', '.log', '.server.lock', '.zip', '.pyc', '.pyd'))):
        return True
    if leaf in {'cloudflared.exe', 'tunnel_sozlama.txt', 'server_pids.json', 'server_status.json',
                'server_online_url.txt', 'restaron_tekshiruv.txt', '_xizmat_ishga_tushirish.cmd', '_saytni_ochish.cmd'}:
        return True
    for item in extra:
        item = str(item).replace('\\', '/').strip('/').lower()
        if str(path) == item or str(path).startswith(item + '/') or item.startswith(str(path) + '/'):
            return True
    return False


def inside(root, name):
    relative = PurePosixPath(str(name).replace('\\', '/'))
    if (relative.is_absolute() or not relative.parts or '..' in relative.parts
            or any(':' in part or part.endswith((' ', '.')) for part in relative.parts)):
        raise UpdateError('Fayl yoli xavfsiz emas; yangilash toxtatildi.')
    target = root.joinpath(*relative.parts)
    target.resolve().relative_to(root.resolve())
    # A reparse point must never redirect a code write into live data or outside root.
    for parent in (target, *target.parents):
        if parent == root.parent:
            break
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise UpdateError('Kod ichida symlink/junction bor; avtomatik almashtirish toxtatildi.')
    return target


def run(command, cwd, log=None, timeout=600, env=None, binary=False):
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    proc = subprocess.Popen([str(arg) for arg in command], cwd=str(cwd), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=flags)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
        else:
            proc.kill()
        proc.communicate()
        raise UpdateError('Buyruq uchun kutish vaqti tugadi; keyingi bosqich boshlanmadi.')
    except BaseException:
        # A cancelled installer must not leave pip/npm writing during rollback.
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
        else:
            proc.kill()
        proc.communicate(timeout=15)
        raise
    if log:
        # Library output can include authenticated URLs. Redact URL credentials/tokens.
        text = (out + err).decode('utf-8', 'replace')
        text = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1[redacted]@', text)
        text = re.sub(r'(https?://)[^\s/@]+@', r'\1[redacted]@', text)
        text = re.sub(r'(?i)(token|password|secret)([=: ]+)[^\s&]+', r'\1\2[redacted]', text)
        with Path(log).open('a', encoding='utf-8') as handle:
            handle.write(text + '\n')
    if proc.returncode:
        raise UpdateError(f'Buyruq bajarilmadi: {Path(str(command[0])).name} (kod {proc.returncode}). Jurnalni tekshiring.')
    return out if binary else out.decode('utf-8', 'replace').strip()


def git(root, *args, **kwargs):
    return run(['git', '-c', 'core.quotePath=false', *args], root, **kwargs)


def files_at(root, revision):
    data = git(root, 'ls-tree', '-rz', '--full-tree', revision, binary=True)
    result = []
    for entry in data.split(b'\0'):
        if not entry:
            continue
        header, name = entry.split(b'\t', 1)
        mode = header.split(b' ', 1)[0]
        if mode in {b'120000', b'160000'}:
            raise UpdateError('Symlink yoki submodule mavjud. Bu yangilagich oddiy loyiha fayllari uchun.')
        result.append(name.decode('utf-8'))
    return result


def upstream(root):
    if git(root, 'rev-parse', '--show-toplevel').replace('\\', '/').lower() != str(root.resolve()).replace('\\', '/').lower():
        raise UpdateError('BAT Git loyihasining asosiy papkasida turishi kerak.')
    branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    remote = git(root, 'config', '--get', f'branch.{branch}.remote')
    merge = git(root, 'config', '--get', f'branch.{branch}.merge')
    if remote == '.' or remote.startswith('-') or not merge.startswith('refs/heads/'):
        raise UpdateError('GitHub branch upstream sozlamasi mos emas.')
    remote_ref = git(root, 'rev-parse', '--symbolic-full-name', '@{upstream}')
    # Do not display remote URLs: they may contain credentials.
    git(root, 'remote', 'get-url', remote)
    return branch, remote, merge, remote_ref


def extract_code(root, revision, destination, extra=()):
    names = files_at(root, revision)
    if len({name.lower() for name in names}) != len(names):
        raise UpdateError('GitHub fayl nomlarida katta/kichik harf kolliziyasi bor; Windows uchun mos emas.')
    for name in names:
        inside(destination, name)
    archive = git(root, 'archive', '--format=zip', revision, binary=True)
    import io
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for item in bundle.infolist():
            if item.is_dir() or protected(item.filename, extra):
                continue
            if stat.S_ISLNK(item.external_attr >> 16):
                raise UpdateError('Arxiv ichida symlink bor.')
            target = inside(destination, item.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(item) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
    for required in ('backend/app/main.py', 'backend/requirements.txt', 'frontend/package-lock.json',
                     'frontend/package.json', 'frontend_build.py', 'server_manager.py'):
        if not (destination / required).is_file():
            raise UpdateError(f'GitHub versiyasida kerakli fayl yoq: {required}. Server ozgartirilmadi.')
    # A first deployment can still point to a commit containing the old BAT.
    # Do not downgrade the installed updater back to that unsafe implementation.
    updater_source = destination / 'tools/windows_update.py'
    protocol = None
    if updater_source.is_file():
        match = re.search(r'^UPDATER_PROTOCOL\s*=\s*(\d+)\s*$', updater_source.read_text(encoding='utf-8'), re.MULTILINE)
        if match:
            protocol = int(match.group(1))
    keep_bootstrap = protocol is None or protocol < UPDATER_PROTOCOL
    return [name for name in names if not protected(name, extra)
            and not (keep_bootstrap and name in BOOTSTRAP_FILES)]


def local_files(root, extra=()):
    tracked = git(root, 'ls-files', '-z', binary=True).split(b'\0')
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z', binary=True).split(b'\0')
    return sorted({item.decode('utf-8') for item in tracked + untracked
                   if item and not protected(item.decode('utf-8'), extra)})


def snapshot_code(root, destination, target_names, extra=()):
    old_head = git(root, 'rev-parse', 'HEAD')
    old_tracked = files_at(root, old_head)
    names = set(local_files(root, extra)) | set(target_names) | {name for name in old_tracked if not protected(name, extra)}
    present, directories = [], []
    for name in sorted(names):
        target = inside(root, name)
        if target.is_dir():
            # Refuse file/directory transitions rather than recursively deleting unknown data.
            if name in target_names:
                raise UpdateError(f'Yangi fayl ornida papka mavjud: {name}. Hech narsa ochirilmadi.')
            directories.append(name)
        elif target.is_file():
            saved = inside(destination / 'code', name)
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            present.append(name)
    index = Path(git(root, 'rev-parse', '--git-path', 'index'))
    if not index.is_absolute():
        index = root / index
    if index.exists():
        shutil.copy2(index, destination / 'index-before')
    record = {'head': old_head, 'files': present, 'index_path': str(index),
              'old_tracked': old_tracked, 'target_files': target_names}
    (destination / 'code-before.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    return record


def atomic_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_name(target.name + '.update-' + secrets.token_hex(4))
    try:
        shutil.copy2(source, pending)
        os.replace(pending, target)
    finally:
        if pending.exists():
            pending.unlink()


def publish_code(root, stage, revision, record, extra=()):
    target_names = set(record['target_files'])
    # No hard reset and no git clean: Git never writes to runtime paths.
    git(root, 'reset', '--mixed', revision)
    remove = set(record['old_tracked']) | {
        name for name in record['files'] if PurePosixPath(name).suffix.lower() in CODE_EXTENSIONS
        or name.startswith(('backend/app/', 'frontend/src/', 'frontend/public/'))
    }
    for name in sorted(remove - target_names, key=len, reverse=True):
        if protected(name, extra) or name in DEPLOY_FILES:
            continue
        target = inside(root, name)
        if target.is_file():
            target.unlink()
    for name in sorted(target_names):
        atomic_copy(inside(stage, name), inside(root, name))


def rollback_code(root, destination, record, extra=()):
    git(root, 'reset', '--mixed', record['head'])
    original = set(record['files'])
    for name in set(record['target_files']) - original:
        if not protected(name, extra):
            target = inside(root, name)
            if target.is_file():
                target.unlink()
    for name in record['files']:
        atomic_copy(inside(destination / 'code', name), inside(root, name))
    saved_index = destination / 'index-before'
    if saved_index.exists():
        atomic_copy(saved_index, Path(record['index_path']))


def backup_sqlite(source, destination):
    if not source.is_file():
        raise UpdateError('Ishchi baza topilmadi. Bosh baza yaratilmaydi.')
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=30)) as src, \
            closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise UpdateError('Baza zaxirasi tekshiruvdan otmadi.')


def load_helper(path):
    spec = importlib.util.spec_from_file_location('restaron_update_runtime', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_action(root, helper, action):
    module = load_helper(helper)
    if action == 'info':
        module.check_port(root)
        db = module.database_path(root)
        with module.read_database(db):
            pass
        domain = module.tunnel_settings(root)
        from dotenv import dotenv_values
        values = dotenv_values(root / 'backend/.env')
        extra = []
        paths = [str(db)] + [os.environ.get(key) or values.get(key) for key in
                            ('UPLOAD_DIR', 'PDF_ARCHIVE_DIR', 'BACKUP_DIR', 'BACKUP_EXTRA_DIR')]
        for raw in paths:
            if raw:
                path = Path(raw)
                if not path.is_absolute():
                    path = root / 'backend' / path
                try:
                    extra.append(path.resolve().relative_to(root).as_posix())
                except ValueError:
                    pass
        print(json.dumps({'database': str(db), 'domain': domain, 'extra': extra}))
    elif action == 'stop':
        module.stop_project(root)


class WindowsTask:
    def __init__(self, root, python, log):
        self.root, self.python, self.log = root, python, log
        self.name = 'RestAron Server'

    @staticmethod
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    def ps(self, body):
        import base64
        script = "$ErrorActionPreference='Stop'; " + body
        encoded = base64.b64encode(script.encode('utf-16-le')).decode()
        exe = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        return run([exe, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', encoded],
                   self.root, log=self.log, timeout=60)

    def inspect(self):
        raw = self.ps("$t=Get-ScheduledTask -TaskName 'RestAron Server' -TaskPath '\\' -ErrorAction SilentlyContinue; "
            "if($null -eq $t){'null'}else{@{State=[string]$t.State;Enabled=[bool]$t.Settings.Enabled;"
            "Actions=@($t.Actions | ForEach-Object {@{Execute=[string]$_.Execute;Arguments=[string]$_.Arguments}})} "
            "| ConvertTo-Json -Depth 5 -Compress}")
        task = json.loads(raw)
        if task:
            actions = task.get('Actions') or []
            if isinstance(actions, dict):
                actions = [actions]
            manager = str(self.root / 'server_manager.py').replace('/', '\\').lower()
            legacy = str(self.root / '_xizmat_ishga_tushirish.cmd').replace('/', '\\').lower()
            if len(actions) != 1 or not (
                ((actions[0].get('Execute') or '').replace('/', '\\').lower() == str(self.python).replace('/', '\\').lower()
                 and re.search(r'(?:^|\s)"?' + re.escape(manager) + r'"?(?:\s|$)',
                               (actions[0].get('Arguments') or '').replace('/', '\\').lower()))
                or (actions[0].get('Execute') or '').replace('/', '\\').lower() == legacy
            ):
                raise UpdateError('RestAron Server vazifasi boshqa loyihaga tegishli. Unga tegilmadi.')
        return task

    def disable(self):
        if self.inspect():
            self.ps("Disable-ScheduledTask -TaskName 'RestAron Server' -TaskPath '\\' | Out-Null")

    def start(self):
        python, root = self.quote(self.python), self.quote(self.root)
        arguments = self.quote(f'-X utf8 -u "{self.root / "server_manager.py"}" serve')
        self.ps(f"$a=New-ScheduledTaskAction -Execute {python} -Argument {arguments} -WorkingDirectory {root}; "
            "$t=New-ScheduledTaskTrigger -AtStartup; $t.Delay='PT30S'; "
            "$p=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest; "
            "$s=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -RestartCount 999 "
            "-RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) "
            "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden -Priority 5; "
            "$d=New-ScheduledTask -Action $a -Trigger $t -Principal $p -Settings $s; "
            "Register-ScheduledTask -TaskName 'RestAron Server' -TaskPath '\\' -InputObject $d -Force | Out-Null; "
            "Start-ScheduledTask -TaskName 'RestAron Server' -TaskPath '\\'")


def health(url):
    try:
        with urlopen(Request(url.rstrip('/') + '/health', headers={'User-Agent': 'Mozilla/5.0 RestAronUpdater'}), timeout=3) as response:
            return response.status == 200 and json.load(response).get('status') == 'healthy'
    except Exception:
        return False


def wait_health(url, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if health(url):
            return True
        time.sleep(2)
    return False


@contextmanager
def update_lock(root):
    with (root / 'update.server.lock').open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise UpdateError('Boshqa yangilash ishlamoqda; ikkinchi nusxa ochilmadi.') from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Updater:
    def __init__(self, root, python, task_factory=WindowsTask):
        self.root, self.python = root.resolve(), python.resolve()
        self.task_factory = task_factory
        self.backup = self.work = self.log = None

    def say(self, message):
        print(message, flush=True)
        if self.log:
            with self.log.open('a', encoding='utf-8') as output:
                output.write(message + '\n')

    def child(self, action, python=None):
        return run([python or self.python, '-X', 'utf8', self.frozen_runner, '--root', self.root,
                    '--helper', self.frozen_helper, '--runtime-action', action], self.root,
                   log=self.log, timeout=90)

    def check(self):
        if not shutil.which('git'):
            raise UpdateError('Git topilmadi. Yangi kompyuterda Git for Windows ornatilishi kerak.')
        if not (self.root / '.git').exists():
            raise UpdateError('.git topilmadi. ZIP nusxasini Git bilan boglash kerak; baza ozgartirilmadi.')
        if not self.python.is_file():
            raise UpdateError('backend/.venv Python topilmadi. Avval birinchi ornatishni bajaring.')
        version = run([self.python, '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'], self.root)
        if version != '3.12':
            raise UpdateError('Yangilash uchun ishchi Python muhiti 3.12 bolishi kerak.')
        branch, remote, merge, remote_ref = upstream(self.root)
        for state in ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'index.lock'):
            path = Path(git(self.root, 'rev-parse', '--git-path', state))
            if not path.is_absolute():
                path = self.root / path
            if path.exists():
                raise UpdateError('Git merge/rebase yoki boshqa Git jarayoni tugamagan. Avval uni yakunlash kerak.')
        node = shutil.which('node.exe' if os.name == 'nt' else 'node')
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        if not node or not npm:
            raise UpdateError('Node.js/npm topilmadi.')
        npm_cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
        if os.name == 'nt' and not npm_cli.is_file():
            raise UpdateError('Node.js npm-cli.js topilmadi. Node.js ornatilishini tekshiring.')
        self.node = node
        self.npm = [node, npm_cli] if os.name == 'nt' else [npm]
        if not (self.root / 'tools/windows_autostart.py').is_file():
            raise UpdateError('tools/windows_autostart.py yetishmayapti. Yangilash ZIP paketini toliq oching.')
        return branch, remote, merge, remote_ref

    def stage(self, revision, extra):
        stage = self.work / 'candidate'
        names = extract_code(self.root, revision, stage, extra)
        # Build-time frontend settings are local deployment settings, never taken from Git.
        for name in ('.env', '.env.local', '.env.production', '.env.production.local'):
            source = self.root / 'frontend' / name
            if source.is_file():
                shutil.copy2(source, stage / 'frontend' / name)
        self.say('[2/6] Python kutubxonalari alohida muhitda tayyorlanmoqda...')
        wheels = self.work / 'wheels'
        wheels.mkdir()
        run([self.python, '-m', 'pip', 'download', '--only-binary=:all:', '-r', stage / 'backend/requirements.txt',
             '--dest', wheels], self.root, log=self.log, timeout=1200)
        envdir = self.work / 'candidate-venv'
        run([self.python, '-m', 'venv', envdir], self.root, log=self.log)
        staged_python = envdir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        run([staged_python, '-m', 'pip', 'install', '--no-index', '--find-links', wheels,
             '-r', stage / 'backend/requirements.txt'], self.root, log=self.log)
        run([staged_python, '-m', 'pip', 'check'], self.root, log=self.log)
        frozen = run([staged_python, '-m', 'pip', 'freeze'], self.root, log=self.log)
        (self.work / 'resolved-requirements.txt').write_text(frozen + '\n', encoding='utf-8')
        self.say('[3/6] Sayt alohida papkada yigilib tekshirilmoqda...')
        run([*self.npm, 'ci', '--no-audit', '--no-fund'], stage / 'frontend', log=self.log, timeout=1200)
        run([self.python, '-X', 'utf8', '-c',
             'from pathlib import Path; from frontend_build import ensure_frontend_build; ensure_frontend_build(Path.cwd())'],
            stage, log=self.log, timeout=600)
        # Smoke test on a CLONE: no real printer worker or live database access.
        self.smoke(stage, staged_python)
        # Check the current app can also start against the migrated clone before
        # allowing a release that might need code rollback later.
        self.smoke(self.root, self.python, reset_db=False)
        return stage, names, staged_python

    def smoke(self, stage, python, reset_db=True):
        probe_db = self.work / 'smoke.db'
        if reset_db:
            backup_sqlite(self.database, probe_db)
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        env = os.environ.copy()
        env.update({'DATABASE_URL': 'sqlite+aiosqlite:///' + probe_db.as_posix(),
                    'SYNC_DATABASE_URL': 'sqlite:///' + probe_db.as_posix(),
                    'SECRET_KEY': secrets.token_hex(32), 'AUTO_SEED': 'false',
                    'UPLOAD_DIR': str(self.work / 'smoke-uploads'), 'PDF_ARCHIVE_DIR': str(self.work / 'smoke-pdf'),
                    'QR_BASE_URL': self.domain, 'FRONTEND_URL': self.domain, 'DEBUG': 'false',
                    'PYTHONPATH': str(stage / 'backend'), 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})
        script = self.work / 'smoke_runner.py'
        script.write_text(
            'import sys, asyncio\nsys.path.insert(0, sys.argv[1])\n'
            'from app.core import printer_queue\n'
            'printer_queue.start_printer_worker = lambda: None\n'
            'async def no_stop(): pass\nprinter_queue.stop_printer_worker = no_stop\n'
            'import uvicorn\nuvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[2]), '
            'log_level="warning", access_log=False)\n', encoding='utf-8')
        with (self.work / ('smoke.log' if reset_db else 'rollback-smoke.log')).open('wb') as output:
            proc = subprocess.Popen([str(python), str(script), str(stage / 'backend'), str(port)],
                    cwd=stage / 'backend', env=env, stdout=output, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                deadline = time.monotonic() + 90
                while proc.poll() is None and time.monotonic() < deadline:
                    if health(f'http://127.0.0.1:{port}'):
                        return
                    time.sleep(1)
                raise UpdateError('Yangi backend sinov bazasida ishga tushmadi. smoke.log ni tekshiring; ishchi server saqlandi.')
            finally:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
                elif proc.poll() is None:
                    proc.terminate()
                proc.wait(timeout=15)
                # Windows can finish descendant handle cleanup just after taskkill
                # returns. Opening a fresh SQLite connection avoids deleting WAL files.

    def apply(self, stage, revision, names, staged_python, task, extra):
        record = snapshot_code(self.root, self.backup, names, extra)
        venv = self.root / 'backend/.venv'
        # Copy before stopping, and before package installation can change it.
        shutil.copytree(venv, self.backup / 'venv-before', ignore=shutil.ignore_patterns('__pycache__'))
        dist = self.root / 'frontend/dist'
        if dist.is_dir():
            shutil.copytree(dist, self.backup / 'dist-before')
        previous_task = task.inspect()
        (self.backup / 'task-before.json').write_text(json.dumps(previous_task), encoding='utf-8')
        task.disable()
        stopped = changed = False
        try:
            self.say('[4/6] Chek tugashi kutilmoqda; server qisqa muddat toxtatiladi...')
            # Mark before call: a partially failed stop still needs recovery.
            stopped = True
            self.child('stop')
            backup_sqlite(self.database, self.backup / 'database-before.db')
            (self.backup / 'status.json').write_text(json.dumps({'phase': 'stopped', 'target': revision}), encoding='utf-8')
            self.say('[5/6] GitHub kodi va tayyor kutubxonalar joylanmoqda...')
            changed = True
            publish_code(self.root, stage, revision, record, extra)
            run([self.python, '-m', 'pip', 'install', '--no-index', '--find-links', self.work / 'wheels',
                 '-r', self.work / 'resolved-requirements.txt'], self.root, log=self.log)
            run([self.python, '-m', 'pip', 'check'], self.root, log=self.log)
            # Same source fingerprint, plus existing old assets for open browser tabs.
            build = load_helper(stage / 'frontend_build.py')
            metadata = json.loads((stage / 'frontend/dist/restaron-build.json').read_text(encoding='utf-8'))
            build.publish_build(self.root, stage / 'frontend/dist', metadata['source_sha256'])
            self.say('[6/6] Server qayta ishga tushirilmoqda...')
            task.start()
            if not wait_health('http://127.0.0.1:8000'):
                raise UpdateError('Yangi server soglom javob bermadi.')
            current = task.inspect()
            if not current or current['State'] not in (4, 'Running'):
                raise UpdateError('Avtomatik vazifa ishlayotgani tasdiqlanmadi.')
            (self.backup / 'status.json').write_text(json.dumps({'phase': 'success', 'target': revision}), encoding='utf-8')
        except BaseException:
            if stopped:
                self.say('Yangilash tasdiqlanmadi. Oldingi kod va Python muhiti tiklanmoqda...')
                try:
                    task.disable()
                    # The staged environment remains usable even if the live venv install failed.
                    if changed:
                        self.child('stop', python=staged_python)
                        rollback_code(self.root, self.backup, record, extra)
                        replace_tree(self.root, venv, self.backup / 'venv-before')
                        if (self.backup / 'dist-before').exists():
                            replace_tree(self.root, dist, self.backup / 'dist-before')
                    task.start()
                    healthy = wait_health('http://127.0.0.1:8000')
                    self.say('Oldingi server tiklandi.' if healthy else 'Server tiklanishi tasdiqlanmadi. Zaxira va jurnallar saqlandi.')
                except Exception as recovery:
                    self.say('Tiklash xatosi: ' + str(recovery))
                # NEVER restore the live DB: new user writes must not be overwritten.
                (self.backup / 'status.json').write_text(json.dumps({'phase': 'failed', 'target': revision}), encoding='utf-8')
            raise

    def execute(self, check_only=False):
        branch, remote, merge, remote_ref = self.check()
        if check_only:
            self.say(f'TEKSHIRUV OTDI. Joriy branch: {branch}. Kod yuklanmadi, server ozgartirilmadi.')
            return 0
        with update_lock(self.root):
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            self.backup = self.root / 'backups/updates' / stamp
            self.work = self.root / 'scratch/updates' / stamp
            self.backup.mkdir(parents=True)
            self.work.mkdir(parents=True)
            self.log = self.backup / 'update.log'
            self.say(f'Zaxira va jurnal: {self.backup}')
            self.say(f'[1/6] GitHub dan joriy branch olinmoqda: {branch}')
            self.frozen_runner = self.work / 'windows_update.py'
            self.frozen_helper = self.work / 'windows_autostart.py'
            shutil.copy2(Path(__file__), self.frozen_runner)
            shutil.copy2(self.root / 'tools/windows_autostart.py', self.frozen_helper)
            shutil.copy2(self.root / 'frontend_build.py', self.backup / 'frontend_build.py')
            info = json.loads(self.child('info').splitlines()[-1])
            self.database, self.domain = Path(info['database']), info['domain']
            extra = info['extra']
            git(self.root, 'fetch', '--no-tags', remote, f'+{merge}:{remote_ref}', log=self.log, timeout=300)
            revision = git(self.root, 'rev-parse', '--verify', f'{remote_ref}^{{commit}}')
            task = self.task_factory(self.root, self.python, self.log)
            task.inspect()  # Ownership/permission errors are detected before download/build.
            free = shutil.disk_usage(self.root).free
            venv_size = sum(path.stat().st_size for path in (self.root / 'backend/.venv').rglob('*') if path.is_file())
            if free < max(2 * 1024**3, venv_size * 4):
                raise UpdateError('Zaxira va yigish uchun diskda kamida 2 GB bosh joy kerak.')
            stage, names, staged_python = self.stage(revision, extra)
            self.apply(stage, revision, names, staged_python, task, extra)
            self.say('YANGILASH TUGADI. Lokal server soglom. Commit: ' + revision[:12])
            if not wait_health(self.domain, timeout=30):
                self.say('ESLATMA: domen hali tasdiqlanmadi. Internet/Cloudflare ulanishini tekshiring; lokal server ishlayapti.')
                return 2
            self.say('Domen ham javob berdi: ' + self.domain)
            return 0


def replace_tree(root, target, backup):
    resolved = target.resolve()
    resolved.relative_to(root.resolve())
    if resolved not in {(root / 'backend/.venv').resolve(), (root / 'frontend/dist').resolve()}:
        raise UpdateError('Tiklash papkasi ruxsat etilgan chegaradan tashqarida.')
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(backup, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--runtime-action', choices=('info', 'stop'))
    parser.add_argument('--helper', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.runtime_action:
            runtime_action(root, args.helper, args.runtime_action)
            return 0
        return Updater(root, args.python or root / 'backend/.venv/Scripts/python.exe').execute(args.check)
    except (Exception, KeyboardInterrupt) as error:
        print('XATO: ' + str(error), flush=True)
        print('Yangilash muvaffaqiyati tasdiqlanmadi. backups/updates ichidagi jurnalni tekshiring.', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
