import React, { useState, useEffect } from 'react';
import {
  UtensilsCrossed,
  QrCode,
  Sparkles,
  Coffee,
  Flame,
  ShieldCheck,
  Clock,
  MapPin,
  Phone,
  ArrowRight,
  Users,
  ChevronRight,
  Star,
  Layers,
  HeartHandshake
} from 'lucide-react';
import api from '../../utils/api';

export const DunyoLanding = ({ onSelectTable, onOpenLogin, onOpenMenuPreview }) => {
  const [tables, setTables] = useState([]);
  const [loadingTables, setLoadingTables] = useState(true);
  const [selectedRoom, setSelectedRoom] = useState('all');

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const data = await api.get('/tables?restaurant_id=1');
        if (data && Array.isArray(data)) {
          setTables(data);
        }
      } catch (err) {
        // Fallback demo tables if API is warming up
        const fallback = Array.from({ length: 12 }, (_, i) => ({
          id: i + 1,
          number: i + 1,
          name: `Stol #${i + 1}`,
          room: i < 4 ? "Asosiy Zal (So'ri)" : (i < 8 ? "Shinam Ayvon" : "VIP Xona"),
          capacity: i < 4 ? 6 : (i < 8 ? 8 : 12),
          status: 'available',
        }));
        setTables(fallback);
      } finally {
        setLoadingTables(false);
      }
    };
    fetchTables();
  }, []);

  const rooms = ['all', "Asosiy Zal (So'ri)", "Shinam Ayvon", "VIP Xona"];

  const filteredTables = selectedRoom === 'all'
    ? tables
    : tables.filter(t => (t.room || '').includes(selectedRoom) || (selectedRoom.includes("So'ri") && (t.room || '').includes('Zal')));

  return (
    <div className="min-h-screen bg-theme-bg text-theme-text selection:bg-amber-500/30">
      {/* ─── Hero Section ───────────────────────────────────── */}
      <section className="relative overflow-hidden pt-8 pb-16 px-4 sm:px-6 lg:px-8 border-b border-theme-border/50">
        {/* Background glow & traditional patterns */}
        <div className="absolute inset-0 bg-radial-at-t from-amber-500/10 via-transparent to-transparent pointer-events-none" />
        <div className="absolute top-10 right-10 w-96 h-96 bg-amber-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-10 w-80 h-80 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-6xl mx-auto text-center relative z-10 space-y-6">
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
            Samovarda damlangan shifobaxsh choylar, issiq tandir somsasi, qarsildoq qozon kabob va afsonaviy devzira palovimizdan bahramand bo'ling.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <a
              href="#tables-section"
              className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold text-sm shadow-xl shadow-amber-500/20 flex items-center gap-2 active:scale-98 transition-all"
            >
              <QrCode className="w-5 h-5" />
              <span>Stolni Tanlash / QR Kirish</span>
            </a>

            <button
              onClick={onOpenLogin}
              className="px-5 py-3.5 rounded-2xl bg-theme-surface/80 hover:bg-theme-surface border border-theme-border text-white font-bold text-sm flex items-center gap-2 transition-all hover:border-amber-500/50"
            >
              <Users className="w-4 h-4 text-theme-primary" />
              <span>Xodimlar Portali</span>
            </button>
          </div>

          {/* Feature Highlights Pill */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-8 max-w-4xl mx-auto text-left">
            <div className="p-3.5 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center shrink-0">
                <QrCode className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">QR Buyurtma</h4>
                <p className="text-[11px] text-theme-muted">Navbatsiz, to'g'ridan-to'g'ri stoldan</p>
              </div>
            </div>

            <div className="p-3.5 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">100% Halol</h4>
                <p className="text-[11px] text-theme-muted">Faqat barra go'sht va tabiiy masalliqlar</p>
              </div>
            </div>

            <div className="p-3.5 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/15 text-blue-400 flex items-center justify-center shrink-0">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Tezkor Xizmat</h4>
                <p className="text-[11px] text-theme-muted">Issiq holatda yetkaziladi</p>
              </div>
            </div>

            <div className="p-3.5 rounded-2xl glass-card border border-theme-border bg-theme-surface/60 flex items-center gap-3">
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

      {/* ─── Table Selector / QR Section ────────────────────── */}
      <section id="tables-section" className="py-14 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-bold">
            <QrCode className="w-3.5 h-3.5" />
            <span>STOLINGIZNI TANLANG</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
            Qaysi stolda o'tiribsiz?
          </h2>
          <p className="text-xs sm:text-sm text-theme-muted max-w-xl mx-auto">
            Stolingizdagi <strong>QR kodni</strong> telefon kamerangizda skaner qiling yoki menyuni ochish uchun pastdagi stollardan birini bosing:
          </p>
        </div>

        {/* Room Filter Pills */}
        <div className="flex items-center justify-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {rooms.map((room) => (
            <button
              key={room}
              onClick={() => setSelectedRoom(room)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                selectedRoom === room
                  ? 'bg-amber-500 text-black shadow-glow scale-105'
                  : 'bg-theme-surface border border-theme-border text-theme-muted hover:text-white'
              }`}
            >
              {room === 'all' ? '🏠 Barcha Stollar' : room}
            </button>
          ))}
        </div>

        {/* Tables Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
          {filteredTables.map((t) => (
            <button
              key={t.id}
              onClick={() => onSelectTable(t)}
              className="p-4 rounded-2xl glass-card border border-theme-border hover:border-amber-500/80 bg-theme-surface/70 hover:bg-theme-surface text-center group transition-all transform hover:-translate-y-1 hover:shadow-xl hover:shadow-amber-500/10 flex flex-col items-center justify-between min-h-[130px]"
            >
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 group-hover:bg-amber-500 group-hover:text-black text-amber-400 flex items-center justify-center font-black text-sm transition-colors">
                #{t.number}
              </div>

              <div className="my-1.5">
                <span className="block font-bold text-sm text-white group-hover:text-amber-300 transition-colors">
                  Stol #{t.number}
                </span>
                <span className="block text-[10px] text-theme-muted line-clamp-1">
                  {t.room || "Asosiy Zal"}
                </span>
              </div>

              <div className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400/90 group-hover:text-amber-300">
                <span>Menyuga kirish</span>
                <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* ─── Choyxona Menu Highlights ──────────────────────── */}
      <section className="py-12 px-4 sm:px-6 lg:px-8 bg-black/20 border-t border-theme-border/50">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-bold mb-2">
                <Flame className="w-3.5 h-3.5" />
                <span>MASHHUR TAOMLAR</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
                Dunyo Choyxonasi Maxsus Taomlari
              </h2>
            </div>
            <p className="text-xs text-theme-muted max-w-sm">
              Har bir taom milliy an'analar va eng sara barra masalliqlar asosida tayyorlanadi.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                title: "Choyxona Maxsus Palovi",
                price: "48,000 so'm",
                desc: "Devzira guruch, barra qo'y go'shti, qazi, bedana tuxum va mayiz bilan damlangan afsonaviy palov.",
                img: "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80",
                tag: "Bosh Taom 🔥"
              },
              {
                title: "Qozon Kabob (Barra Go'sht)",
                price: "58,000 so'm",
                desc: "Qarsildoq tillarang kartoshka va erib ketadigan barra qo'y qovurg'asi.",
                img: "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80",
                tag: "Eng Ko'p Buyurtma ⭐️"
              },
              {
                title: "G'ijduvon Shashlik (Qiyma)",
                price: "22,000 so'm",
                desc: "Yumshoq mol va qo'y go'shti qiymasi, maxsus sharqona ziravorlar bilan.",
                img: "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80",
                tag: "Olovda Pishgan 🍢"
              },
              {
                title: "Tandir Somsa (Go'shtli)",
                price: "12,000 so'm",
                desc: "Qarsildoq qatlama xamir, mayda to'g'ralgan lahm go'sht va dumba.",
                img: "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=600&q=80",
                tag: "Issiq Tandir 🥟"
              },
              {
                title: "Samovar Ko'k Choy (Limon & Novvot)",
                price: "10,000 so'm",
                desc: "Samovarda damlangan an'anaviy xushbo'y ko'k choy, limon va novvot bilan.",
                img: "https://images.unsplash.com/photo-1576092768241-dec231879fc3?auto=format&fit=crop&w=600&q=80",
                tag: "Choyxona Ruhı 🫖"
              },
              {
                title: "Asalli Chak-Chak",
                price: "20,000 so'm",
                desc: "Xonaki tog' asali va bodom donalari bilan bezatilgan qarsildoq shirinlik.",
                img: "https://images.unsplash.com/photo-1579372786545-d24232daf58c?auto=format&fit=crop&w=600&q=80",
                tag: "Shirinlik 🍯"
              }
            ].map((item, idx) => (
              <div
                key={idx}
                className="rounded-3xl glass-card border border-theme-border bg-theme-surface/80 overflow-hidden group hover:border-amber-500/50 transition-all shadow-lg"
              >
                <div className="relative h-44 overflow-hidden bg-black/40">
                  <img
                    src={item.img}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-black/70 backdrop-blur-md text-amber-300 text-[10px] font-extrabold border border-amber-500/30">
                    {item.tag}
                  </span>
                </div>
                <div className="p-4 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-extrabold text-sm text-white">{item.title}</h3>
                    <span className="font-black text-amber-400 text-sm whitespace-nowrap">{item.price}</span>
                  </div>
                  <p className="text-xs text-theme-muted line-clamp-2 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
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
              <span>Toshkent shahri, Chilonzor tumani</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Phone className="w-4 h-4 text-amber-400" />
              <span>+998 71 200 00 00</span>
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
