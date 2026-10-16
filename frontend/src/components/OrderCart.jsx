import React from 'react';
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
  MapPin
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
 * VAKOLATLARNI AJRATISH (RBAC):
 * - Ofitsiant (waiter) kirganda:
 *   * "To'landi va stolni bo'shatish" (Checkout) tugmasi BUTUNLAY YASHIRILADI.
 *   * Faqat "Buyurtmani tasdiqlash" (Oshxonaga yuborish) tugmasi ko'rinadi.
 * - Admin / Kassir kirganda:
 *   * "To'landi va stolni bo'shatish" (Checkout) tugmasi pastda doimo faol bo'ladi.
 *   * Hisob chekini chiqarish tugmasi ham ko'rinadi.
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

  // Agar propCanCheckout aniq uzatilgan bo'lsa uni olamiz, aks holda foydalanuvchi roliga qaraymiz.
  // FAQAT Admin va Kassir to'lovni qabul qila oladi. Waiter roliga bu ruxsat berilmaydi!
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
    <div className="flex-1 flex flex-col justify-between overflow-hidden bg-slate-900/95 font-sans">
      {/* ── Active Items Table Header & Customer Info ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Takeaway / Delivery Header details if present */}
        {!isDineIn && (customerInfo.name || customerInfo.phone || customerInfo.address) && (
          <div className="px-4 py-2 bg-slate-950 border-b border-slate-800 text-xs text-slate-300 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2 truncate">
              {orderType === 'takeaway' ? (
                <ShoppingBag className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              ) : (
                <Bike className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
              )}
              <span className="font-extrabold text-white truncate">{customerInfo.name || 'Mijoz'}</span>
              {customerInfo.phone && (
                <span className="font-mono text-slate-400 text-[11px] shrink-0">({customerInfo.phone})</span>
              )}
            </div>
            {customerInfo.address && (
              <span className="text-[11px] text-cyan-300 truncate max-w-[170px] ml-2">
                📍 {customerInfo.address}
              </span>
            )}
          </div>
        )}

        {/* Table column headers */}
        <div className="grid grid-cols-12 text-xs font-black text-slate-300 bg-slate-950/80 px-4 py-2.5 border-b border-slate-800 uppercase tracking-wider shrink-0 select-none">
          <span className="col-span-5">Taom nomi</span>
          <span className="col-span-3 text-right">Narxi</span>
          <span className="col-span-2 text-center">Soni</span>
          <span className="col-span-2 text-right">Jami</span>
        </div>

        {/* ── Items List ── */}
        <div className="flex-1 overflow-y-auto">
          {orderLoading ? (
            <div className="p-10 text-center text-sm font-bold text-slate-400">Yuklanmoqda...</div>
          ) : items.length === 0 ? (
            <div className="p-10 text-center text-slate-400 space-y-1">
              <p className="font-extrabold text-white text-base">Ushbu buyurtmada hali taom yo'q</p>
              <p className="text-xs text-slate-400">O'ng tomondagi menyudan taomlarni bosing</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {items.map((it) => {
                const priced = isItemPriced(it);
                const unitPrice = it.unit_price || it.price || 0;
                const lineTotal = it.total_price || (unitPrice * (it.quantity || 1));

                return (
                  <div
                    key={it.id}
                    className="grid grid-cols-12 items-center px-4 py-2.5 hover:bg-slate-800/50 transition-colors"
                  >
                    {/* Item Name & Meta Buttons */}
                    <div className="col-span-5 pr-1">
                      <p className="font-extrabold text-white text-xs sm:text-sm leading-snug">
                        {it.menu_item_name || it.name || 'Taom'}
                      </p>

                      {/* Weighted Item Price Input Trigger */}
                      {it.is_weighted && (
                        <button
                          type="button"
                          onClick={() => onOpenWeightModal && onOpenWeightModal(it)}
                          title="Summasini kiritish"
                          className={`mt-1 px-2 py-0.5 rounded-lg text-[10px] font-black transition-all active:scale-95 block ${
                            priced
                              ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                              : 'bg-red-600 text-white border border-red-400 animate-pulse'
                          }`}
                        >
                          {priced
                            ? `💰 ${Math.round(lineTotal).toLocaleString('uz-UZ')} so'm` +
                              (it.weight ? ` · ${it.weight} ${it.unit || 'kg'}` : '')
                            : '💰 NARXI YO\'Q — bosing!'}
                        </button>
                      )}

                      {/* Size / Volume Trigger */}
                      {!it.is_weighted && (
                        <button
                          type="button"
                          onClick={() => onOpenSizeModal && onOpenSizeModal(it)}
                          title="Taom hajmi yoki porsiyasini belgilash"
                          className="mt-0.5 text-[10px] text-teal-400 hover:text-teal-300 font-bold block truncate"
                        >
                          {it.portion_size || it.size_or_volume ? `📏 ${it.portion_size || it.size_or_volume}` : "+ o'lcham"}
                        </button>
                      )}

                      {/* Status indicator: Oshxonaga yuborilgan / yangi */}
                      <p className="text-[10px] font-semibold text-slate-400 font-mono mt-0.5">
                        {(() => {
                          const sent = Math.min(it.sent_quantity || 0, it.quantity);
                          const fresh = Math.max((it.quantity || 0) - sent, 0);
                          if (sent > 0 && fresh > 0) {
                            return (
                              <>
                                <span className="text-amber-400 font-bold">{sent} ♨️</span>
                                {' · '}
                                <span className="text-emerald-400 font-bold">{fresh} yangi ✦</span>
                              </>
                            );
                          }
                          return (
                            <span className={sent > 0 ? 'text-amber-400 font-bold' : 'text-emerald-400'}>
                              {sent > 0 ? 'Oshxonada ♨️' : 'Yangi ✦'}
                            </span>
                          );
                        })()}
                      </p>

                      {/* Kitchen special note */}
                      {it.special_note && (
                        <p className="text-[10px] text-amber-300 font-semibold truncate mt-0.5">
                          💬 {it.special_note}
                        </p>
                      )}
                    </div>

                    {/* Unit Price */}
                    <div className="col-span-3 text-right font-mono text-xs text-slate-300">
                      {Math.round(unitPrice).toLocaleString('uz-UZ')}
                    </div>

                    {/* Quantity controls [- 1 +] */}
                    <div className="col-span-2 flex items-center justify-center gap-1">
                      <button
                        type="button"
                        onClick={() => onUpdateQuantity && onUpdateQuantity(it, -1)}
                        className="w-7 h-7 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white font-black flex items-center justify-center text-sm transition-transform active:scale-90"
                        title="Kamaytirish"
                      >
                        -
                      </button>
                      <span className="font-mono text-xs sm:text-sm font-black text-white w-5 text-center">
                        {it.quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => onUpdateQuantity && onUpdateQuantity(it, 1)}
                        className="w-7 h-7 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white font-black flex items-center justify-center text-sm transition-transform active:scale-90"
                        title="Ko'paytirish"
                      >
                        +
                      </button>
                    </div>

                    {/* Total Price & Delete button */}
                    <div className="col-span-2 flex items-center justify-end gap-1.5 font-mono text-xs font-bold text-white">
                      <span>{Math.round(lineTotal).toLocaleString('uz-UZ')}</span>
                      <button
                        type="button"
                        onClick={() => onRemoveItem && onRemoveItem(it.id)}
                        className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="O'chirish"
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
      </div>

      {/* ── Cart Bottom: Summary & Action Buttons ── */}
      <div className="p-4 bg-slate-950 border-t border-slate-800 shrink-0 shadow-2xl">
        {/* Kitchen send success notification */}
        {kitchenSendSuccess && (
          <div className="p-2.5 mb-2.5 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-black text-xs text-center flex items-center justify-center gap-2 animate-bounce-subtle">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>✅ Buyurtma oshxona printerlariga chiqarildi!</span>
          </div>
        )}

        {/* Warning if unpriced weighted items exist */}
        {hasUnpricedWeighted && (
          <div className="p-2.5 mb-2.5 rounded-xl bg-red-950/80 border border-red-600 text-red-200 font-bold text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>Narxi kiritilmagan tarozidagi taom bor. Summasini yozing!</span>
          </div>
        )}

        {/* Subtotal, Service fee, Total */}
        <div className="space-y-1 mb-3 bg-slate-900/70 p-3 rounded-2xl border border-slate-800">
          <div className="flex justify-between text-xs text-slate-300">
            <span className="font-semibold">Taomlar jami:</span>
            <span className="font-bold text-white font-mono">
              {Math.round(subtotal).toLocaleString('uz-UZ')} so'm
            </span>
          </div>
          {isDineIn && (
            <div className="flex justify-between text-xs text-slate-300">
              <span className="font-semibold">Xizmat haqi ({serviceFeePercent}%):</span>
              <span className="font-bold text-amber-300 font-mono">
                {Math.round(serviceFeeAmount).toLocaleString('uz-UZ')} so'm
              </span>
            </div>
          )}
          <div className="flex justify-between text-sm sm:text-base font-black text-white pt-1.5 border-t border-slate-800">
            <span>Jami hisob:</span>
            <span className="text-emerald-400 text-lg sm:text-xl font-mono">
              {Math.round(total).toLocaleString('uz-UZ')} so'm
            </span>
          </div>
        </div>

        {/* Kitchen Note */}
        <div className="mb-2.5">
          <button
            type="button"
            onClick={onOpenKitchenNote}
            className="w-full py-2 px-3 rounded-xl bg-teal-600/15 hover:bg-teal-600/25 border border-teal-500/30 text-teal-300 font-bold text-xs transition-all truncate text-left flex items-center justify-between"
          >
            <span>💬 Oshxona izohi {kitchenNote ? `("${kitchenNote}")` : ''}</span>
            <span className="text-[10px] text-teal-400 underline">Tahrirlash</span>
          </button>
        </div>

        {/* ── Action Buttons ── */}
        <div className="grid grid-cols-1 gap-2">
          {/* Oshxonaga yuborish (Buyurtmani tasdiqlash) — Barcha rollar (Waiters, Cashiers, Admins) */}
          <button
            type="button"
            onClick={onSendToKitchen}
            disabled={!order || items.length === 0 || sendingToKitchen}
            className="w-full py-3.5 px-3 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs sm:text-sm shadow-xl shadow-amber-500/20 transition-all active:scale-95 flex items-center justify-center gap-1.5"
          >
            <Printer className="w-4 h-4 shrink-0" />
            <span>{sendingToKitchen ? 'Chop etilmoqda...' : '🔥 Buyurtmani tasdiqlash'}</span>
          </button>

          {/* 
            CRITICAL ROLE-BASED ACCESS CONTROL (RBAC):
            "To'landi va stolni bo'shatish" (Checkout) tugmasi
            FAKAT Admin yoki Kassir rolida ko'rinadi. 
            Ofitsiant rolida (waiter) bu tugma BUTUNLAY YASHIRILADI.
          */}
          {canCheckout && (
            <button
              type="button"
              onClick={onCheckout}
              disabled={!order || items.length === 0}
              className="w-full py-3.5 px-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 disabled:opacity-40 text-white font-black text-xs sm:text-sm shadow-xl shadow-emerald-600/30 transition-all active:scale-95 flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span>To'landi va stolni bo'shatish</span>
            </button>
          )}

          {/* Admin / Kassir hisob chekini chiqarish */}
          {canCheckout && onPrintBill && (
            <button
              type="button"
              onClick={onPrintBill}
              disabled={!order || items.length === 0 || printingBill}
              className="w-full py-2.5 px-3 rounded-xl bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 disabled:opacity-40 text-sky-300 font-bold text-xs transition-all active:scale-95 flex items-center justify-center gap-1.5"
            >
              <Receipt className="w-3.5 h-3.5 shrink-0" />
              <span>{printingBill ? 'Chop etilmoqda...' : '🧾 Hisob chekini chiqarish'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrderCart;
