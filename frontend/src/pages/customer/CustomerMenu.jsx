import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useWebSocket } from '../../context/WebSocketContext';
import { useLanguage } from '../../context/LanguageContext';
import {
  Search,
  Clock,
  Flame,
  BellRing,
  Sparkles,
  Utensils,
  Receipt,
  Image as ImageIcon,
  Info,
  X,
  Scale
} from 'lucide-react';

export const CustomerMenu = ({
  restaurantId = 1,
  tableInfo,
  onOpenCallWaiter,
  onOpenBill,
  onReturnToLanding,
}) => {
  const { t, getLocalizedName, getLocalizedDesc } = useLanguage();
  const [categories, setCategories] = useState([]);
  const [selectedCatId, setSelectedCatId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeItemDetail, setActiveItemDetail] = useState(null);
  const { addEventListener } = useWebSocket();

  const fetchMenu = async () => {
    try {
      const data = await api.get(`/menu/full/${restaurantId}`);
      setCategories(data);
      if (data.length > 0 && !selectedCatId) {
        setSelectedCatId(data[0].id);
      }
    } catch (err) {
      console.error('Menu load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMenu();
  }, [restaurantId]);

  // Real-time stop-list yangilanishi
  useEffect(() => {
    const unsub = addEventListener('stop_list_updated', (event) => {
      setCategories((prevCats) =>
        prevCats.map((cat) => ({
          ...cat,
          items: (cat.items || []).map((item) =>
            item.id === event.item_id
              ? { ...item, is_stop_list: event.is_stop_list, is_available: event.is_available }
              : item
          ),
        }))
      );
    });
    return () => unsub();
  }, [addEventListener]);

  const activeCategory = categories.find((c) => c.id === selectedCatId);
  const allItems = categories.flatMap((c) => c.items || []);

  const displayedItems = searchQuery.trim()
    ? allItems.filter(
        (item) =>
          item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (item.description && item.description.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : activeCategory?.items || [];

  return (
    <div className="min-h-screen pb-36 bg-slate-950 text-slate-100">
      {/* Hero Header */}
      <div className="max-w-7xl mx-auto px-4 pt-4 sm:pt-6">
        <div className="p-5 sm:p-7 rounded-3xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-950 to-slate-900 shadow-2xl relative overflow-hidden">
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>
                    Stol #{tableInfo?.number || 1} {tableInfo?.room ? `(${tableInfo.room})` : ''}
                  </span>
                </div>
                {onReturnToLanding && (
                  <button
                    onClick={onReturnToLanding}
                    className="text-xs text-slate-400 hover:text-white underline transition-colors"
                  >
                    ← Bosh sahifaga
                  </button>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Xush kelibsiz! 🍽️
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-lg">
                Menyudan taomlarni ko'rib chiqing. Buyurtmani ofitsiant stolingizga kelib qabul qiladi.
              </p>
            </div>

            {/* Quick table actions */}
            <div className="flex flex-wrap items-center gap-2.5">
              {onOpenBill && (
                <button
                  onClick={onOpenBill}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/70 text-white text-xs font-bold transition-all shadow-md active:scale-95"
                >
                  <Receipt className="w-4 h-4 text-amber-400" />
                  <span>Hisob (Chek)</span>
                </button>
              )}

              {onOpenCallWaiter && (
                <button
                  onClick={onOpenCallWaiter}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-extrabold transition-all shadow-lg shadow-amber-500/25 active:scale-95"
                >
                  <BellRing className="w-4 h-4" />
                  <span>Ofitsiantni chaqirish</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Info Notice Banner */}
      <div className="max-w-7xl mx-auto px-4 mt-3">
        <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300/90 text-xs">
          <Info className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            <b>Eslatma:</b> Taomlar buyurtmasi ofitsiant orqali olinadi. Ma'qul taomlarni tanlab, pastdagi <b>"Ofitsiantni chaqirish"</b> tugmasini bosing.
          </span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="max-w-7xl mx-auto px-4 mt-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Taom yoki ichimlik qidirish..."
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-slate-900 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500/60 transition-colors shadow-inner"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white p-1"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Categories Horizontal Tabs */}
      {!searchQuery && (
        <div className="max-w-7xl mx-auto px-4 mt-5">
          <div className="flex gap-2 overflow-x-auto no-scrollbar pb-2">
            {categories.map((cat) => {
              const active = cat.id === selectedCatId;
              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCatId(cat.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold shrink-0 transition-all ${
                    active
                      ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-500/25 scale-105'
                      : 'bg-slate-900 hover:bg-slate-850 text-slate-300 border border-slate-800'
                  }`}
                >
                  <span className="text-sm">{cat.icon || '🍽️'}</span>
                  <span>{getLocalizedName(cat)}</span>
                  {cat.items && (
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                        active ? 'bg-slate-950/20 text-slate-950' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {cat.items.length}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Dishes Grid */}
      <div className="max-w-7xl mx-auto px-4 mt-6">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div
                key={n}
                className="h-72 rounded-3xl bg-slate-900/60 border border-slate-800 animate-pulse"
              />
            ))}
          </div>
        ) : displayedItems.length === 0 ? (
          <div className="text-center py-16 px-4 bg-slate-900/40 rounded-3xl border border-slate-800">
            <Utensils className="w-12 h-12 mx-auto text-slate-600 mb-3" />
            <h3 className="text-base font-bold text-white">Hech narsa topilmadi</h3>
            <p className="text-xs text-slate-400 mt-1">Boshqa so'z bilan qidirib ko'ring</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
            {displayedItems.map((item) => {
              const isUnavailable = item.is_stop_list || item.is_available === false;
              return (
                <div
                  key={item.id}
                  onClick={() => setActiveItemDetail(item)}
                  className={`group relative rounded-3xl bg-slate-900 border border-slate-800 overflow-hidden shadow-lg hover:border-slate-700 transition-all cursor-pointer flex flex-col justify-between ${
                    isUnavailable ? 'opacity-65 grayscale-[30%]' : 'hover:-translate-y-1'
                  }`}
                >
                  <div>
                    {/* Item Image */}
                    <div className="relative h-44 w-full bg-slate-950 overflow-hidden">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={getLocalizedName(item)}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex flex-col items-center justify-center text-slate-600">
                          <ImageIcon className="w-8 h-8 mb-1" />
                          <span className="text-[11px]">Rasm yo'q</span>
                        </div>
                      )}

                      {/* Stop-List or Available Tag */}
                      {isUnavailable ? (
                        <div className="absolute top-3 left-3 px-3 py-1 rounded-full bg-red-600/90 text-white text-[11px] font-extrabold shadow-md backdrop-blur-sm">
                          Tugagan (Stop-list)
                        </div>
                      ) : item.is_featured ? (
                        <div className="absolute top-3 left-3 px-3 py-1 rounded-full bg-amber-500 text-slate-950 text-[11px] font-extrabold shadow-md flex items-center gap-1">
                          <Sparkles className="w-3 h-3" />
                          Hit Taom
                        </div>
                      ) : null}

                      {/* Prep Time */}
                      {item.prep_time_minutes && (
                        <div className="absolute bottom-3 right-3 px-2.5 py-1 rounded-xl bg-black/60 backdrop-blur-md text-slate-200 text-[11px] font-medium flex items-center gap-1 border border-white/10">
                          <Clock className="w-3 h-3 text-amber-400" />
                          <span>{item.prep_time_minutes} daq</span>
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="p-4 sm:p-5">
                      <h3 className="font-bold text-white text-base leading-snug group-hover:text-amber-400 transition-colors">
                        {getLocalizedName(item)}
                      </h3>
                      {item.description && (
                        <p className="text-xs text-slate-400 line-clamp-2 mt-1.5 leading-relaxed">
                          {getLocalizedDesc(item)}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Price Bar */}
                  <div className="p-4 pt-0 sm:p-5 sm:pt-0 flex items-center justify-between border-t border-slate-800/60 mt-3 pt-3">
                    <div>
                      <span className="text-[11px] text-slate-400 block font-medium">Narxi:</span>
                      <span className="text-base sm:text-lg font-black text-emerald-400">
                        {item.price.toLocaleString('uz-UZ')} so'm
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveItemDetail(item);
                      }}
                      className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
                    >
                      Batafsil
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Floating Bottom Bar for Call Waiter */}
      <div className="fixed bottom-0 inset-x-0 z-40 p-4 bg-gradient-to-t from-slate-950 via-slate-950/95 to-transparent pointer-events-none">
        <div className="max-w-xl mx-auto flex items-center gap-3 pointer-events-auto">
          {onOpenCallWaiter && (
            <button
              onClick={onOpenCallWaiter}
              className="flex-1 py-3.5 px-6 rounded-2xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:from-amber-400 hover:to-orange-500 text-white font-extrabold text-sm shadow-xl shadow-amber-500/25 active:scale-[0.98] transition-all flex items-center justify-center gap-2.5"
            >
              <BellRing className="w-5 h-5 animate-bounce-subtle" />
              <span>Ofitsiantni chaqirish</span>
            </button>
          )}

          {onOpenBill && (
            <button
              onClick={onOpenBill}
              className="py-3.5 px-4 rounded-2xl bg-slate-900 border border-slate-700 hover:bg-slate-800 text-white text-xs font-bold shadow-xl active:scale-[0.98] transition-all flex items-center justify-center gap-1.5"
            >
              <Receipt className="w-4 h-4 text-amber-400" />
              <span>Hisob</span>
            </button>
          )}
        </div>
      </div>

      {/* Item Details Modal */}
      {activeItemDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full overflow-hidden shadow-2xl relative">
            <button
              onClick={() => setActiveItemDetail(null)}
              className="absolute top-4 right-4 z-10 w-8 h-8 rounded-full bg-black/60 backdrop-blur-md text-white flex items-center justify-center hover:bg-black transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            {activeItemDetail.image_url && (
              <div className="h-64 w-full bg-black overflow-hidden relative">
                <img
                  src={activeItemDetail.image_url}
                  alt={activeItemDetail.name}
                  className="w-full h-full object-cover"
                />
                {activeItemDetail.is_stop_list && (
                  <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center">
                    <span className="px-4 py-1.5 rounded-full bg-red-600 text-white text-xs font-extrabold">
                      Hozirda mavjud emas (Stop-list)
                    </span>
                  </div>
                )}
              </div>
            )}

            <div className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-extrabold text-white">{getLocalizedName(activeItemDetail)}</h2>
                  <p className="text-emerald-400 font-black text-lg mt-1">
                    {activeItemDetail.price.toLocaleString('uz-UZ')} so'm
                  </p>
                </div>
              </div>

              {activeItemDetail.description && (
                <p className="text-xs sm:text-sm text-slate-300 mt-3 leading-relaxed">
                  {getLocalizedDesc(activeItemDetail)}
                </p>
              )}

              {/* Extra tags */}
              <div className="flex flex-wrap gap-2.5 mt-5 pt-4 border-t border-slate-800">
                {activeItemDetail.prep_time_minutes && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs">
                    <Clock className="w-3.5 h-3.5 text-amber-400" />
                    <span>Tayyorlash: {activeItemDetail.prep_time_minutes} daqiqa</span>
                  </div>
                )}

                {activeItemDetail.calories && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs">
                    <Flame className="w-3.5 h-3.5 text-orange-400" />
                    <span>{activeItemDetail.calories} kkal</span>
                  </div>
                )}

                {activeItemDetail.weight_grams && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs">
                    <Scale className="w-3.5 h-3.5 text-blue-400" />
                    <span>{activeItemDetail.weight_grams} gr</span>
                  </div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-between gap-3">
                <button
                  onClick={() => setActiveItemDetail(null)}
                  className="w-full py-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-colors"
                >
                  Yopish
                </button>
                {onOpenCallWaiter && (
                  <button
                    onClick={() => {
                      setActiveItemDetail(null);
                      onOpenCallWaiter();
                    }}
                    className="w-full py-3 rounded-2xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black transition-colors flex items-center justify-center gap-2"
                  >
                    <BellRing className="w-4 h-4" />
                    <span>Ofitsiantni chaqirish</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomerMenu;
