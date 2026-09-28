import React, { useState } from 'react';
import StarRating from '../../components/StarRating';
import api from '../../utils/api';
import confetti from 'canvas-confetti';
import { X, Heart, Send, CheckCircle2, Loader2 } from 'lucide-react';

export const ReviewModal = ({ isOpen, onClose, order }) => {
  const [foodRating, setFoodRating] = useState(5);
  const [serviceRating, setServiceRating] = useState(5);
  const [comment, setComment] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen || !order) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.post('/reviews/', {
        restaurant_id: order.restaurant_id,
        order_id: order.id,
        waiter_id: order.waiter_id || undefined,
        customer_name: customerName.trim() || undefined,
        food_rating: foodRating,
        service_rating: serviceRating,
        comment: comment.trim() || undefined,
      });

      setSuccess(true);
      confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });

      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 2500);
    } catch (err) {
      alert(err.message || 'Baho yuborishda xatolik yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md p-6 rounded-2xl glass-card border border-theme-border bg-theme-surface shadow-2xl text-theme-text relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-white/10 text-theme-muted hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {success ? (
          <div className="py-8 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4 animate-bounce">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">
              Katta rahmat! ❤️
            </h3>
            <p className="text-xs text-theme-muted max-w-xs">
              Sizning fikringiz restoran xizmatini yanada mukammallashtirishga yordam beradi.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="text-center pb-2 border-b border-theme-border/60">
              <span className="text-3xl mb-1 block">⭐</span>
              <h3 className="text-lg font-bold text-white">
                Fikr va Baholash
              </h3>
              <p className="text-xs text-theme-muted">
                {order.order_number} buyurtmasi bo'yicha taassurotingiz
              </p>
            </div>

            {/* Food Rating */}
            <div className="p-3.5 rounded-xl border border-theme-border bg-black/20 flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-white">
                  Taomlar sifati va mazasi:
                </div>
                <div className="text-[11px] text-theme-muted">
                  Oshpaz mehnatiga baho
                </div>
              </div>
              <StarRating rating={foodRating} onChange={setFoodRating} size={22} />
            </div>

            {/* Service Rating */}
            <div className="p-3.5 rounded-xl border border-theme-border bg-black/20 flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-white">
                  Ofitsiant xizmati:
                </div>
                <div className="text-[11px] text-theme-muted">
                  {order.waiter_name ? `${order.waiter_name} xizmati` : 'Xushmuomalalik va tezlik'}
                </div>
              </div>
              <StarRating rating={serviceRating} onChange={setServiceRating} size={22} />
            </div>

            {/* Customer name */}
            <div>
              <label className="block text-xs font-semibold text-theme-muted mb-1">
                Ismingiz (ixtiyoriy):
              </label>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Ismingiz..."
                className="w-full text-xs px-3 py-2 rounded-xl bg-black/30 border border-theme-border text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              />
            </div>

            {/* Comment */}
            <div>
              <label className="block text-xs font-semibold text-theme-muted mb-1">
                Fikr yoki taklifingiz:
              </label>
              <textarea
                rows={3}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Taomlar qanday bo'ldi? Takliflaringiz bormi?..."
                className="w-full text-xs px-3 py-2 rounded-xl bg-black/30 border border-theme-border text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white font-bold text-xs uppercase tracking-wider shadow-glow flex items-center justify-center gap-2 active:scale-98 transition-all"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>{loading ? 'Yuborilmoqda...' : 'Bahoni yuborish'}</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ReviewModal;
