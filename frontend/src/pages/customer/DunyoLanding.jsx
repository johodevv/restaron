import React, { useState, useEffect, useMemo } from 'react';
import {
  UtensilsCrossed,
  PhoneCall,
  Search,
  X,
  Clock,
  MapPin,
  Sparkles,
  ArrowRight,
  Flame,
} from 'lucide-react';
import api from '../../utils/api';
import { preloadImages, collectImageUrls } from '../../utils/preloadImages';

export const DunyoLanding = ({ onOpenLogin }) => {
  const [menuGroups, setMenuGroups] = useState([]);
  const [activeCatId, setActiveCatId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDish, setSelectedDish] = useState(null);
  const [loadingDishes, setLoadingDishes] = useState(true);

  useEffect(() => {
    const fetchDishes = async () => {
      try {
        const categories = await api.get('/menu/full/1');
        if (Array.isArray(categories)) {
          const groups = categories
            .filter((c) => c.show_on_landing !== false)
            .map((c) => ({
              ...c,
              items: (c.items || []).filter(
                (it) => it.is_available !== false && !it.is_stop_list
              ),
            }))
            .filter((c) => c.items.length > 0);

          setMenuGroups(groups);
          // Sayt ochilganda 1-kategoriya avtomatik tanlanadi (hech qanday "Barchasi" yo'q)
          if (groups.length > 0) {
            setActiveCatId(groups[0].id);
          }
          preloadImages(collectImageUrls(groups));
        }
      } catch (err) {
        console.warn('Menyuni yuklashda xatolik:', err);
      } finally {
        setLoadingDishes(false);
      }
    };
    fetchDishes();
  }, []);

  // Barcha taomlar yassi ro'yxati (faqat qidiruv uchun ishlatiladi)
  const allDishes = useMemo(() => {
    return menuGroups.flatMap((group) =>
      group.items.map((item) => ({
        ...item,
        categoryName: group.name,
      }))
    );
  }, [menuGroups]);

  // Faol kategoriya ob'ekti
  const activeGroup = useMemo(() => {
    return menuGroups.find((g) => g.id === activeCatId) || menuGroups[0];
  }, [menuGroups, activeCatId]);

  // Ko'rsatiladigan taomlar ro'yxati:
  // Qidiruv bo'lsa barcha taomlar ichidan izlaydi;
  // Aks holda faqat tanlangan kategoriya taomlarini ko'rsatadi
  const displayedDishes = useMemo(() => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      return allDishes.filter(
        (dish) =>
          dish.name.toLowerCase().includes(q) ||
          (dish.description && dish.description.toLowerCase().includes(q))
      );
    }
    return activeGroup
      ? activeGroup.items.map((item) => ({
          ...item,
          categoryName: activeGroup.name,
        }))
      : [];
  }, [searchQuery, allDishes, activeGroup]);

  // O'ng vitrina uchun menyudagi birinchi 3 ta rasmli sara taom
  const showcaseDishes = useMemo(() => {
    return allDishes.filter((d) => Boolean(d.image_url)).slice(0, 3);
  }, [allDishes]);

  // ESC tugmasi orqali modalni yopish
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setSelectedDish(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-[#0f1115] text-zinc-100 font-sans selection:bg-amber-500/30 flex flex-col justify-between">
      <div>
        {/* ─── 1. STICKY HEADER (Faqat mijoz uchun kerakli ma'lumot) ─── */}
        <header className="sticky top-0 z-40 bg-[#0f1115]/95 backdrop-blur-md border-b border-[#262b36] px-4 sm:px-6 py-2.5 sm:py-3 transition-all">
          <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
            {/* Logotip va manzil / ish vaqti */}
            <div className="flex items-center gap-2.5 sm:gap-3">
              <img
                src="/dunyo-logo.png"
                alt="Dunyo Choyxonasi"
                className="w-10 h-10 sm:w-11 sm:h-11 rounded-full object-cover border-2 border-amber-500/50 shadow-md shadow-amber-500/20 shrink-0"
              />
              <div>
                <span className="font-extrabold text-white text-base sm:text-lg tracking-tight block leading-tight font-sans">
                  Dunyo Choyxonasi
                </span>
                <span className="text-[11px] sm:text-xs text-amber-400 font-medium block leading-tight mt-0.5 font-sans">
                  Xorazm, Xiva • 09:00–23:00
                </span>
              </div>
            </div>

            {/* Yashil qo'ng'iroq qilish tugmasi */}
            <a
              href="tel:+998884593400"
              className="bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-bold text-xs sm:text-sm px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-xl flex items-center gap-2 shadow-md shadow-emerald-950/40 transition-all font-sans shrink-0"
              title="Qo'ng'iroq qilish"
            >
              <PhoneCall className="w-4 h-4 shrink-0" />
              <span>
                <span className="hidden sm:inline">Qo'ng'iroq: </span>
                +998 88 459 34 00
              </span>
            </a>
          </div>
        </header>

        {/* ─── 2. VISUAL CULINARY BANNER (Foto-Vitrina) ─── */}
        <section className="relative overflow-hidden border-b border-amber-500/15 bg-[#120e0a]">
          {/* Orqa fonda restoran zalining haqiqiy surati va qorong'u tillarang gradient */}
          <div className="absolute inset-0 z-0">
            <img
              src="/dunyo-hall.png"
              alt="Dunyo Choyxonasi Zali"
              className="w-full h-full object-cover opacity-20 filter blur-[2px] scale-105"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#120e0a] via-[#120e0a]/95 to-[#120e0a]/80" />
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
          </div>

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
            {/* Chap tomondagi boy milliy info-blok */}
            <div className="flex items-start gap-4 max-w-2xl">
              <img
                src="/dunyo-logo.png"
                alt="Dunyo Choyxonasi Logotipi"
                className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover border-2 border-amber-400/80 shadow-2xl shadow-amber-500/30 shrink-0 hidden sm:block"
              />
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[11px] font-black uppercase tracking-wider shadow-sm">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>DUNYO CHOYXONASI — XIVA</span>
                </div>

                <h1 className="text-xl sm:text-2xl lg:text-3xl font-black text-white tracking-tight leading-snug font-sans">
                  Mazali milliy taomlar, issiq kaboblar va fayzli oilaviy dasturxon
                </h1>

                {/* 3 ta chiroyli info-kapsula */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-zinc-300 font-medium">
                    <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>Xorazm, Xiva</span>
                  </div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-zinc-300 font-medium">
                    <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>Har kuni: 09:00 – 23:00</span>
                  </div>
                  <a
                    href="tel:+998884593400"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-300 hover:text-white hover:bg-amber-500/20 transition-colors font-semibold"
                  >
                    <PhoneCall className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>Dastavka va Bron: +998 88 459 34 00</span>
                  </a>
                </div>
              </div>
            </div>

            {/* O'ng tomonda: Menyudagi sara 3 ta taomning mini jonli foto-vitrinasi (Desktop) */}
            {showcaseDishes.length > 0 && (
              <div className="hidden lg:flex items-center gap-3 shrink-0">
                {showcaseDishes.map((dish) => (
                  <div
                    key={dish.id}
                    onClick={() => setSelectedDish(dish)}
                    className="group relative w-24 h-28 rounded-2xl overflow-hidden border border-amber-500/30 bg-[#1a1d24] shadow-lg cursor-pointer hover:border-amber-400 hover:scale-105 transition-all"
                    title={`${dish.name} - ${dish.price?.toLocaleString()} so'm`}
                  >
                    <img
                      src={dish.image_url}
                      alt={dish.name}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent flex flex-col justify-end p-1.5">
                      <span className="text-[10px] font-bold text-white line-clamp-1 leading-tight">
                        {dish.name}
                      </span>
                      <span className="text-[10px] font-black text-amber-400 font-sans">
                        {dish.price?.toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* ─── 3. STICKY KATEGORIYALAR VA QIDIRUV PANELI ─── */}
        <section className="sticky top-[53px] sm:top-[61px] z-30 bg-[#0f1115]/95 backdrop-blur-md py-3 px-4 sm:px-6 border-b border-amber-500/15 shadow-md">
          <div className="max-w-7xl mx-auto space-y-2.5">
            {/* Qidiruv maydoni */}
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-amber-400/80" />
              <input
                type="text"
                placeholder="Menyudan taom qidirish..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-9 py-2 rounded-xl bg-[#181b22] border border-[#262b36] text-white placeholder-zinc-500 text-sm focus:outline-none focus:border-amber-500/80 focus:ring-1 focus:ring-amber-500/30 transition-all font-sans"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white"
                  title="Tozalash"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Kategoriya tugmalari ("Barchasi" olib tashlangan, barchasi bir qarashda ko'rinadi) */}
            <div className="flex flex-wrap items-center gap-2">
              {menuGroups.map((cat) => {
                const active = activeCatId === cat.id && !searchQuery.trim();
                return (
                  <button
                    key={cat.id}
                    onClick={() => {
                      setActiveCatId(cat.id);
                      setSearchQuery('');
                    }}
                    className={`px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-1.5 transition-all font-sans ${
                      active
                        ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-black shadow-lg shadow-amber-500/20 scale-[1.02] border-transparent'
                        : 'bg-[#181b22]/90 hover:bg-[#20242e] text-zinc-300 hover:text-white border border-white/[0.08] hover:border-amber-500/40'
                    }`}
                  >
                    <span>{cat.name}</span>
                    <span
                      className={`text-[10px] sm:text-[11px] px-1.5 py-0.2 rounded-full font-black ${
                        active
                          ? 'bg-slate-950/25 text-slate-950'
                          : 'bg-white/10 text-zinc-400'
                      }`}
                    >
                      {cat.items.length}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* ─── 4. TAOMLAR KATALOGI VA BO'LIM SARLAVHASI ─── */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-5">
          {/* Bo'lim sarlavhasi (Oltin chiziqli ajratuvchi) */}
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-amber-500/20">
            <div className="flex items-center gap-2">
              <div className="w-2 h-5 rounded-full bg-gradient-to-b from-amber-400 to-orange-500" />
              <h2 className="text-base sm:text-lg font-black text-white tracking-tight">
                {searchQuery.trim()
                  ? `Qidiruv natijalari: "${searchQuery}"`
                  : activeGroup
                  ? activeGroup.name
                  : 'Taomlar'}
              </h2>
              <span className="text-xs font-bold text-amber-400/90 ml-1">
                ({displayedDishes.length} xil)
              </span>
            </div>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="text-xs text-amber-400 hover:underline font-bold"
              >
                Kategoriyaga qaytish
              </button>
            )}
          </div>

          {loadingDishes ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3.5 sm:gap-5">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                <div
                  key={n}
                  className="h-64 rounded-2xl bg-[#181b22] border border-[#262b36] animate-pulse"
                />
              ))}
            </div>
          ) : displayedDishes.length === 0 ? (
            <div className="text-center py-16 bg-[#181b22] border border-[#262b36] rounded-2xl p-6 my-6">
              <p className="text-zinc-400 text-sm">
                {searchQuery
                  ? `"${searchQuery}" bo'yicha hech qanday taom topilmadi.`
                  : "Bu bo'limda hozircha taomlar mavjud emas."}
              </p>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="mt-3 px-4 py-1.5 rounded-lg bg-amber-500/15 text-amber-400 hover:bg-amber-500/25 border border-amber-500/30 text-xs font-bold transition-all"
                >
                  Qidiruvni tozalash
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3.5 sm:gap-5">
              {displayedDishes.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedDish(item)}
                  className="bg-gradient-to-b from-[#1a1d24] to-[#12141a] border border-white/[0.08] hover:border-amber-500/50 rounded-2xl overflow-hidden shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer group flex flex-col justify-between"
                >
                  {/* Yuqori qism: Rasm yoki nafis sharqona dekorativ vitrina */}
                  <div className="aspect-[4/3] w-full overflow-hidden relative">
                    {item.image_url ? (
                      <>
                        <img
                          src={item.image_url}
                          alt={item.name}
                          loading="lazy"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                        {/* Yumshoq qora gradient soya */}
                        <div className="absolute inset-0 bg-gradient-to-t from-[#12141a] via-transparent to-transparent opacity-75" />
                      </>
                    ) : (
                      /* Rasmi bo'lmagan taomlar uchun bo'm-bo'sh kulrang quti EMAS, boy qahrabo-oltin nafis fon */
                      <div className="w-full h-full bg-gradient-to-br from-[#2a1f16] via-[#1c1510] to-[#12141a] relative overflow-hidden flex flex-col items-center justify-center p-3 text-center border-b border-amber-500/20">
                        {/* Orqa fon nur effekti */}
                        <div className="absolute -top-10 -right-10 w-28 h-28 bg-amber-500/15 rounded-full blur-2xl pointer-events-none" />
                        <img
                          src="/dunyo-logo.png"
                          alt="Dunyo Choyxonasi"
                          className="w-12 h-12 rounded-full object-cover border border-amber-500/40 shadow-md shadow-amber-500/20 mb-1.5 shrink-0"
                        />
                        <span className="text-xs sm:text-sm font-black text-amber-100/90 line-clamp-1 tracking-wide font-sans">
                          {item.name}
                        </span>
                        <span className="text-[10px] text-amber-400/70 font-semibold tracking-wider uppercase mt-0.5 font-sans">
                          Dunyo Choyxonasi
                        </span>
                      </div>
                    )}

                    {/* Maxsus tavsiya nishoni */}
                    {item.is_featured && (
                      <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 text-[10px] font-black tracking-wide uppercase shadow-md flex items-center gap-1">
                        <Flame className="w-3 h-3 fill-slate-950" />
                        <span>Tavsiya</span>
                      </span>
                    )}
                  </div>

                  {/* O'rta qism: Nomi va taom tavsifi (Kategoriya nomi takrorlanmagan!) */}
                  <div className="p-3 sm:p-3.5 flex flex-col flex-1">
                    <h3 className="font-bold text-white text-sm sm:text-base line-clamp-1 group-hover:text-amber-400 transition-colors font-sans">
                      {item.name}
                    </h3>

                    {/* Tavsif agar bo'lsa chiqadi, bo'lmasa ishtahani ochuvchi yangi tayyorlanadi belgisi */}
                    {item.description ? (
                      <p className="text-xs text-zinc-400 line-clamp-2 mt-1 min-h-[2rem] leading-relaxed font-sans">
                        {item.description}
                      </p>
                    ) : (
                      <p className="text-xs text-amber-400/70 flex items-center gap-1.5 mt-1 min-h-[2rem] font-sans">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 inline-block"></span>
                        <span>Yangi tayyorlanadi • Buyurtma asosida</span>
                      </p>
                    )}

                    {/* Pastki qism: Chiroyli narx kapsulasi va "Ko'rish ->" belgisi */}
                    <div className="mt-auto pt-2.5 border-t border-white/[0.06] flex items-center justify-between gap-1">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 font-black text-xs sm:text-sm font-sans tracking-tight">
                        {item.price?.toLocaleString()} so'm
                      </span>

                      <span className="text-[11px] sm:text-xs text-zinc-400 group-hover:text-amber-400 flex items-center gap-0.5 font-bold transition-colors">
                        <span>Ko'rish</span>
                        <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* ─── 5. TAOM TAFSILOTLARI MODALI (Kattalashtirilgan Premium Ko'rinish) ─── */}
      {selectedDish && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setSelectedDish(null)}
        >
          <div
            className="bg-[#181b22] border border-amber-500/30 rounded-3xl max-w-lg w-full overflow-hidden shadow-2xl relative animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Yopish tugmasi */}
            <button
              onClick={() => setSelectedDish(null)}
              className="absolute top-3 right-3 z-10 p-2 rounded-full bg-black/70 hover:bg-black text-white transition-colors border border-white/10"
              title="Yopish"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Katta rasm yoki nafis naqshli vitrina */}
            <div className="aspect-[16/10] w-full overflow-hidden bg-zinc-900 relative">
              {selectedDish.image_url ? (
                <img
                  src={selectedDish.image_url}
                  alt={selectedDish.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-br from-[#2a1f16] via-[#1c1510] to-[#12141a] flex flex-col items-center justify-center p-6 text-center">
                  <img
                    src="/dunyo-logo.png"
                    alt="Dunyo Choyxonasi"
                    className="w-20 h-20 rounded-full object-cover border-2 border-amber-400/60 shadow-xl shadow-amber-500/30 mb-3"
                  />
                  <span className="text-lg font-black text-white font-sans">
                    {selectedDish.name}
                  </span>
                  <span className="text-xs text-amber-400 font-semibold uppercase mt-1">
                    Dunyo Choyxonasi (Xiva)
                  </span>
                </div>
              )}
            </div>

            {/* Matnli qism */}
            <div className="p-5 sm:p-6 space-y-3.5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  {selectedDish.categoryName && (
                    <span className="text-[11px] font-black text-amber-400 uppercase tracking-wider block mb-1">
                      {selectedDish.categoryName}
                    </span>
                  )}
                  <h2 className="text-lg sm:text-xl font-black text-white leading-tight font-sans">
                    {selectedDish.name}
                  </h2>
                </div>
                <div className="text-right shrink-0">
                  <span className="inline-flex px-3 py-1 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 font-black text-base sm:text-lg font-sans">
                    {selectedDish.price?.toLocaleString()} so'm
                  </span>
                </div>
              </div>

              {selectedDish.description ? (
                <div className="pt-2 border-t border-white/[0.08]">
                  <p className="text-sm text-zinc-300 leading-relaxed font-sans">
                    {selectedDish.description}
                  </p>
                </div>
              ) : (
                <div className="pt-2 border-t border-white/[0.08]">
                  <p className="text-xs text-zinc-400 font-sans">
                    Dunyo Choyxonasining tabiiy masalliqlaridan tayyorlangan mazali milliy taom.
                  </p>
                </div>
              )}

              {/* Qo'ng'iroq qilib buyurtma qilish */}
              <div className="pt-2">
                <a
                  href="tel:+998884593400"
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition-all font-sans"
                >
                  <PhoneCall className="w-4 h-4 shrink-0" />
                  <span>Qo'ng'iroq qilib buyurtma berish: +998 88 459 34 00</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── 6. FOOTER & YASHIRIN XODIMLAR KIRISHI ─── */}
      <footer className="bg-[#0c0e12] border-t border-[#262b36] text-zinc-400 pt-8 pb-24 md:pb-8 px-4 sm:px-6 mt-14">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-center md:text-left">
          {/* Logo & Tavsif */}
          <div className="space-y-1">
            <div className="flex items-center justify-center md:justify-start gap-2.5">
              <img
                src="/dunyo-logo.png"
                alt="Dunyo Choyxonasi"
                className="w-8 h-8 rounded-full object-cover border border-amber-500/40 shadow-sm"
              />
              <span className="font-extrabold text-base text-white">Dunyo Choyxonasi</span>
            </div>
            <p className="text-xs text-zinc-500 max-w-sm">
              Xorazm mehmondo'stligi va eng sara milliy taomlar maskani.
            </p>
          </div>

          {/* Manzil, Telefon, Ish vaqti */}
          <div className="flex flex-wrap items-center justify-center gap-5 text-xs text-zinc-400 font-medium">
            <div className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-amber-500 shrink-0" />
              <span>Xorazm viloyati, Xiva tumani</span>
            </div>
            <div className="flex items-center gap-1.5">
              <PhoneCall className="w-4 h-4 text-amber-500 shrink-0" />
              <a href="tel:+998884593400" className="hover:text-white transition-colors">
                +998 88 459 34 00
              </a>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-500 shrink-0" />
              <span>09:00 — 23:00</span>
            </div>
          </div>
        </div>

        {/* Eng pastki qism: Mualliflik huquqi va ko'zga tashlanmaydigan Xodimlar tugmasi */}
        <div className="max-w-7xl mx-auto mt-6 pt-5 border-t border-[#262b36]/60 flex flex-col sm:flex-row items-center justify-between gap-2.5 text-xs text-zinc-500">
          <span>© 2026 Dunyo Choyxonasi. Barcha huquqlar himoyalangan.</span>

          {/* Talabdagi kamtarona xodimlar havolasi */}
          <button
            onClick={onOpenLogin}
            className="text-[11px] text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            Xodimlar uchun
          </button>
        </div>
      </footer>

      {/* ─── 7. MOBIL SUZUVCHI QO'NG'IROQ PANELI (md:hidden) ─── */}
      <div className="fixed bottom-0 left-0 right-0 p-3 z-40 bg-[#0f1115]/95 backdrop-blur-md border-t border-[#262b36] md:hidden">
        <a
          href="tel:+998884593400"
          className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/50 transition-all font-sans"
        >
          <PhoneCall className="w-4 h-4 shrink-0" />
          <span>Joy band qilish / Dastavka: +998 88 459 34 00</span>
        </a>
      </div>
    </div>
  );
};

export default DunyoLanding;
