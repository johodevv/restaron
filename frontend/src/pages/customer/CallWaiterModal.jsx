import React, { useState } from 'react';
import api from '../../utils/api';
import { BellRing, X, CheckCircle, Clock } from 'lucide-react';

const QUICK_REASONS = [
  '🧾 Hisob-kitob qilish (Chek)',
  '🧻 Salfetka yoki asboblar kerak',
  '❓ Menyu bo\'yicha maslahat',
  '☕ Choy / Ichimlik buyurtma qilish',
  '🧂 Ziravorlar (Tuz, qalampir)',
];

export const CallWaiterModal = ({ isOpen, onClose, tableId, tableNumber }) => {
  const [selectedReason, setSelectedReason] = useState('');
  const [customNote, setCustomNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const finalNote = customNote.trim() || selectedReason || "Ofitsiant chaqirildi";
    setLoading(true);

    try {
      await api.post('/orders/call-waiter', {
        table_id: tableId,
        note: finalNote,
      });
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
        setCustomNote('');
        setSelectedReason('');
      }, 2200);
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
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
              <CheckCircle className="w-10 h-10" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">
              Ofitsiantga xabar yuborildi!
            </h3>
            <p className="text-sm text-theme-muted">
              Xodimimiz hoziroq Stol #{tableNumber} tomon yo'l olmoqda.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
                <BellRing className="w-5 h-5 animate-bounce-subtle" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">
                  Ofitsiantni chaqirish
                </h3>
                <p className="text-xs text-theme-muted">
                  Stol #{tableNumber} uchun xizmat ko'rsatish
                </p>
              </div>
            </div>

            <label className="block text-xs font-semibold text-theme-muted uppercase mb-2">
              Tezkor sabablar:
            </label>
            <div className="flex flex-wrap gap-2 mb-4">
              {QUICK_REASONS.map((reason) => (
                <button
                  key={reason}
                  type="button"
                  onClick={() => {
                    setSelectedReason(reason);
                    setCustomNote(reason);
                  }}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                    selectedReason === reason
                      ? 'border-theme-primary bg-theme-primary/20 text-white font-medium'
                      : 'border-theme-border/70 hover:border-theme-primary/40 bg-white/5 text-theme-muted'
                  }`}
                >
                  {reason}
                </button>
              ))}
            </div>

            <label className="block text-xs font-semibold text-theme-muted uppercase mb-2">
              Qo'shimcha izoh (ixtiyoriy):
            </label>
            <textarea
              rows={2}
              value={customNote}
              onChange={(e) => setCustomNote(e.target.value)}
              placeholder="Masalan: 2 ta qo'shimcha chashka olib keling..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary transition-colors mb-5 resize-none"
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold text-sm shadow-lg shadow-orange-500/20 active:scale-98 transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <Clock className="w-4 h-4 animate-spin" />
              ) : (
                <BellRing className="w-4 h-4" />
              )}
              <span>{loading ? 'Yuborilmoqda...' : 'Chaqirish'}</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default CallWaiterModal;
