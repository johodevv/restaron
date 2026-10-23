"""Validate and publish the frontend without replacing a working build on failure."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

MANIFEST = 'restaron-build.json'


def source_fingerprint(frontend):
    frontend = Path(frontend)
    files = []
    for folder in ('src', 'public'):
        files.extend(path for path in (frontend / folder).rglob('*') if path.is_file())
    for name in ('index.html', 'package.json', 'package-lock.json', 'vite.config.js',
                 'tailwind.config.js', 'postcss.config.js', '.env', '.env.local',
                 '.env.production', '.env.production.local'):
        path = frontend / name
        if path.is_file():
            files.append(path)
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(frontend).as_posix().encode())
        digest.update(b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def validate_build(directory):
    directory = Path(directory).resolve()
    index = directory / 'index.html'
    html = index.read_text(encoding='utf-8')
    assets = re.findall(r'(?:src|href)=["\'](/assets/[^"\']+)["\']', html)
    if not any(path.endswith('.js') for path in assets):
        raise ValueError('Build ichida JavaScript kirish fayli topilmadi')
    for asset in assets:
        target = (directory / asset.lstrip('/')).resolve()
        target.relative_to(directory)
        if not target.is_file():
            raise ValueError(f'Build fayli yetishmayapti: {asset}')
    return hashlib.sha256(index.read_bytes()).hexdigest()


def build_is_current(frontend):
    frontend = Path(frontend)
    try:
        metadata = json.loads((frontend / 'dist' / MANIFEST).read_text(encoding='utf-8'))
        return (metadata['source_sha256'] == source_fingerprint(frontend)
                and metadata['index_sha256'] == validate_build(frontend / 'dist'))
    except (OSError, ValueError, KeyError):
        return False


def publish_build(root, staging, fingerprint):
    root, staging = Path(root).resolve(), Path(staging).resolve()
    index_hash = validate_build(staging)
    if fingerprint != source_fingerprint(root / 'frontend'):
        raise ValueError('Build paytida manba o‘zgardi; qayta yig‘ish kerak')
    dist = root / 'frontend' / 'dist'
    backup = None
    if dist.exists():
        backup = root / 'backups' / ('frontend_before_update_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dist, backup)
    dist.mkdir(parents=True, exist_ok=True)
    # Keep old hashed assets so already-open tabs can finish loading their chunks.
    shutil.copytree(staging, dist, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('index.html', MANIFEST))
    index_pending = dist / 'index.html.pending'
    shutil.copyfile(staging / 'index.html', index_pending)
    os.replace(index_pending, dist / 'index.html')
    metadata_pending = dist / (MANIFEST + '.pending')
    metadata_pending.write_text(json.dumps({'source_sha256': fingerprint,
        'index_sha256': index_hash, 'published_at': datetime.now(timezone.utc).isoformat()}, indent=2), encoding='utf-8')
    os.replace(metadata_pending, dist / MANIFEST)
    return backup


def ensure_frontend_build(root, log=print):
    root = Path(root)
    frontend = root / 'frontend'
    if build_is_current(frontend):
        log('Frontend build tekshirildi: joriy kodga mos.')
        return
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm and os.name == 'nt':
        candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'nodejs/npm.cmd'
        npm = str(candidate) if candidate.is_file() else None
    if not npm or not (frontend / 'node_modules').is_dir():
        raise RuntimeError('Frontend build eskirgan. Node.js/npm va frontend kutubxonalarini o‘rnating; server eski sayt bilan ochilmadi.')
    log('Frontend build eskirgan yoki tekshirilmagan; yangi build tayyorlanmoqda...')
    fingerprint = source_fingerprint(frontend)
    scratch = root / 'scratch'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='frontend-build-', dir=scratch) as folder:
        command = [npm, 'run', 'build', '--', '--outDir', folder]
        result = subprocess.run(command, cwd=frontend, capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode:
            raise RuntimeError('Frontend build xatosi; oldingi build saqlandi.\n' + (result.stdout + result.stderr)[-3000:])
        backup = publish_build(root, folder, fingerprint)
    log(f'Yangi frontend build joylandi. Zaxira: {backup or "birinchi build"}')
