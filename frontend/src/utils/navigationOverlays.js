export function createNavigationOverlays() {
  const entries = new Map();
  const listeners = new Set();
  let order = 0;
  const current = () => [...entries.entries()].filter(([, entry]) => entry.open)
    .sort((a,b) => b[1].order - a[1].order)[0]?.[0] || null;
  const notify = before => { if (before !== current()) listeners.forEach(listener => listener(current())); };
  return {
    current,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    update(id, open, setOpen) {
      const before = current();
      const previous = entries.get(id);
      entries.set(id, { open, setOpen, order: open && !previous?.open ? ++order : previous?.order || 0 });
      notify(before);
    },
    remove(id) { const before = current(); entries.delete(id); notify(before); },
    restore(id) {
      const before = current();
      const updates = [];
      for (const [key, entry] of entries) {
        const open = key === id;
        if (entry.open !== open) { entry.open = open; entry.order = open ? ++order : entry.order; updates.push(() => entry.setOpen(open)); }
      }
      updates.forEach(update => update());
      notify(before);
    },
  };
}
export const navigationOverlays = createNavigationOverlays();
