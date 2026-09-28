import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useWebSocket } from '../../context/WebSocketContext';
import BillModal from '../../components/BillModal';
import {
  LayoutDashboard,
  UtensilsCrossed,
  Table as TableIcon,
  Users,
  Settings,
  Star,
  Plus,
  Trash2,
  Edit2,
  Download,
  Check,
  RefreshCw,
  Sparkles,
  QrCode,
  Printer,
  Copy,
  ExternalLink,
  X,
  Upload,
  Wifi,
  Layers,
  Clock,
  Flame,
  CheckCircle,
  AlertTriangle,
  FileImage,
  Receipt,
  UserMinus,
  BellRing,
  Power,
  ShieldCheck
} from 'lucide-react';

export const AdminDashboard = () => {
  const { user } = useAuth();
  const { activeThemes, setActiveThemes, allThemes } = useTheme();
  const { addEventListener } = useWebSocket();
  const [tab, setTab] = useState('overview'); // 'overview' | 'menu' | 'tables' | 'staff' | 'settings' | 'reviews'

  const restaurantId = user?.restaurant_id || 1;

  // State
  const [stats, setStats] = useState(null);
  const [categories, setCategories] = useState([]);
  const [tables, setTables] = useState([]);
  const [staff, setStaff] = useState([]);
  const [waiterCalls, setWaiterCalls] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  // Bill Modal state
  const [billModalOpen, setBillModalOpen] = useState(false);
  const [selectedBillTable, setSelectedBillTable] = useState(null);
  const [staffActionLoading, setStaffActionLoading] = useState(null);

  // Network & Host Settings for QR codes
  const [lanInfo, setLanInfo] = useState(null);
  const [qrBaseUrl, setQrBaseUrl] = useState(() => {
    return localStorage.getItem('restaron_qr_base_url') || window.location.origin;
  });
  const [isEditingBaseUrl, setIsEditingBaseUrl] = useState(false);
  const [tempBaseUrl, setTempBaseUrl] = useState('');

  // Modals & UI States
  const [selectedTableQR, setSelectedTableQR] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  // Table creation state
  const [newTableNumber, setNewTableNumber] = useState('');
  const [newTableRoom, setNewTableRoom] = useState('');
  const [newTableCapacity, setNewTableCapacity] = useState(4);

  // Staff creation state
  const [newStaffUsername, setNewStaffUsername] = useState('');
  const [newStaffFullName, setNewStaffFullName] = useState('');
  const [newStaffPassword, setNewStaffPassword] = useState('');
  const [newStaffRole, setNewStaffRole] = useState('waiter');

  // Category Modal States (Add & Edit)
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [categoryName, setCategoryName] = useState('');
  const [categoryIcon, setCategoryIcon] = useState('🍽️');
  const [categoryNameRu, setCategoryNameRu] = useState('');
  const [categoryNameEn, setCategoryNameEn] = useState('');

  // Dish Modal States (Add & Edit)
  const [showDishModal, setShowDishModal] = useState(false);
  const [editingDish, setEditingDish] = useState(null);
  const [dishName, setDishName] = useState('');
  const [dishPrice, setDishPrice] = useState('');
  const [dishCategory, setDishCategory] = useState('');
  const [dishDescription, setDishDescription] = useState('');
  const [dishPrepTime, setDishPrepTime] = useState(15);
  const [dishCalories, setDishCalories] = useState('');
  const [dishImageUrl, setDishImageUrl] = useState('');
  const [dishImageFile, setDishImageFile] = useState(null);
  const [dishIsFeatured, setDishIsFeatured] = useState(false);
  const [dishIsAvailable, setDishIsAvailable] = useState(true);
  const [savingDish, setSavingDish] = useState(false);

  const loadAll = async () => {
    try {
      const [statsData, menuData, tablesData, staffData, callsData, reviewsData, lanData] = await Promise.all([
        api.get(`/stats/dashboard?restaurant_id=${restaurantId}`).catch(() => null),
        api.get(`/menu/full/${restaurantId}`).catch(() => []),
        api.get(`/tables/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/users/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/reviews/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get('/stats/lan-info').catch(() => null),
      ]);

      setStats(statsData);
      setCategories(menuData || []);
      setTables(tablesData || []);
      setStaff(staffData || []);
      setWaiterCalls(callsData || []);
      setReviews(reviewsData || []);

      if (lanData) {
        setLanInfo(lanData);
        const savedUrl = localStorage.getItem('restaron_qr_base_url');
        if (!savedUrl && lanData.suggested_frontend_url && window.location.hostname === 'localhost') {
          setQrBaseUrl(lanData.suggested_frontend_url);
          localStorage.setItem('restaron_qr_base_url', lanData.suggested_frontend_url);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();

    const unsubscribe = addEventListener('*', (event) => {
      if (
        event.type === 'new_order' ||
        event.type === 'table_cleared' ||
        event.type === 'table_status_updated' ||
        event.type === 'order_delivered' ||
        event.type === 'order_ready' ||
        event.type === 'order_status_updated' ||
        event.type === 'call_waiter' ||
        event.type === 'call_completed' ||
        event.type === 'bill_paid'
      ) {
        loadAll();
      }
    });

    return () => unsubscribe();
  }, [restaurantId]);

  // Handle Staff Deletion (Bo'shatish)
  const handleDeleteStaff = async (staffId, staffName) => {
    if (!window.confirm(`Haqiqatan ham "${staffName}" xodimini bo'shatish (akkauntini o'chirish)ni tasdiqlaysizmi?`)) {
      return;
    }
    setStaffActionLoading(staffId);
    try {
      await api.delete(`/users/${staffId}`);
      await loadAll();
    } catch (err) {
      alert(err.message || 'Xodimni o\'chirishda xatolik yuz berdi');
    } finally {
      setStaffActionLoading(null);
    }
  };

  // Handle Staff Active Status Toggle
  const handleToggleStaffActive = async (staffId, currentStatus) => {
    setStaffActionLoading(staffId);
    try {
      await api.patch(`/users/${staffId}`, { is_active: !currentStatus });
      await loadAll();
    } catch (err) {
      alert(err.message || 'Holatni o\'zgartirishda xatolik');
    } finally {
      setStaffActionLoading(null);
    }
  };

  // Handle Resolve Call
  const handleResolveCall = async (callId) => {
    try {
      await api.post(`/orders/calls/${callId}/resolve`);
      await loadAll();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  const handleOpenBill = (t) => {
    setSelectedBillTable(t);
    setBillModalOpen(true);
  };

  // Save QR Base URL
  const handleSaveBaseUrl = () => {
    if (tempBaseUrl.trim()) {
      let formatted = tempBaseUrl.trim();
      if (!formatted.startsWith('http://') && !formatted.startsWith('https://')) {
        formatted = `http://${formatted}`;
      }
      formatted = formatted.replace(/\/$/, '');
      setQrBaseUrl(formatted);
      localStorage.setItem('restaron_qr_base_url', formatted);
    }
    setIsEditingBaseUrl(false);
  };

  const handleResetToAutoIp = (suggestedUrl) => {
    if (suggestedUrl) {
      setQrBaseUrl(suggestedUrl);
      localStorage.setItem('restaron_qr_base_url', suggestedUrl);
      setIsEditingBaseUrl(false);
    }
  };

  // ─── TABLES MANAGEMENT ──────────────────────────────────────────
  const handleCreateTable = async (e) => {
    e.preventDefault();
    if (!newTableNumber) return;
    try {
      await api.post('/tables/', {
        restaurant_id: restaurantId,
        number: parseInt(newTableNumber),
        room: newTableRoom.trim() || undefined,
        capacity: parseInt(newTableCapacity) || 4,
      });
      setNewTableNumber('');
      setNewTableRoom('');
      loadAll();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  const handleClearTable = async (tableId, tableNumber) => {
    if (!window.confirm(`#${tableNumber} raqamli stolni bo'shatish (tozalash)ni xohlaysizmi?`)) return;
    try {
      await api.post(`/tables/${tableId}/clear`);
      loadAll();
    } catch (err) {
      alert(err.message || "Stolni bo'shatishda xatolik");
    }
  };

  const handleUpdateTableStatus = async (tableId, newStatus) => {
    try {
      await api.patch(`/tables/${tableId}/status?table_status=${newStatus}`);
      loadAll();
    } catch (err) {
      alert(err.message || "Holatni o'zgartirishda xatolik");
    }
  };

  const handleDeleteTable = async (tableId, tableNumber) => {
    if (!window.confirm(`#${tableNumber} raqamli stolni o'chirishni xohlaysizmi?`)) return;
    try {
      await api.delete(`/tables/${tableId}`);
      loadAll();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  const handleCopyLink = (qrToken, id) => {
    const url = `${qrBaseUrl}/?table=${qrToken}`;
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // ─── CATEGORY MANAGEMENT ──────────────────────────────────────────
  const handleOpenAddCategory = () => {
    setEditingCategory(null);
    setCategoryName('');
    setCategoryIcon('🍽️');
    setCategoryNameRu('');
    setCategoryNameEn('');
    setShowCategoryModal(true);
  };

  const handleOpenEditCategory = (cat) => {
    setEditingCategory(cat);
    setCategoryName(cat.name || '');
    setCategoryIcon(cat.icon || '🍽️');
    setCategoryNameRu(cat.name_ru || '');
    setCategoryNameEn(cat.name_en || '');
    setShowCategoryModal(true);
  };

  const handleSaveCategory = async (e) => {
    e.preventDefault();
    if (!categoryName.trim()) return;

    try {
      if (editingCategory) {
        // Update
        await api.patch(`/menu/categories/${editingCategory.id}`, {
          name: categoryName.trim(),
          icon: categoryIcon.trim() || '🍽️',
          name_ru: categoryNameRu.trim() || undefined,
          name_en: categoryNameEn.trim() || undefined,
        });
      } else {
        // Create
        await api.post('/menu/categories', {
          restaurant_id: restaurantId,
          name: categoryName.trim(),
          icon: categoryIcon.trim() || '🍽️',
          name_ru: categoryNameRu.trim() || undefined,
          name_en: categoryNameEn.trim() || undefined,
          sort_order: categories.length,
        });
      }
      setShowCategoryModal(false);
      loadAll();
    } catch (err) {
      alert(err.message || 'Kategoriyani saqlashda xatolik');
    }
  };

  const handleDeleteCategory = async (catId, catName) => {
    if (!window.confirm(`"${catName}" kategoriyasini o'chirishni xohlaysizmi? Ichidagi barcha taomlar ham o'chiriladi!`)) return;
    try {
      await api.delete(`/menu/categories/${catId}`);
      loadAll();
    } catch (err) {
      alert(err.message || 'Kategoriyani o\'chirishda xatolik');
    }
  };

  // ─── DISH (MENU ITEM) MANAGEMENT ────────────────────────────────
  const handleOpenAddDish = (defaultCatId = null) => {
    setEditingDish(null);
    setDishName('');
    setDishPrice('');
    setDishCategory(defaultCatId ? defaultCatId.toString() : (categories[0]?.id?.toString() || ''));
    setDishDescription('');
    setDishPrepTime(15);
    setDishCalories('');
    setDishImageUrl('');
    setDishImageFile(null);
    setDishIsFeatured(false);
    setDishIsAvailable(true);
    setShowDishModal(true);
  };

  const handleOpenEditDish = (dish) => {
    setEditingDish(dish);
    setDishName(dish.name || '');
    setDishPrice(dish.price ? dish.price.toString() : '');
    setDishCategory(dish.category_id ? dish.category_id.toString() : '');
    setDishDescription(dish.description || '');
    setDishPrepTime(dish.prep_time_minutes || 15);
    setDishCalories(dish.calories ? dish.calories.toString() : '');
    setDishImageUrl(dish.image_url || '');
    setDishImageFile(null);
    setDishIsFeatured(Boolean(dish.is_featured));
    setDishIsAvailable(Boolean(dish.is_available));
    setShowDishModal(true);
  };

  const handleSaveDish = async (e) => {
    e.preventDefault();
    if (!dishName.trim() || !dishPrice || !dishCategory) {
      alert("Iltimos, taom nomi, narxi va kategoriyasini kiriting");
      return;
    }

    setSavingDish(true);
    try {
      let savedDishId = null;

      if (editingDish) {
        // Update Dish
        const updated = await api.patch(`/menu/items/${editingDish.id}`, {
          name: dishName.trim(),
          price: parseFloat(dishPrice),
          category_id: parseInt(dishCategory),
          description: dishDescription.trim() || undefined,
          prep_time_minutes: parseInt(dishPrepTime) || 15,
          calories: dishCalories ? parseInt(dishCalories) : undefined,
          image_url: dishImageUrl.trim() || undefined,
          is_featured: dishIsFeatured,
          is_available: dishIsAvailable,
        });
        savedDishId = updated.id;
      } else {
        // Create Dish
        const created = await api.post('/menu/items', {
          name: dishName.trim(),
          price: parseFloat(dishPrice),
          category_id: parseInt(dishCategory),
          description: dishDescription.trim() || undefined,
          prep_time_minutes: parseInt(dishPrepTime) || 15,
          calories: dishCalories ? parseInt(dishCalories) : undefined,
          image_url: dishImageUrl.trim() || undefined,
          is_featured: dishIsFeatured,
          is_available: dishIsAvailable,
        });
        savedDishId = created.id;
      }

      // If a file was selected, upload image
      if (dishImageFile && savedDishId) {
        const formData = new FormData();
        formData.append('file', dishImageFile);
        const token = localStorage.getItem('restaron_token');
        await fetch(`${import.meta.env.VITE_API_URL || '/api/v1'}/menu/items/${savedDishId}/image`, {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
      }

      setShowDishModal(false);
      loadAll();
    } catch (err) {
      alert(err.message || 'Taomni saqlashda xatolik');
    } finally {
      setSavingDish(false);
    }
  };

  const handleDeleteDish = async (dishId, dishName) => {
    if (!window.confirm(`"${dishName}" taomini o'chirishni xohlaysizmi?`)) return;
    try {
      await api.delete(`/menu/items/${dishId}`);
      loadAll();
    } catch (err) {
      alert(err.message || 'Taomni o\'chirishda xatolik');
    }
  };

  const handleToggleDishAvailability = async (dish) => {
    try {
      await api.patch(`/menu/items/${dish.id}`, {
        is_available: !dish.is_available,
      });
      loadAll();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // ─── STAFF MANAGEMENT ──────────────────────────────────────────
  const handleCreateStaff = async (e) => {
    e.preventDefault();
    if (!newStaffUsername || !newStaffPassword) return;
    try {
      await api.post('/users/', {
        username: newStaffUsername.trim(),
        full_name: newStaffFullName.trim() || newStaffUsername.trim(),
        password: newStaffPassword,
        role: newStaffRole,
        restaurant_id: restaurantId,
      });
      setNewStaffUsername('');
      setNewStaffFullName('');
      setNewStaffPassword('');
      loadAll();
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // Toggle theme selection
  const handleToggleThemeSelection = (slug) => {
    if (activeThemes.includes(slug)) {
      if (activeThemes.length <= 1) {
        alert("Kamida bitta tema faol bo'lishi shart!");
        return;
      }
      setActiveThemes(activeThemes.filter((s) => s !== slug));
    } else {
      if (activeThemes.length >= 2) {
        setActiveThemes([activeThemes[0], slug]);
      } else {
        setActiveThemes([...activeThemes, slug]);
      }
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-fade-in pb-24">
      {/* Top Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-gradient-to-r from-theme-surface via-theme-bg to-theme-surface flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-theme-primary/15 border border-theme-primary/30 text-theme-primary text-xs font-bold mb-2">
            <Sparkles className="w-3.5 h-3.5" />
            <span>RestAron Boshqaruv Markazi</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Restoran Admin Paneli
          </h1>
          <p className="text-xs text-theme-muted mt-1">
            Menyular, rasmlar, stollar holati, QR kodlar va buyurtmalar nazorati.
          </p>
        </div>

        <button
          onClick={loadAll}
          className="self-start sm:self-auto p-2.5 rounded-xl border border-theme-border hover:border-theme-primary bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white transition-all flex items-center gap-2 text-xs font-semibold"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Yangilash</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none no-scrollbar">
        {[
          { key: 'overview', label: 'Xulosa va Statistika', icon: LayoutDashboard },
          { key: 'menu', label: 'Menyu & Taomlar', icon: UtensilsCrossed },
          { key: 'tables', label: 'Stollar & QR Kodlar', icon: TableIcon },
          { key: 'staff', label: 'Xodimlar', icon: Users },
          { key: 'settings', label: 'Dizayn & Temalar', icon: Settings },
          { key: 'reviews', label: 'Baholar', icon: Star },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs font-bold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-theme-primary text-white shadow-glow scale-102'
                  : 'bg-theme-surface/60 border border-theme-border text-theme-muted hover:text-white hover:border-theme-primary/40'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW */}
      {tab === 'overview' && (
        <div className="space-y-6">
          {/* Active Waiter Calls Alert if any */}
          {waiterCalls.length > 0 && (
            <div className="p-5 rounded-3xl bg-amber-500/15 border-2 border-amber-500/50 shadow-xl shadow-amber-500/10 space-y-3 animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                  <BellRing className="w-5 h-5 animate-bounce-subtle" />
                  <span>Ofitsiant chaqiruvlari ({waiterCalls.length} ta stol kutmoqda!)</span>
                </div>
                <span className="text-[11px] uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-amber-500 text-black">
                  Tezkor javob kerak
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
                {waiterCalls.map((call) => (
                  <div
                    key={call.id}
                    className="p-3.5 rounded-2xl bg-black/40 border border-amber-500/40 flex items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="font-extrabold text-white text-sm">
                        Stol #{call.table_number || call.table_id} {call.room ? `(${call.room})` : ''}
                      </div>
                      <div className="text-amber-200/90 text-[11px] truncate max-w-[180px]">
                        "{call.note || 'Ofitsiant chaqirildi'}"
                      </div>
                    </div>
                    <button
                      onClick={() => handleResolveCall(call.id)}
                      className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs whitespace-nowrap shadow-sm active:scale-95 transition-all"
                    >
                      Bajarildi
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80">
              <span className="text-xs text-theme-muted font-medium">Bugungi Tushum:</span>
              <div className="text-2xl font-black text-white mt-1">
                {(stats?.today?.total_revenue || stats?.today_revenue || 0).toLocaleString()} <span className="text-xs font-normal text-theme-muted">so'm</span>
              </div>
            </div>

            <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80">
              <span className="text-xs text-theme-muted font-medium">Bugungi Buyurtmalar:</span>
              <div className="text-2xl font-black text-emerald-400 mt-1">
                {stats?.today?.orders_count || stats?.today_orders || 0} ta
              </div>
            </div>

            <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80">
              <span className="text-xs text-theme-muted font-medium">Jami Stollar:</span>
              <div className="text-2xl font-black text-white mt-1">
                {tables.length} ta
              </div>
            </div>

            <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80">
              <span className="text-xs text-theme-muted font-medium">Faol Xodimlar:</span>
              <div className="text-2xl font-black text-amber-400 mt-1">
                {staff.length} nafar
              </div>
            </div>
          </div>

          {/* Realtime instructions */}
          <div className="p-6 rounded-3xl glass-card border border-theme-border bg-black/20 text-xs text-theme-muted space-y-3">
            <h4 className="font-bold text-white text-sm flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-theme-primary" />
              <span>Real-time boshqaruv va QR kod imkoniyatlari:</span>
            </h4>
            <ul className="space-y-2 list-disc list-inside">
              <li>
                <strong className="text-white">Stollarni bo'shatish:</strong> "Stollar & QR Kodlar" bo'limida har bir stol uchun "Stolni bo'shatish" tugmasini bosing yoki uning holatini o'zgartiring.
              </li>
              <li>
                <strong className="text-white">Telefonda QR skanerlash:</strong> "Stollar & QR Kodlar" bo'limida server IP manzilini tekshiring — telefoningiz ham shu Wi-Fi ga ulangan bo'lsa, QR kod to'g'ridan-to'g'ri ochiladi.
              </li>
              <li>
                <strong className="text-white">Menyu & Taomlar:</strong> Taomlarni qo'shish, rasmlarini yuklash, narxlarini o'zgartirish va yangi kategoriyalar ochish "Menyu & Taomlar" bo'limida amalga oshiriladi.
              </li>
            </ul>
          </div>
        </div>
      )}

      {/* TAB 2: MENU & DISHES MANAGER */}
      {tab === 'menu' && (
        <div className="space-y-6">
          {/* Top Actions: Add Category & Add Dish */}
          <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-extrabold text-white">Menyu va Kategoriyalar Boshqaruvi</h3>
              <p className="text-xs text-theme-muted mt-0.5">
                Taomlarni tahrirlang, yangi kategoriya oching va taom rasmlarini yuklang.
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={handleOpenAddCategory}
                className="px-4 py-2.5 rounded-2xl bg-white/10 hover:bg-white/20 border border-white/15 text-white text-xs font-bold flex items-center gap-2 transition-all"
              >
                <Layers className="w-4 h-4 text-theme-primary" />
                <span>+ Yangi Kategoriya</span>
              </button>

              <button
                onClick={() => handleOpenAddDish()}
                className="px-4 py-2.5 rounded-2xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center gap-2 transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>+ Yangi Taom</span>
              </button>
            </div>
          </div>

          {/* Categories & Dishes List */}
          <div className="space-y-6">
            {categories.length === 0 ? (
              <div className="p-12 text-center rounded-3xl glass-card border border-theme-border text-theme-muted">
                <UtensilsCrossed className="w-12 h-12 mx-auto mb-3 opacity-30 text-theme-primary" />
                <p className="text-base font-semibold text-white">Menyuda kategoriyalar mavjud emas</p>
                <p className="text-xs mt-1">Yangi kategoriya qo'shish orqali boshlang.</p>
                <button
                  onClick={handleOpenAddCategory}
                  className="mt-4 px-4 py-2 rounded-xl bg-theme-primary text-white text-xs font-bold"
                >
                  + Kategoriya yaratish
                </button>
              </div>
            ) : (
              categories.map((cat) => (
                <div
                  key={cat.id}
                  className="p-5 sm:p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/75 space-y-4 shadow-lg"
                >
                  {/* Category Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-theme-border/60">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl p-2 rounded-xl bg-black/30 border border-theme-border/60">{cat.icon || '🍽️'}</span>
                      <div>
                        <h4 className="font-extrabold text-lg text-white flex items-center gap-2">
                          <span>{cat.name}</span>
                          <span className="text-xs text-theme-muted font-normal">
                            ({cat.items?.length || 0} ta taom)
                          </span>
                        </h4>
                        {(cat.name_ru || cat.name_en) && (
                          <div className="text-[11px] text-theme-muted">
                            {cat.name_ru && <span>RU: {cat.name_ru} </span>}
                            {cat.name_en && <span>• EN: {cat.name_en}</span>}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenAddDish(cat.id)}
                        className="px-3 py-1.5 rounded-xl bg-theme-primary/15 hover:bg-theme-primary/25 border border-theme-primary/30 text-theme-primary text-xs font-semibold flex items-center gap-1.5 transition-all"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Taom qo'shish</span>
                      </button>

                      <button
                        onClick={() => handleOpenEditCategory(cat)}
                        title="Kategoriyani tahrirlash"
                        className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white border border-theme-border transition-colors"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleDeleteCategory(cat.id, cat.name)}
                        title="Kategoriyani o'chirish"
                        className="p-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Dishes in Category */}
                  {(!cat.items || cat.items.length === 0) ? (
                    <div className="py-6 text-center text-xs text-theme-muted border border-dashed border-theme-border/60 rounded-2xl">
                      Bu kategoriyada hali taomlar yo'q. "Taom qo'shish" tugmasini bosing.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {cat.items.map((item) => {
                        const imgSrc = item.image_url;
                        return (
                          <div
                            key={item.id}
                            className={`p-4 rounded-2xl border transition-all flex flex-col justify-between gap-3 ${
                              item.is_available
                                ? 'border-theme-border/70 bg-black/25 hover:border-theme-primary/50'
                                : 'border-red-500/30 bg-red-500/5 opacity-75'
                            }`}
                          >
                            <div className="space-y-2.5">
                              {/* Top row with Image and Info */}
                              <div className="flex items-start gap-3">
                                {imgSrc ? (
                                  <img
                                    src={imgSrc}
                                    alt={item.name}
                                    className="w-16 h-16 rounded-xl object-cover border border-theme-border shrink-0 shadow"
                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                  />
                                ) : (
                                  <div className="w-16 h-16 rounded-xl bg-white/5 border border-theme-border flex items-center justify-center text-theme-muted shrink-0">
                                    <UtensilsCrossed className="w-6 h-6 opacity-40" />
                                  </div>
                                )}

                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between gap-1">
                                    <h5 className="font-bold text-sm text-white truncate">
                                      {item.name}
                                    </h5>
                                    {item.is_featured && (
                                      <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                                        🔥
                                      </span>
                                    )}
                                  </div>

                                  <div className="text-xs text-theme-primary font-bold mt-0.5">
                                    {(item.price || 0).toLocaleString()} so'm
                                  </div>

                                  <div className="text-[10px] text-theme-muted flex items-center gap-2 mt-1">
                                    {item.prep_time_minutes && (
                                      <span className="flex items-center gap-0.5">
                                        <Clock className="w-2.5 h-2.5 text-theme-primary" />
                                        {item.prep_time_minutes}m
                                      </span>
                                    )}
                                    {item.calories && (
                                      <span className="flex items-center gap-0.5">
                                        <Flame className="w-2.5 h-2.5 text-orange-400" />
                                        {item.calories} kcal
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {item.description && (
                                <p className="text-[11px] text-theme-muted line-clamp-2 leading-relaxed">
                                  {item.description}
                                </p>
                              )}
                            </div>

                            {/* Actions row */}
                            <div className="flex items-center justify-between pt-2.5 border-t border-theme-border/50 text-xs">
                              <button
                                onClick={() => handleToggleDishAvailability(item)}
                                className={`px-2 py-1 rounded-lg text-[10px] font-bold transition-all ${
                                  item.is_available
                                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25'
                                    : 'bg-red-500/15 text-red-400 border border-red-500/30 hover:bg-red-500/25'
                                }`}
                              >
                                {item.is_available ? '✅ Mavjud' : '❌ Tugagan'}
                              </button>

                              <div className="flex items-center gap-1.5">
                                <button
                                  onClick={() => handleOpenEditDish(item)}
                                  className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white border border-theme-border transition-colors"
                                  title="Taomni tahrirlash"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>

                                <button
                                  onClick={() => handleDeleteDish(item.id, item.name)}
                                  className="p-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-colors"
                                  title="Taomni o'chirish"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 3: TABLES & QR CODES */}
      {tab === 'tables' && (
        <div className="space-y-6">
          {/* Network IP & QR Base URL Configuration */}
          <div className="p-5 sm:p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/80 space-y-3 shadow-lg">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-theme-primary/20 text-theme-primary flex items-center justify-center">
                  <Wifi className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-white">📱 Mobil Qurilmalar (Telefon) Uchun QR URL Manzili</h4>
                  <p className="text-xs text-theme-muted">
                    QR kod telefonda ochilishi uchun serveringizning lokal IP manzili ishlatiladi.
                  </p>
                </div>
              </div>

              {!isEditingBaseUrl ? (
                <button
                  onClick={() => {
                    setTempBaseUrl(qrBaseUrl);
                    setIsEditingBaseUrl(true);
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-theme-border text-white text-xs font-semibold self-start sm:self-auto"
                >
                  Manzilni o'zgartirish
                </button>
              ) : null}
            </div>

            {isEditingBaseUrl ? (
              <div className="pt-2 flex flex-col sm:flex-row items-center gap-2">
                <input
                  type="text"
                  value={tempBaseUrl}
                  onChange={(e) => setTempBaseUrl(e.target.value)}
                  placeholder="masalan: http://192.168.1.15:5173"
                  className="flex-1 w-full px-3.5 py-2 rounded-xl bg-black/40 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                />
                <button
                  onClick={handleSaveBaseUrl}
                  className="w-full sm:w-auto px-4 py-2 rounded-xl bg-theme-primary text-white text-xs font-bold shadow-glow"
                >
                  Saqlash
                </button>
                <button
                  onClick={() => setIsEditingBaseUrl(false)}
                  className="w-full sm:w-auto px-3 py-2 rounded-xl bg-white/5 text-theme-muted hover:text-white text-xs"
                >
                  Bekor qilish
                </button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-xs text-theme-muted">Hozirgi QR havola bazasi:</span>
                <span className="px-2.5 py-1 rounded-lg bg-black/40 border border-theme-border text-xs font-mono text-emerald-400 font-bold">
                  {qrBaseUrl}
                </span>

                {lanInfo?.suggested_frontend_url && qrBaseUrl !== lanInfo.suggested_frontend_url && (
                  <button
                    onClick={() => handleResetToAutoIp(lanInfo.suggested_frontend_url)}
                    className="text-[11px] text-theme-primary underline ml-2"
                  >
                    Avtomatik aniqlangan IP ga o'rnatish ({lanInfo.suggested_frontend_url})
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Add Table Form */}
          <form
            onSubmit={handleCreateTable}
            className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80 flex flex-col sm:flex-row items-center gap-3 shadow-lg"
          >
            <input
              type="number"
              placeholder="Stol raqami (masalan: 6)"
              value={newTableNumber}
              onChange={(e) => setNewTableNumber(e.target.value)}
              className="w-full sm:w-36 px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              required
            />
            <input
              type="text"
              placeholder="Xona / Zal (ixtiyoriy, masalan: VIP 1)"
              value={newTableRoom}
              onChange={(e) => setNewTableRoom(e.target.value)}
              className="w-full sm:flex-1 px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
            />
            <input
              type="number"
              placeholder="Sig'imi"
              value={newTableCapacity}
              onChange={(e) => setNewTableCapacity(e.target.value)}
              className="w-full sm:w-28 px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
            />
            <button
              type="submit"
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow whitespace-nowrap"
            >
              + Stol qo'shish
            </button>
          </form>

          {/* Tables Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {tables.map((t) => {
              const qrLink = `${qrBaseUrl}/?table=${t.qr_token}`;
              const qrImageSrc = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(qrLink)}`;

              const statusStr = (t.status || '').toLowerCase();
              const isOccupied = statusStr === 'occupied';
              const isReserved = statusStr === 'reserved';

              return (
                <div
                  key={t.id}
                  className={`p-5 rounded-3xl glass-card border transition-all duration-300 flex flex-col justify-between gap-4 shadow-lg ${
                    isOccupied
                      ? 'border-red-500/50 bg-red-950/20 shadow-red-500/10'
                      : isReserved
                      ? 'border-amber-500/50 bg-amber-950/20'
                      : 'border-theme-border bg-theme-surface/80 hover:border-theme-primary/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-2xl font-black text-white tracking-tight">
                          Stol #{t.number}
                        </span>
                        <span
                          className={`px-2.5 py-1 rounded-lg font-bold text-[10px] uppercase ${
                            isOccupied
                              ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                              : isReserved
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {isOccupied ? 'Band' : isReserved ? 'Bron' : "Bo'sh"}
                        </span>
                      </div>
                      <div className="text-xs text-theme-muted mt-0.5">
                        {t.room || 'Asosiy zal'} • Sig'imi: {t.capacity || 4} kishi
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteTable(t.id, t.number)}
                      title="Stolni o'chirish"
                      className="p-2 rounded-xl text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {/* QR Image Preview */}
                  <div
                    onClick={() => setSelectedTableQR({ ...t, qrLink })}
                    className="cursor-pointer bg-white p-3 rounded-2xl flex flex-col items-center justify-center gap-1 shadow-md hover:scale-102 transition-transform"
                  >
                    <img
                      src={qrImageSrc}
                      alt={`Stol #${t.number} QR`}
                      className="w-36 h-36 object-contain"
                    />
                    <div className="text-[11px] font-bold text-black flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-amber-500" />
                      <span>Kattalashtirish & Chop etish</span>
                    </div>
                  </div>

                  {/* Admin Table Control: Clear / Bill / Status Change */}
                  <div className="space-y-2 pt-2 border-t border-theme-border/60">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] text-theme-muted font-semibold">Holat:</span>
                      <select
                        value={statusStr || 'available'}
                        onChange={(e) => handleUpdateTableStatus(t.id, e.target.value)}
                        className="text-xs px-2.5 py-1 rounded-lg bg-black/40 border border-theme-border text-white focus:outline-none focus:border-theme-primary"
                      >
                        <option value="available">Bo'sh (AVAILABLE)</option>
                        <option value="occupied">Band (OCCUPIED)</option>
                        <option value="reserved">Bron (RESERVED)</option>
                      </select>
                    </div>

                    {/* View Bill & Checkout Button */}
                    <button
                      onClick={() => handleOpenBill(t)}
                      className="w-full py-2.5 rounded-xl bg-theme-primary/15 hover:bg-theme-primary/25 border border-theme-primary/30 text-theme-primary text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-sm"
                    >
                      <Receipt className="w-3.5 h-3.5" />
                      <span>Chek / Hisobni ko'rish</span>
                    </button>

                    {isOccupied && (
                      <button
                        onClick={() => handleClearTable(t.id, t.number)}
                        className="w-full py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Stolni bo'shatish (Tozalash)</span>
                      </button>
                    )}

                    <div className="grid grid-cols-2 gap-2 pt-1">
                      <button
                        onClick={() => setSelectedTableQR({ ...t, qrLink })}
                        className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-theme-border text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-all"
                      >
                        <QrCode className="w-3.5 h-3.5" />
                        <span>QR Kod</span>
                      </button>

                      <button
                        onClick={() => handleCopyLink(t.qr_token, t.id)}
                        className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-theme-border text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                      >
                        {copiedId === t.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Nusxalandi!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-theme-muted" />
                            <span>Havola</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 4: STAFF (ACCOUNTS) */}
      {tab === 'staff' && (
        <div className="space-y-6">
          {/* Add Staff Form */}
          <form
            onSubmit={handleCreateStaff}
            className="p-5 sm:p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/80 space-y-4 shadow-lg"
          >
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Plus className="w-4 h-4 text-theme-primary" />
              <span>Yangi Xodim Akkaunti (Ofitsiant / Oshpaz / Admin)</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <input
                type="text"
                placeholder="Login (username)"
                value={newStaffUsername}
                onChange={(e) => setNewStaffUsername(e.target.value)}
                className="px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                required
              />
              <input
                type="text"
                placeholder="To'liq ismi"
                value={newStaffFullName}
                onChange={(e) => setNewStaffFullName(e.target.value)}
                className="px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                required
              />
              <input
                type="password"
                placeholder="Parol"
                value={newStaffPassword}
                onChange={(e) => setNewStaffPassword(e.target.value)}
                className="px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                required
              />
              <select
                value={newStaffRole}
                onChange={(e) => setNewStaffRole(e.target.value)}
                className="px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-theme-primary"
              >
                <option value="waiter">Ofitsiant</option>
                <option value="chef">Oshpaz</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <button
              type="submit"
              className="py-2.5 px-6 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow"
            >
              Akkaunt yaratish
            </button>
          </form>

          {/* Staff List */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {staff.map((s) => (
              <div
                key={s.id}
                className={`p-5 rounded-3xl glass-card border transition-all flex flex-col justify-between gap-4 shadow-md ${
                  s.is_active ? 'border-theme-border bg-theme-surface/75' : 'border-red-500/30 bg-red-950/10 opacity-75'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-white">{s.full_name || s.username}</h4>
                    <div className="text-xs text-theme-muted font-mono">@{s.username}</div>
                    <span className="inline-block mt-2 text-[10px] uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-theme-primary/20 text-theme-primary">
                      {s.role === 'waiter' ? 'Ofitsiant' : s.role === 'chef' ? 'Oshpaz' : s.role}
                    </span>
                  </div>

                  <div className="text-right text-xs">
                    <span className={`w-2 h-2 rounded-full inline-block mr-1.5 ${s.is_active ? 'bg-emerald-400' : 'bg-red-400'}`} />
                    <span className="text-theme-muted font-medium">{s.is_active ? 'Faol' : 'Nofaol'}</span>
                  </div>
                </div>

                {/* Staff Actions: Toggle Active + Delete / Bo'shatish */}
                <div className="pt-3 border-t border-theme-border/60 flex items-center justify-between gap-2">
                  <button
                    onClick={() => handleToggleStaffActive(s.id, s.is_active)}
                    disabled={staffActionLoading === s.id}
                    className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      s.is_active
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20'
                        : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20'
                    }`}
                  >
                    <Power className="w-3.5 h-3.5" />
                    <span>{s.is_active ? 'Nofaol qilish' : 'Faollashtirish'}</span>
                  </button>

                  <button
                    onClick={() => handleDeleteStaff(s.id, s.full_name || s.username)}
                    disabled={staffActionLoading === s.id}
                    title="Xodimni bo'shatish (O'chirish)"
                    className="px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 hover:text-red-300 text-xs font-bold flex items-center gap-1.5 transition-all"
                  >
                    <UserMinus className="w-3.5 h-3.5" />
                    <span>Bo'shatish</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 5: SETTINGS & THEMES */}
      {tab === 'settings' && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/75 space-y-4 shadow-lg">
            <div>
              <h3 className="text-base font-bold text-white">
                🎨 Dizayn Temalari (Mijozlar uchun 2 ta tanlash)
              </h3>
              <p className="text-xs text-theme-muted mt-1">
                Admin 6 ta temadan istalgan 2 tasini belgilaydi. Mijoz QR menyuga kirganda o'sha 2 tadan xohlaganini tanlashi mumkin bo'ladi.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
              {allThemes.map((t) => {
                const isPicked = activeThemes.includes(t.slug);
                return (
                  <button
                    key={t.slug}
                    onClick={() => handleToggleThemeSelection(t.slug)}
                    className={`p-4 rounded-2xl border text-left flex items-center justify-between transition-all ${
                      isPicked
                        ? 'border-theme-primary bg-theme-primary/10 shadow-glow'
                        : 'border-theme-border/60 bg-black/20 hover:border-theme-primary/40'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-sm shadow-inner"
                        style={{ backgroundColor: t.bg, border: `2px solid ${t.primary}` }}
                      >
                        {t.icon}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-white">{t.name}</div>
                        <div className="text-[10px] text-theme-muted">Rang: {t.primary}</div>
                      </div>
                    </div>

                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                        isPicked
                          ? 'bg-theme-primary text-white font-bold'
                          : 'border border-theme-border text-transparent'
                      }`}
                    >
                      <Check className="w-3.5 h-3.5" />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: REVIEWS */}
      {tab === 'reviews' && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Mijozlarning Baholari va Fikrlari ({reviews.length})
          </h3>

          {reviews.length === 0 ? (
            <div className="p-12 text-center rounded-3xl glass-card border border-theme-border text-theme-muted">
              <Star className="w-12 h-12 mx-auto mb-3 opacity-30 text-amber-400" />
              <p className="text-base font-semibold">Hozircha baholar yo'q</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {reviews.map((r) => (
                <div
                  key={r.id}
                  className="p-5 rounded-2xl glass-card border border-theme-border bg-theme-surface/75 space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-white">
                      {r.customer_name || 'Mijoz'}
                    </span>
                    <span className="text-[10px] text-theme-muted">
                      {new Date(r.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs">
                    <div>
                      Taom: <span className="text-amber-400 font-bold">⭐ {r.food_rating}/5</span>
                    </div>
                    <div>
                      Ofitsiant: <span className="text-amber-400 font-bold">⭐ {r.service_rating}/5</span>
                    </div>
                  </div>

                  {r.comment && (
                    <p className="text-xs text-theme-muted italic bg-black/20 p-2.5 rounded-xl border border-theme-border/40">
                      "{r.comment}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── MODAL: CATEGORY CREATE / EDIT ───────────────────────────── */}
      {showCategoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-md rounded-3xl glass-card border border-theme-border bg-theme-surface p-6 sm:p-8 space-y-5 shadow-2xl">
            <button
              onClick={() => setShowCategoryModal(false)}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-theme-primary" />
              <span>{editingCategory ? 'Kategoriyani Tahrirlash' : 'Yangi Kategoriya Qo\'shish'}</span>
            </h3>

            <form onSubmit={handleSaveCategory} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Kategoriya Nomi (O'zbekcha): *
                </label>
                <input
                  type="text"
                  value={categoryName}
                  onChange={(e) => setCategoryName(e.target.value)}
                  placeholder="masalan: Asosiy taomlar"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Emoji / Ikonka:
                </label>
                <input
                  type="text"
                  value={categoryIcon}
                  onChange={(e) => setCategoryIcon(e.target.value)}
                  placeholder="masalan: 🍖 yoki 🥗 yoki 🥤"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Ruscha nomi (ixtiyoriy):
                  </label>
                  <input
                    type="text"
                    value={categoryNameRu}
                    onChange={(e) => setCategoryNameRu(e.target.value)}
                    placeholder="Основные блюда"
                    className="w-full px-3 py-2 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Inglizcha nomi (ixtiyoriy):
                  </label>
                  <input
                    type="text"
                    value={categoryNameEn}
                    onChange={(e) => setCategoryNameEn(e.target.value)}
                    placeholder="Main Dishes"
                    className="w-full px-3 py-2 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCategoryModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white text-xs font-semibold"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow"
                >
                  {editingCategory ? 'Saqlash' : 'Qo\'shish'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── MODAL: DISH CREATE / EDIT ───────────────────────────── */}
      {showDishModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in overflow-y-auto">
          <div className="relative w-full max-w-lg rounded-3xl glass-card border border-theme-border bg-theme-surface p-6 sm:p-8 space-y-5 shadow-2xl my-8">
            <button
              onClick={() => setShowDishModal(false)}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <UtensilsCrossed className="w-5 h-5 text-theme-primary" />
              <span>{editingDish ? 'Taomni Tahrirlash' : 'Yangi Taom Qo\'shish'}</span>
            </h3>

            <form onSubmit={handleSaveDish} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Taom Nomi: *
                  </label>
                  <input
                    type="text"
                    value={dishName}
                    onChange={(e) => setDishName(e.target.value)}
                    placeholder="masalan: Qozon Kabob"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Narxi (so'm): *
                  </label>
                  <input
                    type="number"
                    value={dishPrice}
                    onChange={(e) => setDishPrice(e.target.value)}
                    placeholder="masalan: 45000"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Kategoriya: *
                  </label>
                  <select
                    value={dishCategory}
                    onChange={(e) => setDishCategory(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-theme-primary"
                    required
                  >
                    <option value="">Tanlang</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.icon} {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Tayyorlanish vaqti (daqiqa):
                  </label>
                  <input
                    type="number"
                    value={dishPrepTime}
                    onChange={(e) => setDishPrepTime(e.target.value)}
                    placeholder="15"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Kaloriyasi (kcal):
                  </label>
                  <input
                    type="number"
                    value={dishCalories}
                    onChange={(e) => setDishCalories(e.target.value)}
                    placeholder="450"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Taom Haqida / Tarkibi:
                  </label>
                  <textarea
                    value={dishDescription}
                    onChange={(e) => setDishDescription(e.target.value)}
                    placeholder="Taom tarkibi va lazzati haqida qisqacha ma'lumot..."
                    rows={2}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />
                </div>

                {/* Image Section */}
                <div className="sm:col-span-2 space-y-2">
                  <label className="block text-xs font-semibold text-theme-muted">
                    Taom Rasmi (URL yoki Fayl yuklash):
                  </label>
                  
                  <input
                    type="text"
                    value={dishImageUrl}
                    onChange={(e) => setDishImageUrl(e.target.value)}
                    placeholder="Rasm havolasi (masalan: https://images.unsplash.com/...)"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />

                  <div className="flex items-center gap-3">
                    <label className="flex-1 cursor-pointer flex items-center justify-center gap-2 p-2.5 rounded-xl border border-dashed border-theme-border hover:border-theme-primary bg-black/20 text-xs text-theme-muted hover:text-white transition-all">
                      <Upload className="w-4 h-4 text-theme-primary" />
                      <span>{dishImageFile ? dishImageFile.name : "Kompyuterdan rasm yuklash"}</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => setDishImageFile(e.target.files[0] || null)}
                        className="hidden"
                      />
                    </label>

                    {(dishImageUrl || dishImageFile) && (
                      <div className="w-12 h-12 rounded-xl bg-black/40 border border-theme-border overflow-hidden shrink-0">
                        <img
                          src={dishImageFile ? URL.createObjectURL(dishImageFile) : dishImageUrl}
                          alt="Preview"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* Toggles */}
                <div className="sm:col-span-2 flex items-center justify-between gap-4 pt-1">
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-white">
                    <input
                      type="checkbox"
                      checked={dishIsAvailable}
                      onChange={(e) => setDishIsAvailable(e.target.checked)}
                      className="rounded accent-theme-primary w-4 h-4"
                    />
                    <span>Taom sotuvda mavjud (is_available)</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer text-xs text-white">
                    <input
                      type="checkbox"
                      checked={dishIsFeatured}
                      onChange={(e) => setDishIsFeatured(e.target.checked)}
                      className="rounded accent-theme-primary w-4 h-4"
                    />
                    <span>🔥 Tavsiya etiladi (is_featured)</span>
                  </label>
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-theme-border/60">
                <button
                  type="button"
                  onClick={() => setShowDishModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-theme-muted hover:text-white text-xs font-semibold"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={savingDish}
                  className="px-5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow disabled:opacity-50"
                >
                  {savingDish ? 'Saqlanmoqda...' : (editingDish ? 'Saqlash' : 'Qo\'shish')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── MODAL: QR CODE LARGE VIEW & PRINT ───────────────────────────── */}
      {selectedTableQR && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-sm rounded-3xl glass-card border border-theme-border bg-theme-surface p-6 sm:p-8 space-y-6 shadow-2xl text-center">
            <button
              onClick={() => setSelectedTableQR(null)}
              className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Printable Area */}
            <div id="printable-qr-badge" className="p-5 rounded-2xl bg-white text-black space-y-3 shadow-xl">
              <div className="flex items-center justify-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-black text-white flex items-center justify-center font-black text-sm">
                  🍽️
                </div>
                <div className="text-left">
                  <div className="text-xs font-black tracking-wider uppercase text-zinc-800">RestAron</div>
                  <div className="text-[10px] text-zinc-500 font-medium">Aqlli Restoran Tizimi</div>
                </div>
              </div>

              <div className="py-1">
                <span className="text-2xl font-black text-black">
                  Stol #{selectedTableQR.number}
                </span>
                {selectedTableQR.room && (
                  <div className="text-xs font-semibold text-zinc-600">
                    ({selectedTableQR.room})
                  </div>
                )}
              </div>

              <div className="flex justify-center p-2 bg-white rounded-xl border border-zinc-200">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(
                    selectedTableQR.qrLink || `${qrBaseUrl}/?table=${selectedTableQR.qr_token}`
                  )}`}
                  alt={`Stol #${selectedTableQR.number} QR`}
                  className="w-48 h-48 object-contain"
                />
              </div>

              <div className="text-[11px] font-bold text-zinc-800">
                📱 Kamerangizni yoqing va menyuni oching
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-2 pt-1">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => window.print()}
                  className="w-full py-3 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center justify-center gap-2 transition-all"
                >
                  <Printer className="w-4 h-4" />
                  <span>Chop etish</span>
                </button>

                <a
                  href={`https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=${encodeURIComponent(
                    selectedTableQR.qrLink || `${qrBaseUrl}/?table=${selectedTableQR.qr_token}`
                  )}`}
                  download={`Stol_${selectedTableQR.number}_QR.png`}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-bold border border-white/15 flex items-center justify-center gap-2 transition-all"
                >
                  <Download className="w-4 h-4" />
                  <span>PNG Yuklash</span>
                </a>
              </div>

              <a
                href={selectedTableQR.qrLink || `${qrBaseUrl}/?table=${selectedTableQR.qr_token}`}
                target="_blank"
                rel="noreferrer"
                className="w-full py-2.5 rounded-xl bg-black/30 hover:bg-black/50 text-theme-muted hover:text-white text-xs font-semibold flex items-center justify-center gap-2 transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Mijoz sifatida ochish</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Table Bill & Checkout Modal */}
      <BillModal
        isOpen={billModalOpen}
        onClose={() => setBillModalOpen(false)}
        tableId={selectedBillTable?.id}
        tableNumber={selectedBillTable?.number}
        isStaff={true}
        onTableCleared={loadAll}
      />
    </div>
  );
};

export default AdminDashboard;

