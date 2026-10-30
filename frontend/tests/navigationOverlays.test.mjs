import test from 'node:test';
import assert from 'node:assert/strict';
import { createNavigationOverlays } from '../src/utils/navigationOverlays.js';
test('external dialogs can be closed and reopened by Back and Forward', () => {
  const store = createNavigationOverlays();
  const calls = [];
  store.update('theme',true,open=>calls.push(open));
  store.restore(null); assert.equal(store.current(),null);
  store.restore('theme'); assert.equal(store.current(),'theme');
  assert.deepEqual(calls,[false,true]);
});
test('only the latest open overlay is active; unmounted dialogs cannot reopen', () => {
  const store = createNavigationOverlays();
  store.update('theme',true,()=>{}); store.update('printer',true,()=>{});
  assert.equal(store.current(),'printer');
  store.restore('theme'); assert.equal(store.current(),'theme');
  store.remove('theme'); store.restore('theme'); assert.equal(store.current(),null);
});
test('unchanged state does not notify or reorder; unsubscribe stops notifications', () => {
  const store = createNavigationOverlays(); const calls = [];
  const unsubscribe = store.subscribe(value=>calls.push(value));
  store.update('theme',false,()=>{}); store.update('theme',true,()=>{});
  store.update('theme',true,()=>{}); assert.deepEqual(calls,['theme']);
  unsubscribe(); store.remove('theme'); assert.deepEqual(calls,['theme']);
});
