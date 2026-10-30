import { useEffect, useId, useRef } from 'react';
import { navigationOverlays } from '../utils/navigationOverlays';

export function useNavigationOverlay(name, open, setOpen) {
  const id = `${name}-${useId()}`;
  const callback = useRef(setOpen);
  callback.current = setOpen;
  useEffect(() => () => navigationOverlays.remove(id), [id]);
  useEffect(() => { navigationOverlays.update(id, open, value => callback.current(value)); }, [id, open]);
}
