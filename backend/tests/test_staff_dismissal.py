"""Dismissal preserves accounting, persists revocation and reports a reliable result."""
import asyncio
import pytest
from unittest.mock import AsyncMock
from sqlalchemy import select, func
from httpx import AsyncClient, ASGITransport
from test_audit_regressions import env
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models import User, Order
from app.models.audit_log import AuditLog

pytestmark = pytest.mark.anyio


async def test_dismissal_keeps_paid_and_open_orders_and_revokes_sessions(env, monkeypatch):
    from app.websockets.manager import manager
    notify = AsyncMock(); monkeypatch.setattr(manager, 'send_to_user', notify)
    rid, req, create = env
    paid = await create(); opened = await create(table=rid+1)
    assert (await req('POST', f"/orders/{paid['id']}/checkout", {'print_receipt':False})).status_code == 200
    before = [(await req('GET', f"/orders/{order['id']}")).json() for order in (paid, opened)]
    token = create_access_token({'sub':str(rid+1), 'role':'waiter'})
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        headers = {'Authorization':'Bearer '+token}
        assert (await client.get('/api/v1/auth/me', headers=headers)).status_code == 200
        result = await req('DELETE', f'/users/{rid+1}')
        assert result.status_code == 200, result.text
        assert result.json()['is_active'] is False
        assert (await client.get('/api/v1/auth/me', headers=headers)).status_code == 401
    after = [(await req('GET', f"/orders/{order['id']}")).json() for order in (paid, opened)]
    assert after == before
    async with AsyncSessionLocal() as db:
        staff = await db.get(User, rid+1)
        assert staff and not staff.is_active and staff.tokens_valid_after > 0
        assert await db.scalar(select(func.count(Order.id)).where(Order.waiter_id==staff.id)) == 2
        audit = await db.scalar(select(AuditLog).where(AuditLog.action=='user_deactivated'))
        assert audit is not None and audit.user_id == rid and audit.entity_id == str(staff.id)
    notify.assert_awaited_once_with(rid, rid+1, {'type':'session_revoked','user_id':rid+1})
    assert (await req('PATCH', f'/users/{rid+1}', {'is_active':True})).status_code == 200
    # Reactivation must not resurrect a previously issued token, even after a restart.
    from app.core.security import _user_revocation_timestamps
    _user_revocation_timestamps.pop(rid+1, None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/api/v1/auth/me', headers={'Authorization':'Bearer '+token})).status_code == 401


@pytest.mark.parametrize('method', ['DELETE','PATCH'])
async def test_failed_audit_does_not_partially_dismiss_or_revoke_employee(env, monkeypatch, method):
    from importlib import import_module
    users = import_module('app.routers.users')
    rid, req, create = env
    token = create_access_token({'sub':str(rid+1), 'role':'waiter'})
    monkeypatch.setattr(users, 'log_audit_event', AsyncMock(return_value=None))
    result = await req(method, f'/users/{rid+1}', {'is_active':False} if method=='PATCH' else None)
    assert result.status_code == 503, result.text
    async with AsyncSessionLocal() as db:
        staff = await db.get(User, rid+1)
        assert staff.is_active and staff.tokens_valid_after == 0
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/api/v1/auth/me', headers={'Authorization':'Bearer '+token})).status_code == 200


async def test_repeated_parallel_dismissal_has_one_audit_event(env):
    rid, req, create = env
    results = await asyncio.gather(*(req('DELETE', f'/users/{rid+1}') for _ in range(5)))
    assert all(result.status_code == 200 for result in results)
    assert sum(bool(result.json().get('already_inactive')) for result in results) == 4
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='user_deactivated')) == 1


async def test_notification_failure_does_not_report_saved_dismissal_as_failed(env, monkeypatch):
    from app.websockets.manager import manager
    monkeypatch.setattr(manager, 'send_to_user', AsyncMock(side_effect=RuntimeError('test socket unavailable')))
    rid, req, create = env
    result = await req('DELETE', f'/users/{rid+1}')
    assert result.status_code == 200
    async with AsyncSessionLocal() as db:
        assert (await db.get(User, rid+1)).is_active is False
