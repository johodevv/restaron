import { useEffect, useRef } from 'react';
import { createPanelHistory } from '../utils/panelHistory';

export function usePanelHistory(enabled, snapshot, restore, canRestore) {
  const controller = useRef(null);
  const latest = useRef({ snapshot, restore, canRestore });
  latest.current = { snapshot, restore, canRestore };
  const signature = JSON.stringify(snapshot);
  useEffect(() => {
    if (!enabled) return;
    const history = createPanelHistory(window, latest.current.snapshot,
      state => latest.current.restore(state), () => latest.current.canRestore?.() !== false);
    controller.current = history;
    return () => { history.dispose(); controller.current = null; };
  }, [enabled]);
  useEffect(() => { controller.current?.update(latest.current.snapshot); }, [enabled, signature]);
}
