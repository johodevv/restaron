import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import {
  Trophy,
  Users,
  DollarSign,
  TrendingUp,
  Award,
  Calendar,
  RefreshCw,
  ShoppingBag,
  Percent,
  Coins
} from 'lucide-react';

export const WaiterKpiTab = ({ restaurantId }) => {
  const [waiterList, setWaiterList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(1); // 1st of current month
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    return d.toISOString().split('T')[0];
  });

  const fetchKpi = async () => {
    setLoading(true);
    try {
      const data = await api.get(
        `/stats/waiter-kpi-detail?restaurant_id=${restaurantId}&start_date=${startDate}&end_date=${endDate}`
      );
      setWaiterList(data || []);
    } catch (err) {
      console.error('Error fetching waiter KPI:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKpi();
  }, [restaurantId, startDate, endDate]);

  // Aggregate totals
  const totalSalesAll = waiterList.reduce((acc, w) => acc + (w.total_sales || 0), 0);
  const totalCommissionsAll = waiterList.reduce((acc, w) => acc + (w.earned_share || 0), 0);
  const totalOrdersAll = waiterList.reduce((acc, w) => acc + (w.orders_count || 0), 0);

  // Sorted by sales desc
  const sortedWaiters = [...waiterList].sort((a, b) => (b.total_sales || 0) - (a.total_sales || 0));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/85 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider mb-1">
            <Trophy className="w-4 h-4" />
            <span>Xodimlar Samaradorligi</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-white">
            Ofitsiantlar KPI va Tushum Hisoboti
          </h2>
          <p className="text-xs text-theme-muted mt-1">
            Xodimlarning xizmat ko'rsatgan buyurtmalari, umumiy tushumi va ularga hisoblangan komissiya (choychaqa) daromadlari.
          </p>
        </div>

        <button
          onClick={fetchKpi}
          className="self-start sm:self-auto p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs flex items-center gap-2 font-semibold transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Yangilash</span>
        </button>
      </div>

      {/* Date Range Selector */}
      <div className="p-4 rounded-2xl bg-black/40 border border-theme-border/70 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 text-xs text-theme-muted font-semibold">
          <Calendar className="w-4 h-4 text-theme-primary" />
          <span>Hisobot davri:</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs font-mono focus:outline-none focus:border-theme-primary"
          />
          <span>—</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-theme-surface border border-theme-border text-white text-xs font-mono focus:outline-none focus:border-theme-primary"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              const d = new Date().toISOString().split('T')[0];
              setStartDate(d);
              setEndDate(d);
            }}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-zinc-300 font-semibold"
          >
            Bugun
          </button>
          <button
            onClick={() => {
              const d = new Date();
              d.setDate(1);
              setStartDate(d.toISOString().split('T')[0]);
              setEndDate(new Date().toISOString().split('T')[0]);
            }}
            className="px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-zinc-300 font-semibold"
          >
            Shu oy
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-theme-muted font-bold uppercase">Umumiy Ofitsiantlar Savdosi</div>
            <div className="text-xl font-black text-white font-mono mt-0.5">
              {totalSalesAll.toLocaleString()} so'm
            </div>
            <div className="text-[11px] text-emerald-400 font-semibold mt-0.5">
              {totalOrdersAll} ta xizmat ko'rsatilgan buyurtma
            </div>
          </div>
        </div>

        <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
            <Coins className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-theme-muted font-bold uppercase">To'langan Komissiya / Choychaqa</div>
            <div className="text-xl font-black text-purple-300 font-mono mt-0.5">
              {totalCommissionsAll.toLocaleString()} so'm
            </div>
            <div className="text-[11px] text-theme-muted mt-0.5">Xodimlarning sof ulushi</div>
          </div>
        </div>

        <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-theme-muted font-bold uppercase">Oyning Eng Faol Xodimi</div>
            <div className="text-lg font-black text-amber-300 mt-0.5 truncate max-w-[200px]">
              {sortedWaiters[0] ? (sortedWaiters[0].full_name || sortedWaiters[0].username) : '—'}
            </div>
            <div className="text-[11px] text-zinc-400 mt-0.5 font-mono">
              {sortedWaiters[0] ? `${sortedWaiters[0].total_sales?.toLocaleString()} so'm savdo` : 'Hozircha ma\'lumot yo\'q'}
            </div>
          </div>
        </div>
      </div>

      {/* Waiters KPI Grid Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full py-12 text-center text-theme-muted">
            <RefreshCw className="w-6 h-6 mx-auto animate-spin mb-2 text-theme-primary" />
            <span>KPI ko'rsatkichlari hisoblanmoqda...</span>
          </div>
        ) : sortedWaiters.length === 0 ? (
          <div className="col-span-full py-12 text-center text-theme-muted">
            Ushbu davrda ofitsiantlar buyurtmasi mavjud emas
          </div>
        ) : (
          sortedWaiters.map((w, index) => {
            const avgCheck = w.orders_count > 0 ? Math.round(w.total_sales / w.orders_count) : 0;
            const isTop1 = index === 0;

            return (
              <div
                key={w.waiter_id}
                className={`p-5 rounded-3xl glass-card border transition-all flex flex-col justify-between gap-4 shadow-xl ${
                  isTop1
                    ? 'border-amber-500/50 bg-amber-950/10'
                    : 'border-theme-border bg-theme-surface/80'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-2xl flex items-center justify-center font-black text-sm ${
                          isTop1
                            ? 'bg-gradient-to-tr from-amber-500 to-amber-300 text-black shadow-lg shadow-amber-500/20'
                            : 'bg-white/10 text-white'
                        }`}
                      >
                        {isTop1 ? '👑' : `#${index + 1}`}
                      </div>
                      <div>
                        <h4 className="font-bold text-sm text-white">
                          {w.full_name || w.username}
                        </h4>
                        <div className="text-[11px] text-theme-muted font-mono">
                          @{w.username}
                        </div>
                      </div>
                    </div>

                    <div className="px-2.5 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-[10px] font-extrabold">
                      {w.commission_percent}% stavka
                    </div>
                  </div>

                  {/* Metrics summary */}
                  <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-theme-border/60">
                    <div className="p-2.5 rounded-xl bg-black/30 border border-theme-border/50">
                      <div className="text-[10px] text-theme-muted font-semibold uppercase">Buyurtmalar</div>
                      <div className="text-base font-black text-white font-mono mt-0.5">
                        {w.orders_count} ta
                      </div>
                    </div>

                    <div className="p-2.5 rounded-xl bg-black/30 border border-theme-border/50">
                      <div className="text-[10px] text-theme-muted font-semibold uppercase">O'rtacha Chek</div>
                      <div className="text-base font-black text-white font-mono mt-0.5">
                        {avgCheck.toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <div className="p-3 rounded-2xl bg-black/40 border border-theme-border/60 mt-3 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-theme-muted">Keltirilgan Tushum:</span>
                      <span className="font-black text-emerald-400 font-mono">
                        {w.total_sales?.toLocaleString()} so'm
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-theme-muted">Ofitsiant Daromadi:</span>
                      <span className="font-black text-purple-300 font-mono text-sm">
                        {w.earned_share?.toLocaleString()} so'm
                      </span>
                    </div>
                  </div>
                </div>

                {/* Progress bar compared to total */}
                <div>
                  <div className="flex items-center justify-between text-[10px] text-theme-muted mb-1 font-semibold">
                    <span>Umumiy tushumdagi ulushi</span>
                    <span>{totalSalesAll > 0 ? Math.round((w.total_sales / totalSalesAll) * 100) : 0}%</span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-theme-primary to-amber-400 transition-all duration-500"
                      style={{
                        width: `${totalSalesAll > 0 ? (w.total_sales / totalSalesAll) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default WaiterKpiTab;
