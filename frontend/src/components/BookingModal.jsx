import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Clock,
  User,
  Phone,
  Users,
  MessageSquare,
  DollarSign,
  CheckCircle2,
  X,
  Sparkles
} from 'lucide-react';
import api from '../utils/api';

/**
 * BookingModal — Stolni bron qilish / rezervatsiya modali.
 * 
 * MOBIL MOSLASHUVCHAN (FULLY MOBILE RESPONSIVE):
 * - max-h-[92vh] va custom-scrollbar orqali kichik telefon ekranlarida ham to'liq sig'adi.
 * - Harakat tugmalari: min-h-[44px] sensorli o'lchamda, grid-cols-2 ko'rinishida qulay joylashgan.
 */
export const BookingModal = ({
  isOpen,
  onClose,
  table,
  tables = [],
  onBookingConfirmed,
}) => {
  const [selectedTableId, setSelectedTableId] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [bookingDate, setBookingDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [bookingTime, setBookingTime] = useState('18:00');
  const [guestCount, setGuestCount] = useState(4);
  const [depositAmount, setDepositAmount] = useState('');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSelectedTableId(table ? String(table.id) : (tables[0] ? String(tables[0].id) : ''));
      setCustomerName('');
      setCustomerPhone('+998 ');
      setBookingDate(new Date().toISOString().split('T')[0]);
      setBookingTime('18:00');
      setGuestCount(table?.capacity || 4);
      setDepositAmount('');
      setNote('');
      setError('');
      setSuccess(false);
    }
  }, [isOpen, table, tables]);

  if (!isOpen) return null;

  const currentTable = tables.find((t) => String(t.id) === String(selectedTableId)) || table;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!selectedTableId) {
      setError('Iltimos, bron qilinadigan stolni tanlang');
      return;
    }
    if (!customerName.trim()) {
      setError('Mijoz ismini kiriting');
      return;
    }

    setLoading(true);
    try {
      // Stol holatini 'reserved' ga o'zgartirish
      await api.patch(`/tables/${selectedTableId}/status`, {
        status: 'reserved'
      });

      setSuccess(true);
      setTimeout(() => {
        if (onBookingConfirmed) {
          onBookingConfirmed({
            tableId: selectedTableId,
            tableNumber: currentTable?.number,
            customerName,
            customerPhone,
            bookingDate,
            bookingTime,
            guestCount,
            depositAmount,
            note,
          });
        }
        onClose();
      }, 1000);
    } catch (err) {
      setError(err.message || 'Bron qilishda xatolik yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fade-in overflow-y-auto">
      <div className="relative w-full max-w-lg rounded-2xl sm:rounded-3xl glass-card border border-theme-border bg-theme-surface p-4 sm:p-7 shadow-2xl my-6 max-h-[92vh] flex flex-col justify-between overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 sm:pb-4 border-b border-theme-border/60 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-white flex items-center gap-2">
                <span>Stol Bron Qilish (Rezervatsiya)</span>
              </h3>
              <p className="text-[11px] sm:text-xs text-theme-muted">
                {currentTable ? `Stol #${currentTable.number} (${currentTable.room || 'Zal'})` : 'Stol tanlang'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-theme-muted hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto custom-scrollbar py-3 sm:py-4 space-y-3.5 pr-1 text-xs">
          {error && (
            <div className="p-2.5 rounded-xl bg-red-950/80 border border-red-600 text-red-200 font-bold text-xs">
              ⚠️ {error}
            </div>
          )}

          {success && (
            <div className="p-3 rounded-xl bg-emerald-500/20 border border-emerald-500 text-emerald-300 font-bold text-xs text-center flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Stol muvaffaqiyatli bron qilindi!</span>
            </div>
          )}

          {/* Stolni tanlash (agar bir nechta bo'lsa) */}
          <div>
            <label className="block text-[11px] font-bold text-slate-300 mb-1">
              Qaysi stol: *
            </label>
            <select
              value={selectedTableId}
              onChange={(e) => setSelectedTableId(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs font-bold focus:outline-none focus:border-amber-400"
              required
            >
              {tables.map((t) => (
                <option key={t.id} value={t.id}>
                  Stol #{t.number} — {t.room || 'Asosiy zal'} ({t.capacity || 4} kishilik) [{t.status === 'occupied' ? 'Band' : t.status === 'reserved' ? 'Bron' : "Bo'sh"}]
                </option>
              ))}
            </select>
          </div>

          {/* Mijoz ismi va telefoni */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <label className="block text-[11px] font-bold text-slate-300 mb-1">
                Mijoz ismi: *
              </label>
              <div className="relative">
                <User className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="masalan: Alisher Navoiy"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="w-full pl-8.5 pr-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs placeholder-slate-500 focus:outline-none focus:border-amber-400 font-medium"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-300 mb-1">
                Telefon raqami:
              </label>
              <div className="relative">
                <Phone className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="+998 90 123 45 67"
                  value={customerPhone}
                  onChange={(e) => setCustomerPhone(e.target.value)}
                  className="w-full pl-8.5 pr-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-amber-400 font-bold"
                />
              </div>
            </div>
          </div>

          {/* Sana va Vaqt */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <label className="block text-[11px] font-bold text-slate-300 mb-1">
                Bron sanasi: *
              </label>
              <div className="relative">
                <Calendar className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="date"
                  value={bookingDate}
                  onChange={(e) => setBookingDate(e.target.value)}
                  className="w-full pl-8.5 pr-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs focus:outline-none focus:border-amber-400 font-bold"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-300 mb-1">
                Kelish vaqti: *
              </label>
              <div className="relative">
                <Clock className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="time"
                  value={bookingTime}
                  onChange={(e) => setBookingTime(e.target.value)}
                  className="w-full pl-8.5 pr-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs font-mono font-bold focus:outline-none focus:border-amber-400"
                  required
                />
              </div>
            </div>
          </div>

          {/* Mehmonlar soni va Zakalat (Oldindan to'lov) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <label className="block text-[11px] font-bold text-slate-300 mb-1">
                Mehmonlar soni:
              </label>
              <div className="relative">
                <Users className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={guestCount}
                  onChange={(e) => setGuestCount(Number(e.target.value))}
                  className="w-full pl-8.5 pr-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs font-bold focus:outline-none focus:border-amber-400"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-300 mb-1">
                Zakalat / Avans (so'm):
              </label>
              <div className="relative">
                <DollarSign className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="masalan: 100 000"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="w-full pl-8.5 pr-3 py-2.5 rounded-xl bg-slate-900 border border-theme-border text-white text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-amber-400 font-bold"
                />
              </div>
            </div>
          </div>

          {/* Qo'shimcha Izoh */}
          <div>
            <label className="block text-[11px] font-bold text-slate-300 mb-1">
              Qo'shimcha izoh / istaklar:
            </label>
            <div className="relative">
              <MessageSquare className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
              <textarea
                rows="2"
                placeholder="masalan: Tug'ilgan kun, gul yoki shamlar bilan bezatilsin..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="w-full pl-8.5 pr-3 py-2 rounded-xl bg-slate-900 border border-theme-border text-white text-xs placeholder-slate-500 focus:outline-none focus:border-amber-400 font-medium resize-none"
              />
            </div>
          </div>

          {/* Action Footer Buttons (min-h-[44px], responsive 2 ustun) */}
          <div className="grid grid-cols-2 gap-2.5 pt-3 border-t border-theme-border/60 shrink-0">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="w-full min-h-[44px] py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs sm:text-sm active:scale-95 transition-all"
            >
              Bekor qilish
            </button>
            <button
              type="submit"
              disabled={loading || success}
              className="w-full min-h-[44px] py-2.5 px-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs sm:text-sm shadow-md active:scale-95 transition-all flex items-center justify-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{loading ? 'Saqlanmoqda...' : '✅ Bronni tasdiqlash'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BookingModal;
