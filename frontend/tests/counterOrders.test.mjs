import test from 'node:test';
import assert from 'node:assert/strict';
import { openCounterOrders } from '../src/utils/counterOrders.js';

test('takeaway and delivery lists stay separate and hide closed, paid and merged accounts', () => {
  const orders = [
    { id: 1, order_type: 'takeaway', status: 'pending' },
    { id: 2, order_type: 'delivery', status: 'ready' },
    ...['paid', 'completed', 'cancelled'].map((status, i) => ({ id: 3 + i, order_type: 'takeaway', status })),
    { id: 6, order_type: 'takeaway', status: 'served', is_paid: true },
    { id: 7, order_type: 'takeaway', status: 'pending', merged_into_order_id: 1 },
    { id: 8, order_type: 'dine_in', status: 'pending' },
  ];
  assert.deepEqual(openCounterOrders(orders, 'takeaway').map(order => order.id), [1]);
  assert.deepEqual(openCounterOrders(orders, 'delivery').map(order => order.id), [2]);
  assert.deepEqual(openCounterOrders(orders, 'table'), []);
  assert.deepEqual(openCounterOrders([], 'delivery'), []);
});
