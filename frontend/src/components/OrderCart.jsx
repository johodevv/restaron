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
    <div className="flex-1 flex flex-col justify-between overflow-hidden bg-slate-900/95 font-sans w-full">
      {/* ── Active Items Table Header & Customer Info ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        {/* Takeaway / Delivery Header details if present */}
        {!isDineIn && (customerInfo.name || customerInfo.phone || customerInfo.address) && (
          <div className="px-3 sm:px-4 py-2 bg-slate-950 border-b border-slate-800 text-xs text-slate-300 flex items-center justify-between shrink-0">
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
              <span className="text-[11px] text-cyan-300 truncate max-w-[140px] sm:max-w-[180px] ml-2">
                📍 {customerInfo.address}
              </span>
            )}
          </div>
        )}

        {/* Table column headers (Desktop / Tablet) */}
        <div className="hidden sm:grid grid-cols-12 text-xs font-black text-slate-300 bg-slate-950/90 px-4 py-2 border-b border-slate-800 uppercase tracking-wider shrink-0 select-none">
          <span className="col-span-4">Taom nomi</span>
          <span className="col-span-2 text-right">Narxi</span>
          <span className="col-span-3 text-center">Soni</span>
          <span className="col-span-3 text-right">Jami</span>
        </div>

        {/* ── Items List: Mobil ekranda max-h-44 sm:max-h-56, skrollanadigan custom-scrollbar ── */}
        <div className="max-h-44 sm:max-h-60 lg:max-h-[calc(100vh-420px)] lg:flex-1 overflow-y-auto custom-scrollbar overflow-x-hidden">
          {orderLoading ? (
            <div className="p-6 text-center text-xs sm:text-sm font-bold text-slate-400">Yuklanmoqda...</div>
          ) : items.length === 0 ? (
            <div className="p-5 text-center text-slate-400 space-y-1">
              <p className="font-extrabold text-white text-xs sm:text-sm">Ushbu buyurtmada hali taom yo'q</p>
              <p className="text-[11px] text-slate-400">Menyudan taomlarni tanlang</p>
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
                    className="p-2 sm:px-4 sm:py-2 hover:bg-slate-800/50 transition-colors"
                  >
                    {/* Mobil ko'rinish (sm dan kichik ekranlar): 2 qatorli qulay tartib */}
                    <div className="sm:hidden space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-white text-xs leading-snug break-words">
                            {it.menu_item_name || it.name || 'Taom'}
                          </p>
                          <div className="flex items-center gap-1.5 flex-wrap mt-0.5">
                            {/* Weighted trigger */}
                            {it.is_weighted && (
                              <button
                                type="button"
                                onClick={() => onOpenWeightModal && onOpenWeightModal(it)}
                                className={`px-1.5 py-0.5 rounded text-[9px] font-black leading-none ${
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

                            {/* Size trigger */}
                            {!it.is_weighted && (
                              <button
                                type="button"
                                onClick={() => onOpenSizeModal && onOpenSizeModal(it)}
                                className="text-[9px] text-teal-400 hover:text-teal-300 font-bold"
                              >
                                {it.portion_size || it.size_or_volume ? `📏 ${it.portion_size || it.size_or_volume}` : "+ o'lcham"}
                              </button>
                            )}

                            {/* Status */}
                            <span className="text-[9px] font-semibold text-slate-400 font-mono">
                              {(it.sent_quantity || 0) > 0 ? '♨️ Oshxonada' : '✦ Yangi'}
                            </span>
                          </div>
                        </div>

                        {/* Delete button */}
                        <button
                          type="button"
                          onClick={() => onRemoveItem && onRemoveItem(it.id)}
                          className="p-1 rounded text-slate-500 hover:text-red-400 shrink-0"
                          title="O'chirish"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Mobil pastki qator: [Narx] | [- 1 +] | [Jami] */}
                      <div className="flex items-center justify-between pt-1 border-t border-slate-800/40 text-xs">
                        <span className="font-mono text-[11px] text-slate-400">
                          {Math.round(unitPrice).toLocaleString('uz-UZ')} so'm
                        </span>

                        <div className="flex items-center gap-1.5 bg-slate-950 px-2 py-0.5 rounded-lg border border-slate-800">
                          <button
                            type="button"
                            onClick={() => onUpdateQuantity && onUpdateQuantity(it, -1)}
                            className="w-5 h-5 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-black flex items-center justify-center text-xs active:scale-90"
                          >
                            -
                          </button>
                          <span className="font-mono text-xs font-black text-white w-4 text-center">
                            {it.quantity}
                          </span>
                          <button
                            type="button"
                            onClick={() => onUpdateQuantity && onUpdateQuantity(it, 1)}
                            className="w-5 h-5 rounded bg-emerald-700 hover:bg-emerald-600 text-white font-black flex items-center justify-center text-xs active:scale-90"
                          >
                            +
                          </button>
                        </div>

                        <span className="font-mono font-bold text-emerald-400 text-xs">
                          {Math.round(lineTotal).toLocaleString('uz-UZ')} so'm
                        </span>
                      </div>
                    </div>

                    {/* Desktop ko'rinish (sm va undan katta ekranlar): To'liq grid */}
                    <div className="hidden sm:grid grid-cols-12 items-center gap-2">
                      {/* Item Name & Meta Buttons */}
                      <div className="col-span-4 pr-1 min-w-0">
                        <p className="font-bold text-white text-xs sm:text-sm leading-tight break-words">
                          {it.menu_item_name || it.name || 'Taom'}
                        </p>

                        {/* Weighted Item Price Input Trigger */}
                        {it.is_weighted && (
                          <button
                            type="button"
                            onClick={() => onOpenWeightModal && onOpenWeightModal(it)}
                            title="Summasini kiritish"
                            className={`mt-1 px-1.5 py-0.5 rounded-lg text-[9px] sm:text-[10px] font-black transition-all active:scale-95 block leading-tight ${
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
                            className="mt-0.5 text-[9px] sm:text-[10px] text-teal-400 hover:text-teal-300 font-bold block truncate"
                          >
                            {it.portion_size || it.size_or_volume ? `📏 ${it.portion_size || it.size_or_volume}` : "+ o'lcham"}
                          </button>
                        )}

                        {/* Status indicator */}
                        <p className="text-[9px] sm:text-[10px] font-semibold text-slate-400 font-mono mt-0.5">
                          {(it.sent_quantity || 0) > 0 ? '♨️ Oshxonada' : '✦ Yangi'}
                        </p>
                      </div>

                      {/* Unit Price */}
                      <div className="col-span-2 text-right font-mono text-xs text-slate-300 whitespace-nowrap">
                        {Math.round(unitPrice).toLocaleString('uz-UZ')}
                      </div>

                      {/* Quantity controls [- 1 +] */}
                      <div className="col-span-3 flex items-center justify-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => onUpdateQuantity && onUpdateQuantity(it, -1)}
                          className="w-6 h-6 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white font-black flex items-center justify-center text-xs transition-transform active:scale-90 shrink-0"
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
                          className="w-6 h-6 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white font-black flex items-center justify-center text-xs transition-transform active:scale-90 shrink-0"
                          title="Ko'paytirish"
                        >
                          +
                        </button>
                      </div>

                      {/* Total Price & Delete button */}
                      <div className="col-span-3 flex items-center justify-end gap-1.5 font-mono text-xs font-bold text-white">
                        <span className="truncate">{Math.round(lineTotal).toLocaleString('uz-UZ')}</span>
                        <button
                          type="button"
                          onClick={() => onRemoveItem && onRemoveItem(it.id)}
                          className="p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors shrink-0"
                          title="O'chirish"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Cart Bottom: Summary & Action Buttons (Ixcham va doim ko'rinuvchi) ── */}
      <div className="p-2.5 sm:p-4 bg-slate-950 border-t border-slate-800 shrink-0 shadow-2xl space-y-2">
        {/* Kitchen send success notification */}
        {kitchenSendSuccess && (
          <div className="p-2 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-bold text-xs text-center flex items-center justify-center gap-1.5 animate-bounce-subtle">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>✅ Buyurtma oshxona printerlariga chiqarildi!</span>
          </div>
        )}

        {/* Warning if unpriced weighted items exist */}
        {hasUnpricedWeighted && (
          <div className="p-2 rounded-xl bg-red-950/80 border border-red-600 text-red-200 font-bold text-xs flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span className="leading-tight text-[11px] sm:text-xs">
              Narxi kiritilmagan tarozidagi taom bor. Summasini yozing!
            </span>
          </div>
        )}

        {/* Subtotal, Service fee, Total */}
        <div className="space-y-1 bg-slate-900/80 p-2.5 sm:p-3 rounded-2xl border border-slate-800 text-xs">
          <div className="flex justify-between text-slate-300">
            <span className="font-semibold">Taomlar jami:</span>
            <span className="font-bold text-white font-mono">
              {Math.round(subtotal).toLocaleString('uz-UZ')} so'm
            </span>
          </div>
          {isDineIn && (
            <div className="flex justify-between text-slate-300">
              <span className="font-semibold">Xizmat haqi ({serviceFeePercent}%):</span>
              <span className="font-bold text-amber-300 font-mono">
                {Math.round(serviceFeeAmount).toLocaleString('uz-UZ')} so'm
              </span>
            </div>
          )}
          <div className="flex justify-between text-xs sm:text-sm font-black text-white pt-1 border-t border-slate-800 items-baseline">
            <span>Jami hisob:</span>
            <span className="text-emerald-400 text-base sm:text-lg font-mono">
              {Math.round(total).toLocaleString('uz-UZ')} so'm
            </span>
          </div>
        </div>

        {/* Kitchen Note */}
        <div>
          <button
            type="button"
            onClick={onOpenKitchenNote}
            className="w-full py-1.5 px-2.5 rounded-xl bg-teal-600/15 hover:bg-teal-600/25 border border-teal-500/30 text-teal-300 font-bold text-xs transition-all truncate text-left flex items-center justify-between"
          >
            <span className="truncate">💬 Oshxona izohi {kitchenNote ? `("${kitchenNote}")` : ''}</span>
            <span className="text-[10px] text-teal-400 underline shrink-0 ml-1">Tahrirlash</span>
          </button>
        </div>

        {/* ── Action Buttons: Mobilda ham qulay grid-cols-2, min-h-[44px] ── */}
        <div className="grid grid-cols-2 gap-2 pt-0.5">
          {/* Oshxonaga yuborish (Buyurtmani tasdiqlash) */}
          <button
            type="button"
            onClick={onSendToKitchen}
            disabled={!order || items.length === 0 || sendingToKitchen}
            className={`w-full min-h-[44px] py-2 px-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs sm:text-sm shadow-md transition-all active:scale-95 flex items-center justify-center gap-1.5 ${
              !canCheckout ? 'col-span-2' : 'col-span-1'
            }`}
          >
            <Printer className="w-4 h-4 shrink-0" />
            <span className="truncate">{sendingToKitchen ? 'Chop etilmoqda...' : '🔥 Tasdiqlash'}</span>
          </button>

          {/* To'landi va stolni bo'shatish (Checkout) — FAKAT Admin / Kassir */}
          {canCheckout && (
            <button
              type="button"
              onClick={onCheckout}
              disabled={!order || items.length === 0}
              className="w-full min-h-[44px] col-span-1 py-2 px-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 text-white font-black text-xs sm:text-sm shadow-md shadow-emerald-600/25 transition-all active:scale-95 flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span className="truncate">✅ To'landi</span>
            </button>
          )}

          {/* Admin / Kassir hisob chekini chiqarish */}
          {canCheckout && onPrintBill && (
            <button
              type="button"
              onClick={onPrintBill}
              disabled={!order || items.length === 0 || printingBill}
              className="w-full min-h-[40px] col-span-2 py-2 px-3 rounded-xl bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 disabled:opacity-40 text-sky-300 font-bold text-xs transition-all active:scale-95 flex items-center justify-center gap-1.5"
            >
              <Receipt className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{printingBill ? 'Chop etilmoqda...' : '🧾 Hisob chekini chiqarish'}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrderCart;
