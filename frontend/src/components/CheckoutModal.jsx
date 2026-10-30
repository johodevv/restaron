import React, { useState, useEffect } from 'react';
import { CreditCard, X, Printer, Banknote, Sparkles, AlertCircle, Percent } from 'lucide-react';
import api from '../utils/api';
import CashKeypad from './CashKeypad';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { cashIsInsufficient } from '../utils/cashKeypad';

/**
 * Kassa oynasi — to'lovni qabul qilish va chek chiqarish (Aliposter 1.0.0.0 andozasida)
 * 
 * Imkoniyatlar:
 * 1. Naqd to'lov: tezkor kupyuralar (Aniq summa, 50k, 100k, 200k, 500k) va katta qaytim displeyi
 * 2. Aralash to'lov (Split Payment): Naqd + Karta + Click
 * 3. Chegirma (Discount) kiritish
 * 4. Nasiya (Qarz) rasmiylashtirish
 */
const PAYMENT_METHODS = [
  { id: 'cash', label: 'Naqd' },
  { id: 'card', label: 'Karta' },
  { id: 'click', label: 'Click / Payme' },
  { id: 'mixed', label: 'Aralash to\'lov' },
  { id: 'debt', label: 'Qarz (nasiya)' },
];

export const CheckoutModal = ({ isOpen, onClose, order, tableLabel, onPaid }) => {
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [cashReceived, setCashReceived] = useState('');
  const [discountAmount, setDiscountAmount] = useState('');
  
  // Aralash to'lov uchun
  const [mixedCash, setMixedCash] = useState('');
  const [mixedCard, setMixedCard] = useState('');
  const [mixedClick, setMixedClick] = useState('');

  // Nasiya uchun
  const [debtCustomerName, setDebtCustomerName] = useState('');
  const [debtCustomerPhone, setDebtCustomerPhone] = useState('');
  const [debtDueDate, setDebtDueDate] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [quote, setQuote] = useState(null);
  const close = () => { if (!loading) onClose(); };
  const dialogRef = useDialogFocus(isOpen && Boolean(order), close);

  const originalTotal = quote?.total ?? order?.total ?? 0;
  const advance = quote?.advance_amount ?? order?.advance_amount ?? 0;
  const discount = Math.max(0, Math.min(originalTotal, parseFloat(String(discountAmount).replace(/\s/g, '')) || 0));
  const finalTotal = Math.max(0, originalTotal - discount - advance);

  // Oyna ochilganda tozalash
  useEffect(() => {
    if (isOpen) {
      setQuote(order);
      setPaymentMethod('cash');
      setCashReceived('');
      setDiscountAmount('');
      setMixedCash('');
      setMixedCard('');
      setMixedClick('');
      setDebtCustomerName('');
      setDebtCustomerPhone('');
      setDebtDueDate('');
      setError('');
    }
  }, [isOpen, order?.id]);

  if (!isOpen || !order) return null;

  // Naqd hisob-kitob
  const receivedCash = parseFloat(String(cashReceived).replace(/\s/g, '')) || 0;
  const change = paymentMethod === 'cash' && receivedCash > finalTotal ? receivedCash - finalTotal : 0;
  const cashNotEnough = paymentMethod === 'cash' && cashIsInsufficient(cashReceived, finalTotal);

  // Aralash hisob-kitob
  const mCash = parseFloat(String(mixedCash).replace(/\s/g, '')) || 0;
  const mCard = parseFloat(String(mixedCard).replace(/\s/g, '')) || 0;
  const mClick = parseFloat(String(mixedClick).replace(/\s/g, '')) || 0;
  const mixedSum = mCash + mCard + mClick;
  const mixedDiff = Math.round(finalTotal - mixedSum);

  // Quick cash buttons (Aliposter 1.0.0.0 andozasi)
  const quickBills = [
    { label: 'Aniq summa', val: finalTotal },
    { label: '50 000', val: 50000 },
    { label: '100 000', val: 100000 },
    { label: '200 000', val: 200000 },
    { label: '500 000', val: 500000 },
  ].filter((b) => b.val >= finalTotal || b.label === 'Aniq summa');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (cashNotEnough) {
      setError(`Naqd pul yetarli emas. Yetishmayapti: ${(finalTotal - receivedCash).toLocaleString('uz-UZ')} so'm`);
      return;
    }

    if (paymentMethod === 'mixed' && Math.abs(mixedDiff) > 1) {
      if (mixedDiff > 0) {
        setError(`Aralash to'lov to'liq kiritilmadi. Yetishmayapti: ${mixedDiff.toLocaleString('uz-UZ')} so'm`);
      } else {
        setError(`Aralash to'lov hisobdan oshib ketdi: ${Math.abs(mixedDiff).toLocaleString('uz-UZ')} so'm`);
      }
      return;
    }

    setLoading(true);
    try {
      const payload = {
        payment_method: paymentMethod,
        expected_version: quote?.version ?? order.version,
        discount: discount,
        print_receipt: true,
      };

      if (paymentMethod === 'cash') {
        if (receivedCash > 0) {
          payload.cash_amount = receivedCash;
        } else {
          payload.cash_amount = finalTotal;
        }
      } else if (paymentMethod === 'card') {
        payload.card_amount = finalTotal;
      } else if (paymentMethod === 'click') {
        payload.click_amount = finalTotal;
      } else if (paymentMethod === 'mixed') {
        payload.cash_amount = mCash;
        payload.card_amount = mCard;
        payload.click_amount = mClick;
      } else if (paymentMethod === 'debt') {
        payload.debt_amount = finalTotal;
        payload.debt_customer_name = debtCustomerName;
        payload.debt_customer_phone = debtCustomerPhone;
        payload.debt_due_date = debtDueDate || null;
      }

      const res = await api.post(`/orders/${order.id}/checkout`, payload, { idempotent: true });
      onClose();
      if (onPaid) onPaid(res);
    } catch (err) {
      setError(err.message || "To'lovni qabul qilishda xatolik yuz berdi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="checkout-title" className="dunyo-checkout bg-slate-900 border border-slate-800 rounded-2xl w-full p-4 sm:p-5 shadow-2xl max-h-[94dvh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CreditCard className="w-5 h-5" />
            </div>
            <div>
              <h3 id="checkout-title" className="text-white font-extrabold text-lg">To‘lovni qabul qilish</h3>
              <p className="text-[11px] text-slate-400 font-medium">
                {tableLabel} {order?.order_number ? `• ${order.order_number}` : ''}
              </p>
            </div>
          </div>
          <button
            type="button" aria-label="Kassani yopish" disabled={loading} onClick={close}
            className="w-11 h-11 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center transition-colors disabled:opacity-40"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="checkout-grid">
          <aside className="checkout-order" aria-label="To‘lanayotgan buyurtma">
            <h4 className="font-bold text-base mb-3">{tableLabel || 'Buyurtma'}</h4>
            <ul className="space-y-3">
              {(order.items || []).map(item => <li key={item.id} className="border-b border-slate-700 pb-3">
                <p className="font-semibold break-words">{item.menu_item_name || item.menu_item?.name || 'Taom'}</p>
                <div className="flex flex-wrap justify-between gap-2 text-sm mt-1 text-slate-300"><span>{item.quantity} × {Number(item.unit_price || 0).toLocaleString('uz-UZ')}</span><strong>{Number(item.total_price || 0).toLocaleString('uz-UZ')}</strong></div>
                {item.is_weighted && item.weight && <p className="text-sm text-slate-400 mt-1">{item.weight} kg</p>}
              </li>)}
            </ul>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-2"><dt>Taomlar</dt><dd>{Number(order.subtotal || 0).toLocaleString('uz-UZ')}</dd></div>
              <div className="flex justify-between gap-2"><dt>Xizmat ({order.service_fee_percent ?? 0}%)</dt><dd>{Number(order.service_fee_amount || 0).toLocaleString('uz-UZ')}</dd></div>
            </dl>
          </aside>
          <section aria-label="To‘lov hisobi" className="checkout-summary">
        {/* Summa kartochkasi */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-700 mb-4 flex flex-col gap-5">
          <div>
            <span className="text-[11px] uppercase tracking-wider font-bold text-slate-400 block">Qolgan to'lov:</span>
            {advance > 0 && <p className="text-xs text-emerald-400">Avans ayrildi: {advance.toLocaleString('uz-UZ')} so'm</p>}
            {discount > 0 ? (
              <div className="flex items-center gap-2">
                <span className="text-xs line-through text-slate-500 font-mono">
                  {originalTotal.toLocaleString('uz-UZ')}
                </span>
                <span className="text-xl sm:text-2xl font-black text-emerald-400 font-mono">
                  {finalTotal.toLocaleString('uz-UZ')} so'm
                </span>
              </div>
            ) : (
              <span className="text-xl sm:text-2xl font-black text-emerald-400 font-mono">
                {finalTotal.toLocaleString('uz-UZ')} so'm
              </span>
            )}
          </div>
          <div className="w-full">
            <label htmlFor="checkout-discount" className="text-sm text-slate-300 font-bold block mb-2">Chegirma (so'm):</label>
            <input
              id="checkout-discount"
              type="number"
              min="0"
              max={originalTotal}
              value={discountAmount}
              onChange={(e) => setDiscountAmount(e.target.value)}
              placeholder="0"
              className="w-full min-h-[48px] px-3 rounded-lg bg-slate-900 border border-slate-600 text-lg text-white font-mono text-right focus:outline-none focus:border-emerald-400"
            />
          </div>
        </div>
        {paymentMethod === 'cash' && <div className="checkout-change"><p className="text-sm text-slate-300">Qaytim</p><p className="text-2xl font-bold mt-2">{change.toLocaleString('uz-UZ')} <span className="text-sm">so‘m</span></p></div>}
          </section>

        <form onSubmit={handleSubmit} className="checkout-payment space-y-4">
          {/* To'lov usullari */}
          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              To'lov turi:
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {PAYMENT_METHODS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  aria-pressed={paymentMethod === m.id}
                  onClick={() => setPaymentMethod(m.id)}
                  className={`py-2 px-2.5 rounded-xl border text-xs font-bold transition-all text-left flex items-center gap-1.5 ${
                    paymentMethod === m.id
                      ? 'bg-emerald-600 text-white border-emerald-500 shadow-md shadow-emerald-600/30 ring-1 ring-emerald-400'
                      : 'bg-slate-800/80 border-slate-700/80 text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <span className="truncate">{m.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ── 1. NAQD TO'LOV: TEZKOR TUGMALAR VA QAYTIM ── */}
          {paymentMethod === 'cash' && (
            <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 space-y-2 animate-in fade-in">
              <div className="flex items-center justify-between">
                <label className="text-xs text-emerald-300 font-bold flex items-center gap-1.5">
                  <Banknote className="w-4 h-4" />
                  Mijozdan olingan naqd pul:
                </label>
                {cashReceived && (
                  <button
                    type="button"
                    onClick={() => setCashReceived('')}
                    className="text-[11px] text-slate-400 hover:text-white underline"
                  >
                    Tozalash
                  </button>
                )}
              </div>

              {/* Qo'lda kiritish */}
              <input
                aria-label="Mijozdan olingan naqd pul"
                data-dialog-autofocus
                type="number"
                min="0"
                step="any"
                inputMode="decimal"
                value={cashReceived}
                onChange={(e) => setCashReceived(e.target.value)}
                placeholder={`${finalTotal.toLocaleString('uz-UZ')} (aniq summa)`}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-base text-white font-mono font-bold focus:outline-none focus:border-emerald-400"
              />

              {/* Aliposter tezkor pullar */}
              <div>
                <div className="flex flex-wrap gap-1.5">
                  {quickBills.map((b, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setCashReceived(String(b.val))}
                      className="min-h-[44px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-mono font-bold text-white transition-all active:scale-95"
                    >
                      {b.label}
                    </button>
                  ))}
                </div>
              </div>

              <CashKeypad value={cashReceived} onChange={setCashReceived} disabled={loading} />

              {cashNotEnough && (
                <p className="text-[11px] text-red-300 font-semibold">
                  ⚠️ Yetishmayapti: {(finalTotal - receivedCash).toLocaleString('uz-UZ')} so'm
                </p>
              )}
            </div>
          )}

          {/* ── 2. ARALASH TO'LOV (SPLIT PAYMENT) ── */}
          {paymentMethod === 'mixed' && (
            <div className="p-3.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between">
                <span className="text-xs text-cyan-300 font-bold">Aralash to'lov taqsimoti:</span>
                <span className={`text-xs font-mono font-bold ${mixedDiff === 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {mixedDiff === 0 ? '✓ To\'liq mos' : `Qolgan: ${mixedDiff.toLocaleString('uz-UZ')} so'm`}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-slate-300 font-semibold">💵 Naqd summa:</label>
                    <button
                      type="button"
                      onClick={() => setMixedCash(String(Math.max(0, finalTotal - mCard - mClick)))}
                      className="text-[10px] text-cyan-400 hover:underline"
                    >
                      qolganini qo'yish
                    </button>
                  </div>
                  <input
                    type="number"
                    min="0"
                    aria-label="Aralash naqd summa"
                    value={mixedCash}
                    onChange={(e) => setMixedCash(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 font-mono text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-slate-300 font-semibold">💳 Karta (Uzcard/Humo):</label>
                    <button
                      type="button"
                      onClick={() => setMixedCard(String(Math.max(0, finalTotal - mCash - mClick)))}
                      className="text-[10px] text-cyan-400 hover:underline"
                    >
                      qolganini qo'yish
                    </button>
                  </div>
                  <input
                    type="number"
                    min="0"
                    aria-label="Aralash karta summasi"
                    value={mixedCard}
                    onChange={(e) => setMixedCard(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 font-mono text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-slate-300 font-semibold">📲 Click / Payme:</label>
                    <button
                      type="button"
                      onClick={() => setMixedClick(String(Math.max(0, finalTotal - mCash - mCard)))}
                      className="text-[10px] text-cyan-400 hover:underline"
                    >
                      qolganini qo'yish
                    </button>
                  </div>
                  <input
                    type="number"
                    min="0"
                    aria-label="Aralash Click summasi"
                    value={mixedClick}
                    onChange={(e) => setMixedClick(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 font-mono text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── 3. NASIYA (QARZ) ── */}
          {paymentMethod === 'debt' && (
            <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2.5 animate-in fade-in">
              <p className="text-xs font-bold text-amber-300">Qarzdor ma'lumotlari:</p>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Mijoz F.I.Sh:</label>
                <input
                  type="text"
                  required
                  value={debtCustomerName}
                  onChange={(e) => setDebtCustomerName(e.target.value)}
                  placeholder="Masalan: Sardor Rahimov"
                  className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Telefon raqami:</label>
                <input
                  type="text"
                  required
                  value={debtCustomerPhone}
                  onChange={(e) => setDebtCustomerPhone(e.target.value)}
                  placeholder="+998 90 123 45 67"
                  className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Qaytarish muddati:</label>
                <input
                  type="date"
                  value={debtDueDate}
                  onChange={(e) => setDebtDueDate(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="px-3 py-2 rounded-xl bg-red-950/70 border border-red-800 text-[11px] text-red-300 font-semibold flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="checkout-actions flex items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={close} disabled={loading}
              className="min-h-[44px] px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm font-semibold text-slate-300 transition-colors"
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={loading || cashNotEnough || (paymentMethod === 'mixed' && Math.abs(mixedDiff) > 1)}
              className="min-h-[44px] flex-1 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 font-extrabold text-xs sm:text-sm text-white shadow-lg shadow-emerald-600/30 flex items-center justify-center gap-2 transition-all active:scale-95"
            >
              <Printer className="w-4 h-4" />
              <span>{loading ? 'Yopilmoqda...' : "To'lov va Chek chiqarish"}</span>
            </button>
          </div>
        </form>
        </div>
      </div>
    </div>
  );
};

export default CheckoutModal;
