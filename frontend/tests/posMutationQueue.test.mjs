import test from 'node:test';
import assert from 'node:assert/strict';
import { createPosMutationQueue, projectPosOrder } from '../src/utils/posMutationQueue.js';

const menu = { id: 1, name: 'Non', price: 5000 };
const base = { id: 1, service_fee_percent: 12, items: [{ id: 10, menu_item_id: 1, quantity: 1, unit_price: 5000, total_price: 5000 }] };
const add = () => ({ kind: 'add', menu, quantity: 1 });
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };

test('rapid taps are projected immediately, coalesced and retain exact final count', async () => {
  const gate = deferred(), calls = [], views = [];
  const q = createPosMutationQueue({ onChange: (_, order) => views.push(order), execute: async (intent, order) => {
    calls.push(intent.quantity); await gate.promise; return projectPosOrder(order, [intent]);
  } });
  let idle;
  idle = q.enqueue('t:1', base, add(), 'first'); await tick();
  for (let i = 0; i < 20; i++) idle = q.enqueue('t:1', base, add(), `k${i}`);
  assert.equal(views.at(-1).items[0].quantity, 22);
  assert.equal(views.at(-1).total, 123200);
  gate.resolve(); await idle;
  assert.deepEqual(calls, [1, 20]);
  assert.equal(views.at(-1).items[0].quantity, 22);
  // First acknowledgement still has the remaining twenty taps projected.
  assert.equal(views.at(-2).items[0].quantity, 22);
  assert.equal(base.items[0].quantity, 1);
});

test('unknown create result pauses later taps; retry keeps the same key and creates only once', async () => {
  const keys = [], errors = [], views = []; let failed = false, created = 0;
  const cached = new Map();
  const q = createPosMutationQueue({ onChange: (_, order) => views.push(order), onError: error => errors.push(error),
    execute: async (intent, order, key) => {
      keys.push(key);
      if (cached.has(key)) return cached.get(key);
      if (!order) { created++; order = { ...base, items: [] }; }
      const result = projectPosOrder(order, [intent]); cached.set(key, result);
      if (!failed) { failed = true; throw new Error('response lost after commit'); }
      return result;
    } });
  const idle = q.enqueue('t:1', null, add(), 'create-key'); await tick();
  q.enqueue('t:1', null, add(), 'next-key'); await tick();
  assert.equal(keys.length, 1); assert.equal(errors.length, 1); assert.ok(q.error);
  q.retry(); await idle;
  assert.equal(created, 1);
  assert.deepEqual(keys, ['create-key', 'create-key', 'next-key']);
  assert.equal(views.at(-1).items[0].quantity, 2);
});

test('switching tables cannot apply a queued response to another table', async () => {
  const views = [];
  const q = createPosMutationQueue({ onChange: (scope, order) => views.push([scope, order]), execute: async (intent, order) => projectPosOrder(order, [intent]) });
  q.enqueue('a', base, add(), 'a');
  await q.enqueue('b', { ...base, id: 2 }, add(), 'b');
  assert.equal(views.filter(([scope]) => scope === 'a').at(-1)[1].id, 1);
  assert.equal(views.filter(([scope]) => scope === 'b').at(-1)[1].id, 2);
});

test('batches respect API limits and do not merge across a reversal or weighted additions', async () => {
  const calls = [];
  const q = createPosMutationQueue({ onChange() {}, execute: async (intent, order) => { calls.push(intent); return projectPosOrder(order, [intent]); } });
  for (let i = 0; i < 120; i++) q.enqueue('a', base, add(), `k${i}`);
  q.enqueue('a', base, { kind: 'delta', itemId: 10, delta: -1 }, 'minus');
  q.enqueue('a', base, { kind: 'delta', itemId: 10, delta: 1 }, 'plus');
  q.enqueue('a', base, { ...add(), menu: { ...menu, is_weighted: true } }, 'w1');
  await q.enqueue('a', base, { ...add(), menu: { ...menu, is_weighted: true } }, 'w2');
  assert.deepEqual(calls.slice(0, 3).map(i => i.quantity), [50, 50, 20]);
  assert.equal(calls.length, 7);
});

test('weighted preview preserves a manually entered amount when quantity changes', () => {
  const order = { ...base, items: [{ id: 10, is_weighted: true, quantity: 1, unit_price: 120000, manual_price: 180000, total_price: 180000, weight: 1.5 }] };
  const result = projectPosOrder(order, [{ kind: 'delta', itemId: 10, delta: 1 }]);
  assert.equal(result.items[0].quantity, 2);
  assert.equal(result.items[0].total_price, 180000);
});

test('discarding unexecuted intentions releases waiters without sending later jobs', async () => {
  let calls = 0;
  const q = createPosMutationQueue({ onChange() {}, execute: async () => { calls++; throw new Error('offline'); } });
  const idle = q.enqueue('a', base, add(), 'a'); await tick();
  q.enqueue('a', base, add(), 'b'); q.discard(); await idle;
  assert.equal(calls, 1); assert.equal(q.pending, 0); assert.equal(q.error, null);
});
