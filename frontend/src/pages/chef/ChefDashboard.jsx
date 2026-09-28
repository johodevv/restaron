import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import confetti from 'canvas-confetti';
import {
  ChefHat,
  CheckCircle2,
  Clock,
  RefreshCw,
  Sparkles,
  Flame,
  Utensils
} from 'lucide-react';

export const ChefDashboard = () => {
  const { user } = useAuth();
  const { addEventListener, playChime } = useWebSocket();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const restaurantId = user?.restaurant_id || 1;

  const loadOrders = async () => {
    try {
      // Oshxonadagi barcha faol buyurtmalarni to'liq tarkibi bilan olish
      const list = await api.get(`/orders/?restaurant_id=${restaurantId}`);
      // pending, confirmed, preparing, ready bo'lganlarni saralash
      const activeList = list.filter((o) => ['pending', 'confirmed', 'preparing'].includes(o.status));

      // Har birining batafsil tarkibini yuklash
      const detailed = await Promise.all(
        activeList.map(async (o) => {
          try {
            return await api.get(`/orders/${o.id}`);
          } catch {
            return null;
          }
        })
      );

      setOrders(detailed.filter(Boolean));
    } catch (err) {
      console.error('Chef orders error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();

    const unsubscribe = addEventListener('*', (event) => {
      if (
        event.type === 'new_order' ||
        event.type === 'order_status_updated' ||
        event.type === 'order_ready'
      ) {
        loadOrders();
      }
    });

    return () => unsubscribe();
  }, [restaurantId]);

  // Mark single item prepared
  const handleItemPrepared = async (orderId, itemId) => {
    try {
      await api.patch(`/orders/${orderId}/items/${itemId}/prepared`);
      playChime('info');
      await loadOrders();
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
    }
  };

  // Mark whole order READY
  const handleOrderReady = async (orderId) => {
    setActionLoadingId(orderId);
    try {
      await api.patch(`/orders/${orderId}/status`, { status: 'ready' });
      playChime('success');
      confetti({ particleCount: 70, spread: 60, origin: { y: 0.7 } });
      await loadOrders();
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-gradient-to-r from-theme-surface via-theme-bg to-theme-surface flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/15 border border-orange-500/30 text-orange-300 text-xs font-bold mb-2">
            <ChefHat className="w-3.5 h-3.5" />
            <span>Oshxona Monitori (KDS)</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            Oshpaz Paneli 👨‍🍳
          </h1>
          <p className="text-xs text-theme-muted mt-1">
            Yangi buyurtmalarni qabul qiling va tayyor bo'lgach ofitsiantlarga xabar yuboring.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-2xl bg-white/5 border border-theme-border text-xs font-semibold text-white">
            Navbatda: <span className="text-orange-400 font-bold">{orders.length} ta buyurtma</span>
          </div>
          <button
            onClick={loadOrders}
            className="p-2.5 rounded-xl border border-theme-border hover:border-theme-primary bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white transition-all"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Orders Grid */}
      {loading ? (
        <div className="py-20 text-center text-theme-muted">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-orange-400" />
          <p className="text-sm">Buyurtmalar yuklanmoqda...</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="p-16 text-center rounded-3xl glass-card border border-theme-border text-theme-muted">
          <Utensils className="w-16 h-16 mx-auto mb-3 opacity-30 text-orange-400" />
          <h3 className="text-lg font-bold text-white">Hozircha buyurtmalar yo'q</h3>
          <p className="text-xs mt-1">Mijozlar buyurtma berganda ekranda ovozli xabar bilan chiqadi.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {orders.map((order) => {
            const allItemsReady = order.items?.every((i) => i.is_prepared);

            return (
              <div
                key={order.id}
                className="rounded-3xl glass-card border border-theme-border bg-theme-surface/80 flex flex-col justify-between overflow-hidden shadow-2xl"
              >
                {/* Order Top Bar */}
                <div className="p-5 bg-black/30 border-b border-theme-border/60 flex items-center justify-between">
                  <div>
                    <span className="text-2xl font-black text-white">
                      Stol #{order.table_number || order.table_id}
                    </span>
                    <div className="text-xs text-orange-400 font-bold">
                      {order.order_number}
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[10px] uppercase font-extrabold px-2.5 py-1 rounded-full bg-orange-500/20 text-orange-300 border border-orange-500/30">
                      {order.status}
                    </span>
                    <div className="text-[10px] text-theme-muted mt-1">
                      Ofitsiant: {order.waiter_name || 'Biriktirilmoqda'}
                    </div>
                  </div>
                </div>

                {/* Customer Note if present */}
                {order.customer_note && (
                  <div className="px-5 py-2.5 bg-amber-500/10 border-b border-amber-500/20 text-xs text-amber-300 font-medium">
                    ⚠️ Mijoz izohi: "{order.customer_note}"
                  </div>
                )}

                {/* Items List */}
                <div className="p-5 flex-1 divide-y divide-theme-border/40 space-y-3">
                  {order.items?.map((item) => (
                    <div
                      key={item.id}
                      className="pt-2.5 flex items-start justify-between gap-3"
                    >
                      <div className="flex-1">
                        <div className="text-sm font-bold text-white flex items-center gap-2">
                          <span className="w-6 h-6 rounded-lg bg-white/10 text-center leading-6 text-xs text-orange-400 font-black">
                            {item.quantity}x
                          </span>
                          <span>{item.menu_item_name || `Taom #${item.menu_item_id}`}</span>
                        </div>
                        {item.special_note && (
                          <div className="text-xs text-red-400 font-medium mt-0.5 italic">
                            Talab: "{item.special_note}"
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => handleItemPrepared(order.id, item.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                          item.is_prepared
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-white/10 hover:bg-emerald-500 hover:text-white text-zinc-300'
                        }`}
                      >
                        {item.is_prepared ? '✅ Tayyor' : 'Tayyorlash'}
                      </button>
                    </div>
                  ))}
                </div>

                {/* Bottom Complete Button */}
                <div className="p-4 bg-black/40 border-t border-theme-border/60">
                  <button
                    onClick={() => handleOrderReady(order.id)}
                    disabled={actionLoadingId === order.id}
                    className={`w-full py-3.5 rounded-2xl font-black text-xs uppercase tracking-wider shadow-lg flex items-center justify-center gap-2 transition-all active:scale-98 ${
                      allItemsReady
                        ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 text-white shadow-emerald-500/20 animate-pulse'
                        : 'bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 text-white shadow-orange-500/20'
                    }`}
                  >
                    {actionLoadingId === order.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4" />
                    )}
                    <span>Butun buyurtma Tayyor! (Ofitsiantga uzatish)</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ChefDashboard;
