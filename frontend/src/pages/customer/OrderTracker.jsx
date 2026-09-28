import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../../context/WebSocketContext';
import api from '../../utils/api';
import confetti from 'canvas-confetti';
import {
  CheckCircle2,
  Clock,
  ChefHat,
  Bike,
  Sparkles,
  Star,
  RefreshCw,
  Receipt
} from 'lucide-react';

const STATUS_STEPS = [
  { key: 'pending', label: 'Qabul qilindi', desc: 'Oshxonaga uzatildi', icon: Clock },
  { key: 'preparing', label: 'Tayyorlanmoqda', desc: 'Oshpaz pishirmoqda', icon: ChefHat },
  { key: 'ready', label: 'Tayyor!', desc: 'Ofitsiant olib kelmoqda', icon: Bike },
  { key: 'served', label: 'Yetkazib berildi', desc: 'Yoqimli ishtaha!', icon: CheckCircle2 },
];

export const OrderTracker = ({ orderId, onOpenReview, onOpenBill, onBackToMenu }) => {
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const { addEventListener } = useWebSocket();

  const fetchOrder = async () => {
    try {
      const data = await api.get(`/orders/${orderId}`);
      setOrder(data);

      if (data.status === 'served') {
        confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrder();

    // Listen for WebSocket updates on this order
    const unsubscribe = addEventListener('*', (event) => {
      if (
        event.order_id === orderId ||
        event.type === 'order_status_updated' ||
        event.type === 'order_ready' ||
        event.type === 'order_delivered'
      ) {
        fetchOrder();
      }
    });

    return () => unsubscribe();
  }, [orderId]);

  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-theme-muted">
        <RefreshCw className="w-8 h-8 animate-spin mb-3 text-theme-primary" />
        <p className="text-sm">Buyurtma ma'lumotlari yuklanmoqda...</p>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="py-16 text-center text-theme-muted">
        <p>Buyurtma topilmadi.</p>
        <button
          onClick={onBackToMenu}
          className="mt-4 px-4 py-2 rounded-xl bg-theme-primary text-white text-xs font-semibold"
        >
          Menyuga qaytish
        </button>
      </div>
    );
  }

  const currentStepIndex = STATUS_STEPS.findIndex((s) => s.key === order.status);
  const activeIndex = currentStepIndex >= 0 ? currentStepIndex : 0;

  return (
    <div className="max-w-xl mx-auto px-4 py-6 space-y-6 animate-fade-in">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl glass-card border border-theme-border bg-gradient-to-br from-theme-surface to-black/40 text-center relative overflow-hidden">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-theme-primary/10 border border-theme-primary/30 text-theme-primary text-xs font-bold mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Jonli Kuzatuv</span>
        </div>

        <h2 className="text-2xl font-black text-white tracking-tight">
          {order.order_number}
        </h2>
        <p className="text-xs text-theme-muted mt-1">
          Stol #{order.table_number || order.table_id} • Ofitsiant: {order.waiter_name || 'Tayinlanmoqda...'}
        </p>

        {order.status === 'served' && (
          <div className="mt-4 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center justify-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>Ofitsiant taomingizni stolga yetkazib berdi! Yoqimli ishtaha!</span>
          </div>
        )}
      </div>

      {/* Progress Steps */}
      <div className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70 space-y-6">
        <h3 className="text-xs font-bold text-theme-muted uppercase tracking-wider">
          Buyurtma Jarayoni
        </h3>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-6 top-4 bottom-4 w-0.5 bg-theme-border/60" />
          <div
            className="absolute left-6 top-4 w-0.5 bg-gradient-to-b from-theme-primary to-emerald-400 transition-all duration-700"
            style={{
              height: `${(activeIndex / (STATUS_STEPS.length - 1)) * 100}%`,
            }}
          />

          <div className="space-y-6 relative">
            {STATUS_STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isPast = idx < activeIndex;
              const isCurrent = idx === activeIndex;

              let iconBg = 'bg-black/50 border-theme-border text-zinc-500';
              if (isPast) {
                iconBg = 'bg-emerald-500 border-emerald-400 text-white shadow-lg shadow-emerald-500/20';
              } else if (isCurrent) {
                iconBg = 'bg-theme-primary border-white/60 text-white shadow-glow animate-pulse';
              }

              return (
                <div key={step.key} className="flex items-start gap-4">
                  <div
                    className={`w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 z-10 transition-all ${iconBg}`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="pt-1 flex-1">
                    <div className="flex items-center justify-between">
                      <h4
                        className={`text-sm font-bold ${
                          isCurrent ? 'text-white text-base' : isPast ? 'text-zinc-200' : 'text-zinc-500'
                        }`}
                      >
                        {step.label}
                      </h4>
                      {isCurrent && (
                        <span className="text-[10px] uppercase font-extrabold px-2 py-0.5 rounded-full bg-theme-primary/20 text-theme-primary">
                          Hozirgi holat
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-theme-muted mt-0.5">
                      {step.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Ordered Items summary */}
      <div className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/70 space-y-3">
        <h3 className="text-xs font-bold text-theme-muted uppercase tracking-wider">
          Taomlar Ro'yxati ({order.items?.length || 0})
        </h3>
        <div className="divide-y divide-theme-border/40">
          {order.items?.map((item) => (
            <div key={item.id} className="py-2.5 flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">
                  {item.quantity}x {item.menu_item_name || `Taom #${item.menu_item_id}`}
                </div>
                {item.special_note && (
                  <div className="text-[11px] text-amber-400 italic">
                    "{item.special_note}"
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="text-xs font-bold text-theme-primary">
                  {(item.total_price || 0).toLocaleString()} so'm
                </div>
                <div className="text-[10px] text-theme-muted">
                  {item.is_prepared ? '✅ Tayyor' : '⏳ Pishirilmoqda'}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="pt-3 border-t border-theme-border flex items-center justify-between font-bold text-sm">
          <span>Jami:</span>
          <span className="text-base text-white">{(order.total || 0).toLocaleString()} so'm</span>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        {onOpenBill && (
          <button
            onClick={onOpenBill}
            className="flex-1 py-3.5 rounded-xl border border-theme-border/80 hover:border-theme-primary bg-white/5 hover:bg-white/10 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md"
          >
            <Receipt className="w-4 h-4 text-theme-primary" />
            <span>Mening Hisobim (Chek)</span>
          </button>
        )}

        {order.status === 'served' && (
          <button
            onClick={() => onOpenReview && onOpenReview(order)}
            className="flex-1 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold text-sm shadow-lg shadow-orange-500/20 flex items-center justify-center gap-2 active:scale-98 transition-all"
          >
            <Star className="w-4 h-4 fill-white text-white" />
            <span>Xizmatga Baho Berish</span>
          </button>
        )}

        <button
          onClick={onBackToMenu}
          className="flex-1 py-3.5 rounded-xl border border-theme-border hover:border-theme-primary/60 bg-white/5 hover:bg-white/10 text-white font-semibold text-xs transition-all text-center"
        >
          Menyuni ko'rish
        </button>
      </div>
    </div>
  );
};

export default OrderTracker;
