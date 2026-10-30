import test from 'node:test';
import assert from 'node:assert/strict';
import api from '../src/utils/api.js';

test('a delayed 401 from the previous login cannot log out the newer session', async () => {
  const original = { fetch: globalThis.fetch, localStorage: globalThis.localStorage, sessionStorage: globalThis.sessionStorage, window: globalThis.window };
  let token = 'old-session', finish;
  const events = [];
  globalThis.localStorage = { getItem: () => token, removeItem: () => { token = null; } };
  globalThis.sessionStorage = { getItem: () => '{}' };
  globalThis.window = { dispatchEvent: event => events.push(event.type) };
  globalThis.fetch = () => new Promise(resolve => { finish = resolve; });
  try {
    const result = api.get('/auth/me');
    token = 'new-session';
    finish(new Response(JSON.stringify({ detail: 'Old token expired' }), { status: 401 }));
    await assert.rejects(result, /Old token expired/);
    assert.equal(token, 'new-session'); assert.deepEqual(events, []);
    const current = api.get('/auth/me');
    finish(new Response('{}', { status: 401 }));
    await assert.rejects(current);
    assert.equal(token, null); assert.deepEqual(events, ['restaron:unauthorized']);
  } finally { Object.assign(globalThis, original); }
});
