from pathlib import Path
from types import SimpleNamespace
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import frontend_build as build


@pytest.fixture
def project(tmp_path):
    frontend = tmp_path / 'frontend'
    (frontend / 'src').mkdir(parents=True)
    (frontend / 'src/main.jsx').write_text('new source')
    (frontend / 'dist/assets').mkdir(parents=True)
    (frontend / 'dist/index.html').write_text('<script src="/assets/old.js"></script>')
    (frontend / 'dist/assets/old.js').write_text('old bundle')
    staging = tmp_path / 'staged'
    (staging / 'assets').mkdir(parents=True)
    (staging / 'index.html').write_text('<script src="/assets/new.js"></script>')
    (staging / 'assets/new.js').write_text('new bundle')
    return tmp_path, frontend, staging


def test_unverified_legacy_build_is_not_current(project):
    _, frontend, _ = project
    assert not build.build_is_current(frontend)


def test_publish_keeps_old_assets_and_backup(project):
    root, frontend, staging = project
    backup = build.publish_build(root, staging, build.source_fingerprint(frontend))
    assert build.build_is_current(frontend)
    assert (frontend / 'dist/assets/old.js').read_text() == 'old bundle'
    assert (frontend / 'dist/assets/new.js').read_text() == 'new bundle'
    assert '/assets/old.js' in (backup / 'index.html').read_text()
    assert '/assets/new.js' in (frontend / 'dist/index.html').read_text()


def test_incomplete_build_cannot_replace_working_build(project):
    root, frontend, staging = project
    (staging / 'assets/new.js').unlink()
    with pytest.raises(ValueError, match='yetishmayapti'):
        build.publish_build(root, staging, build.source_fingerprint(frontend))
    assert '/assets/old.js' in (frontend / 'dist/index.html').read_text()


def test_source_change_marks_published_build_stale(project):
    root, frontend, staging = project
    build.publish_build(root, staging, build.source_fingerprint(frontend))
    (frontend / 'src/main.jsx').write_text('changed source')
    assert not build.build_is_current(frontend)


def test_failed_npm_build_preserves_previous_files(project, monkeypatch):
    root, frontend, _ = project
    (frontend / 'node_modules').mkdir()
    monkeypatch.setattr(build.shutil, 'which', lambda command: 'npm')
    monkeypatch.setattr(build.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout='', stderr='test compiler failure'))
    with pytest.raises(RuntimeError, match='oldingi build saqlandi'):
        build.ensure_frontend_build(root, lambda message: None)
    assert '/assets/old.js' in (frontend / 'dist/index.html').read_text()


def test_current_build_does_not_rebuild_on_each_start(project, monkeypatch):
    root, frontend, staging = project
    build.publish_build(root, staging, build.source_fingerprint(frontend))
    def unexpected(*args, **kwargs):
        raise AssertionError('A matching build must not launch npm')
    monkeypatch.setattr(build.subprocess, 'run', unexpected)
    build.ensure_frontend_build(root, lambda message: None)


def test_stale_build_is_built_in_staging_before_publication(project, monkeypatch):
    root, frontend, _ = project
    (frontend / 'node_modules').mkdir()
    monkeypatch.setattr(build.shutil, 'which', lambda command: 'npm')
    def compiler(command, **kwargs):
        staging = Path(command[-1])
        assert staging.parent == root / 'scratch'
        assert '/assets/old.js' in (frontend / 'dist/index.html').read_text()
        (staging / 'assets').mkdir()
        (staging / 'assets/built.js').write_text('compiled')
        (staging / 'index.html').write_text('<script src="/assets/built.js"></script>')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(build.subprocess, 'run', compiler)
    build.ensure_frontend_build(root, lambda message: None)
    assert build.build_is_current(frontend)
    assert '/assets/built.js' in (frontend / 'dist/index.html').read_text()
