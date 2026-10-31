import React from 'react';
import { ShoppingBag, Bike, Plus, User, Clock } from 'lucide-react';
import { openCounterOrders } from '../utils/counterOrders';

export default function CounterOrderPicker({ orders, type, label, onCreate, onSelect, loading, openingOrderId, disabled }) {
  const Icon = type === 'delivery' ? Bike : ShoppingBag;
  const title = label(type === 'delivery' ? 'Yetkazib berish' : 'Olib ketish');
  const matches = openCounterOrders(orders, type);
  return <section aria-label={title} className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4" data-testid="counter-order-picker">
    <h1 className="text-xl font-bold mb-4">{title} <span className="text-sm text-slate-400">({matches.length})</span></h1>
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 items-stretch">
      <button type="button" onClick={onCreate} disabled={disabled || openingOrderId != null} className="min-h-[180px] rounded-2xl border-2 border-emerald-500 bg-slate-900 text-emerald-300 flex flex-col items-center justify-center gap-4 p-4 font-bold hover:bg-emerald-900/30 disabled:opacity-50">
        <span className="relative p-4 rounded-full bg-emerald-600 text-white"><Icon size={32} /><Plus size={16} className="absolute bottom-2 right-2" /></span>
        {label('Yangi buyurtma')}
      </button>
      {matches.map(order => {
        const date = new Date(order.created_at);
        const dateText = Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        return <button key={order.id} type="button" disabled={disabled || openingOrderId != null} onClick={() => onSelect(order)} aria-busy={openingOrderId === order.id} className="min-h-[180px] rounded-2xl border border-slate-600 bg-slate-800 overflow-hidden text-left flex flex-col hover:border-emerald-400 disabled:opacity-50" data-order-id={order.id}>
          <div className="px-4 py-2 bg-emerald-800/60 font-bold break-words">{order.order_number || `#${order.id}`}</div>
          <div className="p-4 flex-1 space-y-2">
            <span className="flex items-center gap-2 text-xs text-slate-300"><Clock size={14} />{dateText}</span>
            {order.customer_name && <span className="block text-sm truncate">{order.customer_name}</span>}
            <strong className="block text-right text-xl font-mono text-emerald-300">{Number(order.total || 0).toLocaleString('uz-UZ')} <small className="text-xs">{label("so'm")}</small></strong>
          </div>
          <div className="px-4 py-2 border-t border-slate-600 flex items-center gap-2 text-sm text-slate-300"><User size={16} /><span className="truncate">{openingOrderId === order.id ? label('Hisob yuklanmoqda...') : order.waiter_name || '—'}</span></div>
        </button>;
      })}
    </div>
    {loading && <p role="status" className="mt-4 text-slate-400 text-sm">{label('Yuklanmoqda...')}</p>}
  </section>;
}
