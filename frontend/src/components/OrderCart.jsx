import React, { useState } from 'react';
import {
  Printer,
  Receipt,
  CheckCircle2,
  Trash2,
  Plus,
  Minus,
  MessageSquare,
  AlertTriangle,
  ShoppingBag,
  Bike,
  UtensilsCrossed,
  User,
  Phone,
  MapPin,
  X,
  Hash
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const isItemPriced = (item) => {
  if (!item) return true;
  if (!item.is_weighted) return true;
  if (item.manual_price !== null && item.manual_price !== undefined) return true;
  if (item.weight && item.weight > 0 && item.total_price && item.total_price > 0) return true;
  return false;
};

/**
 * OrderCart — RestAron Faol Buyurtma Savati.
 * 
 * MOBIL VA DESKTOP RESPONSIVE XUSUSIYATLARI:
 * 1. Taomlar ro'yxati: max-h-48 (mobilda) / custom-scrollbar orqali skroll bo'ladi,
 *    ekrandan oshib ketmaydi va pastki tugmalarni siqib chiqarmaydi.
 * 2. Tugmalar: min-h-[44px] standart sensorli o'lchamda, mobilda grid-cols-1 / sm:grid-cols-2
 *    ko'rinishida to'liq ko'rinadi va bosishga qulay joylashadi.
 * 3. Vakolatlarni ajratish (RBAC):
 *    - Ofitsiantda Checkout tugmasi yashirin.
 *    - Admin va Kassirda "To'landi va stolni bo'shatish" va "Hisob chekini chiqarish" faol.
 */
export const OrderCart = ({
  order,
  table,
  orderType = 'dine_in',
  customerInfo = {},
  orderLoading = false,
  sendingToKitchen = false,
  printingBill = false,
  canCheckout: propCanCheckout,
  onSendToKitchen,
  onPrintBill,
  onCheckout,
  onUpdateQuantity,
  onRemoveItem,
  onOpenWeightModal,
  onOpenSizeModal,
  onOpenKitchenNote,
  kitchenNote = '',
  kitchenSendSuccess = false,
}) => {
  const { user, isAdmin, isCashier, canCheckout: authCanCheckout } = useAuth();
  const [qtyModalItem, setQtyModalItem] = useState(null);
  const [qtyInput, setQtyInput] = useState('');

  // Rolga qarab Checkout ruxsati
  const isPrivileged = user?.role === 'admin' || user?.role === 'cashier' || user?.role === 'developer';
  const canCheckout = propCanCheckout !== undefined
    ? propCanCheckout
    : (authCanCheckout || isAdmin || isCashier || isPrivileged);

  const items = order?.items || [];
  const hasUnpricedWeighted = items.some((i) => i.is_weighted && !isItemPriced(i));

  const subtotal = order?.subtotal || items.reduce((acc, it) => acc + (it.total_price || (it.price || it.unit_price || 0) * it.quantity), 0);
  const isDineIn = orderType === 'table' || orderType === 'dine_in';
  const serviceFeePercent = order?.service_fee_percent !== undefined ? order.service_fee_percent : (isDineIn ? 12 : 0);
  const serviceFeeAmount = order?.service_fee_amount !== undefined ? order.service_fee_amount : (subtotal * serviceFeePercent / 100);
  const total = order?.total || (subtotal + serviceFeeAmount);

  return (
    <div className="h-full w-full flex flex-col bg-slate-900/95 font-sans overflow-hidden select-none">
      {/* ── Active Items Table Header & Customer Info ── */}
      <div className="flex-1 overflow-y-auto custom-scrollbar overflow-x-hidden min-h-0 flex flex-col">
        {/* Takeaway / Delivery Header details if present */}
        {!isDineIn && (customerInfo.name || customerInfo.phone || customerInfo.address) && (
          <div className="px-3 sm:px-4 py-2 bg-slate-950 border-b border-slate-800 text-xs sm:text-sm text-slate-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2 truncate">
              {orderType === 'takeaway' ? (
                <ShoppingBag className="w-4 h-4 text-amber-400 shrink-0" />
              ) : (
                <Bike className="w-4 h-4 text-cyan-400 shrink-0" />
              )}
              <span className="font-extrabold text-white truncate text-xs sm:text-sm">{customerInfo.name || 'Mijoz'}</span>
              {customerInfo.phone && (
                <span className="font-mono text-slate-400 text-xs shrink-0">({customerInfo.phone})</span>
              )}
            </div>
            {customerInfo.address && (
              <span className="text-xs text-cyan-300 truncate max-w-[150px] sm:max-w-[200px] ml-2">
                📍 {customerInfo.address}
              </span>
            )}
          </div>
        )}

        {/* Table column headers (Ofitsiant paneli andozasida) */}
        <div className="grid grid-cols-12 text-xs sm:text-sm font-black text-slate-300 bg-slate-950/70 px-3 sm:px-4 py-2 border-b border-slate-800 uppercase tracking-wider shrink-0 select-none">
          <span className="col-span-5">Taom nomi</span>
          <span className="col-span-2 text-right">Narxi</span>
          <span className="col-span-2 text-center">Soni</span>
          <span className="col-span-2 text-right">Jami</span>
          <span className="col-span-1 text-center"></span>
        </div>

        {/* ── Items List: Ofitsiant paneli kabi qulay va aniq ── */}
        {orderLoading ? (
          <div className="p-8 text-center text-xs sm:text-sm font-bold text-slate-400">Yuklanmoqda...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-slate-400 space-y-1">
            <p className="font-extrabold text-white text-sm sm:text-base">Ushbu buyurtmada hali taom yo'q</p>
            <p className="text-xs text-slate-400">O'ng tomondagi menyudan taomlarni tanlang</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {items.map((it) => {
              const priced = isItemPriced(it);
              const unitPrice = it.unit_price || it.price || 0;
              const lineTotal = it.total_price || (unitPrice * (it.quantity || 1));
              const sent = Math.min(it.sent_quantity || 0, it.quantity || 1);
              const fresh = Math.max((it.quantity || 1) - sent, 0);

              return (
                <div
                  key={it.id}
                  className="grid grid-cols-12 items-center px-2.5 sm:px-3 py-1.5 hover:bg-slate-800/50 transition-colors"
                >
                  {/* Name & time & status */}
                  <div className="col-span-5 pr-1 min-w-0">
                    <p className="font-extrabold text-white text-xs sm:text-sm leading-tight truncate">
                      {it.menu_item_name || it.name || 'Taom'}
                    </p>

                    <div className="flex items-center gap-1 flex-wrap mt-0.5 text-[10px] sm:text-[11px] font-semibold text-slate-400 font-mono leading-none">
                      {/* Tortiladigan taom (baliq, go'sht): SUMMASI */}
                      {it.is_weighted && (
                        <button
                          type="button"
                          onClick={() => onOpenWeightModal && onOpenWeightModal(it)}
                          title="Summasini kiritish"
                          className={`px-1.5 py-0.5 rounded text-[10px] font-black transition-all active:scale-95 inline-block ${priced
                              ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                              : 'bg-red-600 text-white border border-red-400 animate-pulse'
                            }`}
                        >
                          {priced
                            ? `💰 ${Math.round(lineTotal).toLocaleString('uz-UZ')}` +
                            (it.weight ? `·${it.weight}${it.unit || 'kg'}` : '')
                            : "💰 Narx yo'q"}
                        </button>
                      )}

                      {/* O'lchanadigan taom hajmi */}
                      {!it.is_weighted && (
                        <button
                          type="button"
                          onClick={() => onOpenSizeModal && onOpenSizeModal(it)}
                          title="Hajm / o'lchamni kiritish"
                          className={`px-1.5 py-0.5 rounded text-[10px] font-black transition-all active:scale-95 inline-block ${it.portion_size
                              ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50'
                              : 'bg-slate-800 text-slate-400 border border-dashed border-slate-600 hover:text-amber-300'
                            }`}
                        >
                          {it.portion_size ? `📏 ${it.portion_size}` : "📏 Hajm"}
                        </button>
                      )}

                      <span>{it.item_time || '12:00'}</span>
                      <span>•</span>
                      {sent > 0 && fresh > 0 ? (
                        <>
                          <span className="text-amber-400 font-bold">{sent}♨️</span>
                          <span>·</span>
                          <span className="text-emerald-400 font-bold">{fresh}✦</span>
                        </>
                      ) : sent > 0 ? (
                        <span className="text-amber-400 font-bold">Oshxonada♨️</span>
                      ) : (
                        <span className="text-emerald-400 font-bold">Yangi✦</span>
                      )}
                    </div>
                  </div>

                  {/* Narxi */}
                  <div className="col-span-2 text-right font-bold text-slate-300 text-xs sm:text-sm font-mono truncate">
                    {Math.round(unitPrice).toLocaleString('uz-UZ')}
                  </div>

                  {/* Soni [- 1 +] */}
                  <div className="col-span-2 flex items-center justify-center gap-0.5">
                    <button
                      type="button"
                      onClick={() => onUpdateQuantity && onUpdateQuantity(it, -1)}
                      className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-xs active:scale-90 shadow-sm shrink-0"
                      title="Kamaytirish"
                    >
                      -
                    </button>
                    <span
                      onClick={() => {
                        setQtyModalItem(it);
                        setQtyInput(String(it.quantity || 1));
                      }}
                      className="text-xs sm:text-sm font-black text-white w-4 sm:w-5 text-center font-mono cursor-pointer hover:bg-slate-800 rounded py-0.5 select-none shrink-0"
                      title="Sonini kiritish uchun bosing"
                    >
                      {it.quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => onUpdateQuantity && onUpdateQuantity(it, 1)}
                      className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-xs active:scale-90 shadow-sm shrink-0"
                      title="Ko'paytirish"
                    >
                      +
                    </button>
                  </div>

                  {/* Jami narxi */}
                  <div className="col-span-2 text-right font-black text-emerald-400 text-xs sm:text-sm font-mono truncate">
                    {Math.round(lineTotal).toLocaleString('uz-UZ')}
                  </div>

                  {/* O'chirish (Trash) */}
                  <div className="col-span-1 flex justify-end">
                    <button
                      type="button"
                      onClick={() => onRemoveItem && onRemoveItem(it.id)}
                      className="p-1 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 active:scale-90 transition-all"
                      title="Taomni o'chirish"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Cart Bottom: Summary & Action Buttons (Doimo ko'rinib turadi, maksimal ixcham) ── */}
      <div className="p-2 sm:p-2.5 bg-slate-950 border-t border-slate-800 shadow-2xl space-y-1 shrink-0">
        {/* Bildirishnoma: Oshxonaga avtomatik chop etildi */}
        {kitchenSendSuccess && (
          <div className="p-1 mb-0.5 rounded-lg bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-bold text-xs text-center flex items-center justify-center gap-1.5 animate-bounce-subtle">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>✅ Buyurtma oshxonaga chop etildi!</span>
          </div>
        )}

        {/* Narxi kiritilmagan taom ogohlantirishi */}
        {hasUnpricedWeighted && (
          <div className="p-1 mb-0.5 rounded-lg bg-red-950/70 border border-red-600 text-red-200 font-bold text-[11px] flex items-center gap-1">
            <span className="text-xs shrink-0 leading-none">💰</span>
            <span className="truncate">Narxi kiritilmagan taom bor!</span>
          </div>
        )}

        {/* Subtotal & Service fee & Total compact summary (Ixcham 2 qator) */}
        <div className="bg-slate-900/80 px-2.5 py-1.5 rounded-xl border border-slate-800 text-xs">
          <div className="flex items-center justify-between text-slate-300 pb-1 border-b border-slate-800/80 text-[11px] sm:text-xs font-medium">
            <span>Taomlar: <strong className="text-white font-mono">{Math.round(subtotal).toLocaleString('uz-UZ')}</strong></span>
            {isDineIn && (
              <span>Xizmat ({serviceFeePercent}%): <strong className="text-amber-300 font-mono">{Math.round(serviceFeeAmount).toLocaleString('uz-UZ')}</strong></span>
            )}
          </div>
          <div className="flex items-center justify-between pt-1">
            <span className="font-black text-white text-xs uppercase tracking-wider">Jami hisob:</span>
            <span className="text-emerald-400 text-base sm:text-lg font-mono font-black">
              {Math.round(total).toLocaleString('uz-UZ')} so'm
            </span>
          </div>
        </div>

        {/* ── Action Buttons: 2x2 ixcham grid ── */}
        <div className="grid grid-cols-2 gap-1.5 pt-0.5">
          {/* Oshxonaga yuborish (Buyurtmani tasdiqlash) */}
          <button
            type="button"
            onClick={onSendToKitchen}
            disabled={!order || items.length === 0 || sendingToKitchen}
            className={`min-h-[38px] py-1 px-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs sm:text-sm shadow-md transition-all active:scale-95 flex items-center justify-center gap-1.5 ${!canCheckout ? 'col-span-2' : ''}`}
          >
            <Printer className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">{sendingToKitchen ? 'Chop...' : '🔥 Tasdiqlash'}</span>
          </button>

          {/* To'landi va stolni bo'shatish (Checkout) — FAKAT Admin / Kassir */}
          {canCheckout && (
            <button
              type="button"
              onClick={onCheckout}
              disabled={!order || items.length === 0}
              className="min-h-[38px] py-1 px-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-black text-xs sm:text-sm shadow-md transition-all active:scale-95 flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">✅ To'landi</span>
            </button>
          )}

          {/* Oshxona izohi */}
          <button
            type="button"
            onClick={onOpenKitchenNote}
            className={`min-h-[32px] py-1 px-2 rounded-xl bg-teal-600/20 hover:bg-teal-600/30 border border-teal-500/40 text-teal-300 font-bold text-[11px] sm:text-xs transition-all truncate flex items-center justify-center gap-1 ${!canCheckout ? 'col-span-2' : ''}`}
          >
            <span>💬 Izoh</span>
            {kitchenNote && <span className="text-teal-200">✓</span>}
          </button>

          {/* Admin / Kassir hisob chekini chiqarish */}
          {canCheckout && onPrintBill && (
            <button
              type="button"
              onClick={onPrintBill}
              disabled={!order || items.length === 0 || printingBill}
              className="min-h-[32px] py-1 px-2 rounded-xl bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 disabled:opacity-40 text-sky-300 font-bold text-[11px] sm:text-xs transition-all active:scale-95 flex items-center justify-center gap-1"
            >
              <Receipt className="w-3 h-3 shrink-0" />
              <span className="truncate">{printingBill ? 'Chop...' : '🧾 Chek'}</span>
            </button>
          )}
        </div>
      </div>

      {/* ── ALIPOSTER TEZKOR SENSORLI NUMPAD MODALI ── */}
      {qtyModalItem && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-3 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-xs w-full p-5 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-1.5 min-w-0 pr-2">
                <Hash className="w-4 h-4 text-emerald-400 shrink-0" />
                <h4 className="text-white font-extrabold text-sm truncate">
                  {qtyModalItem.menu_item_name || qtyModalItem.name || 'Taom soni'}
                </h4>
              </div>
              <button
                type="button"
                onClick={() => setQtyModalItem(null)}
                className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Raqam oynasi */}
            <div className="mb-3 text-center">
              <span className="text-[11px] text-slate-400 block font-bold mb-1">Buyurtma miqdori:</span>
              <div className="text-3xl font-black font-mono text-emerald-400 bg-slate-950 py-2.5 rounded-2xl border border-slate-800 flex items-center justify-center gap-1.5">
                <span>{qtyInput || '0'}</span>
                <span className="text-xs text-slate-400 font-sans font-medium">{qtyModalItem.unit || 'ta'}</span>
              </div>
            </div>

            {/* Tezkor qo'shish tugmalari (+1, +2, +5, +10) */}
            <div className="grid grid-cols-4 gap-1.5 mb-3">
              {[1, 2, 5, 10].map((inc) => (
                <button
                  key={inc}
                  type="button"
                  onClick={() => setQtyInput(String((parseInt(qtyInput, 10) || 0) + inc))}
                  className="py-1 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-mono font-bold text-amber-300 border border-slate-700 active:scale-95 transition-all"
                >
                  +{inc}
                </button>
              ))}
            </div>

            {/* Sensorli kalkulyator klaviaturasi */}
            <div className="grid grid-cols-3 gap-1.5 mb-4">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
                <button
                  key={digit}
                  type="button"
                  onClick={() => setQtyInput((prev) => (prev === '0' || prev === '' ? String(digit) : `${prev}${digit}`))}
                  className="h-11 rounded-xl bg-slate-800 hover:bg-slate-700 text-base font-mono font-black text-white active:scale-95 transition-all shadow-sm"
                >
                  {digit}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setQtyInput('')}
                className="h-11 rounded-xl bg-red-950/60 hover:bg-red-900/60 text-red-300 font-bold text-xs active:scale-95 transition-all"
              >
                C
              </button>
              <button
                type="button"
                onClick={() => setQtyInput((prev) => (prev === '0' || prev === '' ? '0' : `${prev}0`))}
                className="h-11 rounded-xl bg-slate-800 hover:bg-slate-700 text-base font-mono font-black text-white active:scale-95 transition-all"
              >
                0
              </button>
              <button
                type="button"
                onClick={() => setQtyInput((prev) => (prev.length > 0 ? prev.slice(0, -1) : ''))}
                className="h-11 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-base active:scale-95 transition-all"
              >
                ⌫
              </button>
            </div>

            {/* Tasdiqlash / Bekor */}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setQtyModalItem(null)}
                className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 transition-colors"
              >
                Bekor
              </button>
              <button
                type="button"
                onClick={() => {
                  const targetQty = parseInt(qtyInput, 10);
                  if (!isNaN(targetQty) && targetQty > 0) {
                    const delta = targetQty - qtyModalItem.quantity;
                    if (delta !== 0 && onUpdateQuantity) {
                      onUpdateQuantity(qtyModalItem, delta);
                    }
                  } else if (targetQty === 0 && onRemoveItem) {
                    onRemoveItem(qtyModalItem.id);
                  }
                  setQtyModalItem(null);
                }}
                className="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-black text-xs text-white shadow-md shadow-emerald-600/30 active:scale-95 transition-all"
              >
                Saqlash
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OrderCart;
