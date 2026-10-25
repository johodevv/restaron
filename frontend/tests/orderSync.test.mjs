import test from 'node:test';
import assert from 'node:assert/strict';
import { latestOrder } from '../src/utils/orderSync.js';

test('a remote delta updates an existing cart', () => {
  const old = { id: 1, version: 2, total: 22000 };
  const fresh = { id: 1, version: 3, total: 33000 };
  assert.equal(latestOrder(old, fresh), fresh);
});
test('a delayed version cannot roll the cart back', () => {
  const fresh = { id: 1, version: 4, total: 44000 };
  assert.equal(latestOrder(fresh, { id: 1, version: 3, total: 33000 }), fresh);
});
test('an unrelated order cannot replace the selected order', () => {
  const selected = { id: 1, version: 3 };
  assert.equal(latestOrder(selected, { id: 2, version: 100 }), selected);
  assert.equal(latestOrder(null, selected), selected);
});
