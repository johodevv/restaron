"""No live database writes, process termination, task registration or reboot."""
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server_manager
from tools import windows_autostart as startup


class SupervisorTests(unittest.TestCase):
    def test_windows_bom_does_not_change_fixed_domain(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "tunnel_sozlama.txt"
            config.write_text("TOKEN=test-secret\nMANZIL=https://dunyochoyxona.uz\n", encoding="utf-8-sig")
            with patch.object(server_manager, "TUNNEL_CONFIG", config):
                self.assertEqual(server_manager.read_tunnel_config(), ("test-secret", "https://dunyochoyxona.uz"))

    def test_lock_excludes_another_process_then_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "test.server.lock"
            script = Path(folder) / "lock_probe.py"
            script.write_text(
                "import sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\n"
                "from server_manager import supervisor_lock\n"
                "with supervisor_lock(Path(sys.argv[2])) as ok: print(ok, flush=True)\n", encoding="utf-8")
            def probe():
                return subprocess.check_output([sys.executable, str(script), str(ROOT), str(lock)], text=True).strip()
            with server_manager.supervisor_lock(lock) as owned:
                self.assertTrue(owned)
                self.assertEqual(probe(), "False")
            self.assertEqual(probe(), "True")

    def test_second_supervisor_does_not_prepare_or_start_anything(self):
        with patch.object(server_manager, "supervisor_lock") as lock, \
                patch.object(server_manager, "_serve_forever_locked") as run, \
                patch.object(server_manager, "attach_windows_child_job") as job, \
                patch.object(server_manager, "log"):
            lock.return_value.__enter__.return_value = False
            server_manager.serve_forever()
            run.assert_not_called()
            job.assert_not_called()

    def test_build_failure_is_nonzero_for_scheduler_recovery(self):
        with patch.object(server_manager, "prepare_frontend", return_value=False), \
                patch.object(server_manager, "log"):
            with self.assertRaises(SystemExit) as error:
                server_manager._serve_forever_locked()
            self.assertEqual(error.exception.code, 1)

    def test_tunnel_token_is_environment_only(self):
        stop = threading.Event()
        fake = Mock()
        fake.stdout = iter(())
        fake.pid = 42
        fake.wait.side_effect = lambda: stop.set()
        secret = "private-test-token-do-not-log"
        with patch.object(server_manager, "read_tunnel_config", return_value=(secret, "https://dunyochoyxona.uz")), \
                patch.object(server_manager, "CLOUDFLARED_EXE") as exe, \
                patch.object(server_manager, "URL_FILE") as url, \
                patch.object(server_manager, "log") as logger, \
                patch.object(server_manager.subprocess, "Popen", return_value=fake) as popen:
            exe.exists.return_value = True
            server_manager._tunnel_supervisor(stop)
            self.assertNotIn(secret, repr(popen.call_args.args))
            self.assertEqual(popen.call_args.kwargs["env"]["TUNNEL_TOKEN"], secret)
            self.assertNotIn(secret, repr(logger.call_args_list))
            url.write_text.assert_called_once_with("https://dunyochoyxona.uz", encoding="utf-8")

    @unittest.skipUnless(os.name == "nt", "Windows job object")
    def test_supervisor_crash_cleans_descendants_and_releases_lock(self):
        import psutil
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / "test.server.lock"
            pidfile = Path(folder) / "child.json"
            script = Path(folder) / "job_probe.py"
            script.write_text(
                "import os, sys, json, subprocess, time\nfrom pathlib import Path\n"
                "sys.path.insert(0, sys.argv[1])\nfrom server_manager import supervisor_lock, attach_windows_child_job\n"
                "with supervisor_lock(Path(sys.argv[2])) as owned:\n"
                " assert owned\n job = attach_windows_child_job()\n"
                " child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                " Path(sys.argv[3]).write_text(json.dumps({'pid': child.pid}))\n"
                " time.sleep(0.2)\n os._exit(19)\n", encoding="utf-8")
            proc = subprocess.Popen([sys.executable, str(script), str(ROOT), str(lock), str(pidfile)])
            try:
                self.assertEqual(proc.wait(timeout=15), 19)
                child_pid = json.loads(pidfile.read_text())["pid"]
                deadline = time.monotonic() + 5
                while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertFalse(psutil.pid_exists(child_pid), "orphan child survived")
                with server_manager.supervisor_lock(lock) as owned:
                    self.assertTrue(owned)
            finally:
                if proc.poll() is None:
                    proc.kill()
                if pidfile.exists():
                    child_pid = json.loads(pidfile.read_text())["pid"]
                    if psutil.pid_exists(child_pid):
                        psutil.Process(child_pid).kill()


class InstallerTests(unittest.TestCase):
    def test_domain_validation_preserves_config_and_does_not_print_token(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "tunnel_sozlama.txt"
            for domain in ("https://dunyochoyxona.uz", "dunyochoyxona.uz/"):
                original = f"TOKEN=private-test-secret\nMANZIL={domain}\n"
                path.write_text(original, encoding="utf-8-sig")
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(startup.tunnel_settings(root), "https://dunyochoyxona.uz")
                self.assertNotIn("private-test-secret", output.getvalue())
                self.assertEqual(path.read_text(encoding="utf-8-sig"), original)

    def test_wrong_domain_and_missing_token_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for config in ("TOKEN=secret\nMANZIL=https://other.uz", "TOKEN=\nMANZIL=dunyochoyxona.uz",
                           "TOKEN=secret\nMANZIL=https://dunyochoyxona.uz@evil.uz",
                           "TOKEN=secret\nMANZIL=https://dunyochoyxona.uz?token=secret"):
                (root / "tunnel_sozlama.txt").write_text(config, encoding="utf-8")
                with self.assertRaises(RuntimeError) as error:
                    startup.tunnel_settings(root)
                self.assertNotIn("secret", str(error.exception))

    def test_only_this_checkout_is_selected(self):
        with tempfile.TemporaryDirectory(prefix="RestAron space ! ") as folder:
            root = Path(folder).resolve()
            own = str(root / "server_manager.py")
            self.assertEqual(startup.process_role(["python.exe", own, "serve"], str(root), root), "supervisor")
            self.assertEqual(startup.process_role(["python.exe", "-X", "utf8", "-u", own, "serve"], str(root), root), "supervisor")
            self.assertEqual(startup.process_role(["python.exe", "server_manager.py", "serve"], str(root), root), "supervisor")
            self.assertIsNone(startup.process_role(["python.exe", own, "start"], str(root), root))
            self.assertIsNone(startup.process_role(["python.exe", own + ".other", "serve"], str(root), root))
            self.assertIsNone(startup.process_role(["notepad.exe", own, "serve"], str(root), root))
            self.assertIsNone(startup.process_role(["python.exe", str(root / "other" / "server_manager.py"), "serve"], str(root), root))
            args = ["python.exe", "-m", "uvicorn", "app.main:app", "--port", "8000"]
            self.assertEqual(startup.process_role(args, str(root / "backend"), root), "backend")
            self.assertIsNone(startup.process_role(args, str(root / "other"), root))
            self.assertIsNone(startup.process_role(args[:-1] + ["8001"], str(root / "backend"), root))

    def test_unrelated_port_owner_is_never_stopped(self):
        import psutil
        connection = Mock(status=psutil.CONN_LISTEN, pid=999, laddr=Mock(port=8000))
        with patch.object(startup, "project_processes", return_value=({}, {}, {})), \
                patch.object(psutil, "net_connections", return_value=[connection]):
            with self.assertRaisesRegex(RuntimeError, "boshqa"):
                startup.check_port()

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.db"
            with self.assertRaises(RuntimeError):
                with startup.read_database(missing):
                    self.fail("Missing database unexpectedly opened")
            self.assertFalse(missing.exists())

    def test_active_printing_aborts_without_terminating_processes(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "test.db"
            with contextlib.closing(sqlite3.connect(db)) as conn, conn:
                conn.execute("CREATE TABLE print_jobs(status TEXT)")
                conn.execute("INSERT INTO print_jobs VALUES ('printing')")
            with self.assertRaisesRegex(RuntimeError, "Server to'xtatilmadi"):
                startup.wait_print_idle(db, timeout=0)
            with startup.read_database(db) as conn:
                self.assertEqual(conn.execute("SELECT status FROM print_jobs").fetchone()[0], "printing")
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute("DELETE FROM print_jobs")

    def test_pending_jobs_do_not_get_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "test.db"
            with contextlib.closing(sqlite3.connect(db)) as conn, conn:
                conn.execute("CREATE TABLE print_jobs(status TEXT)")
                conn.execute("INSERT INTO print_jobs VALUES ('pending')")
            startup.wait_print_idle(db, timeout=0)
            with startup.read_database(db) as conn:
                self.assertEqual(conn.execute("SELECT status FROM print_jobs").fetchone()[0], "pending")

    def test_stop_backs_up_and_targets_only_classified_processes(self):
        import psutil
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = root / "test.db"
            with contextlib.closing(sqlite3.connect(db)) as conn, conn:
                conn.execute("CREATE TABLE print_jobs(status TEXT)")
                conn.execute("INSERT INTO print_jobs VALUES ('pending')")
            supervisor, backend, tunnel, unrelated = (Mock() for _ in range(4))
            selected = ({11: supervisor}, {12: backend}, {12: backend, 13: tunnel})
            with patch.object(startup, "database_path", return_value=db), \
                    patch.object(startup, "check_port", return_value=selected), \
                    patch.object(psutil, "wait_procs", return_value=([], [])), \
                    patch.object(psutil, "net_connections", return_value=[]), \
                    contextlib.redirect_stdout(io.StringIO()):
                startup.stop_project(root)
            for proc in (supervisor, backend, tunnel):
                proc.terminate.assert_called_once()
            unrelated.terminate.assert_not_called()
            backups = list((root / "backups" / "autostart").glob("*.db"))
            self.assertEqual(len(backups), 1)
            with contextlib.closing(sqlite3.connect(backups[0])) as conn:
                self.assertEqual(conn.execute("SELECT status FROM print_jobs").fetchone()[0], "pending")

    def test_health_rejects_html_and_database_error(self):
        for body in (b'<!doctype html>', b'{"status":"unhealthy"}'):
            response = io.BytesIO(body)
            response.status = 200
            with patch.object(startup, "urlopen", return_value=response):
                self.assertFalse(startup.health("https://example.test"))
        response = io.BytesIO(b'{"status":"healthy"}')
        response.status = 200
        with patch.object(startup, "urlopen", return_value=response):
            self.assertTrue(startup.health("https://example.test"))

    def test_real_scoped_stop_leaves_unrelated_python_running(self):
        import psutil
        with tempfile.TemporaryDirectory(prefix="RestAron test ! ") as folder:
            root = Path(folder).resolve()
            db = root / "test.db"
            with contextlib.closing(sqlite3.connect(db)) as conn, conn:
                conn.execute("CREATE TABLE print_jobs(status TEXT)")
            manager = root / "server_manager.py"
            pidfile = root / "child.json"
            manager.write_text(
                "import subprocess, sys, time, json\nfrom pathlib import Path\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "Path(__file__).with_name('child.json').write_text(json.dumps({'pid': child.pid}))\n"
                "time.sleep(60)\n", encoding="utf-8")
            own = subprocess.Popen([sys.executable, str(manager), "serve"], cwd=root)
            unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            targets = []
            try:
                deadline = time.monotonic() + 10
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(0.1)
                self.assertTrue(pidfile.exists())
                supervisors, _, descendants = startup.project_processes(root)
                self.assertIn(own.pid, supervisors)
                targets = list(supervisors.values()) + list(descendants.values())
                self.assertTrue(descendants)
                # Isolate the real restaurant's occupied port; never start an HTTP server.
                with patch.object(startup, "database_path", return_value=db), \
                        patch.object(psutil, "net_connections", return_value=[]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    startup.stop_project(root)
                self.assertIsNotNone(own.poll())
                self.assertIsNone(unrelated.poll())
                self.assertFalse(any(proc.is_running() for proc in targets))
            finally:
                for proc in targets:
                    try:
                        if proc.is_running():
                            proc.kill()
                    except psutil.NoSuchProcess:
                        pass
                # The unrelated sentinel has its own venv wrapper/child; close only that tree.
                try:
                    sentinel = psutil.Process(unrelated.pid)
                    sentinels = sentinel.children(recursive=True) + [sentinel]
                    for proc in sentinels:
                        try:
                            proc.kill()
                        except psutil.NoSuchProcess:
                            pass
                    psutil.wait_procs(sentinels, timeout=5)
                except psutil.NoSuchProcess:
                    pass
                if own.poll() is None:
                    own.kill()
                own.wait(timeout=5)
                unrelated.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
