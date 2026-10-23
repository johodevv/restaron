import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { api } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { createPortal } from 'react-dom';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { useLanguage } from '../context/LanguageContext';
import { posLabel } from '../utils/posLabels';
import { AlertTriangle, RefreshCw, X } from 'lucide-react';

export const PrinterStatusBanner = () => {
  const { canCheckout } = useAuth();
  const { lang } = useLanguage();
  const label = text => posLabel(text, lang);
  const [expanded, setExpanded] = useState(false);
  const [resolving, setResolving] = useState(null);
  const [stuckPrinters, setStuckPrinters] = useState([]);
  const { addEventListener } = useWebSocket() || {};
  const isMountedRef = useRef(true);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api.get('/receipts/print-jobs/summary');
      if (!isMountedRef.current) return;
      if (Array.isArray(data)) {
        // oldest_age_seconds > 20 bo'lgan printerlarni
        //  filtrlaymiz
        const stuck = data.filter(
          (p) =>
            p.uncertain_ids?.length || (p.oldest_age_seconds !== null &&
            p.oldest_age_seconds !== undefined &&
            Number(p.oldest_age_seconds) > 20)
        );
        setStuckPrinters(stuck);
      }
    } catch (err) {
      console.warn('Printer summary yuklashda xatolik:', err);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    fetchSummary();

    // Har 10 soniyada yangilab turish
    const interval = setInterval(() => {
      fetchSummary();
    }, 10000);

    // WebSocket hodisalari: print_alert va print_ok
    const unsubAlert = addEventListener
      ? addEventListener('print_alert', () => {
        fetchSummary();
      })
      : null;

    const unsubOk = addEventListener
      ? addEventListener('print_ok', () => {
        fetchSummary();
      })
      : null;

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
      if (typeof unsubAlert === 'function') unsubAlert();
      if (typeof unsubOk === 'function') unsubOk();
    };
  }, [fetchSummary, addEventListener]);

  const dialogRef = useDialogFocus(expanded && stuckPrinters.length > 0, () => setExpanded(false));
  const resolve = async (id, action) => {
    const question = action === 'printed' ? `#${id} chek qog'ozda chiqqanini tekshirdingizmi?` : `#${id} chekni TAKROR belgisi bilan qayta yuborilsinmi?`;
    if (!window.confirm(question)) return;
    setResolving(id);
    try { await api.post(`/receipts/print-jobs/${id}/resolve?action=${action}`, {}); await fetchSummary(); }
    catch (err) { window.alert(err.message); }
    finally { setResolving(null); }
  };
  const pending = stuckPrinters.reduce((sum, printer) => sum + Number(printer.pending_count || 0), 0);
  const uncertain = stuckPrinters.reduce((sum, printer) => sum + (printer.uncertain_ids?.length || 0), 0);

  if (!stuckPrinters || stuckPrinters.length === 0) {
    return null;
  }

  return <>
    <div role="status" data-testid="printer-status-summary" className="w-full shrink-0 bg-rose-950 border-b border-rose-500/50 text-rose-100 px-3 flex items-center gap-2 min-h-[44px]">
      <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0" />
      <p className="flex-1 min-w-0 truncate text-xs sm:text-sm font-semibold" title={`${pending} ${label('ta chek')} · ${stuckPrinters.length} printer`}>
        {label('Printer navbati')}: {pending} {label('ta chek')} <span className="hidden sm:inline opacity-70">· {stuckPrinters.length} printer</span>
      </p>
      <button aria-haspopup="dialog" aria-expanded={expanded} onClick={() => setExpanded(true)} className="min-h-[44px] px-2 text-xs sm:text-sm font-bold underline underline-offset-4">{label('Tafsilotlar')}</button>
      <button onClick={fetchSummary} aria-label={label('Yangilash')} title={label('Yangilash')} className="w-11 h-11 flex items-center justify-center rounded-lg hover:bg-white/10 shrink-0"><RefreshCw size={17} /></button>
    </div>
    {expanded && createPortal(<div className="fixed inset-0 z-[80] bg-black/75 flex items-center justify-center p-3 sm:p-6" onClick={event => { if (event.target === event.currentTarget) setExpanded(false); }}>
      <section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="printer-queue-title" className="w-full max-w-2xl max-h-[85dvh] flex flex-col bg-slate-950 text-slate-100 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
          <div><h2 id="printer-queue-title" className="text-lg font-bold">{label('Printer navbati')}</h2><p className="text-xs text-slate-400">{pending} {label('ta chek')} · {uncertain} {label('tasdiq kutilmoqda')}</p></div>
          <button aria-label={label('Yopish')} onClick={() => setExpanded(false)} className="w-11 h-11 flex items-center justify-center rounded-xl hover:bg-slate-800"><X size={22} /></button>
        </div>
        <div className="overflow-y-auto p-4 space-y-3 min-h-0">
          {stuckPrinters.map((printer, index) => <article key={printer.printer_name || index} className="p-3 rounded-xl border border-rose-900 bg-rose-950/20">
            <h3 className="font-bold break-words">{printer.printer_name || label("Noma'lum")}</h3>
            <p className="text-sm text-amber-200 mt-1">{printer.pending_count || 0} {label('ta chek')}</p>
            {printer.last_error && <p className="text-xs text-rose-200 mt-2 break-words">{printer.last_error}</p>}
            {canCheckout && (printer.uncertain_ids || []).map(id => <div key={id} className="flex flex-wrap items-center gap-2 mt-3 border-t border-slate-700 pt-2 text-xs">
              <span className="text-slate-400">#{id}</span>
              <button disabled={resolving !== null} onClick={() => resolve(id, 'printed')} className="min-h-[44px] px-3 rounded-lg border border-slate-600 hover:bg-slate-800 disabled:opacity-40">{label('Qog‘ozda chiqdi')}</button>
              <button disabled={resolving !== null} onClick={() => resolve(id, 'retry')} className="min-h-[44px] px-3 rounded-lg border border-amber-800 text-amber-300 hover:bg-slate-800 disabled:opacity-40">{label('Qayta yuborish')}</button>
            </div>)}
          </article>)}
        </div>
      </section>
    </div>, document.body)}
  </>;
};

export default PrinterStatusBanner;
