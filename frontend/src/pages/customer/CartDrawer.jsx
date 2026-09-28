import React, { useState } from 'react';
import { useCart } from '../../context/CartContext';
import api from '../../utils/api';
import { X, Trash2, Plus, Minus, ArrowRight, Loader2, MessageSquare } from 'lucide-react';

export const CartDrawer = ({ isOpen, onClose, tableId, onOrderCreated }) => {
  const { items, updateQuantity, updateNote, removeFromCart, clearCart, subtotal } = useCart();
  const [customerName, setCustomerName] = useState('');
  const [customerNote, setCustomerNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleCreateOrder = async () => {
    if (!items.length) return;
    setLoading(true);
    setError('');

    try {
      const payload = {
        table_id: tableId,
        customer_name: customerName.trim() || undefined,
        customer_note: customerNote.trim() || undefined,
        items: items.map((i) => ({
          menu_item_id: i.item.id,
          quantity: i.quantity,
          special_note: i.note || undefined,
        })),
      };

      const newOrder = await api.post('/orders/', payload);
      clearCart();
      onClose();
      if (onOrderCreated) {
        onOrderCreated(newOrder);
      }
    } catch (err) {
      setError(err.message || 'Buyurtma berishda xatolik yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md h-full bg-theme-surface border-l border-theme-border flex flex-col shadow-2xl text-theme-text animate-slide-up">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-theme-border flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">Savatchangiz</h3>
            <p className="text-xs text-theme-muted">
              {items.length} xil taom tanlandi
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-white/10 text-theme-muted hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Items List */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
          {items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-theme-muted py-12">
              <span className="text-4xl mb-3">🛒</span>
              <p className="text-base font-medium">Savatchangiz bo'sh</p>
              <p className="text-xs max-w-xs mt-1">
                Menyudan o'zingizga yoqqan lazzatli taomlarni tanlang va qo'shing.
              </p>
            </div>
          ) : (
            items.map(({ item, quantity, note }) => (
              <div
                key={item.id}
                className="p-3.5 rounded-xl border border-theme-border bg-white/[0.03] space-y-2.5"
              >
                <div className="flex items-center justify-between gap-3">
                  {item.image_url && (
                    <img
                      src={item.image_url}
                      alt={item.name}
                      className="w-12 h-12 rounded-xl object-cover border border-theme-border shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-sm text-white truncate">
                      {item.name}
                    </h4>
                    <span className="text-xs text-theme-primary font-bold">
                      {(item.price * quantity).toLocaleString()} so'm
                    </span>
                  </div>

                  {/* Quantity control */}
                  <div className="flex items-center gap-1.5 bg-black/40 border border-theme-border/60 rounded-lg p-1 shrink-0">
                    <button
                      onClick={() => updateQuantity(item.id, -1)}
                      className="p-1 rounded hover:bg-white/10 text-theme-muted hover:text-white"
                    >
                      <Minus className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-xs font-bold px-1.5 min-w-[20px] text-center">
                      {quantity}
                    </span>
                    <button
                      onClick={() => updateQuantity(item.id, 1)}
                      className="p-1 rounded hover:bg-white/10 text-theme-muted hover:text-white"
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <button
                    onClick={() => removeFromCart(item.id)}
                    className="p-1.5 text-zinc-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Note for dish */}
                <input
                  type="text"
                  value={note || ''}
                  onChange={(e) => updateNote(item.id, e.target.value)}
                  placeholder="Maxsus talab (masalan: qalampir kam bo'lsin)..."
                  className="w-full text-xs px-2.5 py-1.5 rounded-lg bg-black/20 border border-theme-border/60 text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary transition-colors"
                />
              </div>
            ))
          )}
        </div>

        {/* Footer with summary and button */}
        {items.length > 0 && (
          <div className="p-4 sm:p-5 border-t border-theme-border bg-theme-bg/60 space-y-3">
            {error && (
              <div className="text-xs text-red-400 bg-red-500/10 p-2.5 rounded-lg border border-red-500/20">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Ismingiz (ixtiyoriy)"
                className="w-full text-xs px-3 py-2 rounded-xl bg-black/30 border border-theme-border text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              />
              <input
                type="text"
                value={customerNote}
                onChange={(e) => setCustomerNote(e.target.value)}
                placeholder="Umumiy buyurtma uchun izoh..."
                className="w-full text-xs px-3 py-2 rounded-xl bg-black/30 border border-theme-border text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              />
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-theme-border/60">
              <span className="text-xs text-theme-muted font-medium">Jami to'lov:</span>
              <span className="text-lg font-extrabold text-white">
                {subtotal.toLocaleString()} so'm
              </span>
            </div>

            <button
              onClick={handleCreateOrder}
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white font-bold text-sm shadow-glow flex items-center justify-center gap-2 active:scale-98 transition-all"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Yuborilmoqda...</span>
                </>
              ) : (
                <>
                  <span>Buyurtmani tasdiqlash</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CartDrawer;
