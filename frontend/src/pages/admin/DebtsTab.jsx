import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import {
  Wallet,
  DollarSign,
  Phone,
  Calendar,
  Send,
  Plus,
  CheckCircle2,
  AlertCircle,
  Clock,
  Search,
  RefreshCw,
  X,
  CreditCard,
  User,
  Trash2,
  MessageSquare
} from 'lucide-react';

export const DebtsTab = ({ restaurantId }) => {
  const [debts, setDebts] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(''); // '' | 'unpaid' | 'partially_paid' | 'paid'

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showPayModal, setShowPayModal] = useState(false);
  const [selectedDebt, setSelectedDebt] = useState(null);

  // New Debt Form State
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('+998 ');
  const [newAmount, setNewAmount] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newNote, setNewNote] = useState('');
  const [savingDebt, setSavingDebt] = useState(false);

  // Pay Debt Form State
  const [payAmount, setPayAmount] = useState('');
  const [payNote, setPayNote] = useState('');
  const [payingDebt, setPayingDebt] = useState(false);

  // SMS Sending state
  const [sendingSmsId, setSendingSmsId] = useState(null);
  const [smsFeedback, setSmsFeedback] = useState(null);

  const fetchDebts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ restaurant_id: restaurantId });
      if (statusFilter) params.append('status_filter', statusFilter);
      if (search.trim()) params.append('search', search.trim());

      const [debtsData, statsData] = await Promise.all([
        api.get(`/debts/?${params.toString()}`),
        api.get(`/debts/stats?restaurant_id=${restaurantId}`),
      ]);

      setDebts(debtsData || []);
      setStats(statsData || null);
    } catch (err) {
      console.error('Error fetching debts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDebts();
  }, [restaurantId, statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchDebts();
  };

  // Create Debt
  const handleCreateDebt = async (e) => {
    e.preventDefault();
    if (!newName.trim() || !newAmount) {
      alert("Mijoz ismi va summa kiritilishi shart");
      return;
    }
    setSavingDebt(true);
    try {
      await api.post('/debts/', {
        restaurant_id: restaurantId,
        customer_name: newName.trim(),
        customer_phone: newPhone.trim(),
        amount: parseFloat(newAmount),
        due_date: newDueDate ? new Date(newDueDate).toISOString() : null,
        note: newNote.trim() || undefined,
      });
      setShowAddModal(false);
      setNewName('');
      setNewPhone('+998 ');
      setNewAmount('');
      setNewDueDate('');
      setNewNote('');
      fetchDebts();
    } catch (err) {
      alert(err.message || "Qarz kiritishda xatolik");
    } finally {
      setSavingDebt(false);
    }
  };

  // Pay Debt
  const handleOpenPayModal = (debt) => {
    setSelectedDebt(debt);
    setPayAmount(debt.remaining_amount);
    setPayNote('');
    setShowPayModal(true);
  };

  const handlePayDebt = async (e) => {
    e.preventDefault();
    if (!payAmount || parseFloat(payAmount) <= 0) {
      alert("To'lov summasini kiriting");
      return;
    }
    setPayingDebt(true);
    try {
      await api.patch(`/debts/${selectedDebt.id}/pay`, {
        payment_amount: parseFloat(payAmount),
        note: payNote.trim() || undefined,
      });
      setShowPayModal(false);
      setSelectedDebt(null);
      fetchDebts();
    } catch (err) {
      alert(err.message || "To'lovni qabul qilishda xatolik");
    } finally {
      setPayingDebt(false);
    }
  };

  // Send SMS Reminder
  const handleSendSms = async (debt) => {
    if (!debt.customer_phone || debt.customer_phone.length < 9) {
      alert("Mijoz telefon raqami noto'g'ri kiritilgan");
      return;
    }

    if (!window.confirm(`${debt.customer_name} raqamiga (${debt.customer_phone}) qarz haqida SMS eslatma yuborilsinmi?`)) {
      return;
    }

    setSendingSmsId(debt.id);
    setSmsFeedback(null);
    try {
      const res = await api.post(`/debts/${debt.id}/send-sms`, {});
      setSmsFeedback({
        debtId: debt.id,
        success: true,
        message: `SMS yuborildi: "${res.message_sent}"`,
      });
      fetchDebts();
      setTimeout(() => setSmsFeedback(null), 5000);
    } catch (err) {
      alert(err.message || "SMS yuborishda xatolik yuz berdi");
    } finally {
      setSendingSmsId(null);
    }
  };

  // Delete Debt
  const handleDeleteDebt = async (debtId, customerName) => {
    if (!window.confirm(`"${customerName}"ning ushbu qarz qaydini o'chirishni xohlaysizmi?`)) {
      return;
    }
    try {
      await api.delete(`/debts/${debtId}`);
      fetchDebts();
    } catch (err) {
      alert(err.message || "O'chirishda xatolik");
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/85 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider mb-1">
            <Wallet className="w-4 h-4" />
            <span>Nasiya va Qarzlar Daftari</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-white">
            Qarzlar Nazorati & SMS Eslatmalar
          </h2>
          <p className="text-xs text-theme-muted mt-1">
            Mijozlarning nasiya hisoblari, to'lovlar monitoringi va 1-bosishda SMS eslatmalar yuborish tizimi.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center gap-2 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Yangi Nasiya Kiritish</span>
          </button>

          <button
            onClick={fetchDebts}
            className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs transition-all"
            title="Yangilash"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-amber-950/20 border border-amber-500/30 flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase text-amber-400">Jami Nasiya</div>
          <div className="mt-2 text-xl font-black text-amber-300 font-mono">
            {stats ? `${stats.total_debt_amount?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-theme-muted mt-1">Umumiy berilgan qarz</div>
        </div>

        <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase text-emerald-400">Qaytarilgan Summa</div>
          <div className="mt-2 text-xl font-black text-emerald-300 font-mono">
            {stats ? `${stats.total_paid_amount?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-emerald-400/80 mt-1">
            {stats?.paid_count || 0} ta qarz to'liq yopilgan
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-rose-950/20 border border-rose-500/30 flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase text-rose-400">Qoldiq Qarz</div>
          <div className="mt-2 text-xl font-black text-rose-300 font-mono">
            {stats ? `${stats.total_remaining_amount?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-rose-400/80 mt-1">
            {stats?.unpaid_count || 0} ta qarzdor kutmoqda
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-theme-surface border border-theme-border flex flex-col justify-between">
          <div className="text-[11px] font-bold uppercase text-theme-muted">SMS Eslatmalar</div>
          <div className="mt-2 text-xl font-black text-white font-mono flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-cyan-400" />
            <span>Faol</span>
          </div>
          <div className="text-[10px] text-cyan-400 font-semibold mt-1">Avtomat / 1-klik SMS</div>
        </div>
      </div>

      {/* SMS feedback banner if recently sent */}
      {smsFeedback && (
        <div className="p-3.5 rounded-2xl bg-cyan-500/15 border border-cyan-500/40 text-cyan-300 text-xs font-semibold flex items-center gap-2.5 animate-fade-in">
          <Send className="w-4 h-4 text-cyan-400" />
          <span>{smsFeedback.message}</span>
        </div>
      )}

      {/* Filters & Search */}
      <div className="p-4 rounded-2xl bg-black/40 border border-theme-border/70 flex flex-wrap items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {[
            { key: '', label: 'Barchasi' },
            { key: 'unpaid', label: "To'lanmagan" },
            { key: 'partially_paid', label: 'Qisman to\'langan' },
            { key: 'paid', label: 'Yopilgan' },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => setStatusFilter(item.key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                statusFilter === item.key
                  ? 'bg-amber-500 text-black shadow-md'
                  : 'bg-theme-surface text-theme-muted hover:text-white border border-theme-border'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              placeholder="Ism yoki telefon qidirish..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs focus:outline-none focus:border-amber-400 w-48 sm:w-64"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors"
          >
            Qidirish
          </button>
        </form>
      </div>

      {/* Debts Table */}
      <div className="rounded-3xl glass-card border border-theme-border overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/50 text-theme-muted uppercase tracking-wider text-[11px] border-b border-theme-border">
              <tr>
                <th className="py-3 px-3.5 font-bold">Mijoz</th>
                <th className="py-3 px-3 font-bold">Telefon</th>
                <th className="py-3 px-3 font-bold text-right">Qarz Summasi</th>
                <th className="py-3 px-3 font-bold text-right text-emerald-400">To'langan</th>
                <th className="py-3 px-3 font-bold text-right text-rose-400">Qoldiq</th>
                <th className="py-3 px-3 font-bold">Muddati</th>
                <th className="py-3 px-3 font-bold text-center">Holat</th>
                <th className="py-3 px-3 font-bold text-center">SMS Holati</th>
                <th className="py-3 px-3.5 font-bold text-center">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme-border/40 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-theme-muted font-sans text-xs">
                    <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-2 text-theme-primary" />
                    <span>Qarzlar yuklanmoqda...</span>
                  </td>
                </tr>
              ) : debts.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-theme-muted font-sans text-xs">
                    Nasiya qarzlar ro'yxati bo'sh
                  </td>
                </tr>
              ) : (
                debts.map((d) => {
                  const isPaid = d.status === 'paid';
                  const isOverdue = d.due_date && new Date(d.due_date) < new Date() && !isPaid;

                  return (
                    <tr key={d.id} className="hover:bg-white/5 transition-colors text-zinc-300">
                      <td className="py-3 px-3.5 font-sans font-bold text-white text-xs">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-300 flex items-center justify-center font-bold text-xs">
                            {d.customer_name?.charAt(0) || 'M'}
                          </div>
                          <div>
                            <div>{d.customer_name}</div>
                            {d.note && (
                              <div className="text-[10px] text-zinc-400 font-normal truncate max-w-[150px]">
                                {d.note}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-zinc-300 text-xs">
                        {d.customer_phone || '—'}
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-white">
                        {d.amount.toLocaleString()}
                      </td>
                      <td className="py-3 px-3 text-right text-emerald-300">
                        {d.paid_amount.toLocaleString()}
                      </td>
                      <td className="py-3 px-3 text-right font-black text-rose-400 text-sm">
                        {d.remaining_amount.toLocaleString()}
                      </td>
                      <td className="py-3 px-3 text-xs font-sans">
                        {d.due_date ? (
                          <span className={isOverdue ? 'text-rose-400 font-bold flex items-center gap-1' : 'text-zinc-400'}>
                            {isOverdue && <AlertCircle className="w-3.5 h-3.5" />}
                            {new Date(d.due_date).toLocaleDateString()}
                          </span>
                        ) : (
                          <span className="text-zinc-500">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-center font-sans">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                            isPaid
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : d.status === 'partially_paid'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                              : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          }`}
                        >
                          {isPaid ? "To'langan" : d.status === 'partially_paid' ? 'Qisman' : 'Faol'}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center text-xs font-sans text-zinc-400">
                        {d.sms_count > 0 ? (
                          <span className="text-cyan-300 font-mono font-bold">
                            {d.sms_count} marta
                          </span>
                        ) : (
                          <span className="text-zinc-500">Yuborilmagan</span>
                        )}
                      </td>
                      <td className="py-3 px-3.5 text-center font-sans">
                        <div className="flex items-center justify-center gap-1.5">
                          {/* Send SMS Button */}
                          {!isPaid && (
                            <button
                              onClick={() => handleSendSms(d)}
                              disabled={sendingSmsId === d.id}
                              className="px-2.5 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-[11px] font-bold flex items-center gap-1 transition-all disabled:opacity-50"
                              title="Qarzdorga SMS eslatma yuborish"
                            >
                              <Send className={`w-3 h-3 ${sendingSmsId === d.id ? 'animate-pulse' : ''}`} />
                              <span>{sendingSmsId === d.id ? '...' : 'SMS'}</span>
                            </button>
                          )}

                          {/* Record Payment Button */}
                          {!isPaid && (
                            <button
                              onClick={() => handleOpenPayModal(d)}
                              className="px-2.5 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-[11px] font-bold flex items-center gap-1 transition-all"
                              title="To'lov qabul qilish"
                            >
                              <CreditCard className="w-3 h-3" />
                              <span>To'lash</span>
                            </button>
                          )}

                          {/* Delete Button */}
                          <button
                            onClick={() => handleDeleteDebt(d.id, d.customer_name)}
                            className="p-1.5 rounded-lg bg-white/5 hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                            title="O'chirish"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── MODAL: CREATE DEBT ─────────────────────────────────────────── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-md rounded-3xl glass-card border border-theme-border bg-theme-surface p-6 sm:p-8 space-y-5 shadow-2xl">
            <button
              onClick={() => setShowAddModal(false)}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Wallet className="w-5 h-5 text-amber-400" />
              <span>Yangi Nasiya (Qarz) Kiritish</span>
            </h3>

            <form onSubmit={handleCreateDebt} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Mijoz Ismi-Familiyasi: *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: Sardor Rahimov"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Telefon Raqami (SMS uchun):
                </label>
                <input
                  type="tel"
                  placeholder="+998 90 123 45 67"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Qarz Summasi (so'm): *
                </label>
                <input
                  type="number"
                  required
                  min="1000"
                  step="500"
                  placeholder="Masalan: 250000"
                  value={newAmount}
                  onChange={(e) => setNewAmount(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-sm text-white font-mono font-bold focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Qaytarish Muddati (ixtiyoriy):
                </label>
                <input
                  type="date"
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Izoh / Sababi:
                </label>
                <input
                  type="text"
                  placeholder="Masalan: Banket hisobidan qolgan qoldiq"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-theme-border/60">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white text-xs font-semibold"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={savingDebt}
                  className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-black text-xs font-bold shadow-lg disabled:opacity-50"
                >
                  {savingDebt ? 'Saqlanmoqda...' : 'Nasiyani Saqlash'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── MODAL: PAY DEBT ────────────────────────────────────────────── */}
      {showPayModal && selectedDebt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-sm rounded-3xl glass-card border border-theme-border bg-theme-surface p-6 sm:p-7 space-y-5 shadow-2xl">
            <button
              onClick={() => setShowPayModal(false)}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-emerald-400" />
              <span>Qarz To'lovini Qabul Qilish</span>
            </h3>

            <div className="p-3.5 rounded-2xl bg-black/30 border border-theme-border text-xs space-y-1">
              <div className="text-theme-muted">Mijoz: <span className="text-white font-bold">{selectedDebt.customer_name}</span></div>
              <div className="text-theme-muted">Umumiy qarz: <span className="text-white font-mono">{selectedDebt.amount?.toLocaleString()} so'm</span></div>
              <div className="text-theme-muted">Qoldiq qarz: <span className="text-rose-400 font-mono font-bold">{selectedDebt.remaining_amount?.toLocaleString()} so'm</span></div>
            </div>

            <form onSubmit={handlePayDebt} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Kiritilayotgan To'lov Summasi: *
                </label>
                <input
                  type="number"
                  required
                  min="1000"
                  max={selectedDebt.remaining_amount}
                  step="500"
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-base text-emerald-300 font-mono font-black focus:outline-none focus:border-emerald-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  To'lov izohi (ixtiyoriy):
                </label>
                <input
                  type="text"
                  placeholder="Masalan: Naqd pulda to'landi"
                  value={payNote}
                  onChange={(e) => setPayNote(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-emerald-400"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-theme-border/60">
                <button
                  type="button"
                  onClick={() => setShowPayModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white text-xs font-semibold"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={payingDebt}
                  className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black text-xs font-bold shadow-lg disabled:opacity-50"
                >
                  {payingDebt ? 'Qabul qilinmoqda...' : 'To\'lovni Tasdiqlash'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DebtsTab;
