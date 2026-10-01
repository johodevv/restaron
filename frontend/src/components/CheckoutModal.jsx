import React, { useState, useEffect } from 'react';
import { CreditCard, X, Printer } from 'lucide-react';
import api from '../utils/api';

/**
 * Kassa oynasi — to'lovni qabul qilish va chek chiqarish.
 *
 * Ilgari bu faqat ofitsiant panelida edi. Endi kassada o'tirgan odam
 * admin panelda ishlaydi, shuning uchun umumiy komponentga chiqarildi.
 *
 * props:
 *   order      — buyurtma obyekti ({ id, total, ... })
 *   tableLabel — sarlavhada ko'rsatiladigan stol nomi
 *   onPaid(res) — to'lov muvaffaqiyatli bo'lgach chaqiriladi (res.raw_text — chek matni)
 */
const PAYMENT_METHODS = [
  { id: 'cash', label: '💵 Naqd (Наличные)' },
  { id: 'card', label: '💳 Karta (Uzcard/Humo)' },
  { id: 'click', label: '📲 Click / Payme' },
  { id: 'debt', label: '📝 Nasiya / Qarz' },
];

export const CheckoutModal = ({ isOpen, onClose, order, tableLabel, onPaid }) => {
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [cashReceived, setCashReceived] = useState('');
  const [debtCustomerName, setDebtCustomerName] = useState('');
  const [debtCustomerPhone, setDebtCustomerPhone] = useState('');
  const [debtDueDate, setDebtDueDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const total = order?.total || 0;

  // Oyna har ochilganda maydonlar tozalansin
  useEffect(() => {
    if (isOpen) {
      setPaymentMethod('cash');
      setCashReceived('');
      setDebtCustomerName('');
      setDebtCustomerPhone('');
      setDebtDueDate('');
      setError('');
    }
  }, [isOpen]);

  if (!isOpen || !order) return null;

  const received = parseFloat(String(cashReceived).replace(/\s/g, '')) || 0;
  const change = paymentMethod === 'cash' && received > total ? received - total : 0;
  const notEnough = paymentMethod === 'cash' && received > 0 && received < total;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (notEnough) {
      setError(`Naqd pul yetarli emas. Yetishmayapti: ${(total - received).toLocaleString('uz-UZ')} so'm`);
      return;
    }

    setLoading(true);
    try {
      const payload = {
        payment_method: paymentMethod,
        discount: 0.0,
        print_receipt: true,
      };
      // Naqd summa kiritilgan bo'lsa yuboramiz — backend qaytimni hisoblaydi.
      // Kiritilmasa backend butun summani naqd deb yozadi.
      if (paymentMethod === 'cash' && received > 0) {
        payload.cash_amount = received;
      }
      if (paymentMethod === 'debt') {
        payload.debt_customer_name = debtCustomerName;
        payload.debt_customer_phone = debtCustomerPhone;
        payload.debt_due_date = debtDueDate || null;
      }

      const res = await api.post(`/orders/${order.id}/checkout`, payload);
      onClose();
      if (onPaid) onPaid(res);
    } catch (err) {
      setError(err.message || "To'lovni qabul qilishda xatolik");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
              <CreditCard className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-white font-extrabold text-sm">To'lovni qabul qilish</h3>
              <p className="text-[11px] text-slate-400">
                {tableLabel} • Jami:{' '}
                <span className="text-emerald-400 font-bold">
                  {total.toLocaleString('uz-UZ')} so'm
                </span>
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <label className="block text-xs font-bold text-slate-400 uppercase mb-2">
            To'lov turi:
          </label>
          <div className="grid grid-cols-2 gap-2 mb-4">
            {PAYMENT_METHODS.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setPaymentMethod(m.id)}
                className={`py-2.5 px-3 rounded-xl border text-xs font-bold transition-all text-left ${
                  paymentMethod === m.id
                    ? 'bg-emerald-600 text-white border-emerald-500 shadow-md'
                    : 'bg-slate-800/80 border-slate-700/80 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Naqd: olingan pul va qaytim */}
          {paymentMethod === 'cash' && (
            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 mb-4 space-y-2.5">
              <label className="text-[11px] text-slate-300 block mb-1 font-bold">
                Mijozdan olingan naqd (ixtiyoriy):
              </label>
              <input
                type="number"
                min="0"
                step="any"
                inputMode="decimal"
                value={cashReceived}
                onChange={(e) => setCashReceived(e.target.value)}
                placeholder={`${total.toLocaleString('uz-UZ')} (aniq summa)`}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-sm text-white font-mono focus:outline-none focus:border-emerald-400"
              />
              {change > 0 && (
                <div className="flex items-center justify-between px-1 pt-1">
                  <span className="text-xs font-bold text-slate-300">Qaytim:</span>
                  <span className="text-lg font-black text-amber-300 font-mono">
                    {change.toLocaleString('uz-UZ')} so'm
                  </span>
                </div>
              )}
              {notEnough && (
                <p className="text-[11px] text-red-300 font-semibold">
                  Yetishmayapti: {(total - received).toLocaleString('uz-UZ')} so'm
                </p>
              )}
            </div>
          )}

          {/* Nasiya (qarz) ma'lumotlari */}
          {paymentMethod === 'debt' && (
            <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 mb-4 space-y-2.5 animate-in fade-in">
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
            <div className="mb-3 px-3 py-2 rounded-xl bg-red-950/70 border border-red-800 text-[11px] text-red-300 font-semibold">
              {error}
            </div>
          )}

          <div className="flex items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={loading || notEnough}
              className="flex-1 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 font-extrabold text-xs text-white shadow-lg shadow-emerald-600/30 flex items-center justify-center gap-2 transition-all active:scale-95"
            >
              <Printer className="w-4 h-4" />
              <span>{loading ? 'Yopilmoqda...' : "To'lov va Chek chiqarish"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CheckoutModal;
