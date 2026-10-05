import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import {
  Receipt,
  Printer,
  Search,
  Calendar,
  Clock,
  Archive,
  RefreshCw,
  CreditCard,
  Coins,
  Smartphone,
  Wallet,
  ShieldCheck,
  FileText
} from 'lucide-react';
import ThermalReceiptModal from '../../components/ThermalReceiptModal';

export const ReceiptsArchiveTab = ({ restaurantId }) => {
  const [receipts, setReceipts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [receiptType, setReceiptType] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');

  // Thermal Receipt Modal
  const [thermalModalOpen, setThermalModalOpen] = useState(false);
  const [thermalRawText, setThermalRawText] = useState('');
  const [thermalTitle, setThermalTitle] = useState('Arxiv Cheki');
  const [reprintingId, setReprintingId] = useState(null);

  const fetchReceipts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ restaurant_id: restaurantId, limit: '100' });
      if (search.trim()) params.append('search', search.trim());
      if (receiptType) params.append('receipt_type', receiptType);
      if (paymentMethod) params.append('payment_method', paymentMethod);

      const data = await api.get(`/receipts/?${params.toString()}`);
      setReceipts(data || []);
    } catch (err) {
      console.error('Error fetching receipts archive:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReceipts();
  }, [restaurantId, receiptType, paymentMethod]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchReceipts();
  };

  // Reprint Receipt from Archive
  const handleReprint = async (r) => {
    setReprintingId(r.id);
    try {
      const res = await api.post(`/receipts/${r.id}/reprint`);
      setThermalRawText(res.raw_text);
      setThermalTitle(`Chek #${r.receipt_number} (Arxivdan)`);
      setThermalModalOpen(true);
    } catch (err) {
      alert(err.message || 'Chek matnini yuklashda xatolik');
    } finally {
      setReprintingId(null);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/85 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-theme-primary text-xs font-bold uppercase tracking-wider mb-1">
            <Archive className="w-4 h-4" />
            <span>3 Yillik Tarixiy Xotira</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-white">
            Cheklar Arxivi (Xprinter Re-print)
          </h2>
          <p className="text-xs text-theme-muted mt-1">
            Chiqarilgan har bir kassa cheki va oshxona begunogi 3 yilgacha arxivda saqlanadi va istalgan paytda qayta chop etiladi.
          </p>
        </div>

        <button
          onClick={fetchReceipts}
          className="self-start sm:self-auto p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs flex items-center gap-2 font-semibold transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Yangilash</span>
        </button>
      </div>

      {/* Security & Retention Info Banner */}
      <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-xs text-emerald-300">
        <ShieldCheck className="w-5 h-5 shrink-0 text-emerald-400" />
        <div>
          <span className="font-bold">O'zgarmas Xavfsiz Saqlov:</span> Har bir chekning to'liq termo-shakl matni, to'lov turlari va ofitsiant imzosi arxivlangan. Soliq va ichki taftish tekshiruvlari uchun to'liq mos keladi.
        </div>
      </div>

      {/* Umumiy hisobot — ro'yxatdagi TO'LANGAN cheklar bo'yicha */}
      {(() => {
        // Oshxona begunoklari pul emas — ularni hisobga qo'shmaymiz.
        const paid = receipts.filter(
          (r) => r.receipt_type !== 'kitchen' && (r.total_amount || 0) > 0
        );
        const jami = paid.reduce((s, r) => s + (r.total_amount || 0), 0);
        const byMethod = (m) =>
          paid.filter((r) => r.payment_method === m).reduce((s, r) => s + (r.total_amount || 0), 0);
        const naqd = byMethod('cash');
        const karta = byMethod('card');
        const click = byMethod('click');
        const nasiya = byMethod('debt');

        const Karta = ({ nom, qiymat, rang, soni }) => (
          <div className={`p-3.5 rounded-2xl border bg-black/30 ${rang}`}>
            <div className="text-[11px] font-bold text-theme-muted uppercase tracking-wider">
              {nom}
            </div>
            <div className="text-lg font-black text-white font-mono mt-1">
              {Math.round(qiymat).toLocaleString()} <span className="text-xs font-bold">so'm</span>
            </div>
            {soni !== undefined && (
              <div className="text-[10px] text-theme-muted mt-0.5">{soni} ta chek</div>
            )}
          </div>
        );

        return (
          <div className="p-4 rounded-2xl bg-theme-surface/70 border border-theme-border/70 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h3 className="text-sm font-black text-white">
                📊 Umumiy hisobot — to'langan cheklar
              </h3>
              <span className="text-[11px] text-theme-muted">
                Quyidagi ro'yxatdagi {paid.length} ta chek bo'yicha
                {(receiptType || paymentMethod || search) ? ' (filtr qo\'llangan)' : ''}
              </span>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-2.5">
              <Karta nom="Jami tushum" qiymat={jami} soni={paid.length}
                     rang="border-emerald-500/40" />
              <Karta nom="💵 Naqd" qiymat={naqd} rang="border-theme-border" />
              <Karta nom="💳 Karta" qiymat={karta} rang="border-theme-border" />
              <Karta nom="📲 Click" qiymat={click} rang="border-theme-border" />
              <Karta nom="📝 Nasiya" qiymat={nasiya} rang="border-amber-500/40" />
            </div>
          </div>
        );
      })()}

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-black/40 border border-theme-border/70 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Receipt Type Filter */}
          <select
            value={receiptType}
            onChange={(e) => setReceiptType(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs focus:outline-none focus:border-theme-primary"
          >
            <option value="">Barcha Chek Turlari</option>
            <option value="final_bill">Hisob Cheklari (Final Bill)</option>
            <option value="pre_check">Oraliq Cheklar (Pre-check)</option>
            <option value="kitchen">Oshxona Begunoklari (Kitchen)</option>
          </select>

          {/* Payment Method Filter */}
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs focus:outline-none focus:border-theme-primary"
          >
            <option value="">Barcha To'lovlar</option>
            <option value="cash">Naqd pul</option>
            <option value="card">Uzcard / Humo</option>
            <option value="click">Click / Payme</option>
            <option value="debt">Nasiya / Qarz</option>
          </select>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              placeholder="Chek #, stol yoki ofitsiant..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs focus:outline-none focus:border-theme-primary w-48 sm:w-64"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors"
          >
            Izlash
          </button>
        </form>
      </div>

      {/* Receipts Table */}
      <div className="rounded-3xl glass-card border border-theme-border overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/50 text-theme-muted uppercase tracking-wider text-[11px] border-b border-theme-border">
              <tr>
                <th className="py-3 px-3.5 font-bold">Chek Raqami</th>
                <th className="py-3 px-3 font-bold">Sana va Vaqt</th>
                <th className="py-3 px-3 font-bold">Stol / Xona</th>
                <th className="py-3 px-3 font-bold">Ofitsiant</th>
                <th className="py-3 px-3 font-bold">To'lov Turi</th>
                <th className="py-3 px-3 font-bold text-right">Xizmat Haqi</th>
                <th className="py-3 px-3.5 font-bold text-right text-white">Jami Summa</th>
                <th className="py-3 px-3.5 font-bold text-center">Xprinter</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme-border/40 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-theme-muted font-sans text-xs">
                    <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-2 text-theme-primary" />
                    <span>Arxiv cheklari yuklanmoqda...</span>
                  </td>
                </tr>
              ) : receipts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-theme-muted font-sans text-xs">
                    Ushbu parametrlar bo'yicha arxiv cheklari topilmadi
                  </td>
                </tr>
              ) : (
                receipts.map((r) => {
                  const pMethod = r.payment_method;
                  return (
                    <tr key={r.id} className="hover:bg-white/5 transition-colors text-zinc-300">
                      <td className="py-3 px-3.5 text-theme-primary font-bold">
                        #{r.receipt_number}
                      </td>
                      <td className="py-3 px-3 text-zinc-400 text-[11px] whitespace-nowrap">
                        {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
                      </td>
                      <td className="py-3 px-3 font-bold text-white font-sans whitespace-nowrap">
                        {r.table_name || '—'}
                      </td>
                      <td className="py-3 px-3 font-sans text-zinc-300 whitespace-nowrap">
                        {r.waiter_name || '—'}
                      </td>
                      <td className="py-3 px-3 font-sans text-xs">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-white/5 border border-white/10 text-zinc-300">
                          {pMethod === 'cash' && <Coins className="w-3 h-3 text-emerald-400" />}
                          {pMethod === 'card' && <CreditCard className="w-3 h-3 text-blue-400" />}
                          {pMethod === 'click' && <Smartphone className="w-3 h-3 text-cyan-400" />}
                          {pMethod === 'debt' && <Wallet className="w-3 h-3 text-amber-400" />}
                          <span>{pMethod === 'cash' ? 'Naqd' : pMethod === 'card' ? 'Karta' : pMethod === 'click' ? 'Click' : pMethod === 'debt' ? 'Nasiya' : pMethod || '—'}</span>
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right text-zinc-400">
                        {r.service_fee_amount > 0 ? `${r.service_fee_amount.toLocaleString()} (${r.service_fee_percent}%)` : '0%'}
                      </td>
                      <td className="py-3 px-3.5 text-right font-black text-white text-sm">
                        {r.total_amount?.toLocaleString()} so'm
                      </td>
                      <td className="py-3 px-3.5 text-center font-sans">
                        <button
                          onClick={() => handleReprint(r)}
                          disabled={reprintingId === r.id}
                          className="px-3 py-1.5 rounded-xl bg-theme-primary/15 hover:bg-theme-primary/25 border border-theme-primary/40 text-theme-primary hover:text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-sm active:scale-95 disabled:opacity-50 mx-auto"
                        >
                          <Printer className={`w-3.5 h-3.5 ${reprintingId === r.id ? 'animate-pulse' : ''}`} />
                          <span>{reprintingId === r.id ? 'Yuklanmoqda...' : 'Chop etish'}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Realistic Thermal Receipt Modal for Xprinter */}
      <ThermalReceiptModal
        isOpen={thermalModalOpen}
        onClose={() => setThermalModalOpen(false)}
        title={thermalTitle}
        rawText={thermalRawText}
        paperWidth={80}
      />
    </div>
  );
};

export default ReceiptsArchiveTab;
