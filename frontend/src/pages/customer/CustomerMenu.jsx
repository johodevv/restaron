import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useCart } from '../../context/CartContext';
import {
  Search,
  Plus,
  Clock,
  Flame,
  ShoppingBag,
  BellRing,
  Sparkles,
  Utensils,
  Receipt,
  Image as ImageIcon
} from 'lucide-react';

export const CustomerMenu = ({
  restaurantId = 1,
  tableInfo,
  onOpenCart,
  onOpenCallWaiter,
  onOpenBill,
  onReturnToLanding,
}) => {
  const [categories, setCategories] = useState([]);
  const [selectedCatId, setSelectedCatId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const { addToCart, totalCount, subtotal } = useCart();

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const data = await api.get(`/menu/full/${restaurantId}`);
        setCategories(data);
        if (data.length > 0) {
          setSelectedCatId(data[0].id);
        }
      } catch (err) {
        console.error('Menu load error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMenu();
  }, [restaurantId]);

  // Filter items
  const activeCategory = categories.find((c) => c.id === selectedCatId);
  const allItems = categories.flatMap((c) => c.items || []);

  const displayedItems = searchQuery.trim()
    ? allItems.filter((item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.description && item.description.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : activeCategory?.items || [];

  return (
    <div className="min-h-screen pb-32">
      {/* Hero Banner for Table */}
      <div className="max-w-7xl mx-auto px-4 pt-4 sm:pt-6">
        <div className="p-5 sm:p-7 rounded-3xl glass-card border border-theme-border bg-gradient-to-r from-theme-surface via-theme-bg to-theme-surface shadow-2xl relative overflow-hidden">
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-bold">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Dunyo Choyxonasi • Stol #{tableInfo?.number || 1} {tableInfo?.room ? `(${tableInfo.room})` : ''}</span>
                </div>
                {onReturnToLanding && (
                  <button
                    onClick={onReturnToLanding}
                    className="text-xs text-theme-muted hover:text-white underline transition-colors"
                  >
                    ← Bosh sahifaga qaytish
                  </button>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Xush kelibsiz! 🫖 🍽️
              </h1>
              <p className="text-xs sm:text-sm text-theme-muted mt-1 max-w-lg">
                Stolingizdan to'g'ridan-to'g'ri buyurtma bering yoki ofitsiantni chaqiring. Taomlar issiq va xushbo'y holda yetkaziladi.
              </p>
            </div>

            {/* Quick table action buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {onOpenBill && (
                <button
                  onClick={onOpenBill}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-white/5 hover:bg-white/10 border border-theme-border text-white text-xs font-bold transition-all shadow-md active:scale-95"
                >
                  <Receipt className="w-4 h-4 text-theme-primary" />
                  <span>Hisob (Chek)</span>
                </button>
              )}

              <button
                onClick={onOpenCallWaiter}
                className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs font-bold transition-all shadow-lg active:scale-95"
              >
                <BellRing className="w-4 h-4 animate-bounce-subtle" />
                <span>Ofitsiant chaqirish</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="max-w-7xl mx-auto px-4 pt-5">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-theme-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Taom yoki ichimlik qidirish..."
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-theme-surface/70 border border-theme-border text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary shadow-sm backdrop-blur-md transition-colors"
          />
        </div>
      </div>

      {/* Category Pills (Horizontal scroll on mobile) */}
      {!searchQuery && (
        <div className="max-w-7xl mx-auto px-4 pt-4">
          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none no-scrollbar">
            {categories.map((cat) => {
              const isSelected = selectedCatId === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCatId(cat.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold whitespace-nowrap transition-all ${
                    isSelected
                      ? 'bg-theme-primary text-white shadow-glow scale-102'
                      : 'bg-theme-surface/60 border border-theme-border/70 text-theme-muted hover:text-white hover:border-theme-primary/40'
                  }`}
                >
                  <span className="text-base">{cat.icon || '🍽️'}</span>
                  <span>{cat.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 font-normal">
                    {cat.items?.length || 0}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Dish Grid */}
      <div className="max-w-7xl mx-auto px-4 pt-5">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <div
                key={n}
                className="h-72 rounded-3xl bg-white/5 animate-pulse border border-theme-border"
              />
            ))}
          </div>
        ) : displayedItems.length === 0 ? (
          <div className="py-20 text-center text-theme-muted">
            <Utensils className="w-12 h-12 mx-auto mb-3 opacity-40" />
            <p className="text-base font-semibold text-white">Taomlar topilmadi</p>
            <p className="text-xs mt-1">Boshqa kalit so'z orqali qidirib ko'ring yoki boshqa kategoriyani tanlang.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {displayedItems.map((dish) => {
              const imgSrc = dish.image_url
                ? (dish.image_url.startsWith('http') ? dish.image_url : dish.image_url)
                : null;

              return (
                <div
                  key={dish.id}
                  className="group rounded-3xl glass-card border border-theme-border bg-theme-surface/75 hover:border-theme-primary/60 transition-all duration-300 flex flex-col justify-between overflow-hidden shadow-lg hover:shadow-2xl hover:-translate-y-1"
                >
                  {/* Dish Image Container */}
                  <div className="relative w-full h-44 bg-black/40 overflow-hidden">
                    {imgSrc ? (
                      <img
                        src={imgSrc}
                        alt={dish.name}
                        loading="lazy"
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-theme-muted/40 bg-gradient-to-br from-black/20 to-black/40">
                        <Utensils className="w-10 h-10 mb-1" />
                        <span className="text-[10px]">RestAron Taomi</span>
                      </div>
                    )}

                    {/* Gradient Overlay for Badges */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30 pointer-events-none" />

                    {/* Top Badges */}
                    <div className="absolute top-3 left-3 right-3 flex items-center justify-between gap-2 pointer-events-none">
                      {dish.is_featured ? (
                        <span className="text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full bg-amber-500 text-black shadow-md">
                          🔥 Tavsiya
                        </span>
                      ) : <span />}

                      <div className="flex items-center gap-1.5">
                        {dish.prep_time_minutes && (
                          <span className="flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-white border border-white/10">
                            <Clock className="w-3 h-3 text-theme-primary" />
                            {dish.prep_time_minutes}m
                          </span>
                        )}
                        {dish.calories && (
                          <span className="flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-orange-300 border border-white/10">
                            <Flame className="w-3 h-3 text-orange-400" />
                            {dish.calories}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-3">
                    <div>
                      <h3 className="font-bold text-base text-white group-hover:text-theme-primary transition-colors line-clamp-1">
                        {dish.name}
                      </h3>

                      {dish.description && (
                        <p className="text-xs text-theme-muted mt-1 line-clamp-2 leading-relaxed">
                          {dish.description}
                        </p>
                      )}
                    </div>

                    {/* Price & Add to Cart Button */}
                    <div className="flex items-center justify-between pt-3 border-t border-theme-border/60">
                      <div>
                        <span className="text-[11px] text-theme-muted block font-medium">Narxi:</span>
                        <span className="text-base font-extrabold text-white">
                          {(dish.price || 0).toLocaleString()} <span className="text-xs font-normal text-theme-muted">so'm</span>
                        </span>
                      </div>

                      <button
                        onClick={() => addToCart(dish)}
                        className="px-3.5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white shadow-glow active:scale-95 transition-all flex items-center gap-1.5 text-xs font-bold"
                      >
                        <Plus className="w-4 h-4" />
                        <span>Qo'shish</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Floating Bottom Cart Bar for Customer */}
      {totalCount > 0 && (
        <div className="fixed bottom-4 left-4 right-4 z-40 max-w-xl mx-auto animate-slide-up">
          <div className="p-3.5 rounded-2xl glass-card border border-theme-primary/50 bg-theme-surface/95 shadow-2xl backdrop-blur-xl flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-theme-primary text-white flex items-center justify-center font-bold text-sm shadow-glow">
                {totalCount}
              </div>
              <div>
                <div className="text-xs text-theme-muted font-medium">Jami savat:</div>
                <div className="text-sm font-extrabold text-white">
                  {subtotal.toLocaleString()} so'm
                </div>
              </div>
            </div>

            <button
              onClick={onOpenCart}
              className="px-5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center gap-2 active:scale-95 transition-all"
            >
              <ShoppingBag className="w-4 h-4" />
              <span>Buyurtma berish</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomerMenu;
