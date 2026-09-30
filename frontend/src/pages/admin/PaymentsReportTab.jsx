import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import {
  FileSpreadsheet,
  Printer,
  Calendar,
  DollarSign,
  CreditCard,
  Smartphone,
  Wallet,
  Coins,
  RefreshCw,
  Search,
  CheckCircle,
  Clock,
  UserCheck
} from 'lucide-react';
import ThermalReceiptModal from '../../components/ThermalReceiptModal';

export const PaymentsReportTab = ({ restaurantId }) => {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    return d.toISOString().split('T')[0];
  });
  const [filterWaiter, setFilterWaiter] = useState('');
  const [searchTable, setSearchTable] = useState('');

  // Thermal Print Modal
  const [thermalModalOpen, setThermalModalOpen] = useState(false);
  const [thermalRawText, setThermalRawText] = useState('');
  const [thermalModalTitle, setThermalModalTitle] = useState('Hisobot Cheki');
  const [actionLoading, setActionLoading] = useState(null);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const data = await api.get(
        `/stats/payments-report?restaurant_id=${restaurantId}&start_date=${startDate}&end_date=${endDate}`
      );
      setReportData(data);
    } catch (err) {
      console.error('Error fetching payments report:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [restaurantId, startDate, endDate]);

  // Set preset dates
  const handlePresetDate = (type) => {
    const now = new Date();
    if (type === 'today') {
      const todayStr = now.toISOString().split('T')[0];
      setStartDate(todayStr);
      setEndDate(todayStr);
    } else if (type === 'yesterday') {
      const y = new Date(now);
      y.setDate(y.getDate() - 1);
      const yStr = y.toISOString().split('T')[0];
      setStartDate(yStr);
      setEndDate(yStr);
    } else if (type === 'this_month') {
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
      const todayStr = now.toISOString().split('T')[0];
      setStartDate(firstDay);
      setEndDate(todayStr);
    }
  };

  // Generate X-Report or Z-Report
  const handleShiftReport = async (reportType) => {
    setActionLoading(reportType);
    try {
      const res = await api.post('/receipts/shift-report', {
        restaurant_id: restaurantId,
        report_type: reportType === 'X' ? 'x_report' : 'z_report',
      });
      setThermalRawText(res.raw_text);
      const shiftNum = res.shift_number || 1;
      setThermalModalTitle(
        reportType === 'X'
          ? `X-Hisobot (Smena #${shiftNum})`
          : `Z-Hisobot (Kunlik kassa yopilishi #${shiftNum})`
      );
      setThermalModalOpen(true);
      if (reportType === 'Z') {
        fetchReport();
      }
    } catch (err) {
      alert(err.message || 'Hisobot shakllantirishda xatolik yuz berdi');
    } finally {
      setActionLoading(null);
    }
  };

  // View receipt for a specific order - search receipts archive
  const handleViewOrderReceipt = async (orderId, orderNum) => {
    setActionLoading(`order_${orderId}`);
    try {
      const res = await api.get(
        `/receipts/?restaurant_id=${restaurantId}&search=${orderNum}&limit=5`
      );
      const found = (res || []).find((r) => r.order_id === orderId) || (res || [])[0];
      if (found) {
        const reprintRes = await api.post(`/receipts/${found.id}/reprint`);
        setThermalRawText(reprintRes.raw_text);
        setThermalModalTitle(`Chek #${orderNum} (Arxivdan)`);
        setThermalModalOpen(true);
      } else {
        alert(`#${orderNum} buyurtma uchun arxivda chek topilmadi`);
      }
    } catch (err) {
      alert(err.message || "Chek matnini yuklab bolmadi");
    } finally {
      setActionLoading(null);
    }
  };


  // Filter rows
  const filteredRows = (reportData?.rows || []).filter((r) => {
    const matchWaiter = !filterWaiter || r.waiter_name.toLowerCase().includes(filterWaiter.toLowerCase());
    const matchTable = !searchTable || r.table_name.toLowerCase().includes(searchTable.toLowerCase()) || String(r.order_number).includes(searchTable);
    return matchWaiter && matchTable;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header bar matching Photo 3 "Отчет по оплатам" */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/85 shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 text-theme-primary text-xs font-bold uppercase tracking-wider mb-1">
            <FileSpreadsheet className="w-4 h-4" />
            <span>Kassa Nazorati va Hisoboti</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-white">
            Отчет по оплатам (Kassa Tushumi Hisoboti)
          </h2>
          <p className="text-xs text-theme-muted mt-1">
            Ali Poster andozasidagi kassa to‘lovlari, ofitsiantlar ulushi va kunlik X/Z hisobotlar.
          </p>
        </div>

        {/* Action Buttons: X-Report & Z-Report */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={() => handleShiftReport('X')}
            disabled={actionLoading === 'X'}
            className="px-4 py-2.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/40 text-blue-300 font-bold text-xs flex items-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-50"
          >
            <Printer className="w-4 h-4 text-blue-400" />
            <span>{actionLoading === 'X' ? 'Chiqarilmoqda...' : '⚡ X-Hisobot (Oraliq)'}</span>
          </button>

          <button
            onClick={() => {
              if (window.confirm("Kunlik smenani yopish va Z-Hisobot chiqarishni tasdiqlaysizmi?")) {
                handleShiftReport('Z');
              }
            }}
            disabled={actionLoading === 'Z'}
            className="px-4 py-2.5 rounded-xl bg-emerald-600/25 hover:bg-emerald-600/35 border border-emerald-500/50 text-emerald-300 font-bold text-xs flex items-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-50"
          >
            <Printer className="w-4 h-4 text-emerald-400" />
            <span>{actionLoading === 'Z' ? 'Yopilmoqda...' : '🔒 Z-Hisobot (Smenani yopish)'}</span>
          </button>

          <button
            onClick={fetchReport}
            className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs transition-all"
            title="Yangilash"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Date Filter & Presets */}
      <div className="p-4 rounded-2xl bg-black/40 border border-theme-border/70 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-theme-muted font-semibold">
            <Calendar className="w-4 h-4 text-theme-primary" />
            <span>Davr:</span>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs font-mono focus:outline-none focus:border-theme-primary"
            />
            <span className="text-theme-muted text-xs">—</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs font-mono focus:outline-none focus:border-theme-primary"
            />
          </div>

          {/* Quick preset buttons */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handlePresetDate('today')}
              className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] text-zinc-300 font-medium"
            >
              Bugun
            </button>
            <button
              onClick={() => handlePresetDate('yesterday')}
              className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] text-zinc-300 font-medium"
            >
              Kecha
            </button>
            <button
              onClick={() => handlePresetDate('this_month')}
              className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] text-zinc-300 font-medium"
            >
              Shu oy
            </button>
          </div>
        </div>

        {/* Table & Waiter quick search */}
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              placeholder="Stol yoki chek #..."
              value={searchTable}
              onChange={(e) => setSearchTable(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs focus:outline-none focus:border-theme-primary w-36 sm:w-44"
            />
          </div>

          <input
            type="text"
            placeholder="Ofitsiant..."
            value={filterWaiter}
            onChange={(e) => setFilterWaiter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs focus:outline-none focus:border-theme-primary w-32"
          />
        </div>
      </div>

      {/* KPI Cards (Breakdown matching Photo 3 totals) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-2xl bg-theme-surface/80 border border-theme-border flex flex-col justify-between">
          <div className="flex items-center justify-between text-theme-muted text-[11px] font-bold uppercase">
            <span>Jami Tushum</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-lg sm:text-xl font-black text-white font-mono">
            {reportData ? `${reportData.total_revenue?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-emerald-400 font-semibold mt-1">
            {reportData?.orders_count || 0} ta buyurtma
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between text-emerald-400 text-[11px] font-bold uppercase">
            <span>Наличные (Naqd)</span>
            <Coins className="w-4 h-4" />
          </div>
          <div className="mt-2 text-lg sm:text-xl font-black text-emerald-300 font-mono">
            {reportData ? `${reportData.total_cash?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-theme-muted mt-1">Kassadagi naqd pul</div>
        </div>

        <div className="p-4 rounded-2xl bg-blue-950/20 border border-blue-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between text-blue-400 text-[11px] font-bold uppercase">
            <span>Безналичные (Karta)</span>
            <CreditCard className="w-4 h-4" />
          </div>
          <div className="mt-2 text-lg sm:text-xl font-black text-blue-300 font-mono">
            {reportData ? `${reportData.total_card?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-theme-muted mt-1">Uzcard / Humo</div>
        </div>

        <div className="p-4 rounded-2xl bg-cyan-950/20 border border-cyan-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between text-cyan-400 text-[11px] font-bold uppercase">
            <span>Click / Payme</span>
            <Smartphone className="w-4 h-4" />
          </div>
          <div className="mt-2 text-lg sm:text-xl font-black text-cyan-300 font-mono">
            {reportData ? `${reportData.total_click?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-theme-muted mt-1">Onlayn to'lovlar</div>
        </div>

        <div className="p-4 rounded-2xl bg-amber-950/20 border border-amber-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between text-amber-400 text-[11px] font-bold uppercase">
            <span>Долг (Nasiya)</span>
            <Wallet className="w-4 h-4" />
          </div>
          <div className="mt-2 text-lg sm:text-xl font-black text-amber-300 font-mono">
            {reportData ? `${reportData.total_debt?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-amber-400/80 mt-1">Qarz daftari</div>
        </div>

        <div className="p-4 rounded-2xl bg-purple-950/20 border border-purple-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between text-purple-400 text-[11px] font-bold uppercase">
            <span>Ofitsiantlar Ulushi</span>
            <UserCheck className="w-4 h-4" />
          </div>
          <div className="mt-2 text-lg sm:text-xl font-black text-purple-300 font-mono">
            {reportData ? `${reportData.total_waiter_earnings?.toLocaleString()} so'm` : '0'}
          </div>
          <div className="text-[10px] text-theme-muted mt-1">Xizmat haqi ulushi</div>
        </div>
      </div>

      {/* Main Table: Exact Columns matching Photo 3 */}
      <div className="rounded-3xl glass-card border border-theme-border overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-black/50 text-theme-muted uppercase tracking-wider text-[11px] border-b border-theme-border">
              <tr>
                <th className="py-3 px-3.5 font-bold">Дата открытия</th>
                <th className="py-3 px-3 font-bold">Дата закрытия</th>
                <th className="py-3 px-3 font-bold">Стол</th>
                <th className="py-3 px-2.5 font-bold">Чек №</th>
                <th className="py-3 px-3 font-bold text-right text-emerald-400">Наличные</th>
                <th className="py-3 px-3 font-bold text-right text-blue-400">Безналичные</th>
                <th className="py-3 px-3 font-bold text-right text-cyan-400">Click/Payme</th>
                <th className="py-3 px-3 font-bold text-right text-amber-400">Долг (Nasiya)</th>
                <th className="py-3 px-3 font-bold">Официант</th>
                <th className="py-3 px-3 font-bold text-right text-purple-400">Заработок официанта</th>
                <th className="py-3 px-3.5 font-bold text-right text-white">Итого</th>
                <th className="py-3 px-3 font-bold text-center">Чек</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-theme-border/40 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-theme-muted font-sans text-xs">
                    <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-2 text-theme-primary" />
                    <span>Hisobot yuklanmoqda...</span>
                  </td>
                </tr>
              ) : filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={12} className="py-12 text-center text-theme-muted font-sans text-xs">
                    Ushbu sanada yopilgan cheklar topilmadi
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr
                    key={row.order_id}
                    className="hover:bg-white/5 transition-colors text-zinc-300"
                  >
                    <td className="py-2.5 px-3.5 text-zinc-400 text-[11px] whitespace-nowrap">
                      {row.created_at}
                    </td>
                    <td className="py-2.5 px-3 text-zinc-400 text-[11px] whitespace-nowrap">
                      {row.closed_at}
                    </td>
                    <td className="py-2.5 px-3 font-bold text-white font-sans whitespace-nowrap">
                      {row.table_name}
                    </td>
                    <td className="py-2.5 px-2.5 text-theme-primary font-bold">
                      #{row.order_number}
                    </td>
                    <td className="py-2.5 px-3 text-right text-emerald-300">
                      {row.cash_amount > 0 ? row.cash_amount.toLocaleString() : '0'}
                    </td>
                    <td className="py-2.5 px-3 text-right text-blue-300">
                      {row.card_amount > 0 ? row.card_amount.toLocaleString() : '0'}
                    </td>
                    <td className="py-2.5 px-3 text-right text-cyan-300">
                      {row.click_amount > 0 ? row.click_amount.toLocaleString() : '0'}
                    </td>
                    <td className="py-2.5 px-3 text-right text-amber-300">
                      {row.debt_amount > 0 ? row.debt_amount.toLocaleString() : '0'}
                    </td>
                    <td className="py-2.5 px-3 font-sans text-white text-[11.5px] whitespace-nowrap">
                      {row.waiter_name}
                    </td>
                    <td className="py-2.5 px-3 text-right text-purple-300">
                      {row.waiter_earning > 0 ? row.waiter_earning.toLocaleString() : '0'}
                    </td>
                    <td className="py-2.5 px-3.5 text-right font-black text-white text-[12.5px]">
                      {row.total.toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        onClick={() => handleViewOrderReceipt(row.order_id, row.order_number)}
                        disabled={actionLoading === `order_${row.order_id}`}
                        className="p-1.5 rounded-lg bg-white/5 hover:bg-white/15 text-zinc-300 hover:text-white transition-colors"
                        title="Xprinter chekini ko'rish va chop etish"
                      >
                        <Printer className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>

            {/* Bottom Total Row matching Photo 3 */}
            {reportData && filteredRows.length > 0 && (
              <tfoot className="bg-black/80 border-t-2 border-theme-border font-mono font-black text-xs text-white">
                <tr>
                  <td colSpan={4} className="py-3 px-3.5 font-bold uppercase tracking-wider text-theme-muted font-sans">
                    Итого (Jami):
                  </td>
                  <td className="py-3 px-3 text-right text-emerald-400">
                    {reportData.total_cash?.toLocaleString()}
                  </td>
                  <td className="py-3 px-3 text-right text-blue-400">
                    {reportData.total_card?.toLocaleString()}
                  </td>
                  <td className="py-3 px-3 text-right text-cyan-400">
                    {reportData.total_click?.toLocaleString()}
                  </td>
                  <td className="py-3 px-3 text-right text-amber-400">
                    {reportData.total_debt?.toLocaleString()}
                  </td>
                  <td className="py-3 px-3"></td>
                  <td className="py-3 px-3 text-right text-purple-400">
                    {reportData.total_waiter_earnings?.toLocaleString()}
                  </td>
                  <td className="py-3 px-3.5 text-right text-sm text-theme-primary">
                    {reportData.total_revenue?.toLocaleString()} so'm
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* Realistic Thermal Receipt Modal for Xprinter */}
      <ThermalReceiptModal
        isOpen={thermalModalOpen}
        onClose={() => setThermalModalOpen(false)}
        title={thermalModalTitle}
        rawText={thermalRawText}
        paperWidth={80}
      />
    </div>
  );
};

export default PaymentsReportTab;
