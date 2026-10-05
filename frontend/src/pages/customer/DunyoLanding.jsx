import React, { useState, useEffect } from 'react';
import {
  UtensilsCrossed,
  Sparkles,
  Coffee,
  Flame,
  ShieldCheck,
  Clock,
  MapPin,
  Phone,
  Users,
  Star
} from 'lucide-react';
import api from '../../utils/api';

export const DunyoLanding = ({ onOpenLogin }) => {
  // Menyu KATEGORIYALAR bo'yicha ko'rsatiladi (Kaboblar, Salatlar,
  // Ichimliklar, Choylar...). Faqat admin panelda qo'shilgan taomlar
  // chiqadi — boshqa hech narsa ko'rinmaydi.
  const [menuGroups, setMenuGroups] = useState([]);
  const [activeCatId, setActiveCatId] = useState(null);
  const [loadingDishes, setLoadingDishes] = useState(true);

  useEffect(() => {
    const fetchDishes = async () => {
      try {
        const categories = await api.get('/menu/full/1');
        if (Array.isArray(categories)) {
          const groups = categories
            // Admin panelda "Bosh sahifa" tugmasi o'chirilgan
            // kategoriyalar bu yerda ko'rsatilmaydi.
            .filter((c) => c.show_on_landing !== false)
            .map((c) => ({
              ...c,
              items: (c.items || []).filter(
                (it) => it.is_available !== false && !it.is_stop_list
              ),
            }))
            // Bo'sh kategoriya ko'rsatilmaydi
            .filter((c) => c.items.length > 0);
          setMenuGroups(groups);
          if (groups.length > 0) setActiveCatId(groups[0].id);
        }
      } catch (err) {
        console.warn('Menyuni yuklashda xatolik:', err);
      } finally {
        setLoadingDishes(false);
      }
    };
    fetchDishes();
  }, []);

  const activeGroup = menuGroups.find((c) => c.id === activeCatId) || menuGroups[0];

  return (
    <div className="min-h-screen bg-theme-bg text-theme-text selection:bg-amber-500/30">
      {/* ─── Hero Section ───────────────────────────────────── */}
      <section className="relative overflow-hidden pt-12 pb-16 px-4 sm:px-6 lg:px-8 border-b border-theme-border/50">
        {/* Background glow */}
        <div className="absolute inset-0 bg-radial-at-t from-amber-500/10 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-10 right-10 w-96 h-96 bg-amber-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-10 w-80 h-80 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative z-10 space-y-6">
          {/* Top Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold tracking-wide shadow-glow animate-fade-in">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <span>XUSH KELIBSIZ • DUNYO CHOYXONASI</span>
          </div>

          {/* Main Title */}
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight max-w-4xl mx-auto">
            O'zbekona Mehmondo'stlik & <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-amber-400 via-orange-300 to-amber-500 bg-clip-text text-transparent">
              Haqiqiy Milliy Taomlar
            </span>
          </h1>

          <p className="text-sm sm:text-base text-theme-muted max-w-2xl mx-auto leading-relaxed">
            Shinam so'rilar, samovarda damlangan choy va issiq taomlar.
            Menyu bilan quyida tanishing yoki stoldagi QR kodni skaner qiling.
          </p>

          {/* QR orqali kirishni eslatish */}
          <div className="flex items-center justify-center pt-2">
            <div className="inline-flex items-center gap-2 px-5 py-3 rounded-2xl bg-white/5 border border-white/10 text-theme-muted text-xs">
              <span>📱</span>
              <span>Menyuni ko'rish uchun stoldagi QR kodni skaner qiling</span>
            </div>
          </div>

          {/* Feature Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-8 max-w-4xl mx-auto text-left">
            <div className="p-4 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center shrink-0">
                <UtensilsCrossed className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Smart QR Menyu</h4>
                <p className="text-[11px] text-theme-muted">Stol ustidagi QR kod orqali</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">100% Halol</h4>
                <p className="text-[11px] text-theme-muted">Faqat barra go'sht va tabiiy masalliqlar</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/15 text-blue-400 flex items-center justify-center shrink-0">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Tezkor Xizmat</h4>
                <p className="text-[11px] text-theme-muted">Issiq holatda yetkaziladi</p>
              </div>
            </div>

            <div className="p-4 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/15 text-purple-400 flex items-center justify-center shrink-0">
                <Coffee className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Samovar Choyi</h4>
                <p className="text-[11px] text-theme-muted">Limon va novvot bilan xushbo'y</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Choyxona Menu Highlights (Admin orqali boshqariladi) ─── */}
      <section className="py-14 px-4 sm:px-6 lg:px-8 bg-black/20 border-t border-theme-border/50">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-bold mb-2">
                <Flame className="w-3.5 h-3.5" />
                <span>MENYU</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
                Taomlarimiz
              </h2>
            </div>
            <p className="text-xs text-theme-muted max-w-sm">
              Kategoriyani tanlang va taomlar bilan tanishing.
            </p>
          </div>

          {loadingDishes ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <div key={n} className="h-64 rounded-3xl bg-white/5 animate-pulse" />
              ))}
            </div>
          ) : menuGroups.length === 0 ? (
            <div className="text-center py-12 text-theme-muted text-sm">
              Taomlar menyusi tez orada yangilanadi.
            </div>
          ) : (
            <>
              {/* Kategoriya tugmalari — katta va aniq, oson bosiladi */}
              <div className="flex gap-2.5 overflow-x-auto no-scrollbar pb-2 mb-6">
                {menuGroups.map((cat) => {
                  const active = cat.id === (activeGroup?.id);
                  return (
                    <button
                      key={cat.id}
                      onClick={() => setActiveCatId(cat.id)}
                      className={`flex items-center gap-2 px-5 py-3 rounded-2xl text-sm font-extrabold shrink-0 transition-all ${
                        active
                          ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/25'
                          : 'glass-card border border-theme-border bg-theme-surface/70 text-theme-text hover:border-amber-500/50'
                      }`}
                    >
                      <span className="text-lg leading-none">{cat.icon || '🍽️'}</span>
                      <span>{cat.name}</span>
                      <span
                        className={`text-[11px] px-1.5 py-0.5 rounded-full font-bold ${
                          active ? 'bg-slate-950/20 text-slate-950' : 'bg-white/10 text-theme-muted'
                        }`}
                      >
                        {cat.items.length}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Tanlangan kategoriya taomlari */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {(activeGroup?.items || []).map((item) => (
                  <div
                    key={item.id}
                    className="rounded-3xl glass-card border border-theme-border bg-theme-surface/80 overflow-hidden group hover:border-amber-500/50 transition-all shadow-lg"
                  >
                    {/* Rasm faqat admin yuklagan bo'lsa ko'rsatiladi.
                        Ilgari internetdan olingan begona surat chiqardi. */}
                    {item.image_url ? (
                      <div className="relative h-44 overflow-hidden bg-black/40">
                        <img
                          src={item.image_url}
                          alt={item.name}
                          loading="lazy"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                        {item.is_featured && (
                          <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-black/70 backdrop-blur-md text-amber-300 text-[10px] font-extrabold border border-amber-500/30">
                            Maxsus Tavsiya 🔥
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="h-24 flex items-center justify-center bg-black/30 border-b border-theme-border/50">
                        <span className="text-3xl opacity-60">{activeGroup?.icon || '🍽️'}</span>
                      </div>
                    )}

                    <div className="p-4 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-extrabold text-base text-white leading-snug">
                          {item.name}
                        </h3>
                        <span className="font-black text-amber-400 text-base whitespace-nowrap">
                          {item.price?.toLocaleString()} so'm
                        </span>
                      </div>
                      {item.description && (
                        <p className="text-xs text-theme-muted line-clamp-2 leading-relaxed">
                          {item.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      {/* ─── Footer & Contact ──────────────────────────────── */}
      <footer className="py-10 px-4 sm:px-6 lg:px-8 border-t border-theme-border/60 bg-theme-surface/50 text-center sm:text-left">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center sm:text-left">
            <div className="flex items-center justify-center sm:justify-start gap-2">
              <div className="w-8 h-8 rounded-xl bg-amber-500 text-black flex items-center justify-center font-bold">
                <UtensilsCrossed className="w-4 h-4" />
              </div>
              <span className="font-extrabold text-lg text-white">Dunyo Choyxonasi</span>
            </div>
            <p className="text-xs text-theme-muted">
              O'zbekona mehmondo'stlik, shinam so'rilar va eng sara milliy taomlar maskani.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-theme-muted font-medium">
            <div className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-amber-400" />
              <span>Xorazm viloyati, Xiva tumani</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Phone className="w-4 h-4 text-amber-400" />
              <span>+998 88 459 34 00</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-400" />
              <span>Har kuni: 09:00 — 23:00</span>
            </div>
          </div>
        </div>

        <div className="max-w-6xl mx-auto mt-6 pt-6 border-t border-theme-border/30 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-theme-muted">
          <span>© {new Date().getFullYear()} Dunyo Choyxonasi. Barcha huquqlar himoyalangan.</span>
          <button
            onClick={onOpenLogin}
            className="hover:text-amber-400 transition-colors font-semibold flex items-center gap-1"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Xodimlar & Admin tizimiga kirish</span>
          </button>
        </div>
      </footer>
    </div>
  );
};

export default DunyoLanding;
