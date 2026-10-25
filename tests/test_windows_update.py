"""Updater regression tests use disposable repositories/databases, never the live app."""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import windows_update as update


class RepositoryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='RestAron update ! ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.remote = self.base / 'remote'
        self.remote.mkdir()
        self.command(self.remote, 'init', '-b', 'main')
        self.command(self.remote, 'config', 'user.email', 'fixture@example.invalid')
        self.command(self.remote, 'config', 'user.name', 'Fixture')
        files = {
            '.gitignore': 'backups/\nscratch/\n*.db\n.env\nbackend/.env\nbackend/.venv/\nbackend/uploads/\nfrontend/dist/\ntunnel_sozlama.txt\n',
            'backend/app/main.py': '# OLD APP\n',
            'backend/requirements.txt': '# old requirements\n',
            'frontend/package.json': '{}\n',
            'frontend/package-lock.json': '{}\n',
            'frontend/src/main.jsx': 'old source\n',
            'server_manager.py': '# old supervisor\n',
            'frontend_build.py': (ROOT / 'frontend_build.py').read_text(encoding='utf-8'),
            'deleted.py': '# old tracked file\n',
            'cloudflared.exe': 'KEEP LOCAL TUNNEL BINARY',
        }
        for name, content in files.items():
            self.write(self.remote, name, content)
        self.command(self.remote, 'add', '.')
        self.command(self.remote, 'commit', '-qm', 'initial')
        self.root = self.base / 'checkout'
        self.command(self.base, 'clone', '-q', str(self.remote), str(self.root))
        self.old_head = self.command(self.root, 'rev-parse', 'HEAD')
        self.write(self.root, 'backend/.env', 'SECRET_KEY=LOCAL_SECRET_DO_NOT_REPLACE\n')
        self.write(self.root, 'tunnel_sozlama.txt', 'TOKEN=LOCAL_TUNNEL\n')
        self.write(self.root, 'backend/uploads/qr.png', 'LOCAL_QR')
        self.write(self.root, 'backend/.venv/runtime.txt', 'OLD VENV')
        self.write(self.root, 'backend/.venv_eski/runtime.txt', 'OLDER VENV')
        self.write(self.root, 'frontend/dist/index.html', '<script src="/assets/old.js"></script>')
        self.write(self.root, 'frontend/dist/assets/old.js', 'OLD ASSET')
        self.db = self.root / 'backend/restaron.db'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY, total INTEGER)')
            conn.execute('INSERT INTO orders VALUES (1, 1000)')
            conn.execute('CREATE TABLE print_jobs(status TEXT)')
            conn.execute("INSERT INTO print_jobs VALUES ('pending')")
        # Simulate the zip copy, including staged and untracked edits.
        self.write(self.root, 'backend/app/main.py', '# LOCAL EDIT\n')
        self.write(self.root, 'frontend/src/main.jsx', 'STAGED LOCAL EDIT\n')
        self.command(self.root, 'add', 'frontend/src/main.jsx')
        self.write(self.root, 'backend/app/local_extra.py', '# untracked local code\n')
        self.index_before = (self.root / '.git/index').read_bytes()
        # New upstream version also deliberately includes data that must be skipped.
        self.write(self.remote, 'backend/app/main.py', '# NEW REMOTE APP\n')
        self.write(self.remote, 'frontend/src/main.jsx', 'new source\n')
        self.write(self.remote, 'backend/app/added.py', '# new module\n')
        (self.remote / 'deleted.py').unlink()
        self.write(self.remote, 'backend/.env', 'SECRET_KEY=REMOTE_BAD_SECRET\n')
        self.write(self.remote, 'backend/restaron.db', 'REMOTE_BAD_DATABASE')
        self.write(self.remote, 'tunnel_sozlama.txt', 'TOKEN=REMOTE_BAD_TOKEN')
        self.write(self.remote, 'backend/uploads/qr.png', 'REMOTE_BAD_QR')
        self.write(self.remote, 'cloudflared.exe', 'REMOTE TUNNEL BINARY')
        self.command(self.remote, 'add', '-f', 'backend/.env', 'backend/restaron.db', 'tunnel_sozlama.txt', 'backend/uploads/qr.png')
        self.command(self.remote, 'add', '-A')
        self.command(self.remote, 'commit', '-qm', 'new upstream')
        self.command(self.root, 'fetch', '-q', 'origin')
        self.target = self.command(self.root, 'rev-parse', 'origin/main')
        self.stage = self.base / 'stage'
        self.names = update.extract_code(self.root, self.target, self.stage)
        self.write(self.stage, 'frontend/dist/index.html', '<script src="/assets/new.js"></script>')
        self.write(self.stage, 'frontend/dist/assets/new.js', 'NEW ASSET')
        sys.path.insert(0, str(ROOT))
        import frontend_build
        self.write(self.stage, 'frontend/dist/restaron-build.json',
                   json.dumps({'source_sha256': frontend_build.source_fingerprint(self.stage / 'frontend')}))
        self.backup = self.root / 'backups/updates/test'
        self.backup.mkdir(parents=True)

    @staticmethod
    def command(root, *args):
        result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, encoding='utf-8')
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout.strip()

    @staticmethod
    def write(root, relative, text):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def assert_data_preserved(self):
        self.assertEqual((self.root / 'backend/.env').read_text(), 'SECRET_KEY=LOCAL_SECRET_DO_NOT_REPLACE\n')
        self.assertEqual((self.root / 'tunnel_sozlama.txt').read_text(), 'TOKEN=LOCAL_TUNNEL\n')
        self.assertEqual((self.root / 'backend/uploads/qr.png').read_text(), 'LOCAL_QR')
        self.assertEqual((self.root / 'cloudflared.exe').read_text(), 'KEEP LOCAL TUNNEL BINARY')
        self.assertEqual((self.root / 'backend/.venv_eski/runtime.txt').read_text(), 'OLDER VENV')
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute('SELECT total FROM orders WHERE id=1').fetchone()[0], 1000)
            self.assertEqual(conn.execute('SELECT status FROM print_jobs').fetchone()[0], 'pending')

    def test_dirty_staged_untracked_code_is_replaced_and_backed_up(self):
        record = update.snapshot_code(self.root, self.backup, self.names)
        update.publish_code(self.root, self.stage, self.target, record)
        self.assertEqual((self.root / 'backend/app/main.py').read_text(), '# NEW REMOTE APP\n')
        self.assertEqual((self.root / 'frontend/src/main.jsx').read_text(), 'new source\n')
        self.assertFalse((self.root / 'deleted.py').exists())
        self.assertFalse((self.root / 'backend/app/local_extra.py').exists())
        self.assertEqual((self.backup / 'code/backend/app/main.py').read_text(), '# LOCAL EDIT\n')
        self.assertEqual((self.backup / 'code/frontend/src/main.jsx').read_text(), 'STAGED LOCAL EDIT\n')
        self.assertEqual(self.command(self.root, 'rev-parse', 'HEAD'), self.target)
        self.assert_data_preserved()

    def test_rollback_restores_dirty_code_index_and_deleted_files(self):
        record = update.snapshot_code(self.root, self.backup, self.names)
        update.publish_code(self.root, self.stage, self.target, record)
        update.rollback_code(self.root, self.backup, record)
        self.assertEqual((self.root / 'backend/app/main.py').read_text(), '# LOCAL EDIT\n')
        self.assertEqual((self.root / 'frontend/src/main.jsx').read_text(), 'STAGED LOCAL EDIT\n')
        self.assertTrue((self.root / 'deleted.py').is_file())
        self.assertTrue((self.root / 'backend/app/local_extra.py').is_file())
        self.assertFalse((self.root / 'backend/app/added.py').exists())
        self.assertEqual((self.root / '.git/index').read_bytes(), self.index_before)
        self.assertEqual(self.command(self.root, 'rev-parse', 'HEAD'), self.old_head)
        self.assert_data_preserved()

    def test_locally_deleted_tracked_file_stays_deleted_after_rollback(self):
        (self.root / 'deleted.py').unlink()
        self.command(self.root, 'add', 'deleted.py')
        record = update.snapshot_code(self.root, self.backup, self.names)
        update.publish_code(self.root, self.stage, self.target, record)
        update.rollback_code(self.root, self.backup, record)
        self.assertFalse((self.root / 'deleted.py').exists())

    def test_branch_is_configured_upstream_not_assumed_main(self):
        self.command(self.root, 'branch', '-m', 'production-local')
        branch, remote, merge, reference = update.upstream(self.root)
        self.assertEqual((branch, remote, merge, reference),
                         ('production-local', 'origin', 'refs/heads/main', 'refs/remotes/origin/main'))

    def test_symlink_and_directory_collision_abort_before_writing(self):
        collision = self.root / 'backend/app/added.py'
        collision.mkdir()
        (collision / 'customer.db').write_bytes(b'KEEP')
        with self.assertRaisesRegex(update.UpdateError, 'papka'):
            update.snapshot_code(self.root, self.backup, self.names)
        self.assertEqual((collision / 'customer.db').read_bytes(), b'KEEP')
        self.assertEqual(self.command(self.root, 'rev-parse', 'HEAD'), self.old_head)

    def test_late_deploy_helpers_are_kept_when_not_yet_in_upstream(self):
        self.write(self.root, 'tools/windows_update.py', '# local updater')
        record = update.snapshot_code(self.root, self.backup, self.names)
        update.publish_code(self.root, self.stage, self.target, record)
        self.assertEqual((self.root / 'tools/windows_update.py').read_text(), '# local updater')

    def test_old_remote_bat_cannot_downgrade_new_updater(self):
        self.write(self.root, 'RESTARON_YANGILASH.bat', '# new safe updater')
        self.write(self.remote, 'RESTARON_YANGILASH.bat', '# old unsafe updater')
        self.command(self.remote, 'add', '.')
        self.command(self.remote, 'commit', '-qm', 'old updater in remote')
        self.command(self.root, 'fetch', '-q', 'origin')
        target = self.command(self.root, 'rev-parse', 'origin/main')
        names = update.extract_code(self.root, target, self.base / 'second-stage')
        self.assertNotIn('RESTARON_YANGILASH.bat', names)
        record = update.snapshot_code(self.root, self.backup, names)
        update.publish_code(self.root, self.base / 'second-stage', target, record)
        self.assertEqual((self.root / 'RESTARON_YANGILASH.bat').read_text(), '# new safe updater')

    def updater(self):
        instance = update.Updater(self.root, self.root / 'backend/.venv/Scripts/python.exe')
        instance.backup, instance.work = self.backup, self.root / 'scratch/update-work'
        instance.work.mkdir(parents=True)
        instance.log = instance.backup / 'update.log'
        instance.database = self.db
        instance.domain = 'https://example.invalid'
        instance.frozen_runner = instance.work / 'runner.py'
        instance.frozen_helper = instance.work / 'helper.py'
        (instance.work / 'wheels').mkdir()
        (instance.work / 'resolved-requirements.txt').write_text('')
        return instance

    def exercise_apply(self, failure=None):
        instance = self.updater()
        events = []
        real_run = update.run

        class FakeTask:
            def inspect(task): return {'State': 4, 'Enabled': True}
            def disable(task): events.append('disable')
            def start(task):
                events.append('start')
                # A real customer write after new startup must survive rollback.
                if failure == 'health' and events.count('start') == 1:
                    with closing(sqlite3.connect(self.db)) as conn, conn:
                        conn.execute('INSERT INTO orders VALUES (2, 2000)')

        def child(action, python=None):
            events.append('stop')
            if failure == 'printing' and events.count('stop') == 1:
                raise update.UpdateError('Printer hali ishlayapti')
            return ''

        def run(command, cwd, **kwargs):
            if str(command[0]) == str(instance.python):
                (self.root / 'backend/.venv/runtime.txt').write_text('NEW VENV')
                if failure == 'pip':
                    raise update.UpdateError('Simulated install failure')
                return ''
            return real_run(command, cwd, **kwargs)

        instance.child = child
        with patch.object(update, 'run', side_effect=run), \
                patch.object(update, 'wait_health', side_effect=[False, True] if failure == 'health' else [True]):
            if failure:
                with self.assertRaises(update.UpdateError):
                    instance.apply(self.stage, self.target, self.names, self.base / 'recovery-python', FakeTask(), [])
            else:
                instance.apply(self.stage, self.target, self.names, self.base / 'recovery-python', FakeTask(), [])
        self.assert_data_preserved()
        return instance, events

    def test_success_restarts_task_preserves_old_assets_and_db(self):
        _, events = self.exercise_apply()
        self.assertEqual(events, ['disable', 'stop', 'start'])
        self.assertTrue((self.root / 'frontend/dist/assets/old.js').exists())
        self.assertTrue((self.root / 'frontend/dist/assets/new.js').exists())
        self.assertEqual((self.root / 'backend/.venv/runtime.txt').read_text(), 'NEW VENV')
        self.assertTrue((self.backup / 'database-before.db').is_file())

    def test_dependency_failure_restores_old_env_and_code(self):
        _, events = self.exercise_apply('pip')
        self.assertEqual((self.root / 'backend/.venv/runtime.txt').read_text(), 'OLD VENV')
        self.assertEqual((self.root / 'backend/app/main.py').read_text(), '# LOCAL EDIT\n')
        self.assertEqual(events[-1], 'start')

    def test_health_failure_rollback_does_not_discard_new_sales(self):
        self.exercise_apply('health')
        self.assertEqual((self.root / 'backend/.venv/runtime.txt').read_text(), 'OLD VENV')
        self.assertIn('old.js', (self.root / 'frontend/dist/index.html').read_text())
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute('SELECT total FROM orders WHERE id=2').fetchone()[0], 2000)

    def test_busy_printer_aborts_before_changing_code_and_recovers_task(self):
        _, events = self.exercise_apply('printing')
        self.assertEqual((self.root / 'backend/app/main.py').read_text(), '# LOCAL EDIT\n')
        self.assertEqual(self.command(self.root, 'rev-parse', 'HEAD'), self.old_head)
        self.assertEqual((self.root / 'backend/.venv/runtime.txt').read_text(), 'OLD VENV')
        self.assertEqual(events, ['disable', 'stop', 'disable', 'start'])

    def test_build_or_download_failure_never_stops_running_server(self):
        self.write(self.root, 'tools/windows_autostart.py', '# helper fixture')
        instance = update.Updater(self.root, self.root / 'backend/.venv/Scripts/python.exe')
        calls = []
        class FakeTask:
            def __init__(task, *args): pass
            def inspect(task): return {'State': 4}
            def disable(task): self.fail('Service must remain enabled')
            def start(task): self.fail('No restart was needed')
        instance.task_factory = FakeTask
        instance.check = lambda: ('main', 'origin', 'refs/heads/main', 'refs/remotes/origin/main')
        def child(action, python=None):
            calls.append(action)
            self.assertEqual(action, 'info')
            return json.dumps({'database': str(self.db), 'domain': 'https://example.invalid', 'extra': []})
        instance.child = child
        with patch.object(instance, 'stage', side_effect=update.UpdateError('simulated build failure')):
            with self.assertRaisesRegex(update.UpdateError, 'simulated build failure'):
                instance.execute()
        self.assertEqual(calls, ['info'])
        self.assertEqual((self.root / 'backend/app/main.py').read_text(), '# LOCAL EDIT\n')
        self.assertEqual(self.command(self.root, 'rev-parse', 'HEAD'), self.old_head)
        self.assert_data_preserved()


class GuardTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows CIM serialization')
    def test_task_inspection_serializes_real_cim_action_properties(self):
        import base64
        with tempfile.TemporaryDirectory(prefix='RestAron task ! ') as folder:
            root = Path(folder)
            task = update.WindowsTask(root, root / 'backend/.venv/Scripts/python.exe', None)
            def fake_run(command, cwd, **kwargs):
                body = base64.b64decode(command[-1]).decode('utf-16-le')
                prefix = f'''
Import-Module ScheduledTasks
$ProgressPreference='SilentlyContinue'
$a=New-ScheduledTaskAction -Execute {task.quote(task.python)} -Argument {task.quote(f'-X utf8 -u "{root / "server_manager.py"}" serve')}
$script:definition=New-ScheduledTask -Action $a -Settings (New-ScheduledTaskSettingsSet)
function global:Get-ScheduledTask {{ param($TaskName,$TaskPath,$ErrorAction) $script:definition }}
'''
                encoded = base64.b64encode((prefix + body).encode('utf-16-le')).decode()
                result = subprocess.run(command[:-1] + [encoded], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout.strip()
            with patch.object(update, 'run', side_effect=fake_run):
                result = task.inspect()
            self.assertEqual(result['Actions'][0]['Execute'], str(task.python))
            self.assertIn('server_manager.py', result['Actions'][0]['Arguments'])

    @unittest.skipUnless(os.name == 'nt', 'Windows Task Scheduler definition')
    def test_task_definition_uses_system_boot_and_no_time_limit_without_registering(self):
        import base64
        with tempfile.TemporaryDirectory(prefix='RestAron task ! ') as folder:
            root = Path(folder)
            task = update.WindowsTask(root, root / 'backend/.venv/Scripts/python.exe', None)
            output = []
            def fake_run(command, cwd, **kwargs):
                body = base64.b64decode(command[-1]).decode('utf-16-le')
                prefix = '''
Import-Module ScheduledTasks
$ProgressPreference = 'SilentlyContinue'
function global:Register-ScheduledTask { param($TaskName,$TaskPath,$InputObject,[switch]$Force) $script:definition=$InputObject }
function global:Start-ScheduledTask { param($TaskName,$TaskPath) }
if ((Get-Command Register-ScheduledTask).CommandType -ne 'Function') { throw 'Mock was not installed' }
'''
                suffix = '''
$d=$script:definition
@{user=$d.Principal.UserId;logon=$d.Principal.LogonType;time=$d.Settings.ExecutionTimeLimit;
instances=$d.Settings.MultipleInstances;restarts=$d.Settings.RestartCount;
delay=$d.Triggers[0].Delay;working=$d.Actions[0].WorkingDirectory} | ConvertTo-Json -Compress
'''
                encoded = base64.b64encode((prefix + body + suffix).encode('utf-16-le')).decode()
                result = subprocess.run(command[:-1] + [encoded], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                output.append(json.loads(result.stdout))
                return ''
            with patch.object(update, 'run', side_effect=fake_run):
                task.start()
            definition = output[0]
            self.assertIn(definition['user'], ('SYSTEM', 'S-1-5-18'))
            self.assertEqual(definition['logon'], 5)
            self.assertEqual(definition['time'], 'PT0S')
            self.assertEqual(definition['instances'], 2)
            self.assertEqual(definition['restarts'], 999)
            self.assertEqual(definition['delay'], 'PT30S')
            self.assertEqual(definition['working'], str(root))

    def test_other_projects_task_cannot_be_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            task = update.WindowsTask(root, root / 'backend/.venv/Scripts/python.exe', None)
            for action in ({'Execute': 'C:\\other\\python.exe', 'Arguments': f'"{root / "server_manager.py"}" serve'},
                           {'Execute': str(task.python), 'Arguments': f'"{root / "server_manager.py"}-other" serve'}):
                with patch.object(task, 'ps', return_value=json.dumps({'Actions': [action]})):
                    with self.assertRaises(update.UpdateError):
                        task.inspect()

    def test_all_data_and_renamed_venvs_are_protected(self):
        for name in ('backend/restaron.db', 'backend/restaron.db-wal', 'backend/.env',
                     'frontend/.env.production', 'backend/.venv/Scripts/python.exe',
                     'backend/.venv_eski2/Lib/data.py', 'backend/uploads/qr.png',
                     'backend/receipts_archive/a.pdf', 'backups/any.py', 'scratch/any.py',
                     'cloudflared.exe', 'tunnel_sozlama.txt', '.git/config', '../outside'):
            self.assertTrue(update.protected(name), name)
        self.assertTrue(update.protected('custom_images/qr.png', ['custom_images']))
        self.assertTrue(update.protected('custom_images', ['custom_images/qr.png']))
        self.assertFalse(update.protected('backend/app/main.py'))
        self.assertFalse(update.protected('frontend/public/logo.png'))

    def test_escape_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in ('../outside', '/absolute', 'C:/absolute', 'folder/../escape', 'bad./x', 'bad /x'):
                with self.assertRaises((update.UpdateError, ValueError)):
                    update.inside(Path(folder), path)

    def test_logs_redact_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            log = root / 'log.txt'
            update.run([sys.executable, '-c', 'print("https://PRIVATE_USER:PRIVATE_PASSWORD@example.invalid https://PRIVATE_PAT@example.invalid token=PRIVATE_TOKEN")'], root, log=log)
            text = log.read_text()
            for secret in ('PRIVATE_USER', 'PRIVATE_PASSWORD', 'PRIVATE_PAT', 'PRIVATE_TOKEN'):
                self.assertNotIn(secret, text)

    def test_update_lock_excludes_second_instance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with update.update_lock(root):
                with self.assertRaises(update.UpdateError):
                    with update.update_lock(root):
                        self.fail('Second updater entered')
            with update.update_lock(root):
                pass

    def test_sqlite_backup_is_integral(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, backup = root / 'source.db', root / 'backup.db'
            with closing(sqlite3.connect(source)) as conn, conn:
                conn.execute('CREATE TABLE sales(total INTEGER)')
                conn.execute('INSERT INTO sales VALUES(1000)')
            update.backup_sqlite(source, backup)
            with closing(sqlite3.connect(backup)) as conn:
                self.assertEqual(conn.execute('SELECT total FROM sales').fetchone()[0], 1000)


if __name__ == '__main__':
    unittest.main()
