import test from 'node:test';
import assert from 'node:assert/strict';
import { canDeleteOrderItem, canDecreaseOrderItem, kitchenSentQuantity } from '../src/utils/kitchenPermissions.js';

test('waiter and cashier cannot remove sent items; administrator can', () => {
  const item = { quantity: 2, sent_quantity: 2, sent_to_kitchen: true };
  for (const role of ['waiter', 'cashier']) {
    assert.equal(canDeleteOrderItem({ role }, item), false);
    assert.equal(canDecreaseOrderItem({ role }, item), false);
  }
  assert.equal(canDeleteOrderItem({ role: 'admin' }, item), true);
  assert.equal(canDecreaseOrderItem({ role: 'admin' }, item), true);
});

test('unsent additions can be reduced while the sent quantity remains protected', () => {
  const user = { role: 'waiter' };
  assert.equal(canDecreaseOrderItem(user, { quantity: 3, sent_quantity: 2 }), true);
  assert.equal(canDeleteOrderItem(user, { quantity: 3, sent_quantity: 2 }), false);
  assert.equal(canDeleteOrderItem(user, { quantity: 1, sent_quantity: 0 }), true);
});

test('legacy flags, timestamps and prepared counters also protect a kitchen item', () => {
  assert.equal(kitchenSentQuantity({ quantity: 2, sent_to_kitchen: true }), 2);
  assert.equal(kitchenSentQuantity({ quantity: 2, sent_to_kitchen_at: '2026-10-24' }), 2);
  assert.equal(kitchenSentQuantity({ quantity: 3, prepared_quantity: 2 }), 2);
});
