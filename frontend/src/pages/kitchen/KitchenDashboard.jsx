import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Check, ChefHat } from 'lucide-react';
import api from '../../utils/api';
import { useWebSocket } from '../../context/WebSocketContext';

const stations = [['all', 'Barchasi'], ['hot_kitchen', '1-oshxona'], ['cold_kitchen', '2-oshxona'], ['bar', 'Ichimliklar']];

export default function KitchenDashboard() {
  const [orders, setOrders] = useState([]);
  const [station, setStation] = useState('all');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);
  const [now, setNow] = useState(Date.now());
  const { addEventListener, connected } = useWebSocket() || {};
  const load = useCallback(async () => {
    try { setOrders(await api.get('/kitchen/orders')); setError(''); }
    catch (err) { setError(err.message); }
  }, []);
  useEffect(() => {
    load();
    const timer = setInterval(() => { setNow(Date.now()); if (document.visibilityState === 'visible') load(); }, 5000);
    let refreshTimer;
    const unsubscribe = addEventListener?.('*', () => { clearTimeout(refreshTimer); refreshTimer = setTimeout(load, 200); });
    return () => { clearInterval(timer); clearTimeout(refreshTimer); unsubscribe?.(); };
  }, [load, addEventListener]);
  const prepare = async (order, item) => {
    if (busy) return;
    setBusy(item.id);
    try { await api.patch(`/orders/${order.id}/items/${item.id}/prepared`, { expected_sent_quantity: item.sent_quantity }); await load(); }
    catch (err) { setError(err.message); }
    finally { setBusy(null); }
  };
  const visible = orders.map(order => ({ ...order, items: order.items.filter(item => item.kitchen_pending_quantity > 0 &&
    (station === 'all' || item.kitchen_station === station || item.kitchen_station === 'all')) })).filter(order => order.items.length > 0);
  return <section className="min-h-[80vh] bg-slate-950 text-white p-4 sm:p-6">
    <header className="flex flex-wrap items-center justify-between gap-3 mb-5">
      <h1 className="text-2xl font-bold flex gap-2 items-center"><ChefHat /> Oshpaz ekrani</h1>
      <div className="flex items-center gap-3"><span className={connected ? 'text-emerald-400' : 'text-amber-400'}>{connected ? 'Jonli aloqa' : 'Aloqa tekshirilmoqda'}</span>
        <button aria-label="Yangilash" onClick={load} className="p-3 bg-slate-800 rounded-xl"><RefreshCw size={20} /></button></div>
    </header>
    <nav className="flex gap-2 flex-wrap mb-5">{stations.map(([value, label]) => <button key={value} onClick={() => setStation(value)} className={`px-4 py-3 rounded-xl font-semibold ${station === value ? 'bg-amber-500 text-slate-950' : 'bg-slate-800'}`}>{label}</button>)}</nav>
    {error ? <div role="alert" className="p-5 rounded-xl bg-amber-950 border border-amber-700">{error}</div> : visible.length === 0 ? <p className="p-10 text-center text-slate-400">Hozir tayyorlanadigan taom yo'q</p> :
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">{visible.map(order => <article key={order.id} className="rounded-2xl border border-slate-700 bg-slate-900 overflow-hidden">
        <div className="p-4 border-b border-slate-700 flex justify-between gap-3"><div><h2 className="text-xl font-bold">{order.table_number ? `Stol #${order.table_number}` : order.order_type === 'delivery' ? 'Yetkazib berish' : 'Olib ketish'}</h2><p className="text-sm text-slate-400">{order.order_number} · {order.waiter_name}</p></div><span className="text-amber-400 font-bold">{Math.max(0, Math.floor((now - new Date(order.preparing_at || order.created_at).getTime()) / 60000))} daq</span></div>
        {order.kitchen_note && <p className="px-4 py-3 bg-amber-500/10 text-amber-300 font-bold">{order.kitchen_note}</p>}
        <ul className="divide-y divide-slate-800">{order.items.map(item => <li key={item.id} className={`p-4 flex items-center gap-3 ${item.is_prepared ? 'opacity-50' : ''}`}><strong className="text-2xl text-amber-400">{item.kitchen_pending_quantity}×</strong><div className="flex-1"><p className="text-lg font-semibold">{item.menu_item_name}</p><p className="text-sm text-slate-400">{item.portion_size} {item.weight ? `${item.weight} ${item.unit}` : ''}</p>{item.special_note && <p className="text-amber-300">{item.special_note}</p>}</div><button disabled={Boolean(busy) || item.is_prepared} onClick={() => prepare(order, item)} className="min-h-[48px] px-4 py-3 rounded-xl bg-emerald-600 disabled:opacity-40 font-bold">{item.is_prepared ? <Check /> : busy === item.id ? '...' : 'Tayyor'}</button></li>)}</ul>
      </article>)}</div>}
  </section>;
}
