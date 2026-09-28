import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import confetti from 'canvas-confetti';
import {
  Code,
  Building2,
  DollarSign,
  TrendingUp,
  Percent,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Power,
  CreditCard,
  Sparkles,
  ShieldCheck
} from 'lucide-react';

export const DeveloperDashboard = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  // New restaurant modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [newAddress, setNewAddress] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newCommission, setNewCommission] = useState(5.0);

  // Pay commission modal
  const [payModalRest, setPayModalRest] = useState(null);
  const [payAmount, setPayAmount] = useState('');
  const [payNote, setPayNote] = useState('');

  const loadSummary = async () => {
    try {
      const data = await api.get('/restaurants/commissions/summary');
      setSummary(data);
    } catch (err) {
      console.error('Developer summary error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  const handleCreateRestaurant = async (e) => {
    e.preventDefault();
    if (!newName || !newSlug) return;
    try {
      await api.post('/restaurants/', {
        name: newName,
        slug: newSlug,
        address: newAddress || undefined,
        phone: newPhone || undefined,
      });
      setShowAddModal(false);
      setNewName('');
      setNewSlug('');
      setNewAddress('');
      setNewPhone('');
      confetti({ particleCount: 70, spread: 60, origin: { y: 0.7 } });
      loadSummary();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  const handleToggleStatus = async (restaurantId) => {
    try {
      await api.patch(`/restaurants/${restaurantId}/toggle-status`);
      loadSummary();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  const handleUpdateCommission = async (restaurantId, currentRate) => {
    const val = prompt('Yangi komissiya foizini kiriting (%):', currentRate);
    if (!val || isNaN(val)) return;
    try {
      await api.patch(`/restaurants/${restaurantId}/commission-rate`, {
        commission_percent: parseFloat(val),
      });
      loadSummary();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  const handlePayCommission = async (e) => {
    e.preventDefault();
    if (!payModalRest || !payAmount) return;
    try {
      await api.post(`/restaurants/${payModalRest.id}/commission/pay`, {
        amount: parseFloat(payAmount),
        note: payNote || undefined,
      });
      setPayModalRest(null);
      setPayAmount('');
      setPayNote('');
      confetti({ particleCount: 80, spread: 70, origin: { y: 0.6 } });
      loadSummary();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
      {/* Top Banner */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-gradient-to-r from-theme-surface via-theme-bg to-theme-surface flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-bold mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Developer / Superadmin Paneli</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            RestAron Ekosistemasi 🌐
          </h1>
          <p className="text-xs text-theme-muted mt-1">
            Barcha ulangan restoranlar aylanmasi, komissiyalar monitoringi va tizim nazorati.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center gap-2 active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Yangi Restoran Qo'shish</span>
          </button>

          <button
            onClick={loadSummary}
            className="p-2.5 rounded-xl border border-theme-border hover:border-theme-primary bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white transition-all"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70">
          <div className="flex items-center justify-between text-theme-muted mb-2">
            <span className="text-xs font-semibold">Ulangan Restoranlar</span>
            <Building2 className="w-4 h-4 text-theme-primary" />
          </div>
          <div className="text-2xl font-black text-white">
            {summary?.total_restaurants || 0} ta
          </div>
          <span className="text-[11px] text-emerald-400 mt-1 block">Faol tizim</span>
        </div>

        <div className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70">
          <div className="flex items-center justify-between text-theme-muted mb-2">
            <span className="text-xs font-semibold">Platforma Umumiy Tushumi</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-white">
            {(summary?.total_platform_revenue || 0).toLocaleString()} <span className="text-xs font-normal text-theme-muted">so'm</span>
          </div>
          <span className="text-[11px] text-theme-muted mt-1 block">Barcha buyurtmalar summasi</span>
        </div>

        <div className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70">
          <div className="flex items-center justify-between text-theme-muted mb-2">
            <span className="text-xs font-semibold">Dasturchi Komissiya Daromadi</span>
            <DollarSign className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-400">
            {(summary?.total_platform_commission || 0).toLocaleString()} <span className="text-xs font-normal text-theme-muted">so'm</span>
          </div>
          <span className="text-[11px] text-theme-muted mt-1 block">Hisoblangan ulush</span>
        </div>

        <div className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70">
          <div className="flex items-center justify-between text-theme-muted mb-2">
            <span className="text-xs font-semibold">Kutilayotgan Komissiya</span>
            <CreditCard className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-black text-indigo-400">
            {(summary?.total_pending_commission || 0).toLocaleString()} <span className="text-xs font-normal text-theme-muted">so'm</span>
          </div>
          <span className="text-[11px] text-emerald-400 mt-1 block">
            To'langan: {(summary?.total_paid_commission || 0).toLocaleString()} so'm
          </span>
        </div>
      </div>

      {/* Restaurants Table */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/70 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-theme-primary" />
            <span>Restoranlar va Komissiya Hisob-Kitoblari</span>
          </h3>
          <span className="text-xs text-theme-muted">
            Jami: {summary?.restaurants?.length || 0} ta restoran
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-theme-muted">
            <thead className="text-[11px] uppercase tracking-wider text-theme-muted border-b border-theme-border/60 bg-black/20">
              <tr>
                <th className="py-3 px-4">Restoran</th>
                <th className="py-3 px-4">Komissiya %</th>
                <th className="py-3 px-4">Buyurtmalar</th>
                <th className="py-3 px-4">Umumiy Aylanma</th>
                <th className="py-3 px-4">Hisoblangan Komissiya</th>
                <th className="py-3 px-4">Kutilayotgan</th>
                <th className="py-3 px-4">Holati</th>
                <th className="py-3 px-4 text-right">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme-border/40 font-medium">
              {summary?.restaurants?.map((r) => (
                <tr key={r.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="font-bold text-white text-sm">{r.name}</div>
                    <div className="text-[11px] text-theme-muted font-mono">{r.slug} • {r.phone || 'Tel yo\'q'}</div>
                  </td>

                  <td className="py-3.5 px-4">
                    <button
                      onClick={() => handleUpdateCommission(r.id, r.commission_percent)}
                      className="px-2.5 py-1 rounded-lg bg-theme-primary/10 border border-theme-primary/30 text-theme-primary font-bold hover:bg-theme-primary hover:text-white transition-all"
                      title="Komissiya foizini o'zgartirish"
                    >
                      {r.commission_percent}% ✏️
                    </button>
                  </td>

                  <td className="py-3.5 px-4 text-white font-semibold">
                    {r.total_orders} ta
                  </td>

                  <td className="py-3.5 px-4 text-white font-bold">
                    {(r.total_revenue || 0).toLocaleString()} so'm
                  </td>

                  <td className="py-3.5 px-4 text-amber-400 font-extrabold">
                    {(r.total_commission || 0).toLocaleString()} so'm
                  </td>

                  <td className="py-3.5 px-4 text-indigo-400 font-bold">
                    {(r.pending_commission || 0).toLocaleString()} so'm
                  </td>

                  <td className="py-3.5 px-4">
                    <button
                      onClick={() => handleToggleStatus(r.id)}
                      className={`px-2.5 py-1 rounded-full text-[10px] uppercase font-extrabold transition-all ${
                        r.is_active
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}
                    >
                      {r.is_active ? 'Faol' : 'To\'xtatilgan'}
                    </button>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => {
                        setPayModalRest(r);
                        setPayAmount(r.pending_commission || '');
                      }}
                      className="px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-[11px] shadow-sm active:scale-95 transition-all"
                    >
                      To'lovni qayd etish
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Restaurant Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface shadow-2xl text-theme-text space-y-4">
            <h3 className="text-lg font-bold text-white">Yangi Restoran Qo'shish</h3>
            <form onSubmit={handleCreateRestaurant} className="space-y-3">
              <input
                type="text"
                placeholder="Restoran nomi (masalan: Rayhon Milliy Taomlar)"
                value={newName}
                onChange={(e) => {
                  setNewName(e.target.value);
                  setNewSlug(e.target.value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''));
                }}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                required
              />
              <input
                type="text"
                placeholder="Slug (URL identifikatori, masalan: rayhon)"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                required
              />
              <input
                type="text"
                placeholder="Manzil"
                value={newAddress}
                onChange={(e) => setNewAddress(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              />
              <input
                type="text"
                placeholder="Telefon raqami"
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              />

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl border border-theme-border text-xs text-theme-muted hover:text-white"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow"
                >
                  Qo'shish
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Pay Commission Modal */}
      {payModalRest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface shadow-2xl text-theme-text space-y-4">
            <h3 className="text-lg font-bold text-white">
              Komissiya To'lovini Qayd Etish
            </h3>
            <p className="text-xs text-theme-muted">
              Restoran: <span className="text-white font-bold">{payModalRest.name}</span>
            </p>

            <form onSubmit={handlePayCommission} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                  To'langan summa (so'm):
                </label>
                <input
                  type="number"
                  placeholder="Summa"
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                  Izoh / To'lov cheki (ixtiyoriy):
                </label>
                <input
                  type="text"
                  placeholder="Masalan: Click / Payme orqali sentyabr oyi uchun"
                  value={payNote}
                  onChange={(e) => setPayNote(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setPayModalRest(null)}
                  className="px-4 py-2 rounded-xl border border-theme-border text-xs text-theme-muted hover:text-white"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold shadow-lg"
                >
                  To'lovni saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeveloperDashboard;
