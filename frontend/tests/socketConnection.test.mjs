import test from 'node:test';
import assert from 'node:assert/strict';
import { openSocketConnection } from '../src/utils/socketConnection.js';

function fixture() {
  let clock = 0, id = 0;
  const timers = new Map(), sockets = [], states = [], messages = [], denied = [], retries = [];
  class Socket {
    static OPEN = 1;
    constructor() { this.readyState = 0; this.sent = []; sockets.push(this); }
    close() { this.readyState = 3; this.onclose?.({ code: 1000 }); }
    send(value) { this.sent.push(JSON.parse(value)); }
    open() { this.readyState = 1; this.onopen(); }
    message(value) { this.onmessage({ data: JSON.stringify(value) }); }
  }
  const later = (fn, ms) => { const key = ++id; timers.set(key, { fn, ms }); return key; };
  const clear = key => timers.delete(key);
  const connection = openSocketConnection({ url: 'ws://local', Socket, onState: value => states.push(value), onMessage: value => messages.push(value), onDenied: value => denied.push(value), onRetry: () => retries.push(clock), now: () => clock, random: () => 0, later, cancelLater: clear, repeat: later, cancelRepeat: clear });
  return { connection, sockets, states, messages, denied, retries, timers, setClock: value => { clock = value; }, run(ms) { const [key, value] = [...timers].find(([, value]) => value.ms === ms); timers.delete(key); value.fn(); } };
}

test('heartbeat is answered without broadcasting or rerendering business subscribers', () => {
  const f = fixture(); const ws = f.sockets[0]; ws.open();
  ws.message({ type: 'ping' }); ws.message({ type: 'pong' }); ws.message({ type: 'order_updated', id: 7 });
  assert.deepEqual(ws.sent, [{ type: 'pong' }]);
  assert.deepEqual(f.messages, [{ type: 'order_updated', id: 7 }]); f.connection.dispose();
});

test('an old closing socket cannot mark its replacement disconnected', () => {
  const f = fixture(); const old = f.sockets[0]; old.open(); const oldClose = old.onclose;
  f.setClock(46000); f.connection.resume(); const next = f.sockets[1]; next.open();
  oldClose({ code: 1006 });
  assert.deepEqual(f.states, [true, false, true]); assert.equal(f.sockets.length, 2); f.connection.dispose();
});

test('phone resume replaces stale connection; disposal cancels pending retries', () => {
  const f = fixture(); f.sockets[0].open(); f.setClock(46000); f.connection.resume();
  assert.equal(f.sockets.length, 2); f.sockets[1].onerror(); assert.ok(f.timers.size);
  f.connection.dispose(); assert.equal(f.timers.size, 0); f.connection.resume(); assert.equal(f.sockets.length, 2);
});

test('handshake timeout and absent heartbeat trigger bounded retries', () => {
  const f = fixture(); f.run(12000); f.run(1000); assert.equal(f.sockets.length, 2);
  f.sockets[1].open(); f.setClock(61000); f.run(25000); assert.equal(f.states.at(-1), false);
  f.run(1000); assert.equal(f.sockets.length, 3); f.connection.dispose();
});

for (const code of [4401, 4403]) test(`denial ${code} never reconnects on timers or phone resume`, () => {
  const f = fixture(); f.sockets[0].open(); f.sockets[0].onclose({ code });
  f.connection.resume(); f.connection.retryNow(); assert.deepEqual(f.denied, [code]); assert.equal(f.timers.size, 0); assert.equal(f.sockets.length, 1); f.connection.dispose();
});

test('repeated phone resume events preserve a pending handshake and its timeout', () => {
  const f = fixture();
  f.connection.resume(); f.connection.resume();
  assert.equal(f.sockets.length, 1);
  f.setClock(11000); f.connection.resume(); assert.equal(f.sockets.length, 1);
  f.run(12000); f.run(1000); assert.equal(f.sockets.length, 2);
  f.sockets[1].open(); assert.equal(f.states.at(-1), true); f.connection.dispose();
});

for (const path of ['resume', 'heartbeat', 'pong']) test(`failed ${path} send schedules recovery without an uncaught error`, () => {
  const f = fixture(); const ws = f.sockets[0]; ws.open();
  ws.send = () => { throw new Error('radio disconnected'); };
  assert.doesNotThrow(() => {
    if (path === 'resume') f.connection.resume();
    if (path === 'heartbeat') { f.setClock(31000); f.run(25000); }
    if (path === 'pong') ws.message({ type: 'ping' });
  });
  assert.equal(f.states.at(-1), false);
  f.run(1000); assert.equal(f.sockets.length, 2);
  f.sockets[1].open(); assert.equal(f.states.at(-1), true); f.connection.dispose();
});

test('resume immediately replaces an expired handshake even if timers were suspended', () => {
  const f = fixture(); f.setClock(13000); f.connection.resume();
  assert.equal(f.sockets.length, 2);
  f.connection.resume(); assert.equal(f.sockets.length, 2);
  f.connection.dispose(); assert.equal(f.timers.size, 0);
});

test('manual retry replaces a stalled handshake immediately, throttles clicks and ignores late old events', () => {
  const f = fixture(); const old = f.sockets[0]; const oldOpen = old.onopen;
  f.setClock(2000); f.connection.retryNow();
  assert.equal(f.sockets.length, 2);
  assert.equal(old.readyState, 3);
  f.connection.retryNow(); f.connection.resume();
  assert.equal(f.sockets.length, 2);
  oldOpen(); assert.equal(f.states.at(-1), false);
  f.sockets[1].open(); assert.equal(f.states.at(-1), true);
  f.connection.dispose(); f.setClock(5000); f.connection.retryNow();
  assert.equal(f.sockets.length, 2); assert.equal(f.timers.size, 0);
});

test('manual retry bypasses a long automatic backoff and cancels its timer', () => {
  const f = fixture();
  for (const delay of [1000, 2000, 4000, 8000]) { f.sockets.at(-1).onerror(); f.run(delay); }
  f.sockets.at(-1).onerror();
  assert.ok([...f.timers.values()].some(timer => timer.ms === 15000));
  const count = f.sockets.length;
  f.connection.retryNow();
  assert.equal(f.sockets.length, count + 1);
  assert.ok(![...f.timers.values()].some(timer => timer.ms === 15000));
  f.sockets.at(-1).open(); assert.equal(f.states.at(-1), true);
  f.connection.dispose();
});

test('the first failed connection reports retrying instead of indefinite initial connecting', () => {
  const f = fixture(); f.sockets[0].onerror();
  assert.deepEqual(f.retries, [0]); assert.equal(f.states.at(-1), false);
  f.run(1000); f.sockets[1].open();
  assert.equal(f.states.at(-1), true); f.connection.dispose();
});
