import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import BillModal from '../../components/BillModal';
import confetti from 'canvas-confetti';
import {
  Bike,
  CheckCircle2,
  Clock,
  BellRing,
  ChefHat,
  RefreshCw,
  Sparkles,
  AlertCircle,
  Table as TableIcon,
  Receipt,
  Lock
} from 'lucide-react';

export const WaiterDashboard = () => {
  const { user } = useAuth();
  const { addEventListener, playChime } = useWebSocket();
  const [activeTab, setActiveTab] = useState('ready'); // 'ready' | 'active' | 'calls' | 'tables'
  const [orders, setOrders] = useState([]);
  const [tables, setTables] = useState([]);
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // Bill Modal
  const [billModalOpen, setBillModalOpen] = useState(false);
  const [selectedBillTable, setSelectedBillTable] = useState(null);

  const restaurantId = user?.restaurant_id || 1;

  const loadData = async () => {
    try {
      const [ordersData, tablesData, callsData] = await Promise.all([
        api.get(`/orders/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/tables/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).catch(() => []),
      ]);
      setOrders(ordersData || []);
      setTables(tablesData || []);
      setCalls(callsData || []);
    } catch (err) {
      console.error('Waiter load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // Real-time events
    const unsubscribe = addEventListener('*', (event) => {
      if (
        event.type === 'new_order' ||
        event.type === 'order_ready' ||
        event.type === 'order_delivered' ||
        event.type === 'call_waiter' ||
        event.type === 'call_completed' ||
        event.type === 'order_status_updated' ||
        event.type === 'table_status_updated' ||
        event.type === 'table_guest_arrived' ||
        event.type === 'table_unlocked' ||
        event.type === 'table_cleared' ||
        event.type === 'bill_paid'
      ) {
        if (event.type === 'table_guest_arrived' && playChime) {
          playChime('urgent');
        }
        loadData();
      }
    });

    return () => unsubscribe();
  }, [restaurantId, playChime]);

  // "Ulanishni tasdiqlash" (Unlock table) handler!
  const handleUnlockTable = async (tableId, tableNumber) => {
    setActionLoadingId(`unlock_${tableId}`);
    try {
      await api.post(`/tables/${tableId}/unlock`, {});
      confetti({ particleCount: 80, spread: 70, origin: { y: 0.6 } });
      playChime('success');
      await loadData();
    } catch (err) {
      alert(err.message || 'Stolni tasdiqlashda xatolik yuz berdi');
    } finally {
      setActionLoadingId(null);
    }
  };

  // "Qayta qulflash" (Lock table / New PIN) handler!
  const handleLockTable = async (tableId) => {
    setActionLoadingId(`lock_${tableId}`);
    try {
      await api.post(`/tables/${tableId}/lock`, {});
      await loadData();
    } catch (err) {
      alert(err.message || 'Stolni qulflashda xatolik yuz berdi');
    } finally {
      setActionLoadingId(null);
    }
  };


  // "Yetkazib berdim" (Delivered) handler!
  const handleDeliver = async (orderId, tableNumber) => {
    setActionLoadingId(orderId);
    try {
      await api.patch(`/orders/${orderId}/deliver`, {});
      confetti({ particleCount: 80, spread: 60, origin: { y: 0.7 } });
      playChime('success');
      await loadData();
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
    } finally {
      setActionLoadingId(null);
    }
  };

  // Complete waiter call
  const handleCompleteCall = async (callId) => {
    try {
      await api.post(`/orders/calls/${callId}/resolve`);
      playChime('info');
      setCalls((prev) => prev.filter((c) => c.id !== callId));
      await loadData();
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
    }
  };

  // Clear table
  const handleClearTable = async (tableId) => {
    try {
      await api.post(`/tables/${tableId}/clear`);
      playChime('info');
      await loadData();
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
    }
  };

  const handleOpenBill = (t) => {
    setSelectedBillTable(t);
    setBillModalOpen(true);
  };

  // Categorize orders & tables
  const readyOrders = orders.filter((o) => o.status === 'ready');
  const activeOrders = orders.filter((o) => ['pending', 'confirmed', 'preparing'].includes(o.status));
  const pendingUnlockTables = tables.filter((t) => !t.is_unlocked && t.current_pin);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
      {/* Top Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-gradient-to-r from-theme-surface via-theme-bg to-theme-surface flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-bold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ofitsiant Boshqaruv Markazi</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            Salom, {user?.full_name || user?.username}! 👋
          </h1>
          <p className="text-xs text-theme-muted mt-1">
            Yangi mijozlar ulanishini tasdiqlang, buyurtmalarni yetkazib bering va stollar hisobini boshqaring.
          </p>
        </div>

        <button
          onClick={loadData}
          className="self-start sm:self-auto p-2.5 rounded-xl border border-theme-border hover:border-theme-primary bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white transition-all flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Yangilash</span>
        </button>
      </div>

      {/* PENDING UNLOCK GUESTS ALERT (OFITSIANT TASDIQLASHI KERAK) */}
      {pendingUnlockTables.length > 0 && (
        <div className="p-5 rounded-3xl bg-amber-500/15 border-2 border-amber-500/50 shadow-xl shadow-amber-500/10 space-y-3 animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
              <Sparkles className="w-5 h-5 text-amber-400 animate-bounce-subtle" />
              <span>Yangi mehmonlar ({pendingUnlockTables.length} ta stol tasdiqlashni kutmoqda!)</span>
            </div>
            <span className="text-[11px] uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-amber-500 text-black">
              Stolga borish lozim
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
            {pendingUnlockTables.map((t) => (
              <div
                key={t.id}
                className="p-4 rounded-2xl bg-black/40 border border-amber-500/40 flex items-center justify-between gap-3 text-xs shadow-md"
              >
                <div>
                  <div className="font-extrabold text-white text-sm flex items-center gap-1.5">
                    <span>Stol #{t.number}</span>
                    {t.room && <span className="text-[11px] font-normal text-amber-200/80">({t.room})</span>}
                  </div>
                  <div className="text-amber-300 font-mono font-black text-base mt-0.5">
                    Kodi: <span className="underline">{t.current_pin}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleUnlockTable(t.id, t.number)}
                  disabled={actionLoadingId === `unlock_${t.id}`}
                  className="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold text-xs shadow-md active:scale-95 transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{actionLoadingId === `unlock_${t.id}` ? 'Ochilmoqda...' : 'Tasdiqlash'}</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation Tabs with Counters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none no-scrollbar">
        <button
          onClick={() => setActiveTab('ready')}
          className={`flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold whitespace-nowrap transition-all ${
            activeTab === 'ready'
              ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 scale-102'
              : 'bg-theme-surface/60 border border-theme-border text-theme-muted hover:text-white'
          }`}
        >
          <Bike className="w-4 h-4" />
          <span>Tayyor (Yetkazish kerak)</span>
          {readyOrders.length > 0 && (
            <span className="w-5 h-5 rounded-full bg-white text-emerald-600 text-[11px] font-black flex items-center justify-center animate-bounce">
              {readyOrders.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('active')}
          className={`flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold whitespace-nowrap transition-all ${
            activeTab === 'active'
              ? 'bg-theme-primary text-white shadow-glow scale-102'
              : 'bg-theme-surface/60 border border-theme-border text-theme-muted hover:text-white'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Faol buyurtmalar</span>
          <span className="text-[11px] opacity-80">({activeOrders.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('calls')}
          className={`flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold whitespace-nowrap transition-all ${
            activeTab === 'calls'
              ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20 scale-102'
              : 'bg-theme-surface/60 border border-theme-border text-theme-muted hover:text-white'
          }`}
        >
          <BellRing className="w-4 h-4" />
          <span>Chaqiruvlar</span>
          {calls.length > 0 && (
            <span className="w-5 h-5 rounded-full bg-red-500 text-white text-[11px] font-black flex items-center justify-center animate-pulse">
              {calls.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('tables')}
          className={`flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold whitespace-nowrap transition-all ${
            activeTab === 'tables'
              ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 scale-102'
              : 'bg-theme-surface/60 border border-theme-border text-theme-muted hover:text-white'
          }`}
        >
          <TableIcon className="w-4 h-4" />
          <span>Stollar & Cheklar ({tables.length})</span>
        </button>
      </div>

      {/* TAB 1: READY ORDERS (YETKAZISH KERAK — 'YETKAZIB BERDIM' TUGMASI) */}
      {activeTab === 'ready' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              Oshxona tayyorlagan taomlar (Mijozga yetkazish lozim)
            </h3>
            <span className="text-xs text-theme-muted">
              Jami: {readyOrders.length} ta
            </span>
          </div>

          {readyOrders.length === 0 ? (
            <div className="p-12 text-center rounded-3xl glass-card border border-theme-border text-theme-muted">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-emerald-400/50" />
              <p className="text-base font-semibold text-white">
                Barcha tayyor taomlar yetkazib berilgan!
              </p>
              <p className="text-xs mt-1">
                Yangi taomlar tayyor bo'lishi bilan bu yerda paydo bo'ladi.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {readyOrders.map((order) => (
                <div
                  key={order.id}
                  className="p-5 rounded-2xl glass-card border-2 border-emerald-500/50 bg-emerald-950/20 shadow-xl shadow-emerald-500/10 flex flex-col justify-between space-y-4"
                >
                  <div>
                    {/* Header */}
                    <div className="flex items-center justify-between pb-3 border-b border-emerald-500/20">
                      <div>
                        <span className="text-2xl font-black text-white">
                          Stol #{order.table_number || order.table_id}
                        </span>
                        <div className="text-xs text-emerald-400 font-semibold mt-0.5">
                          {order.order_number}
                        </div>
                      </div>
                      <span className="text-[11px] font-extrabold uppercase px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 animate-pulse">
                        🍳 Tayyor!
                      </span>
                    </div>

                    {/* Meta info */}
                    <div className="py-3 space-y-1.5 text-xs text-theme-muted">
                      <div>
                        Mijoz: <span className="text-white font-medium">{order.customer_name || 'Noma\'lum'}</span>
                      </div>
                      <div>
                        Taomlar soni: <span className="text-white font-medium">{order.items_count} xil</span>
                      </div>
                      <div>
                        Jami summa: <span className="text-white font-bold">{(order.total || 0).toLocaleString()} so'm</span>
                      </div>
                    </div>
                  </div>

                  {/* PROMINENT "YETKAZIB BERDIM" BUTTON */}
                  <button
                    onClick={() => handleDeliver(order.id, order.table_number)}
                    disabled={actionLoadingId === order.id}
                    className="w-full py-4 rounded-xl bg-gradient-to-r from-emerald-500 via-emerald-600 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-black text-sm uppercase tracking-wider shadow-lg shadow-emerald-500/30 flex items-center justify-center gap-2 active:scale-98 transition-all"
                  >
                    {actionLoadingId === order.id ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        <span>Belgilanmoqda...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-5 h-5" />
                        <span>Yetkazib berdim</span>
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ACTIVE ORDERS */}
      {activeTab === 'active' && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Tayyorlanayotgan va Kutilayotgan Buyurtmalar
          </h3>

          {activeOrders.length === 0 ? (
            <div className="p-12 text-center rounded-3xl glass-card border border-theme-border text-theme-muted">
              <Clock className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <p className="text-base font-semibold">Faol buyurtmalar yo'q</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeOrders.map((order) => (
                <div
                  key={order.id}
                  className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70 space-y-3"
                >
                  <div className="flex items-center justify-between pb-3 border-b border-theme-border/60">
                    <div>
                      <span className="text-xl font-bold text-white">
                        Stol #{order.table_number || order.table_id}
                      </span>
                      <div className="text-xs text-theme-muted">{order.order_number}</div>
                    </div>
                    <span className="text-[11px] font-bold uppercase px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
                      {order.status === 'pending' ? 'Kutilmoqda' : 'Oshxonada'}
                    </span>
                  </div>

                  <div className="text-xs space-y-1 text-theme-muted">
                    <div>Jami summa: <span className="text-white font-bold">{(order.total || 0).toLocaleString()} so'm</span></div>
                    <div>Taomlar: <span className="text-white">{order.items_count} xil</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: WAITER CALLS */}
      {activeTab === 'calls' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <BellRing className="w-4 h-4 text-amber-400" />
              <span>Mijozlarning Chaqiruvlari ({calls.length})</span>
            </h3>
            {calls.length > 0 && (
              <span className="text-xs text-amber-400 font-bold animate-pulse">
                🔔 {calls.length} ta stol chaqirmoqda!
              </span>
            )}
          </div>

          {calls.length === 0 ? (
            <div className="p-12 text-center rounded-3xl glass-card border border-theme-border text-theme-muted">
              <BellRing className="w-12 h-12 mx-auto mb-3 opacity-40 text-amber-400" />
              <p className="text-base font-semibold text-white">Hech qaysi stol chaqirmayapti</p>
              <p className="text-xs mt-1">Mijoz chaqirganda darhol ovozli xabar keladi va shu yerda ko'rinadi.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {calls.map((call) => (
                <div
                  key={call.id}
                  className="p-5 rounded-2xl glass-card border-2 border-amber-500/60 bg-amber-950/25 shadow-xl shadow-amber-500/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-black text-white">
                        Stol #{call.table_number || call.table_id}
                      </span>
                      {call.room && (
                        <span className="text-xs px-2 py-0.5 rounded-md bg-white/10 text-theme-muted">
                          {call.room}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-amber-300 font-medium">
                      Sabab: <span className="text-white font-bold">"{call.note || 'Ofitsiant yordami kerak'}"</span>
                    </p>
                    <div className="text-[11px] text-theme-muted flex items-center gap-1 pt-1">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(call.created_at).toLocaleTimeString('uz-UZ')}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleCompleteCall(call.id)}
                    className="px-5 py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold text-xs shadow-lg shadow-orange-500/20 active:scale-95 transition-all whitespace-nowrap flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Bordim (Yakunlash)</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: TABLES STATUS & BILLS */}
      {activeTab === 'tables' && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Stollar Holati va Hisob-Kitob
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {tables.map((t) => {
              const statusStr = (t.status || '').toLowerCase();
              const isOccupied = statusStr === 'occupied';
              const isReserved = statusStr === 'reserved';

              return (
                <div
                  key={t.id}
                  className={`p-5 rounded-3xl border flex flex-col justify-between gap-3 transition-all ${
                    isOccupied
                      ? 'border-red-500/40 bg-red-950/15 shadow-md'
                      : isReserved
                      ? 'border-amber-500/40 bg-amber-950/15'
                      : 'border-theme-border bg-theme-surface/70'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-2xl font-black text-white">
                        #{t.number}
                      </div>
                      <div className="text-xs text-theme-muted">
                        {t.room || 'Asosiy zal'}
                      </div>
                    </div>

                    <span
                      className={`px-2.5 py-1 rounded-lg font-bold text-[10px] uppercase ${
                        !t.is_unlocked && t.current_pin
                          ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50 animate-pulse'
                          : isOccupied
                          ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                          : isReserved
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {!t.is_unlocked && t.current_pin ? '🔒 Kod Kutilmoqda' : (isOccupied ? 'Band' : isReserved ? 'Bron' : "Bo'sh")}
                    </span>
                  </div>

                  {/* If table is locked with pin */}
                  {!t.is_unlocked && t.current_pin && (
                    <div className="p-3 rounded-2xl bg-amber-500/15 border border-amber-500/40 text-center space-y-1.5">
                      <span className="text-[10px] uppercase text-amber-300 font-bold block">Mijoz Kirdi (Kodi):</span>
                      <span className="text-xl font-mono font-black text-amber-300 block">{t.current_pin}</span>
                      <button
                        onClick={() => handleUnlockTable(t.id, t.number)}
                        disabled={actionLoadingId === `unlock_${t.id}`}
                        className="w-full py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold text-xs shadow-md active:scale-95 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>{actionLoadingId === `unlock_${t.id}` ? 'Ochilmoqda...' : 'Ulanishni Tasdiqlash'}</span>
                      </button>
                    </div>
                  )}

                  <div className="space-y-2 pt-2 border-t border-theme-border/50">
                    <button
                      onClick={() => handleOpenBill(t)}
                      className="w-full py-2.5 rounded-xl bg-theme-primary/15 hover:bg-theme-primary/25 border border-theme-primary/30 text-theme-primary text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-sm"
                    >
                      <Receipt className="w-3.5 h-3.5" />
                      <span>Chek / Hisobni ko'rish</span>
                    </button>

                    {t.is_unlocked && (
                      <button
                        onClick={() => handleLockTable(t.id)}
                        disabled={actionLoadingId === `lock_${t.id}`}
                        className="w-full py-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 font-bold text-xs flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>Qayta qulflash (PIN)</span>
                      </button>
                    )}

                    {isOccupied && (
                      <button
                        onClick={() => handleClearTable(t.id)}
                        className="w-full py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-theme-border text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Stolni bo'shatish</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Table Bill Modal */}
      <BillModal
        isOpen={billModalOpen}
        onClose={() => setBillModalOpen(false)}
        tableId={selectedBillTable?.id}
        tableNumber={selectedBillTable?.number}
        isStaff={true}
        onTableCleared={loadData}
      />
    </div>
  );
};

export default WaiterDashboard;

