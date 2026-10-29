import test from 'node:test';
import assert from 'node:assert/strict';
import { createPanelHistory } from '../src/utils/panelHistory.js';

function setup() {
  const stack = [{ state: { existing: true } }];
  let index = 0;
  const listeners = new Set();
  const jobs = [];
  const browser = {
    history: {
      get state() { return stack[index].state; },
      replaceState(state) { stack[index] = { state }; },
      pushState(state) { stack.splice(++index); stack.push({ state }); },
      go(delta) { jobs.push(() => { index += delta; for (const listener of listeners) listener({ state: stack[index]?.state }); }); },
    },
    addEventListener(_, listener) { listeners.add(listener); },
    removeEventListener(_, listener) { listeners.delete(listener); },
  };
  let restored = null;
  let allowed = true;
  const root = { screen: 'tables' };
  const panel = createPanelHistory(browser, root, value => { restored = value; }, () => allowed);
  return { panel, browser, root, stack, flush() { while (jobs.length) jobs.shift()(); }, get restored() { return restored; }, set allowed(value) { allowed = value; } };
}
test('Back closes a dialog, then cart, then order; Forward restores navigation only', () => {
  const s = setup();
  const order = { screen: 'order' }, cart = { screen: 'cart' }, dialog = { screen: 'weight' };
  [order, cart, dialog].forEach(s.panel.update);
  for (const expected of [cart, order, s.root]) {
    s.browser.history.go(-1); s.flush(); assert.deepEqual(s.restored, expected);
  }
  s.browser.history.go(1); s.flush(); assert.deepEqual(s.restored, order);
});
test('on-screen close removes its history entry instead of reopening the dialog on Back', () => {
  const s = setup();
  s.panel.update({ screen: 'order' }); s.panel.update({ screen: 'note' });
  s.panel.update({ screen: 'order' }); s.flush();
  s.browser.history.go(-1); s.flush(); assert.deepEqual(s.restored, s.root);
});
test('rapid close then another screen reconciles the pending history movement', () => {
  const s = setup();
  s.panel.update({ screen: 'order' }); s.panel.update({ screen: 'note' });
  s.panel.update({ screen: 'order' }); s.panel.update({ screen: 'calls' }); s.flush();
  s.browser.history.go(-1); s.flush(); assert.deepEqual(s.restored, { screen: 'order' });
});
test('pending save blocks Back; repeated data refreshes add no entries', () => {
  const s = setup(); s.panel.update({ screen: 'weight' });
  s.allowed = false; s.browser.history.go(-1); s.flush(); assert.equal(s.restored, null);
  const length = s.stack.length;
  s.panel.update({ screen: 'weight' }); assert.equal(s.stack.length, length);
  s.allowed = true; s.browser.history.go(-1); s.flush(); assert.deepEqual(s.restored, s.root);
});
test('preserves unrelated history state and detaches on unmount', () => {
  const s = setup(); assert.equal(s.browser.history.state.existing, true);
  s.panel.update({ screen: 'order' }); s.panel.dispose();
  s.browser.history.go(-1); s.flush(); assert.equal(s.restored, null);
});
test('switching tables retains distinct navigation and discards obsolete forward entries', () => {
  const s = setup();
  s.panel.update({ screen: 'order', table: 1 });
  s.panel.update(s.root); s.flush();
  s.panel.update({ screen: 'order', table: 2 });
  assert.equal(s.stack.length, 2);
  s.browser.history.go(-1); s.flush(); assert.deepEqual(s.restored, s.root);
  s.browser.history.go(1); s.flush(); assert.deepEqual(s.restored, { screen: 'order', table: 2 });
});
test('repeated on-screen Back requests settle at the requested root without restoring stale state', () => {
  const s = setup();
  s.panel.update({ screen: 'order' }); s.panel.update({ screen: 'cart' }); s.panel.update({ screen: 'note' });
  s.panel.update({ screen: 'cart' }); s.panel.update(s.root); s.flush();
  assert.equal(s.restored, null);
  assert.equal(s.browser.history.state.restaronPanel.index, 0);
});
