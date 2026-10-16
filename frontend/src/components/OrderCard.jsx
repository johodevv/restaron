import React from 'react';
import {
  Clock,
  Phone,
  MapPin,
  User,
  Flame,
  Check,
  CheckCircle2,
  Bike,
  ShoppingBag,
  Receipt,
  CreditCard,
  PackageCheck,
  AlertCircle,
  UtensilsCrossed,
  Tag
} from 'lucide-react';

export const STATUS_CONFIG = {
  pending: {
    label: 'Kutilmoqda',
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    border: 'border-amber-500/40',
    dot: 'bg-amber-400',
  },
  confirmed: {
    label: 'Tasdiqlangan',
    bg: 'bg-blue-500/15',
    text: 'text-blue-400',
    border: 'border-blue-500/40',
    dot: 'bg-blue-400',
  },
  preparing: {
    label: 'Tayyorlanmoqda',
    bg: 'bg-purple-500/15',
    text: 'text-purple-400',
    border: 'border-purple-500/40',
    dot: 'bg-purple-400',
  },
  ready: {
    label: 'Tayyor',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    dot: 'bg-emerald-400',
  },
  served: {
    label: 'Yetkazildi',
    bg: 'bg-cyan-500/15',
    text: 'text-cyan-400',
    border: 'border-cyan-500/40',
    dot: 'bg-cyan-400',
  },
  paid: {
    label: "To'langan",
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-300',
    border: 'border-emerald-500/50',
    dot: 'bg-emerald-300',
  },
  cancelled: {
    label: 'Bekor qilingan',
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    border: 'border-red-500/40',
    dot: 'bg-red-400',
  },
};

/**
 * OrderCard — RestAron Mobil va Desktop Moslashuvchan Buyurtma Kartochkasi.
 * 
 * TALABLAR BO'YICHA AMALGA OSHIRILDI:
 * 1. Zakaz Taomlari Ro'yxati: max-h-48 overflow-y-auto custom-scrollbar flex-wrap
 *    berilib, uzun ro'yxat bo'lsa ham ekrandan chiqmaydi va to'liq o'qiladi.
 * 2. Mobil Action Buttons:
 *    - grid grid-cols-2 gap-2
 *    - px-3 py-2 text-xs sm:text-sm font-medium w-full
 *    - Harakat tugmalari ([✅ Tasdiqlash], [🔥 Oshxonaga], [🧾 Chek], [💳 Kassa])
 *      kartochka tubida aniq va bosishga qulay (min-h-[44px]).
 * 3. w-full overflow-x-hidden orqali gorizontal skrollning oldi olingan.
 */
export const OrderCard = ({
  order,
  onConfirm,
  onUpdateStatus,
  onDeliver,
  onPrint,
  onCheckout,
}) => {
  if (!order) return null;

  const stCfg = STATUS_CONFIG[(order.status || '').toLowerCase()] || STATUS_CONFIG.pending;
  const isDelivery = order.order_type === 'delivery';
  const isTakeaway = order.order_type === 'takeaway';
  const isDineIn = order.order_type === 'dine_in' || !order.order_type;

  const timeStr = order.created_at
    ? new Date(order.created_at).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
    : '--:--';

  const items = order.items || [];
  const itemsCount = items.length > 0 ? items.length : (order.items_count || 1);

  return (
    <div className="p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl glass-card border border-theme-border bg-theme-surface/90 hover:border-theme-primary/40 transition-all flex flex-col justify-between shadow-xl w-full overflow-x-hidden">
      <div>
        {/* ─── Card Header: Order Number, Time, Type & Status ───────────────── */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3 gap-2">
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            <span className="text-base sm:text-lg font-black text-white font-mono tracking-tight shrink-0">
              {order.order_number}
            </span>

            {/* Type badge */}
            <span className="text-[10px] sm:text-[11px] font-extrabold px-2 py-0.5 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1 shrink-0">
              {isDelivery ? (
                <>
                  <Bike className="w-3 h-3 text-cyan-400" />
                  <span>Dastavka</span>
                </>
              ) : isTakeaway ? (
                <>
                  <ShoppingBag className="w-3 h-3 text-amber-400" />
                  <span>Olib ketish</span>
                </>
              ) : (
                <>
                  <UtensilsCrossed className="w-3 h-3 text-emerald-400" />
                  <span>Stol #{order.table_number || order.table_id || '—'}</span>
                </>
              )}
            </span>

            {/* Time */}
            <span className="text-xs text-slate-400 flex items-center gap-1 shrink-0 font-mono">
              <Clock className="w-3 h-3" />
              <span>{timeStr}</span>
            </span>
          </div>

          {/* Status badge */}
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-black border flex items-center gap-1.5 shrink-0 ${stCfg.bg} ${stCfg.text} ${stCfg.border}`}
          >
            <span className={`w-2 h-2 rounded-full ${stCfg.dot} animate-pulse`} />
            <span className="whitespace-nowrap">{stCfg.label}</span>
          </span>
        </div>

        {/* ─── Customer Details (Mijoz, Tel, Manzil) ───────────────────────── */}
        {(order.customer_name || order.customer_phone || order.delivery_address || order.kitchen_note) && (
          <div className="space-y-1.5 mb-3 p-3 rounded-2xl bg-slate-900/80 border border-slate-800/80 text-xs">
            {order.customer_name && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-400 font-semibold flex items-center gap-1.5 shrink-0">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  <span>Mijoz:</span>
                </span>
                <span className="font-extrabold text-white truncate text-right">
                  {order.customer_name}
                </span>
              </div>
            )}

            {order.customer_phone && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-400 font-semibold flex items-center gap-1.5 shrink-0">
                  <Phone className="w-3.5 h-3.5 text-slate-500" />
                  <span>Telefon:</span>
                </span>
                <a
                  href={`tel:${order.customer_phone}`}
                  className="font-black text-cyan-400 font-mono hover:underline"
                >
                  {order.customer_phone}
                </a>
              </div>
            )}

            {isDelivery && order.delivery_address && (
              <div className="pt-1.5 border-t border-slate-800">
                <span className="text-[10px] text-amber-400/90 font-black uppercase flex items-center gap-1 mb-0.5">
                  <MapPin className="w-3.5 h-3.5 shrink-0" />
                  <span>Yetkazish manzili:</span>
                </span>
                <p className="text-xs text-slate-200 font-medium leading-relaxed bg-black/40 p-2 rounded-xl border border-slate-800 break-words">
                  {order.delivery_address}
                </p>
              </div>
            )}

            {order.kitchen_note && (
              <div className="pt-1 text-[11px] text-teal-300 italic border-t border-slate-800/60 truncate">
                💬 Izoh: {order.kitchen_note}
              </div>
            )}
          </div>
        )}

        {/* ─── 1. Zakaz Taomlari Ro'yxati (Order Items List) ─────────────────
            max-h-48 overflow-y-auto custom-scrollbar flex-wrap
            Uzun ro'yxat bo'lsa ham sig'adi, yashirinib qolmaydi!
        ──────────────────────────────────────────────────────────────────── */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1.5 px-0.5">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Tag className="w-3 h-3 text-theme-primary" />
              <span>Taomlar ro'yxati ({itemsCount} ta):</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {items.length > 0 ? `${items.length} xil` : ''}
            </span>
          </div>

          <div className="max-h-48 overflow-y-auto custom-scrollbar overflow-x-hidden rounded-xl bg-slate-950/70 border border-slate-800/80 p-2 space-y-1.5">
            {items.length === 0 ? (
              <div className="p-3 text-center text-xs text-slate-400 italic">
                {order.items_count ? `${order.items_count} ta taom buyurtma qilingan` : "Taomlar ro'yxati mavjud emas"}
              </div>
            ) : (
              items.map((it, idx) => {
                const dishName = it.menu_item_name || it.name || `Taom #${it.menu_item_id || idx + 1}`;
                const itemTotal = it.total_price || ((it.unit_price || 0) * (it.quantity || 1));
                const isItemPrepared = it.is_prepared;

                return (
                  <div
                    key={it.id || idx}
                    className="flex items-start justify-between gap-2 p-1.5 rounded-lg hover:bg-slate-900/60 transition-colors text-xs border-b border-slate-800/40 last:border-b-0"
                  >
                    <div className="flex-1 min-w-0 pr-1">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-bold text-white leading-tight break-words">
                          {dishName}
                        </span>
                        {it.is_weighted && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                            {it.weight ? `${it.weight} ${it.unit || 'kg'}` : 'tortilgan'}
                          </span>
                        )}
                        {it.portion_size && (
                          <span className="text-[10px] font-semibold text-teal-400">
                            ({it.portion_size})
                          </span>
                        )}
                      </div>

                      {it.special_note && (
                        <p className="text-[10px] text-amber-300 italic truncate mt-0.5">
                          "{it.special_note}"
                        </p>
                      )}
                    </div>

                    <div className="text-right shrink-0">
                      <div className="flex items-center justify-end gap-1.5 font-mono">
                        <span className="text-slate-400 font-bold">x{it.quantity || 1}</span>
                        <span className="text-emerald-400 font-bold">
                          {Math.round(itemTotal).toLocaleString('uz-UZ')}
                        </span>
                      </div>
                      {isItemPrepared && (
                        <span className="text-[9px] text-emerald-400 font-bold block">
                          ✓ Tayyor
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ─── Financial Summary: Total Amount ─────────────────────────────── */}
        <div className="flex items-center justify-between mb-3 px-1 py-1 bg-slate-900/50 rounded-xl border border-slate-800/60">
          <span className="text-xs text-slate-300 font-bold">Jami to'lov:</span>
          <span className="text-base sm:text-lg font-black text-emerald-400 font-mono">
            {Math.round(order.total || 0).toLocaleString('uz-UZ')} <span className="text-xs font-normal">so'm</span>
          </span>
        </div>
      </div>

      {/* ─── 2. Mobil Admin Panel & Action Buttons (Responsive Layout) ────────
          - grid grid-cols-2 gap-2
          - px-3 py-2 text-xs sm:text-sm font-medium w-full
          - min-h-[44px] sensorli o'lchamda doim ravshan va qulay
      ──────────────────────────────────────────────────────────────────────── */}
      <div className="pt-3 border-t border-slate-800 space-y-2 shrink-0">
        <div className="grid grid-cols-2 gap-2">
          {/* 1. Pending (Kutilmoqda) holati uchun: [✅ Tasdiqlash] tugmasi */}
          {order.status === 'pending' && onConfirm && (
            <button
              type="button"
              onClick={() => onConfirm(order)}
              className="col-span-2 min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium w-full rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black shadow-lg shadow-emerald-600/25 flex items-center justify-center gap-1.5 active:scale-95 transition-all"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-200" />
              <span>✅ Tasdiqlash</span>
            </button>
          )}

          {/* 2. Oshxonaga yuborish (Preparing) */}
          {order.status === 'pending' && onUpdateStatus && !onConfirm && (
            <button
              type="button"
              onClick={() => onUpdateStatus(order.id, 'preparing')}
              className="min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium w-full rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-extrabold flex items-center justify-center gap-1.5 shadow-md active:scale-95 transition-all"
            >
              <Flame className="w-4 h-4 shrink-0" />
              <span>Oshxonaga</span>
            </button>
          )}

          {/* 3. Tayyor (Ready) holatiga o'tkazish */}
          {order.status === 'preparing' && onUpdateStatus && (
            <button
              type="button"
              onClick={() => onUpdateStatus(order.id, 'ready')}
              className="min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium w-full rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold flex items-center justify-center gap-1.5 shadow-md active:scale-95 transition-all"
            >
              <Check className="w-4 h-4 shrink-0" />
              <span>Tayyor</span>
            </button>
          )}

          {/* 4. Yetkazildi (Served / Delivered) */}
          {(order.status === 'ready' || order.status === 'served') && onDeliver && (
            <button
              type="button"
              onClick={() => onDeliver(order.id)}
              disabled={order.status === 'served'}
              className="min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium w-full rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white font-extrabold flex items-center justify-center gap-1.5 shadow-md active:scale-95 transition-all"
            >
              {isDelivery ? <Bike className="w-4 h-4 shrink-0" /> : <PackageCheck className="w-4 h-4 shrink-0" />}
              <span>{order.status === 'served' ? 'Yetkazilgan' : isDelivery ? 'Yetkazildi' : 'Mijoz oldi'}</span>
            </button>
          )}

          {/* 5. Chek chiqarish (Print receipt) */}
          {onPrint && (
            <button
              type="button"
              onClick={() => onPrint(order.id, order.order_number)}
              className={`min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold flex items-center justify-center gap-1.5 border border-slate-700 active:scale-95 transition-all ${
                order.status !== 'pending' && order.status !== 'preparing' && !onDeliver ? 'col-span-2' : 'w-full'
              }`}
            >
              <Receipt className="w-4 h-4 shrink-0" />
              <span>Chek</span>
            </button>
          )}

          {/* 6. To'lov / Kassa (Checkout) */}
          {!order.is_paid && onCheckout && (
            <button
              type="button"
              onClick={() => onCheckout(order)}
              className="col-span-2 min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium w-full rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black shadow-lg shadow-emerald-600/30 flex items-center justify-center gap-2 active:scale-95 transition-all"
            >
              <CreditCard className="w-4 h-4 shrink-0" />
              <span>To'lovni qabul qilish / Yopish</span>
            </button>
          )}

          {/* 7. To'langan belgisi */}
          {order.is_paid && (
            <div className="col-span-2 min-h-[44px] px-3 py-2 text-xs sm:text-sm font-medium w-full text-center font-black text-emerald-400 bg-emerald-500/10 rounded-xl border border-emerald-500/20 flex items-center justify-center gap-1.5">
              <span>✅ To'langan ({order.payment_method || 'naqd'})</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrderCard;
