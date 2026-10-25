import test from 'node:test';
import assert from 'node:assert/strict';
import { tableDirectory, normalizeQrBaseUrl, qrAddressKind, resolveQrBaseUrl } from '../src/utils/tableDirectory.js';

const tables = [
  { id: 1, number: 2, room: 'Zal', status: 'occupied', is_active: true },
  { id: 2, number: 12, room: 'Terrassa', status: 'available', is_active: true },
  { id: 3, number: 2, room: 'Terrassa', status: 'reserved', is_active: true },
  { id: 4, number: 61, room: null, status: 'maintenance', is_active: true },
  { id: 5, number: 3, room: 'Zal', status: 'available', is_active: false },
];

test('number search prioritises exact matches and keeps same-number tables in different rooms', () => {
  const result = tableDirectory(tables, [], { query: '#2' });
  assert.deepEqual(result.matches.map(table => table.id), [1, 3, 2]);
  assert.deepEqual(result.groups.map(group => group.label), ['Zal', 'Terrassa']);
});
test('combined room, number and status filters count only the current search', () => {
  const result = tableDirectory(tables, [], { query: '2', zone: 'Terrassa', status: 'reserved' });
  assert.deepEqual(result.matches.map(table => table.id), [3]);
  assert.equal(result.counts.all, 2);
  assert.equal(result.counts.available, 1);
  assert.equal(result.counts.reserved, 1);
});
test('unregistered room names remain separate; no-zone and maintenance are not labelled available', () => {
  const result = tableDirectory(tables, [{ name: 'Zal' }], {});
  assert.deepEqual(result.groups.map(group => group.label), ['Zal', 'Terrassa', 'Zonasiz']);
  assert.equal(result.counts.maintenance, 1);
  assert.equal(result.active.length, 4);
  assert.deepEqual(tableDirectory(tables, [], { zone: '__nozone__' }).matches.map(table => table.id), [4]);
});
test('a persisted public QR domain survives transient server IP changes', () => {
  assert.equal(resolveQrBaseUrl('https://qr.example.test', { public_url: 'http://10.0.0.7:8000' }, 'http://localhost:8000'), 'https://qr.example.test');
  assert.equal(resolveQrBaseUrl('http://127.0.0.1:8000', { public_url: 'https://qr.example.test' }, 'http://localhost:8000'), 'https://qr.example.test');
});
test('QR address classification distinguishes LAN, loopback and temporary tunnels', () => {
  assert.equal(qrAddressKind('http://127.0.0.1:8000'), 'loopback');
  assert.equal(qrAddressKind('http://10.27.63.36:8000'), 'local');
  assert.equal(qrAddressKind('http://172.31.2.3:8000'), 'local');
  assert.equal(qrAddressKind('https://demo.trycloudflare.com'), 'temporary');
  assert.equal(qrAddressKind('https://qr.example.test'), 'public');
  assert.equal(qrAddressKind('javascript:alert(1)'), 'invalid');
});
test('QR addresses reject scripts, credentials, queries and fragments', () => {
  assert.equal(normalizeQrBaseUrl(' https://qr.example.test/ '), 'https://qr.example.test');
  for (const value of ['javascript:alert(1)', 'https://user:password@qr.example.test', 'https://qr.example.test/?table=wrong', 'https://qr.example.test/#test']) assert.throws(() => normalizeQrBaseUrl(value));
});
