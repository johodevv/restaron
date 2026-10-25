// One owner per connection. Old sockets and timers cannot replace a newer login.
export function openSocketConnection({ url, onState, onMessage, onDenied, Socket = WebSocket,
  now = Date.now, later = setTimeout, cancelLater = clearTimeout,
  repeat = setInterval, cancelRepeat = clearInterval, random = Math.random }) {
  let socket, retry, heartbeat, deadline, disposed = false, denied = false, attempts = 0, lastSeen = 0;
  const clearTimers = () => { cancelLater(retry); cancelLater(deadline); cancelRepeat(heartbeat); };
  const retire = () => {
    if (!socket) return;
    socket.onopen = socket.onclose = socket.onmessage = socket.onerror = null;
    try { socket.close(); } catch {}
    socket = null;
  };
  const schedule = () => {
    if (disposed || denied) return;
    cancelLater(retry);
    retry = later(connect, Math.min(1000 * 2 ** attempts++, 15000) + Math.floor(random() * 500));
  };
  const reconnect = () => { clearTimers(); retire(); onState(false); schedule(); };
  const connect = () => {
    if (disposed || denied) return;
    clearTimers(); retire();
    try {
      const current = socket = new Socket(url);
      const active = () => !disposed && socket === current;
      deadline = later(() => { if (active()) reconnect(); }, 12000);
      current.onopen = () => {
        if (!active()) return;
        cancelLater(deadline); attempts = 0; lastSeen = now(); onState(true);
        heartbeat = repeat(() => {
          if (!active()) return;
          if (now() - lastSeen > 60000) { reconnect(); return; }
          // Server pings already keep the channel alive. Probe only if it went quiet.
          if (now() - lastSeen > 30000 && current.readyState === Socket.OPEN) current.send(JSON.stringify({ type: 'ping' }));
        }, 25000);
      };
      current.onmessage = event => {
        if (!active()) return;
        lastSeen = now();
        let data;
        try { data = JSON.parse(event.data); } catch { return; }
        if (data.type === 'ping') {
          if (current.readyState === Socket.OPEN) current.send(JSON.stringify({ type: 'pong' }));
          return;
        }
        if (data.type !== 'pong') onMessage(data);
      };
      current.onclose = event => {
        if (!active()) return;
        clearTimers(); retire(); onState(false);
        if ([4401, 4403].includes(event.code)) { denied = true; onDenied(event.code); return; }
        schedule();
      };
      current.onerror = () => { if (active()) reconnect(); };
    } catch { onState(false); schedule(); }
  };
  connect();
  return {
    resume() {
      if (disposed || denied) return;
      if (!socket || socket.readyState !== Socket.OPEN || now() - lastSeen > 45000) { attempts = 0; connect(); }
      else socket.send(JSON.stringify({ type: 'ping' }));
    },
    dispose() { disposed = true; clearTimers(); retire(); },
  };
}
