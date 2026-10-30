import { useEffect, useRef, useState } from 'react';
import { createPanelHistory } from '../utils/panelHistory';
import { navigationOverlays } from '../utils/navigationOverlays';

export function usePanelHistory(enabled, snapshot, restore, canRestore) {
  const [overlay, setOverlay] = useState(navigationOverlays.current);
  useEffect(() => {
    setOverlay(navigationOverlays.current());
    return navigationOverlays.subscribe(setOverlay);
  }, []);
  snapshot = { ...snapshot, overlay };
  const controller = useRef(null);
  const latest = useRef({ snapshot, restore, canRestore });
  latest.current = { snapshot, restore, canRestore };
  const signature = JSON.stringify(snapshot);
  useEffect(() => {
    if (!enabled) return;
    const history = createPanelHistory(window, latest.current.snapshot,
      state => { navigationOverlays.restore(state.overlay); latest.current.restore(state); }, () => latest.current.canRestore?.() !== false);
    controller.current = history;
    return () => { history.dispose(); controller.current = null; };
  }, [enabled]);
  useEffect(() => { controller.current?.update(latest.current.snapshot); }, [enabled, signature]);
}
