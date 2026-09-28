import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { X, Check } from 'lucide-react';

export const ThemePickerModal = ({ isOpen, onClose }) => {
  const { currentTheme, setTheme, activeThemes, allThemes } = useTheme();

  if (!isOpen) return null;

  // Foydalanuvchi faqat admin ruxsat bergan 2 ta temadan yoki barchasidan tanlay oladi
  const selectableThemes = allThemes.filter((t) => activeThemes.includes(t.slug));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md p-6 rounded-2xl glass-card border border-theme-border bg-theme-surface shadow-2xl text-theme-text">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">🎨 Dizayn Temasini Tanlash</h3>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/10 text-theme-muted hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-theme-muted mb-4">
          Restoran tomonidan tavsiya etilgan dizayn ko'rinishini tanlang:
        </p>

        <div className="grid grid-cols-1 gap-3">
          {(selectableThemes.length ? selectableThemes : allThemes).map((t) => {
            const isSelected = currentTheme === t.slug;
            return (
              <button
                key={t.slug}
                onClick={() => {
                  setTheme(t.slug);
                  onClose();
                }}
                className={`flex items-center justify-between p-3.5 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-theme-primary bg-theme-primary/10 shadow-glow'
                    : 'border-theme-border hover:border-theme-primary/50 hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-7 h-7 rounded-full flex items-center justify-center text-sm shadow-inner"
                    style={{ backgroundColor: t.bg, border: `2px solid ${t.primary}` }}
                  >
                    {t.icon}
                  </div>
                  <div className="text-left">
                    <div className="text-sm font-semibold">{t.name}</div>
                    <div className="text-[11px] text-theme-muted">
                      Asosiy rang: <span style={{ color: t.primary }}>{t.primary}</span>
                    </div>
                  </div>
                </div>

                {isSelected && (
                  <div className="w-6 h-6 rounded-full bg-theme-primary flex items-center justify-center text-white">
                    <Check className="w-4 h-4" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default ThemePickerModal;
