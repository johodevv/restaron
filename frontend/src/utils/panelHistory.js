// Only navigation belongs in browser history. Never put orders, tokens or prices here.
export function createPanelHistory(browser, initial, restore, canRestore = () => true) {
  const namespace = `panel-${Date.now()}-${Math.random()}`;
  const key = value => JSON.stringify(value);
  let frames = [initial];
  let index = 0;
  let pending = null;
  let desired = initial;
  let disposed = false;
  const state = i => ({ ...browser.history.state, restaronPanel: { namespace, index: i } });
  browser.history.replaceState(state(0), '');

  function update(snapshot) {
    desired = snapshot;
    if (disposed || pending !== null || key(snapshot) === key(frames[index])) return;
    let previous = -1;
    for (let i = index - 1; i >= 0; i -= 1) {
      if (key(frames[i]) === key(snapshot)) { previous = i; break; }
    }
    if (previous >= 0) {
      pending = previous;
      browser.history.go(previous - index);
    } else {
      frames = frames.slice(0, index + 1);
      frames.push(snapshot);
      index += 1;
      browser.history.pushState(state(index), '');
    }
  }

  function onPop(event) {
    if (disposed) return;
    const target = event.state?.restaronPanel;
    if (target?.namespace !== namespace || !frames[target.index]) return;
    index = target.index;
    if (pending !== null) {
      pending = null;
      update(desired); // Reconcile rapid on-screen navigation while history.go was pending.
    } else if (canRestore()) {
      desired = frames[index];
      restore(desired);
    } else {
      update(desired); // A save in progress must not close its dialog.
    }
  }
  browser.addEventListener('popstate', onPop);
  return { update, dispose() { disposed = true; browser.removeEventListener('popstate', onPop); } };
}
