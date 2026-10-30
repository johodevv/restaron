import { previewOrderTotals } from './posTotals.js';

// Project only unconfirmed intentions on top of the last confirmed server order.
// Acknowledgements remove one intention; they cannot roll back later taps.
export function projectPosOrder(base, intents) {
  if (!base) return base;
  let items = (base.items || []).map(item => ({ ...item }));
  for (const intent of intents) {
    if (intent.kind === 'add' && !intent.menu.is_weighted) {
      const found = items.find(item => !item.is_weighted && item.menu_item_id === intent.menu.id);
      if (found) { found.quantity += intent.quantity; found.total_price = found.manual_price ?? found.unit_price * found.quantity; }
      else items.push({ id: `pending:${intent.menu.id}`, menu_item_id: intent.menu.id, menu_item_name: intent.menu.name,
        unit_price: intent.menu.price, quantity: intent.quantity, total_price: intent.menu.price * intent.quantity, sent_quantity: 0 });
    } else if (intent.kind === 'delta') {
      const item = items.find(item => item.id === intent.itemId || (String(intent.itemId).startsWith('pending:') && item.menu_item_id === intent.menuId && !item.is_weighted));
      if (!item) continue;
      item.quantity += intent.delta;
      if (item.quantity <= 0) { items = items.filter(line => line !== item); continue; }
      item.total_price = item.manual_price != null ? item.manual_price
        : item.is_weighted ? (item.weight || 0) * item.unit_price * item.quantity : item.unit_price * item.quantity;
    }
  }
  return { ...base, items, ...previewOrderTotals(base, items.reduce((sum, item) => sum + item.total_price, 0)) };
}

export function createPosMutationQueue({ execute, onChange, onError = () => {}, onConfirmed = () => {} }) {
  const jobs = [], bases = new Map();
  let running = false, blocked = null, resolveIdle, idle = Promise.resolve();
  const notify = scope => onChange(scope, projectPosOrder(bases.get(scope), jobs.filter(job => job.scope === scope).map(job => job.intent)), jobs.length, blocked);
  async function run() {
    if (running || blocked) return;
    running = true;
    while (jobs.length && !blocked) {
      const job = jobs[0]; job.started = true;
      try {
        const order = await execute(job.intent, bases.get(job.scope), job.key);
        bases.set(job.scope, order); jobs.shift();
        onConfirmed(job.scope, order, job.intent);
        notify(job.scope);
      } catch (error) {
        blocked = error; notify(job.scope); onError(error);
      }
    }
    running = false;
    if (!jobs.length) { bases.clear(); resolveIdle?.(); resolveIdle = null; }
  }
  return {
    enqueue(scope, base, intent, key) {
      if (!jobs.length) idle = new Promise(resolve => { resolveIdle = resolve; });
      if (!jobs.some(job => job.scope === scope)) bases.set(scope, base);
      const tail = jobs.at(-1);
      const merge = tail && !tail.started && tail.scope === scope && tail.intent.kind === intent.kind && (
        intent.kind === 'add' ? !intent.menu.is_weighted && tail.intent.menu.id === intent.menu.id && tail.intent.quantity + intent.quantity <= 50
          : tail.intent.itemId === intent.itemId && Math.sign(tail.intent.delta) === Math.sign(intent.delta) && Math.abs(tail.intent.delta + intent.delta) <= 50);
      if (merge) {
        if (intent.kind === 'add') tail.intent.quantity += intent.quantity;
        else tail.intent.delta += intent.delta;
      } else jobs.push({ scope, intent: { ...intent }, key, started: false });
      notify(scope); queueMicrotask(run); return idle;
    },
    has: scope => jobs.some(job => job.scope === scope),
    get pending() { return jobs.length; },
    get error() { return blocked; },
    retry() { blocked = null; if (jobs[0]) notify(jobs[0].scope); void run(); },
    discard() {
      if (!blocked || running) return;
      const scopes = [...new Set(jobs.map(job => job.scope))]; jobs.length = 0; blocked = null;
      scopes.forEach(notify); bases.clear(); resolveIdle?.(); resolveIdle = null;
    },
  };
}
