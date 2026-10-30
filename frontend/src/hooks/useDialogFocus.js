import { useEffect, useRef } from 'react';

export function useDialogFocus(open, onClose) {
  const dialogRef = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement;
    const focusable = () => [...(dialogRef.current?.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], summary, [tabindex="0"]') || [])].filter(node => node.getClientRects().length);
    const frame = requestAnimationFrame(() => (dialogRef.current?.querySelector('[data-dialog-autofocus]') || dialogRef.current?.querySelector('input') || focusable()[0])?.focus());
    const onKeyDown = event => {
      if (event.key === 'Escape') { event.preventDefault(); closeRef.current(); }
      if (event.key !== 'Tab') return;
      const nodes = focusable();
      const target = event.shiftKey ? nodes.at(-1) : nodes[0];
      if (!nodes.length) { event.preventDefault(); return; }
      if (!dialogRef.current?.contains(document.activeElement) || document.activeElement === (event.shiftKey ? nodes[0] : nodes.at(-1))) {
        event.preventDefault(); target.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => { cancelAnimationFrame(frame); document.removeEventListener('keydown', onKeyDown); if (previous?.isConnected) previous.focus(); };
  }, [open]);
  return dialogRef;
}
