import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Search, X, Plus, Settings2, QrCode, Users, MapPin, ChevronRight, Receipt, CreditCard, Calendar, Printer, Copy, Check, Download, ExternalLink, Trash2, Lock, RefreshCw } from 'lucide-react';
import api, { BASE_URL } from '../../utils/api';
import { useDialogFocus } from '../../hooks/useDialogFocus';
import { tableDirectory, tableStatus, tableZone, normalizeQrBaseUrl, qrAddressKind } from '../../utils/tableDirectory';
import './TablesTab.css';

const statuses = {
  available: { label: "Bo‘sh", color: 'text-emerald-200', badge: 'bg-emerald-500/15 border-emerald-400/30' },
  occupied: { label: 'Band', color: 'text-rose-200', badge: 'bg-rose-500/15 border-rose-400/30' },
  reserved: { label: 'Bron', color: 'text-amber-200', badge: 'bg-amber-500/15 border-amber-400/30' },
  maintenance: { label: "Ta’mirda", color: 'text-slate-300', badge: 'bg-slate-500/15 border-slate-400/30' },
};
const statusInfo = table => statuses[tableStatus(table)] || { label: 'Holat noma’lum', color: 'text-slate-300', badge: 'bg-slate-500/15 border-slate-400/30' };
const field = 'table-field w-full min-h-[44px] rounded-xl border px-3 py-2.5 text-sm focus:outline-none';
const button = 'table-button min-h-[44px] rounded-xl border px-3 py-2 text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2';
const primary = `${button} table-button-primary`;
const tableAction = primary;
const money = value => Number(value ?? 0).toLocaleString('uz-UZ', { maximumFractionDigits: 2 });

function InlineTableBill({ bill, onEditFee, feeEditor, busy }) {
  if (!bill?.has_active_orders) return <section aria-label="Stol hisobi" className="table-inline-bill mb-4 rounded-xl border border-slate-600 p-4"><p className="text-sm text-slate-400">Ochiq hisob yo‘q</p><div className="flex items-baseline justify-between gap-3 mt-3"><span>Jami hisob</span><strong className="text-xl text-slate-100" data-testid="table-bill-total">0 so‘m</strong></div></section>;
  return <section aria-label="Stol hisobi" className="table-inline-bill mb-4 rounded-xl border border-slate-600 overflow-hidden">
    <div className="p-3 border-b border-slate-600"><h3 className="font-semibold text-slate-100">Joriy hisob</h3>{bill.waiter_name && <p className="text-xs text-slate-400 mt-1">Ofitsiant: {bill.waiter_name}</p>}</div>
    <div className="p-3 space-y-3">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 text-xs text-slate-400"><span>Taom / miqdor</span><span>Summa</span></div>
      {(bill.items || []).map((item, index) => <div key={item.order_item_id ?? index} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 text-sm">
        <div className="min-w-0"><p className="text-slate-100 break-words">{item.name}{item.portion_size ? ` · ${item.portion_size}` : ''}</p><p className="text-xs text-slate-400 mt-1">{item.quantity}{item.is_weighted && item.weight ? ` × ${item.weight} ${item.unit || 'kg'}` : ' ta'}</p></div><span className="text-slate-200 tabular-nums whitespace-nowrap">{money(item.total_price)}</span>
      </div>)}
    </div>
    <dl className="p-3 border-t border-slate-600 space-y-2 text-sm tabular-nums">
      <div className="flex justify-between gap-3 text-slate-300"><dt>Taomlar</dt><dd>{money(bill.subtotal)} so‘m</dd></div>
      <div className="flex items-start justify-between gap-3 text-slate-300"><dt>Xizmat haqi ({money(bill.service_fee_percent)}%)<button type="button" className={`${button} mt-2 flex text-xs`} disabled={busy || !!feeEditor} onClick={onEditFee}>Foizni o‘zgartirish</button></dt><dd className="whitespace-nowrap">{money(bill.service_fee_amount)} so‘m</dd></div>
      {feeEditor && <div><dt className="sr-only">Komissiya sozlamalari</dt><dd>{feeEditor}</dd></div>}
      {Number(bill.discount) > 0 && <div className="flex justify-between gap-3 text-slate-300"><dt>Chegirma</dt><dd>−{money(bill.discount)} so‘m</dd></div>}
      <div className="flex justify-between gap-3 font-semibold text-slate-100"><dt>Jami hisob</dt><dd data-testid="table-bill-total">{money(bill.grand_total)} so‘m</dd></div>
      {Number(bill.advance_amount) > 0 && <div className="flex justify-between gap-3 text-emerald-200"><dt>Avans</dt><dd>−{money(bill.advance_amount)} so‘m</dd></div>}
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-t border-slate-600 pt-3 text-slate-100"><dt className="font-semibold">To‘lash kerak</dt><dd className="text-xl font-bold" data-testid="table-bill-due">{money(bill.amount_due)} so‘m</dd></div>
    </dl>
  </section>;
}

function Dialog({ title, onClose, children, wide = false }) {
  const ref = useDialogFocus(true, onClose);
  return createPortal(<div className="fixed inset-0 z-[70] bg-black/75 backdrop-blur-sm flex items-center justify-center p-3" onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={ref} role="dialog" aria-modal="true" aria-label={title} className={`tables-workspace table-dialog w-full ${wide ? 'max-w-2xl' : 'max-w-md'} max-h-[90dvh] overflow-y-auto rounded-2xl border p-4 sm:p-6 shadow-2xl`}>
      <div className="flex items-center justify-between gap-3 mb-5"><h2 className="text-xl font-bold text-slate-100">{title}</h2><button type="button" aria-label="Oynani yopish" onClick={onClose} className={button}><X size={18} /></button></div>
      {children}
    </section>
  </div>, document.body);
}

export default function TablesTab({ tables, zones, restaurantId, qrBaseUrl, lanInfo, loading, error, ordersRevision, onQrBaseUrlChange, onRefresh, onCheckout, onPrintBill, onBook }) {
  const [query, setQuery] = useState('');
  const [zone, setZone] = useState('');
  const [status, setStatus] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [modal, setModal] = useState(null);
  const [qrTable, setQrTable] = useState(null);
  const [busy, setBusy] = useState(false);
  const [pendingTableId, setPendingTableId] = useState(null);
  const busyRef = useRef(false);
  const [notice, setNotice] = useState(null);
  const [directQrAccess, setDirectQrAccess] = useState(true);
  const [account, setAccount] = useState({ loading: false, bill: null, error: '' });
  const [accountRevision, setAccountRevision] = useState(0);
  const [feeEditing, setFeeEditing] = useState(false);
  const [feeValue, setFeeValue] = useState('');
  const [feeError, setFeeError] = useState('');
  const [qrReady, setQrReady] = useState(false);
  const [qrError, setQrError] = useState(false);
  const [copied, setCopied] = useState(false);
  const [urlDraft, setUrlDraft] = useState(qrBaseUrl);
  const [newTable, setNewTable] = useState({ number: '', room: '', capacity: 4 });
  const [zoneName, setZoneName] = useState('');
  const [zoneEdit, setZoneEdit] = useState(null);
  const resultsRef = useRef(null);
  const directory = useMemo(() => tableDirectory(tables, zones, { query, zone, status }), [tables, zones, query, zone, status]);
  const zoneAvailability = useMemo(() => {
    const counts = new Map();
    for (const table of tables) {
      if (table.is_active === false || tableStatus(table) !== 'available') continue;
      const key = tableZone(table) || '__nozone__';
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return counts;
  }, [tables]);
  const chooseZone = value => { setZone(value); setQuery(''); setStatus(''); resultsRef.current?.scrollIntoView({ block: 'nearest' }); };
  const zoneTitle = directory.zoneOptions.find(option => option.value === zone)?.label || 'Barcha zonalar';
  const selected = tables.find(table => table.id === selectedId);
  const accountKnown = selectedId !== null && account.tableId === selectedId && !account.loading && !account.error;
  const hasActiveOrders = account.bill?.has_active_orders === true;
  const hasOpen = !accountKnown || hasActiveOrders;
  const addressKind = qrAddressKind(qrBaseUrl);

  useEffect(() => { setFeeEditing(false); setFeeError(''); }, [selectedId]);

  useEffect(() => {
    let disposed = false;
    api.get(`/restaurants/${restaurantId}`).then(data => { if (!disposed) setDirectQrAccess(data.settings?.direct_qr_access !== false); }).catch(() => {});
    return () => { disposed = true; };
  }, [restaurantId]);

  useEffect(() => {
    if (!selectedId) return;
    let disposed = false;
    setAccount({ tableId: selectedId, loading: true, bill: null, error: '' });
    api.get(`/tables/${selectedId}/bill`).then(bill => {
      if (!disposed) setAccount({ tableId: selectedId, loading: false, bill, error: '' });
    }).catch(error => { if (!disposed) setAccount({ tableId: selectedId, loading: false, bill: null, error: error.message }); });
    return () => { disposed = true; };
  }, [selectedId, selected?.status, accountRevision, ordersRevision]);

  const run = async (operation, message, close = false) => {
    if (busyRef.current) return false;
    busyRef.current = true; setBusy(true); setNotice(null);
    try {
      await operation();
      await onRefresh();
      setAccountRevision(value => value + 1);
      if (close) { setModal(null); setSelectedId(null); }
      setNotice({ text: message, error: false });
      return true;
    } catch (error) { setNotice({ text: error.message || 'Amal bajarilmadi. Qayta urinib ko‘ring.', error: true }); return false; }
    finally { busyRef.current = false; setBusy(false); }
  };
  const editFee = () => {
    if (!accountKnown || !hasActiveOrders || busyRef.current) return;
    setFeeValue(String(account.bill.service_fee_percent ?? 0)); setFeeError(''); setFeeEditing(true);
  };
  const saveFee = async event => {
    event.preventDefault();
    if (busyRef.current || !accountKnown || !hasActiveOrders) return;
    const text = feeValue.trim().replace(',', '.');
    const percent = Number(text);
    if (!/^\d{1,3}(\.\d{1,2})?$/.test(text) || !Number.isFinite(percent) || percent < 0 || percent > 100) {
      setFeeError('0 dan 100 gacha foiz kiriting (masalan: 12 yoki 12,5).'); return;
    }
    setFeeError('');
    const saved = await run(() => api.patch(`/tables/${selectedId}/service-fee`, { percent }), `Komissiya ${money(percent)}% qilib saqlandi.`);
    if (saved) setFeeEditing(false);
  };
  const openQr = table => { setSelectedId(null); setQrTable(table); setQrReady(false); setQrError(false); setCopied(false); };
  const occupyTable = async table => {
    if (busyRef.current) return;
    setPendingTableId(table.id);
    try { await run(() => api.patch(`/tables/${table.id}/status`, { status: 'occupied' }), `Stol #${table.number} band qilindi.`); }
    finally { setPendingTableId(null); }
  };
  const qrLink = qrTable ? `${qrBaseUrl}/?table=${encodeURIComponent(qrTable.qr_token)}` : '';
  const qrImage = qrTable ? `${BASE_URL}/tables/qr-image/${encodeURIComponent(qrTable.qr_token)}?base_url=${encodeURIComponent(qrBaseUrl)}` : '';
  const copyQrLink = async () => {
    try { await navigator.clipboard.writeText(qrLink); setCopied(true); }
    catch { setNotice({ error: true, text: 'Avtomatik nusxalash ochilmadi. QR oynasidagi havolani belgilab nusxalang.' }); }
  };

  return <div className="tables-workspace space-y-5" data-testid="table-directory">
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-2xl font-bold text-slate-100">Stollar</h2><p className="text-sm text-slate-400 mt-1">Zonani tanlang. Mehmon kelgan bo‘lsa «Band qilish»ni bosing.</p></div>
      <div className="flex flex-wrap gap-2"><button aria-label="Stollarni yangilash" className={button} disabled={busy} onClick={() => run(() => Promise.resolve(), 'Stollar yangilandi.')}><RefreshCw size={17}/></button><button className={button} onClick={() => { setNotice(null); setUrlDraft(qrBaseUrl); setModal('settings'); }}><Settings2 size={17} />Sozlamalar</button><button className={button} onClick={() => { setNotice(null); setNewTable({ number: '', room: zone && zone !== '__nozone__' ? zone : '', capacity: 4 }); setModal('create'); }}><Plus size={18} />Stol qo‘shish</button></div>
    </header>

    {error && <div role="alert" className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-sm text-rose-200">Stollarni yangilab bo‘lmadi: {error}. Oxirgi yuklangan ma’lumot ko‘rsatilmoqda. Yuqoridagi yangilash tugmasi bilan qayta urinib ko‘ring.</div>}
    {notice && <div role={notice.error ? 'alert' : 'status'} className={`rounded-xl border p-3 flex items-start gap-3 text-sm ${notice.error ? 'border-rose-500/40 bg-rose-950/40 text-rose-200' : 'border-emerald-500/30 bg-emerald-950/40 text-emerald-200'}`}><span className="flex-1">{notice.text}</span><button aria-label="Xabarni yopish" onClick={() => setNotice(null)}><X size={18}/></button></div>}

    <div className="table-zone-layout">
      <aside className="table-zone-sidebar">
        <h3 className="table-zone-heading">Zonalar</h3>
        <nav aria-label="Zonalar" className="table-zone-list">
          {[{ value: '', label: 'Barcha zonalar', count: directory.active.length }, ...directory.zoneOptions].map(option => <button key={option.value} type="button" aria-label={`Zonani tanlash: ${option.label}`} aria-pressed={zone === option.value} onClick={() => chooseZone(option.value)} className="table-zone-button">
            <MapPin size={18} aria-hidden="true"/><span className="min-w-0 flex-1"><span className="block font-semibold break-words">{option.label}</span><span className="table-zone-hint">{option.value ? zoneAvailability.get(option.value) || 0 : [...zoneAvailability.values()].reduce((sum, count) => sum + count, 0)} ta bo‘sh</span></span><span className="table-zone-count">{option.count}</span>
          </button>)}
        </nav>
      </aside>
      <div className="min-w-0 space-y-4">
      <div ref={resultsRef} className="flex flex-wrap items-end justify-between gap-2"><h3 className="text-xl font-bold text-slate-100">{zoneTitle}</h3><span className="text-sm text-slate-400">{directory.matches.length} ta stol</span></div>
    <div className="table-search-panel rounded-2xl border p-3 sm:p-4 space-y-3">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1"><Search size={20} className="absolute left-3 top-3 text-slate-400"/><input aria-label="Stol qidirish" type="search" value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Escape') setQuery(''); }} placeholder="Stol raqami, nomi yoki zal…" className={`${field} pl-10 pr-10`} />{query && <button onClick={() => setQuery('')} aria-label="Qidiruvni tozalash" className="absolute right-0 top-0 w-11 h-11 text-slate-400 flex items-center justify-center"><X size={17}/></button>}</div>
      </div>
      <div className="flex flex-wrap gap-2" aria-label="Stol holati bo‘yicha filtr">
        {[['', 'Hammasi', directory.counts.all], ...Object.entries(statuses).map(([key, info]) => [key, info.label, directory.counts[key]])].map(([key, label, count]) => <button key={key} aria-pressed={status === key} onClick={() => setStatus(key)} className={`${button} table-status-filter`}><span>{label}</span><span className="text-xs tabular-nums rounded-md bg-white/10 px-1.5 py-0.5">{count}</span></button>)}
        {(query || status) && <button className={`${button} text-slate-400 ml-auto`} onClick={() => { setQuery(''); setStatus(''); }}>Filtrlarni tozalash</button>}
      </div>
    </div>

    <p className={loading && !tables.length ? 'text-sm text-slate-400' : 'sr-only'} role="status" aria-live="polite">{loading && !tables.length ? 'Stollar yuklanmoqda…' : `${directory.matches.length} ta stol ko‘rsatilmoqda · Raqam bo‘yicha tartiblangan`}</p>
    {!loading && !error && directory.groups.length === 0 && <div className="text-center py-12 border border-dashed border-slate-600 rounded-2xl"><Search className="mx-auto text-slate-400 mb-3"/><h3 className="font-semibold text-slate-100">Stol topilmadi</h3><p className="text-sm text-slate-400 mt-1">Boshqa raqam kiriting yoki filtrlarni tozalang.</p><button className={`${button} mt-4`} onClick={() => { setQuery(''); setStatus(''); }}>Shu zonadagi barcha stollar</button></div>}
    {directory.groups.map(group => <section key={group.value} aria-label={group.label} className="space-y-3">
      {!zone && <h3 className="flex items-center gap-2 text-sm font-bold text-slate-100"><MapPin size={16} className="text-slate-400"/>{group.label}<span className="text-xs font-normal text-slate-400">{group.items.length} ta stol</span></h3>}
      <div className="grid grid-cols-1 min-[480px]:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-3">
        {group.items.map(table => { const info = statusInfo(table); const state = tableStatus(table); return <article key={table.id} data-testid={`table-card-${table.id}`} data-status={state} className="table-card min-w-0 flex flex-col rounded-2xl border overflow-hidden">
          <button className="w-full text-left px-3.5 pt-4 pb-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-theme-primary" onClick={() => { setNotice(null); setSelectedId(table.id); }} aria-label={`Stol #${table.number}, ${tableZone(table) || 'Zonasiz'}, ${info.label}. Amallarni ochish`}>
            <div className="flex items-center justify-between gap-2"><span className="text-2xl font-extrabold text-slate-100 tabular-nums">Stol #{table.number}</span><span className={`inline-flex px-2 py-1 rounded-md border text-xs font-semibold ${info.color} ${info.badge}`}>{info.label}</span></div>
            <div className="text-xs text-slate-400 truncate mt-1">{table.name && !/^stol\s*#?\d+$/i.test(table.name) ? table.name : tableZone(table) || 'Zonasiz'}</div>
            <div className="inline-flex items-center gap-1.5 text-xs text-slate-400 mt-2"><Users size={14}/>{table.capacity} kishilik</div>
            {!directQrAccess && !table.is_unlocked && table.current_pin && <p className="text-xs text-amber-200 mt-2">Tasdiq kutilmoqda</p>}
          </button>
          <div className="px-3.5 pb-3.5 space-y-2">
            {state === 'available' ? <>
              <button className={`${tableAction} w-full`} disabled={busy} onClick={() => occupyTable(table)}><Users size={17}/>{pendingTableId === table.id ? 'Band qilinmoqda…' : 'Band qilish'}</button>
              <button className={`${button} w-full text-slate-200`} disabled={busy} onClick={() => onBook(table)}><Calendar size={17}/>Bron qilish</button>
            </> : <button className={`${button} w-full text-slate-100`} disabled={busy} onClick={() => { setNotice(null); setSelectedId(table.id); }}>{state === 'occupied' ? <Receipt size={17}/> : state === 'reserved' ? <Calendar size={17}/> : <Settings2 size={17}/>}{state === 'occupied' ? 'Hisob va to‘lov' : state === 'reserved' ? 'Bron tafsilotlari' : 'Stolni boshqarish'}</button>}
          </div>
          <div className="table-card-footer grid grid-cols-2 border-t border-slate-600/70 mt-auto"><button onClick={() => openQr(table)} aria-label={`Stol #${table.number}, ${tableZone(table) || 'Zonasiz'} QR kodi`} className="min-h-[44px] inline-flex items-center justify-center gap-1.5 text-xs text-slate-400"><QrCode size={15}/>QR kod</button><button onClick={() => { setNotice(null); setSelectedId(table.id); }} className="min-h-[44px] inline-flex items-center justify-center gap-1 text-xs text-slate-400 border-l border-slate-600/70">Tafsilotlar<ChevronRight size={14}/></button></div>
        </article>; })}
      </div>
    </section>)}
      </div>
    </div>

    {selected && <Dialog title={`Stol #${selected.number}`} onClose={() => { if (!busy) setSelectedId(null); }}>
      <div className="flex items-center justify-between gap-2 mb-4"><span className="text-sm text-slate-400">{tableZone(selected) || 'Zonasiz'} · {selected.capacity} kishi</span><span className={`rounded-lg border px-2 py-1 text-xs ${statusInfo(selected).badge} ${statusInfo(selected).color}`}>{statusInfo(selected).label}</span></div>
      {notice && <p role={notice.error ? 'alert' : 'status'} className={`text-sm mb-4 ${notice.error ? 'text-rose-300' : 'text-emerald-300'}`}>{notice.text}</p>}
      {account.loading || account.tableId !== selectedId ? <p role="status" className="text-sm text-slate-400 mb-4">Hisob yuklanmoqda…</p> : account.error ? <div role="alert" className="text-sm text-rose-300 mb-4"><p>Hisobni yuklab bo‘lmadi: {account.error}</p><button className={`${button} mt-2`} onClick={() => setAccountRevision(value => value + 1)}><RefreshCw size={16}/>Qayta urinish</button></div> : <InlineTableBill bill={account.bill} onEditFee={editFee} busy={busy} feeEditor={feeEditing ? <form onSubmit={saveFee} className="rounded-xl border border-slate-500 bg-white/5 p-3 space-y-3">
        <label className="block text-sm text-slate-200" htmlFor="table-commission">Komissiya foizi (%)</label>
        <input id="table-commission" aria-describedby="table-commission-hint" aria-invalid={!!feeError} inputMode="decimal" type="text" maxLength={6} autoFocus value={feeValue} disabled={busy} onChange={event => { setFeeValue(event.target.value); setFeeError(''); }} className={field}/>
        <p id="table-commission-hint" className="text-xs text-slate-400">Faqat shu stolning joriy hisobiga qo‘llanadi. 0% ham mumkin.</p>
        {feeError && <p role="alert" className="text-sm text-rose-300">{feeError}</p>}
        <div className="grid grid-cols-2 gap-2"><button type="submit" className={primary} disabled={busy}>{busy ? 'Saqlanmoqda…' : 'Saqlash'}</button><button type="button" className={button} disabled={busy} onClick={() => { setFeeEditing(false); setFeeError(''); }}>Bekor qilish</button></div>
      </form> : null}/>}
      {selected.status === 'reserved' && <div className="rounded-xl bg-white/5 border border-slate-600 p-3 mb-4 text-sm space-y-1 text-slate-200"><p className="font-semibold">{selected.reserved_by_name || 'Bron qilingan'}</p><p>{selected.reserved_time} {selected.reserved_by_phone}</p>{Number(selected.deposit_amount) > 0 && <p>Avans: {Number(selected.deposit_amount).toLocaleString()} so‘m</p>}</div>}
      {tableStatus(selected) === 'available' && <div className="space-y-2 mb-4"><button className={`${tableAction} w-full`} disabled={busy} onClick={() => occupyTable(selected)}><Users size={17}/>{pendingTableId === selected.id ? 'Band qilinmoqda…' : 'Band qilish'}</button><button className={`${button} w-full text-slate-200`} disabled={busy || hasOpen} onClick={() => { setSelectedId(null); onBook(selected); }}><Calendar size={17}/>Bron qilish</button><p className="text-xs text-slate-400">Band qilish — hozir kelgan mehmon uchun. Bron — keyingi vaqt uchun.</p></div>}
      <div className="grid grid-cols-2 gap-2">
        <button className={primary} disabled={busy || feeEditing || !accountKnown || !hasActiveOrders} onClick={() => { setSelectedId(null); onCheckout(selected); }}><CreditCard size={17}/>To‘lov olish</button>
        <button className={button} disabled={busy || feeEditing || !accountKnown || !hasActiveOrders} onClick={() => { setSelectedId(null); onPrintBill(selected.id, selected.number); }}><Printer size={17}/>Hisob chekini chiqarish</button>
      </div>
      {!directQrAccess && !selected.is_unlocked && selected.current_pin && <div className="mt-4 p-3 rounded-xl border border-amber-500/30 text-amber-200 text-sm"><p className="mb-2">Tasdiqlash kodi: <strong>{selected.current_pin}</strong></p><button className={button} disabled={busy} onClick={() => run(() => api.post(`/tables/${selected.id}/unlock`, {}), 'Mijoz kirishi tasdiqlandi.')}><Check size={17}/>Mijozni tasdiqlash</button></div>}
      <details className="mt-5 border-t border-slate-600 pt-3"><summary className="text-sm text-slate-400 cursor-pointer min-h-[44px] flex items-center">Qo‘shimcha amallar</summary><div className="space-y-3 pt-2">
        <label className="block text-sm text-slate-400">Stol holati<select className={`${field} mt-2`} value={selected.status} disabled={busy || hasOpen || Number(selected.deposit_amount) > 0} onChange={event => { const value = event.target.value; if (window.confirm('Stol holatini o‘zgartirasizmi?')) run(() => api.patch(`/tables/${selected.id}/status`, { status: value }), 'Stol holati saqlandi.'); }}>{Object.entries(statuses).filter(([key]) => key !== 'reserved').map(([key, info]) => <option key={key} value={key}>{info.label}</option>)}{selected.status === 'reserved' && <option value="reserved">Bron</option>}</select></label>
        {!directQrAccess && selected.is_unlocked && <button className={`${button} w-full`} disabled={busy} onClick={() => { if (window.confirm('Mijoz kirishini qayta qulflaysizmi? QR kod o‘zgarmaydi.')) run(() => api.post(`/tables/${selected.id}/lock`, {}), 'Mijoz kirishi qulflandi.'); }}><Lock size={16}/>Mijoz kirishini qayta qulflash</button>}
        <button className={`${button} w-full text-rose-300`} disabled={busy || hasOpen || selected.status !== 'available' || Number(selected.deposit_amount) > 0} onClick={() => { if (window.confirm(`Stol #${selected.number} ni o‘chirasizmi? Uning bosilgan QR kodi ishlamay qoladi.`)) run(() => api.delete(`/tables/${selected.id}`), 'Stol o‘chirildi.', true); }}><Trash2 size={16}/>Stolni o‘chirish</button>
      </div></details>
    </Dialog>}

    {qrTable && <Dialog title={`Stol #${qrTable.number} — QR`} onClose={() => setQrTable(null)}>
      {notice?.error && <p role="alert" className="text-sm text-rose-300 mb-3">{notice.text}</p>}
      <style>{`@media print { body > * { display: none !important; } body > .table-qr-print { display: block !important; } .table-qr-print { position: static !important; background: white !important; color: black !important; } }`}</style>
      <div className="rounded-2xl bg-white text-black p-5 text-center" data-testid="qr-preview"><h3 className="text-2xl font-bold">Stol #{qrTable.number}</h3><p className="text-sm text-zinc-600 mt-1">{tableZone(qrTable) || 'Menyu'}</p><img src={qrImage} alt={`Stol #${qrTable.number} QR kodi`} onLoad={() => setQrReady(true)} onError={() => { setQrError(true); setQrReady(false); }} className="w-56 h-56 max-w-full mx-auto my-3 object-contain"/>{qrError ? <p role="alert" className="text-sm text-red-700">QR rasm yuklanmadi. Server bilan aloqani tekshiring.</p> : !qrReady ? <p className="text-sm text-zinc-500">QR yuklanmoqda…</p> : <p className="text-sm font-medium">Menyuni ochish uchun skanerlang</p>}</div>
      {addressKind !== 'public' && <p className="text-xs text-amber-200 mt-3">{addressKind === 'loopback' ? 'Bu manzil faqat shu kompyuterda ochiladi. Sozlamalarda telefonlar uchun domenni tanlang.' : addressKind === 'temporary' ? 'Vaqtinchalik tunnel manzili o‘zgarsa, bosilgan QR ishlamay qoladi.' : 'Bu manzil shu Wi-Fi ichida ishlaydi. Server IP manzili o‘zgarmasligi kerak.'}</p>}
      <label className="block text-xs text-slate-400 mt-4">Stol havolasi<input readOnly value={qrLink} className={`${field} mt-1 text-xs`} onFocus={event => event.target.select()}/></label>
      <div className="grid grid-cols-2 gap-2 mt-3"><button className={button} onClick={copyQrLink}>{copied ? <Check size={16}/> : <Copy size={16}/>} {copied ? 'Nusxalandi' : 'Havolani nusxalash'}</button><a className={button} href={qrImage} download={`Stol_${qrTable.number}_QR.png`} aria-disabled={!qrReady} onClick={event => { if (!qrReady) event.preventDefault(); }}><Download size={16}/>PNG yuklash</a></div>
      <button className={`${primary} w-full mt-2`} disabled={!qrReady} onClick={() => window.print()}><Printer size={17}/>QR kodni chop etish</button>
      <a className={`${button} w-full mt-2 text-slate-400`} href={qrLink} target="_blank" rel="noreferrer"><ExternalLink size={16}/>Menyuni ochish</a>
      {createPortal(<div className="table-qr-print hidden"><h1>Stol #{qrTable.number}</h1><p>{tableZone(qrTable)}</p><img src={qrImage} alt="QR" style={{ width: '65mm', height: '65mm' }}/><p>Menyuni ochish uchun skanerlang</p></div>, document.body)}
    </Dialog>}

    {modal === 'create' && <Dialog title="Stol qo‘shish" onClose={() => { if (!busy) setModal(null); }}><form className="space-y-4" onSubmit={event => { event.preventDefault(); run(() => api.post('/tables/', { restaurant_id: restaurantId, number: Number(newTable.number), room: newTable.room || null, capacity: Number(newTable.capacity) }), 'Yangi stol qo‘shildi.', true); }}>
      {notice?.error && <p role="alert" className="text-sm text-rose-300">{notice.text}</p>}
      <label className="block text-sm text-slate-400">Stol raqami<input required type="number" min="1" step="1" className={`${field} mt-1`} value={newTable.number} onChange={event => setNewTable({ ...newTable, number: event.target.value })}/></label>
      <label className="block text-sm text-slate-400">Zal<select className={`${field} mt-1`} value={newTable.room} onChange={event => setNewTable({ ...newTable, room: event.target.value })}><option value="">Zonasiz</option>{directory.zoneOptions.filter(item => item.value !== '__nozone__').map(item => <option key={item.value}>{item.value}</option>)}</select></label>
      <label className="block text-sm text-slate-400">Necha kishilik<input required type="number" min="1" step="1" className={`${field} mt-1`} value={newTable.capacity} onChange={event => setNewTable({ ...newTable, capacity: event.target.value })}/></label><button className={`${primary} w-full`} disabled={busy} type="submit">{busy ? 'Saqlanmoqda…' : 'Stolni qo‘shish'}</button>
    </form></Dialog>}

    {modal === 'settings' && <Dialog title="Zallar va QR sozlamalari" wide onClose={() => { if (!busy) setModal(null); }}>
      {notice && <p role={notice.error ? 'alert' : 'status'} className={`text-sm mb-4 ${notice.error ? 'text-rose-300' : 'text-emerald-300'}`}>{notice.text}</p>}
      <h3 className="font-semibold text-slate-100 mb-1">QR havolasining manzili</h3><p className="text-sm text-slate-400 mb-3">Stolning QR kodi server qayta yoqilganda o‘zgarmaydi. Telefonlarda doim ishlashi uchun doimiy domen ishlating.</p>
      <form className="flex flex-col sm:flex-row gap-2" onSubmit={event => { event.preventDefault(); try { const value = normalizeQrBaseUrl(urlDraft); if (value !== qrBaseUrl && !window.confirm('Manzil o‘zgarsa, yangi QR rasmlari boshqa havolani ochadi. Oldin bosilgan kodlar eski manzilga bog‘liq qoladi. Davom etasizmi?')) return; onQrBaseUrlChange(value); setUrlDraft(value); setNotice({ error: false, text: 'QR uchun manzil saqlandi. Stol tokenlari o‘zgarmadi.' }); } catch (error) { setNotice({ error: true, text: error.message }); } }}><input aria-label="QR uchun sayt manzili" type="url" required className={field} value={urlDraft} onChange={event => setUrlDraft(event.target.value)}/><button type="submit" className={button}>Saqlash</button></form>
      {lanInfo?.public_url && qrAddressKind(lanInfo.public_url) === 'public' && <button className="min-h-[44px] text-sm text-emerald-200 break-all" onClick={() => setUrlDraft(lanInfo.public_url)}>Doimiy domen: {lanInfo.public_url}</button>}
      {addressKind !== 'public' && <p className="text-xs text-amber-200 mt-2">{addressKind === 'loopback' ? 'Joriy manzil telefonda ochilmaydi: localhost faqat shu kompyuter uchun.' : 'IP yoki vaqtinchalik tunnel manzili almashsa, oldin bosilgan QR havolasi ishlamay qolishi mumkin.'}</p>}
      <div className="mt-6 border-t border-slate-600 pt-5"><h3 className="font-semibold text-slate-100 mb-3">Zallar</h3><form className="flex gap-2" onSubmit={event => { event.preventDefault(); run(async () => { if (zoneEdit) await api.patch(`/tables/zones/${zoneEdit}`, { name: zoneName.trim() }); else await api.post('/tables/zones', { restaurant_id: restaurantId, name: zoneName.trim() }); setZoneName(''); setZoneEdit(null); }, 'Zal saqlandi.'); }}><input aria-label="Zal nomi" required maxLength={100} value={zoneName} onChange={event => setZoneName(event.target.value)} className={field} placeholder="Masalan: Terrassa"/><button className={button} disabled={busy || !zoneName.trim()}>{zoneEdit ? 'Saqlash' : 'Qo‘shish'}</button></form>
      <div className="divide-y divide-theme-border mt-3">{zones.map(item => <div key={item.id} className="flex items-center gap-2 py-2"><span className="flex-1 text-sm text-slate-100 break-words">{item.name}</span><button disabled={busy} className={button} onClick={() => { setZoneEdit(item.id); setZoneName(item.name); }}>Tahrirlash</button><button className={`${button} text-rose-300`} disabled={busy} aria-label={`${item.name} zalini o‘chirish`} onClick={() => { if (window.confirm(`${item.name} zalini o‘chirasizmi?`)) run(() => api.delete(`/tables/zones/${item.id}`), 'Zal o‘chirildi.'); }}><Trash2 size={16}/></button></div>)}</div>
      </div>
    </Dialog>}
  </div>;
}
