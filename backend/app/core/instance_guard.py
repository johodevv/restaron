"""The in-process WebSocket hub and physical printers require one app instance."""
from contextlib import asynccontextmanager
import os
import threading
from sqlalchemy import text
from app.core.database import engine, is_sqlite

_instances = {}
_mutex = threading.Lock()


@asynccontextmanager
async def application_instance_lock():
    if not is_sqlite:
        async with engine.connect() as connection:
            if not await connection.scalar(text('SELECT pg_try_advisory_lock(73412, 0)')):
                raise RuntimeError('RestAron allaqachon ishlayapti. Bitta backend process/worker ishlating.')
            try:
                yield
            finally:
                await connection.execute(text('SELECT pg_advisory_unlock(73412, 0)'))
        return
    path = os.path.abspath(engine.url.database) + '.server.lock'
    with _mutex:
        if path in _instances:
            _instances[path][1] += 1
        else:
            handle = open(path, 'a+b')
            handle.seek(0, os.SEEK_END)
            if not handle.tell():
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
                handle.close()
                raise RuntimeError('RestAron allaqachon ishlayapti. Bitta backend process/worker ishlating.') from exc
            _instances[path] = [handle, 1]
    try:
        yield
    finally:
        with _mutex:
            _instances[path][1] -= 1
            if not _instances[path][1]:
                handle, _ = _instances.pop(path)
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
