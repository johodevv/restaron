import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useWebSocket } from '../../context/WebSocketContext';
import BillModal from '../../components/BillModal';
import CheckoutModal from '../../components/CheckoutModal';
import ThermalReceiptModal from '../../components/ThermalReceiptModal';
import PrinterStatusBanner from '../../components/PrinterStatusBanner';
import TablesTab from './TablesTab';
import StaffDismissDialog from '../../components/StaffDismissDialog';
import { AdminPrimaryNavigation, AdminSectionNavigation } from '../../components/AdminNavigation';
import { resolveQrBaseUrl } from '../../utils/tableDirectory';
import { DebtsTab } from './DebtsTab';
import { ReceiptsArchiveTab } from './ReceiptsArchiveTab';
import { PaymentsReportTab } from './PaymentsReportTab';
import { WaiterKpiTab } from './WaiterKpiTab';
import { RestaurantSettingsTab } from './RestaurantSettingsTab';
const POSView = React.lazy(() => import('./POSView'));
import BookingModal from '../../components/BookingModal';
import {
  LayoutDashboard,
  ShoppingBag,
  Bike,
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
  CheckCircle2,
  AlertTriangle,
  FileImage,
  Receipt,
  UserMinus,
  BellRing,
  Power,
  ShieldCheck,
  Lock,
  Wallet,
  Archive,
  FileSpreadsheet,
  Trophy,
  Palette,
  ShoppingCart,
  CreditCard,
  MapPin,
  Calendar
} from 'lucide-react';

export const AdminDashboard = () => {
  const panelRef = useRef(null);
  const { user } = useAuth();
  const { activeThemes, setActiveThemes, allThemes } = useTheme();
  const { addEventListener, playChime } = useWebSocket();
  const [activePrintAlert, setActivePrintAlert] = useState(null);
  const [tab, setTab] = useState('pos'); // 'pos' | 'tables' | 'receipts' | 'staff' | 'debts' | 'overview' | ...
  useEffect(() => {
    panelRef.current?.closest('main')?.scrollTo({ top: 0 });
  }, [tab]);

  const restaurantId = user?.restaurant_id || 1;

  // State
  const [stats, setStats] = useState(null);
  const [categories, setCategories] = useState([]);
  const [tables, setTables] = useState([]);
  const [tablesError, setTablesError] = useState('');
  const [staff, setStaff] = useState([]);
  const [waiterCalls, setWaiterCalls] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [recentOrders, setRecentOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // Bill Modal state
  const [billModalOpen, setBillModalOpen] = useState(false);
  // Kassa: to'lovni admin panelda qabul qilamiz (kassada o'tirgan xodim shu yerda ishlaydi)
  const [checkoutOrder, setCheckoutOrder] = useState(null);
  const [checkoutTableLabel, setCheckoutTableLabel] = useState('');
  const [thermalOpen, setThermalOpen] = useState(false);
  const [thermalRawText, setThermalRawText] = useState('');
  const [thermalPrintDocument, setThermalPrintDocument] = useState(null);
  const [thermalTitle, setThermalTitle] = useState('Chek');
  const [selectedBillTable, setSelectedBillTable] = useState(null);
  const [staffActionLoading, setStaffActionLoading] = useState(null);
  const [staffView, setStaffView] = useState('active');
  const [staffNotice, setStaffNotice] = useState(null);
  const [staffToDismiss, setStaffToDismiss] = useState(null);
  const [staffDismissError, setStaffDismissError] = useState('');

  // Booking Modal state
  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [selectedBookingTable, setSelectedBookingTable] = useState(null);

  // Network & Host Settings for QR codes
  const [lanInfo, setLanInfo] = useState(null);
  const [qrBaseUrl, setQrBaseUrl] = useState(() =>
    resolveQrBaseUrl(localStorage.getItem('restaron_qr_base_url'), null, window.location.origin));

  // Staff creation state
  const [newStaffUsername, setNewStaffUsername] = useState('');
  const [newStaffFullName, setNewStaffFullName] = useState('');
  const [newStaffPassword, setNewStaffPassword] = useState('');
  const [newStaffRole, setNewStaffRole] = useState('waiter');

  // Zonalar (stol kategoriyalari): Zal, Terrassa, 2-qavat, VIP
  const [zones, setZones] = useState([]);
  // Category Modal States (Add & Edit)
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [categoryName, setCategoryName] = useState('');
  const [categoryIcon, setCategoryIcon] = useState('🍽️');
  const [categoryNameRu, setCategoryNameRu] = useState('');
  const [categoryNameEn, setCategoryNameEn] = useState('');
  const [categoryNameCyrillic, setCategoryNameCyrillic] = useState('');
  // Bosh sahifada ko'rsatilsinmi (yangi kategoriya uchun sukut: yo'q)
  const [categoryShowOnLanding, setCategoryShowOnLanding] = useState(false);

  // Dish Modal States (Add & Edit)
  const [showDishModal, setShowDishModal] = useState(false);
  const [editingDish, setEditingDish] = useState(null);
  const [dishName, setDishName] = useState('');
  const [dishNameCyrillic, setDishNameCyrillic] = useState('');
  const [dishPrice, setDishPrice] = useState('');
  const [dishCategory, setDishCategory] = useState('');
  const [dishKitchenStation, setDishKitchenStation] = useState('hot_kitchen');
  // Tortiladigan taom (baliq, go'sht): narx 1 kg uchun
  const [dishIsWeighted, setDishIsWeighted] = useState(false);
  const [dishUnit, setDishUnit] = useState('kg');
  const [dishDescription, setDishDescription] = useState('');
  const [dishDescriptionCyrillic, setDishDescriptionCyrillic] = useState('');
  const [dishPrepTime, setDishPrepTime] = useState(15);
  const [dishCalories, setDishCalories] = useState('');
  const [dishImageUrl, setDishImageUrl] = useState('');
  const [dishImageFile, setDishImageFile] = useState(null);
  const [dishIsFeatured, setDishIsFeatured] = useState(false);
  const [dishIsAvailable, setDishIsAvailable] = useState(true);
  const [savingDish, setSavingDish] = useState(false);

  const loadAll = async () => {
    try {
      const [statsData, menuData, tablesData, staffData, callsData, reviewsData, lanData, zonesData, ordersData] = await Promise.all([
        (user?.role === 'cashier' ? Promise.resolve(null) : api.get(`/stats/dashboard?restaurant_id=${restaurantId}`)).catch(() => null),
        api.get(`/menu/full/${restaurantId}`).catch(() => []),
        api.get(`/tables/?restaurant_id=${restaurantId}`).catch(error => { setTablesError(error.message); return null; }),
        (user?.role === 'cashier' ? Promise.resolve([]) : api.get(`/users/?restaurant_id=${restaurantId}`)).catch(() => []),
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).catch(() => []),
        (user?.role === 'cashier' ? Promise.resolve([]) : api.get(`/reviews/?restaurant_id=${restaurantId}`)).catch(() => []),
        (user?.role === 'cashier' ? Promise.resolve(null) : api.get('/stats/lan-info')).catch(() => null),
        api.get(`/tables/zones?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/orders/?restaurant_id=${restaurantId}&active_only=true&limit=300`).catch(() => []),
      ]);

      setStats(statsData);
      setCategories(menuData || []);
      if (tablesData !== null) { setTables(tablesData || []); setTablesError(''); }
      setZones(zonesData || []);
      setStaff(staffData || []);
      setWaiterCalls(callsData || []);
      setReviews(reviewsData || []);
      setRecentOrders(ordersData || []);

      if (lanData) {
        setLanInfo(lanData);
        const resolved = resolveQrBaseUrl(localStorage.getItem('restaron_qr_base_url'), lanData, window.location.origin);
        setQrBaseUrl(resolved);
        localStorage.setItem('restaron_qr_base_url', resolved);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const refreshTimerRef = useRef(null);

  // Faqat o'zgargan qismlarni (stollar, buyurtmalar, statistika) yengil va debounced yangilash
  const refreshOrdersAndTables = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const [tablesData, ordersData, statsData] = await Promise.all([
          api.get(`/tables/?restaurant_id=${restaurantId}`).catch(() => null),
          api.get(`/orders/?restaurant_id=${restaurantId}&active_only=true&limit=300`).catch(() => null),
          (user?.role === 'cashier' ? Promise.resolve(null) : api.get(`/stats/dashboard?restaurant_id=${restaurantId}`)).catch(() => null),
        ]);
        if (tablesData) setTables(tablesData);
        if (ordersData) setRecentOrders(ordersData);
        if (statsData) setStats(statsData);
      } catch (err) {
        console.error('Lightweight refresh error:', err);
      }
    }, 350);
  }, [restaurantId]);

  useEffect(() => {
    loadAll();

    const unsubscribe = addEventListener('*', (event) => {
      if (event.type === 'call_waiter' || event.type === 'call_completed') {
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).then((d) => setWaiterCalls(d || [])).catch(() => {});
      } else if (event.type === 'table_status_updated') {
        const nextStatus = event.new_status || event.status;
        setTables((prev) =>
          prev.map((t) =>
            t.id === event.table_id
              ? {
                  ...t,
                  status: nextStatus || t.status,
                  is_occupied: event.is_occupied !== undefined ? event.is_occupied : (nextStatus === 'occupied'),
                }
              : t
          )
        );
        refreshOrdersAndTables();
      } else if (
        event.type === 'new_order' ||
        event.type === 'table_cleared' ||
        event.type === 'table_guest_arrived' ||
        event.type === 'table_unlocked' ||
        event.type === 'order_delivered' ||
        event.type === 'order_ready' ||
        event.type === 'order_status_updated' ||
        event.type === 'bill_paid'
      ) {
        refreshOrdersAndTables();
      }
    });

    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      unsubscribe();
    };
  }, [restaurantId, addEventListener, refreshOrdersAndTables]);

  // Handle Table Unlock (Tasdiqlash)
  const handleUnlockTable = async (tableId) => {
    try {
      await api.post(`/tables/${tableId}/unlock`, {});
      await loadAll();
    } catch (err) {
      alert(err.message || 'Stolni tasdiqlashda xatolik yuz berdi');
    }
  };

  // A dismissed account remains in history and is shown in the inactive list.
  const handleDeleteStaff = (staffId) => {
    setStaffDismissError('');
    setStaffToDismiss(staff.find(person => person.id === staffId) || null);
  };
  const confirmDismissStaff = async () => {
    if (!staffToDismiss || staffActionLoading !== null) return;
    const target = staffToDismiss;
    setStaffActionLoading(target.id);
    setStaffDismissError('');
    try {
      await api.delete(`/users/${target.id}`);
      setStaff(previous => previous.map(person => person.id === target.id ? { ...person, is_active: false } : person));
      setStaffToDismiss(null);
      setStaffNotice({ type: 'success', message: `${target.full_name || target.username} bo‘shatildi. Tizimga kirishi yopildi; tarixi “Nofaol” bo‘limida saqlanadi.` });
    } catch (err) {
      setStaffDismissError(err.message || 'Xodimni bo‘shatib bo‘lmadi. Qayta urinib ko‘ring.');
    } finally { setStaffActionLoading(null); }
  };

  const handleToggleStaffActive = async (staffId, currentStatus) => {
    if (staffActionLoading !== null) return;
    setStaffActionLoading(staffId);
    try {
      const updated = await api.patch(`/users/${staffId}`, { is_active: !currentStatus });
      setStaff(previous => previous.map(person => person.id === staffId ? updated : person));
      setStaffNotice({ type: 'success', message: currentStatus ? 'Xodim nofaol qilindi.' : 'Xodim qayta faollashtirildi. Endi yangi login bilan kirishi mumkin.' });
    } catch (err) {
      setStaffNotice({ type: 'error', message: err.message || 'Holatni o‘zgartirib bo‘lmadi.' });
    } finally { setStaffActionLoading(null); }
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

  // Kassa: stolning ochiq buyurtmasini topib, to'lov oynasini ochadi
  const handleOpenCheckout = async (t) => {
    try {
      const orders = await api.get(`/orders/table/${t.id}/active`);
      const open = (orders || []).find((o) => !o.is_paid);
      if (!open) {
        alert(`Stol #${t.number} da to'lanmagan buyurtma yo'q.`);
        return;
      }
      setCheckoutTableLabel(`Stol #${t.number}`);
      setCheckoutOrder(open);
    } catch (err) {
      alert(err.message || 'Buyurtmani olishda xatolik');
    }
  };

  const handleOpenBill = (t) => {
    setSelectedBillTable(t);
    setBillModalOpen(true);
  };

  // Direct print bill to Printer 1 (Kassa / Mijoz cheki)
  const handleDirectPrintBill = async (tableId, tableNumber) => {
    try {
      const res = await api.post(`/tables/${tableId}/print-bill`);
      // Printerga yuborilmagan bo'lsa ham chek matnini ko'rsatamiz —
      // kassir uni brauzerdan chiqara oladi.
      if (res?.raw_text) {
        setThermalRawText(res.raw_text);
        setThermalPrintDocument(res.print_document || null);
        setThermalTitle(`Hisob Cheki — Stol #${tableNumber}`);
        setThermalOpen(true);
      }
      if (!res?.success) {
        alert(res?.message || `Printerga yuborib bo'lmadi. Chek ekranda ko'rsatildi.`);
      }
    } catch (err) {
      alert(`Chek chiqarishda xatolik: ` + (err.message || ''));
    }
  };

  // WebSocket: real-time buyurtmalar va oshxona printeriga yuborilgan cheklar monitoringi
  useEffect(() => {
    const unsub = addEventListener('*', (event) => {
      if (event.type === 'kitchen_ticket' || event.type === 'order_to_kitchen') {
        if (playChime) playChime('urgent');
        setActivePrintAlert({
          table: event.table_number || event.table_id || '—',
          waiter: event.waiter_name || 'Ofitsiant',
          tickets: event.tickets || [],
          raw_text: event.raw_text,
          print_document: event.print_document || null,
          time: new Date().toLocaleTimeString(),
        });
        loadAll();
      } else if (
        event.type === 'new_order' ||
        event.type === 'order_updated' ||
        event.type === 'table_status_updated' ||
        event.type === 'call_waiter'
      ) {
        loadAll();
      }
    });
    return () => unsub();
  }, [addEventListener, playChime]);

  const reloadTables = async () => {
    try {
      const [nextTables, nextZones] = await Promise.all([
        api.get(`/tables/?restaurant_id=${restaurantId}`),
        api.get(`/tables/zones?restaurant_id=${restaurantId}`),
      ]);
      setTables(nextTables || []);
      setZones(nextZones || []);
      setTablesError('');
    } catch (error) { setTablesError(error.message); throw error; }
  };

  // ─── CATEGORY MANAGEMENT ──────────────────────────────────────────
  const handleOpenAddCategory = () => {
    setEditingCategory(null);
    setCategoryName('');
    setCategoryIcon('🍽️');
    setCategoryNameRu('');
    setCategoryNameEn('');
    setCategoryNameCyrillic('');
    // Yangi kategoriya bosh sahifada ko'rinmaydi — admin o'zi yoqadi
    setCategoryShowOnLanding(false);
    setShowCategoryModal(true);
  };

  const handleOpenEditCategory = (cat) => {
    setEditingCategory(cat);
    setCategoryName(cat.name || '');
    setCategoryIcon(cat.icon || '🍽️');
    setCategoryNameRu(cat.name_ru || '');
    setCategoryNameEn(cat.name_en || '');
    setCategoryNameCyrillic(cat.name_cyrillic || '');
    setCategoryShowOnLanding(cat.show_on_landing === true);
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
          name_cyrillic: categoryNameCyrillic.trim() || undefined,
          show_on_landing: categoryShowOnLanding,
        });
      } else {
        // Create
        await api.post('/menu/categories', {
          restaurant_id: restaurantId,
          name: categoryName.trim(),
          icon: categoryIcon.trim() || '🍽️',
          name_ru: categoryNameRu.trim() || undefined,
          name_en: categoryNameEn.trim() || undefined,
          name_cyrillic: categoryNameCyrillic.trim() || undefined,
          show_on_landing: categoryShowOnLanding,
          sort_order: categories.length,
        });
      }
      setShowCategoryModal(false);
      loadAll();
    } catch (err) {
      alert(err.message || 'Kategoriyani saqlashda xatolik');
    }
  };

  // Bosh sahifada (choyxona menyusida) shu kategoriya ko'rsatiladimi
  const handleToggleLanding = async (cat) => {
    try {
      await api.patch(`/menu/categories/${cat.id}`, {
        show_on_landing: !(cat.show_on_landing !== false),
      });
      loadAll();
    } catch (err) {
      alert(err.message || 'Xatolik');
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
    setDishNameCyrillic('');
    setDishPrice('');
    setDishCategory(defaultCatId ? defaultCatId.toString() : (categories[0]?.id?.toString() || ''));
    setDishKitchenStation('hot_kitchen');
    setDishIsWeighted(false);
    setDishUnit('kg');
    setDishDescription('');
    setDishDescriptionCyrillic('');
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
    setDishNameCyrillic(dish.name_cyrillic || '');
    setDishPrice(dish.price ? dish.price.toString() : '');
    setDishCategory(dish.category_id ? dish.category_id.toString() : '');
    setDishKitchenStation(dish.kitchen_station || 'hot_kitchen');
    setDishIsWeighted(Boolean(dish.is_weighted));
    setDishUnit(dish.unit && dish.unit !== 'dona' ? dish.unit : 'kg');
    setDishDescription(dish.description || '');
    setDishDescriptionCyrillic(dish.description_cyrillic || '');
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
          name_cyrillic: dishNameCyrillic.trim() || undefined,
          price: parseFloat(dishPrice),
          category_id: parseInt(dishCategory),
          kitchen_station: dishKitchenStation,
          is_weighted: dishIsWeighted,
          unit: dishIsWeighted ? dishUnit : 'dona',
          description: dishDescription.trim() || undefined,
          description_cyrillic: dishDescriptionCyrillic.trim() || undefined,
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
          name_cyrillic: dishNameCyrillic.trim() || undefined,
          price: parseFloat(dishPrice),
          category_id: parseInt(dishCategory),
          kitchen_station: dishKitchenStation,
          is_weighted: dishIsWeighted,
          unit: dishIsWeighted ? dishUnit : 'dona',
          description: dishDescription.trim() || undefined,
          description_cyrillic: dishDescriptionCyrillic.trim() || undefined,
          prep_time_minutes: parseInt(dishPrepTime) || 15,
          calories: dishCalories ? parseInt(dishCalories) : undefined,
          image_url: dishImageUrl.trim() || undefined,
          is_featured: dishIsFeatured,
          is_available: dishIsAvailable,
        });
        savedDishId = created.id;
      }

      // Rasm tanlangan bo'lsa yuklaymiz.
      // MUHIM: ilgari bu yerda javob tekshirilmasdi — rasm yuklanmasa ham
      // oyna yopilib ketardi va admin "tahrirlash ishlamadi" deb o'ylardi.
      if (dishImageFile && savedDishId) {
        const formData = new FormData();
        formData.append('file', dishImageFile);
        const token = localStorage.getItem('restaron_token');
        const res = await fetch(
          `${import.meta.env.VITE_API_URL || '/api/v1'}/menu/items/${savedDishId}/image`,
          {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
          }
        );
        if (!res.ok) {
          let sabab = `Server ${res.status} qaytardi`;
          try {
            const data = await res.json();
            if (data?.detail) sabab = typeof data.detail === 'string' ? data.detail : sabab;
          } catch (_) {
            /* javob JSON emas — status kodining o'zi yetarli */
          }
          // Taom saqlandi, faqat rasm yuklanmadi — shuni aniq aytamiz.
          alert(
            `Taom saqlandi, lekin RASM yuklanmadi.\n\n${sabab}\n\n` +
            `Boshqa rasm tanlab, qaytadan saqlab ko'ring.`
          );
          setDishImageFile(null);
          loadAll();
          return;
        }
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
      await api.patch(`/menu/items/${dish.id}/toggle-stop-list`);
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
  const handleToggleThemeSelection = async (slug) => {
    const next = activeThemes.includes(slug)
      ? activeThemes.filter(value => value !== slug)
      : [...activeThemes.slice(0, 1), slug];
    if (!next.length) return;
    try { await api.patch(`/restaurants/${restaurantId}/settings`, { active_themes: next }); setActiveThemes(next); }
    catch (err) { alert(err.message); }
  };

  return (
    <div ref={panelRef} className={`admin-shell mx-auto px-2 sm:px-4 animate-fade-in ${tab === 'tables' ? 'tables-admin-shell ' : ''}${tab === 'pos' ? 'w-full min-h-full flex flex-col gap-1 py-1' : 'w-full py-2 pb-24 space-y-4'}`}>
      {/* Printer statusi (navbat to'lib qolsa yoki printer ishlamasa ogohlantirish) */}
      {tab !== 'pos' && <PrinterStatusBanner />}
      <AdminPrimaryNavigation tab={tab} onNavigate={setTab} role={user?.role} onRefresh={loadAll} />

      {/* Internet URL Status Banner — Faqat POS bo'lmagan sahifalarda chiqadi */}
      {tab !== 'pos' && tab !== 'tables' && lanInfo && (
        <details className="admin-connection-details"><summary>Ulanish manzili</summary>
        <div className={`p-3.5 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-semibold shadow-lg ${
          lanInfo.mode === 'internet'
            ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
            : 'bg-blue-500/10 border-blue-500/30 text-blue-300'
        }`}>
          <div className="flex items-center gap-2.5">
            <div className={`w-2 h-2 rounded-full animate-pulse ${lanInfo.mode === 'internet' ? 'bg-emerald-400' : 'bg-blue-400'}`} />
            {lanInfo.mode === 'internet' ? (
              <span>
                🌐 <strong>Internet (4G/Wi-Fi) rejimi aktiv</strong> — Har qanday joydan kirish mumkin
              </span>
            ) : (
              <span>
                📡 <strong>Lokal Wi-Fi rejimi</strong> — Faqat bir xil tarmoqda ishlaydi
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <code className="px-2.5 py-1 rounded-lg bg-black/40 font-mono text-white text-[11px] break-all">
              {lanInfo.public_url || lanInfo.local_url || qrBaseUrl}
            </code>
            <button
              onClick={() => {
                const urlToCopy = lanInfo.public_url || lanInfo.local_url || qrBaseUrl;
                navigator.clipboard.writeText(urlToCopy);
                alert('URL nusxalandi! Ofitsianlarga yuboring.');
              }}
              className={`px-3 py-1.5 rounded-xl font-bold whitespace-nowrap transition-all active:scale-95 ${
                lanInfo.mode === 'internet'
                  ? 'bg-emerald-500 hover:bg-emerald-400 text-black'
                  : 'bg-blue-500 hover:bg-blue-400 text-white'
              }`}
            >
              📋 Nusxalash
            </button>
            {lanInfo.mode !== 'internet' && (
              <span className="text-amber-400 text-[10px]">
                ⚠ Internet uchun RESTARON_ISHGA_TUSHIR.bat ni ishga tushiring
              </span>
            )}
          </div>
        </div>
        </details>
      )}


      {activePrintAlert && tab !== 'pos' && (
        <div className="p-4 rounded-3xl bg-gradient-to-r from-amber-500/20 via-orange-500/20 to-amber-500/20 border-2 border-amber-500/50 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500 text-slate-950 flex items-center justify-center font-black shrink-0 shadow-lg text-lg">
              🖨️
            </div>
            <div>
              <div className="text-sm font-extrabold text-white flex items-center gap-2">
                <span>Yangi buyurtma! Oshxona navbatiga qabul qilindi</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/40 text-amber-300">
                  {activePrintAlert.time}
                </span>
              </div>
              <div className="text-xs text-amber-200 mt-0.5">
                Stol: <strong>№ {activePrintAlert.table}</strong> • Ofitsiant: <strong>{activePrintAlert.waiter || 'Xodim'}</strong>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            {activePrintAlert.raw_text && (
              <button
                type="button"
                onClick={async () => {
                  try {
                    await api.post('/receipts/print-raw-usb', { text: activePrintAlert.raw_text, print_document: activePrintAlert.print_document, restaurant_id: restaurantId });
                    alert("✅ Chek printerga qayta yuborildi!");
                  } catch (e) {
                    alert("Xatolik: " + e.message);
                  }
                }}
                className="px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all shadow active:scale-95"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Qayta chop etish</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => setActivePrintAlert(null)}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <div className={`admin-work-area ${!['pos', 'tables'].includes(tab) ? 'with-sections' : ''}`}>
        <AdminSectionNavigation tab={tab} onNavigate={setTab} role={user?.role} />
        <section className="admin-page-content" aria-label="Tanlangan bo‘lim">
      {/* TAB 1: OVERVIEW */}
      {tab === 'overview' && (
        <div className="space-y-6">
          {/* Active Guest Verification Alerts (Ofitsiant/Admin tasdiqlashi kerak) */}
          {tables.filter(t => !t.is_unlocked && t.current_pin).length > 0 && (
            <div className="p-3 sm:p-5 rounded-2xl sm:rounded-3xl bg-amber-500/15 border-2 border-amber-500/50 shadow-xl shadow-amber-500/10 space-y-3 animate-fade-in w-full overflow-x-hidden">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-amber-300 font-bold text-xs sm:text-sm">
                  <Sparkles className="w-5 h-5 text-amber-400 animate-bounce-subtle shrink-0" />
                  <span>Yangi mehmonlar ({tables.filter(t => !t.is_unlocked && t.current_pin).length} ta stol tasdiqlashni kutmoqda!)</span>
                </div>
                <span className="text-[10px] sm:text-[11px] uppercase font-extrabold px-2.5 py-1 rounded-full bg-amber-500 text-black w-fit">
                  Stolga borish lozim
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
                {tables.filter(t => !t.is_unlocked && t.current_pin).map((t) => (
                  <div
                    key={t.id}
                    className="p-3.5 sm:p-4 rounded-2xl bg-black/40 border border-amber-500/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shadow-md"
                  >
                    <div>
                      <div className="font-extrabold text-white text-sm">
                        Stol #{t.number} {t.room ? `(${t.room})` : ''}
                      </div>
                      <div className="text-amber-300 font-mono font-black text-base mt-0.5">
                        Kodi: {t.current_pin}
                      </div>
                    </div>
                    <button
                      onClick={() => handleUnlockTable(t.id)}
                      className="w-full sm:w-auto min-h-[44px] px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold text-xs sm:text-sm shadow-md active:scale-95 transition-all flex items-center justify-center gap-1.5 shrink-0"
                    >
                      <CheckCircle2 className="w-4 h-4 shrink-0" />
                      <span>✅ Tasdiqlash</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

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
                {staff.filter(person => person.is_active).length} nafar
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
      {/* ─── Zakas olish: ofitsiant paneli admin uchun ────────────
          Butun POS shu yerga qo'yiladi — admin stolni tanlab, taom
          qo'shib, oshxonaga yuboradi. Kod takrorlanmaydi: ayni bir
          komponent ishlatiladi, shuning uchun ofitsiant panelidagi
          barcha imkoniyatlar (zonalar, baliq narxi, begunok) bir xil
          ishlaydi. */}
      {tab === 'pos' && (
        <div className="admin-pos-workspace w-full shrink-0 overflow-hidden">
          <React.Suspense fallback={<div className="p-12 text-center text-theme-muted"><div className="w-8 h-8 border-3 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />POS yuklanmoqda...</div>}>
            <POSView showModeSwitch={true} canCheckout={true} restaurantId={restaurantId} />
          </React.Suspense>
        </div>
      )}


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
                        onClick={() => handleToggleLanding(cat)}
                        title={
                          cat.show_on_landing !== false
                            ? "Bosh sahifada KO'RINADI — yashirish uchun bosing"
                            : 'Bosh sahifada yashirilgan — ko\'rsatish uchun bosing'
                        }
                        className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold border transition-all flex items-center gap-1 ${
                          cat.show_on_landing !== false
                            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25'
                            : 'bg-zinc-700/30 border-zinc-600/50 text-zinc-400 hover:bg-zinc-700/50'
                        }`}
                      >
                        <span>{cat.show_on_landing !== false ? '👁' : '🚫'}</span>
                        <span className="hidden sm:inline">
                          {cat.show_on_landing !== false
                            ? 'Bosh menyuda'
                            : "Bosh menyuda yo'q"}
                        </span>
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
                                    loading="lazy"
                                    decoding="async"
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

                                  {/* Printer Station badge & quick switcher */}
                                  <div className="mt-1.5 flex items-center gap-1">
                                    <select
                                      value={item.kitchen_station || 'hot_kitchen'}
                                      onChange={async (e) => {
                                        const newStation = e.target.value;
                                        try {
                                          await api.patch(`/menu/items/${item.id}`, { kitchen_station: newStation });
                                          loadAll();
                                        } catch (err) {
                                          alert(err.message || 'Xatolik');
                                        }
                                      }}
                                      className={`text-[10px] font-bold px-2 py-0.5 rounded-lg border cursor-pointer outline-none transition-all ${
                                        item.kitchen_station === 'cold_kitchen'
                                          ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/30'
                                          : item.kitchen_station === 'customer_only'
                                          ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 hover:bg-purple-500/30'
                                          : item.kitchen_station === 'all_kitchens'
                                          ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 hover:bg-indigo-500/30'
                                          : 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                                      }`}
                                      title="Printerni o'zgartirish"
                                    >
                                      <option value="hot_kitchen" className="bg-slate-900 text-white">🫕 1-Oshxona (Qozon)</option>
                                      <option value="cold_kitchen" className="bg-slate-900 text-white">🐟 2-Oshxona (Baliq/Somsa)</option>
                                      <option value="bar" className="bg-slate-900 text-white">🥤 Bar (Ichimliklar)</option>
                                      <option value="customer_only" className="bg-slate-900 text-white">🧾 Kassa (USB printer)</option>
                                      <option value="all_kitchens" className="bg-slate-900 text-white">📢 Har 2 Oshxona</option>
                                    </select>
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
                                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all flex items-center gap-1 ${
                                  !item.is_stop_list && item.is_available
                                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25'
                                    : 'bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 shadow-sm'
                                }`}
                                title="1 bosishda Stop-Listga kiritish yoki chiqarish"
                              >
                                <span>{!item.is_stop_list && item.is_available ? '✅ Mavjud' : '⛔ Stop-List (Tugagan)'}</span>
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

      {/* Compact table directory: fetch accounts only when a table is opened. */}
      {tab === 'tables' && <TablesTab
        tables={tables} zones={zones} restaurantId={restaurantId}
        loading={loading} error={tablesError}
        qrBaseUrl={qrBaseUrl} lanInfo={lanInfo} ordersRevision={recentOrders}
        onQrBaseUrlChange={value => { localStorage.setItem('restaron_qr_base_url', value); setQrBaseUrl(value); }}
        onRefresh={reloadTables} onCheckout={handleOpenCheckout}
        onPrintBill={handleDirectPrintBill}
        onBook={table => { setSelectedBookingTable(table); setBookingModalOpen(true); }}
      />}

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

          <div className="space-y-3">
            <div role="group" aria-label="Xodimlar holati" className="flex flex-wrap gap-2">
              {[['active', 'Faol', staff.filter(person => person.is_active).length], ['inactive', 'Nofaol', staff.filter(person => !person.is_active).length]].map(([value, name, count]) => <button type="button" key={value} aria-pressed={staffView === value} onClick={() => setStaffView(value)} className={`min-h-[48px] px-5 rounded-xl font-bold border ${staffView === value ? 'bg-emerald-700 border-emerald-400 text-white' : 'bg-slate-800 border-slate-600 text-slate-200'}`}>{name} ({count})</button>)}
            </div>
            <p className="text-sm text-theme-muted">{staffView === 'active' ? 'Ishlayotgan xodimlar. O‘z hisobingizni bo‘shatib bo‘lmaydi.' : 'Nofaol va bo‘shatilgan xodimlar. Buyurtmalar tarixi saqlangan.'}</p>
            {staffNotice && <p role={staffNotice.type === 'error' ? 'alert' : 'status'} className={`rounded-xl border px-4 py-3 text-sm ${staffNotice.type === 'error' ? 'bg-red-950/40 border-red-700 text-red-200' : 'bg-emerald-950/40 border-emerald-700 text-emerald-200'}`}>{staffNotice.message}</p>}
          </div>
          {/* Staff List */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {staff.filter(person => staffView === 'active' ? person.is_active : !person.is_active).map((s) => (
              <div
                key={s.id}
                data-testid={`staff-card-${s.id}`}
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

                <div className="pt-3 border-t border-theme-border/60 flex items-center gap-2">
                  {s.id === user?.id ? <span className="text-sm text-theme-muted">Bu sizning hisobingiz</span> : s.is_active ? <button type="button" onClick={() => handleDeleteStaff(s.id)} disabled={staffActionLoading !== null} className="min-h-[48px] px-4 rounded-xl bg-red-500/10 border border-red-500/40 text-red-300 font-bold text-sm flex items-center gap-2 disabled:opacity-50"><UserMinus size={18} />Bo‘shatish</button> : <button type="button" onClick={() => handleToggleStaffActive(s.id, false)} disabled={staffActionLoading !== null} className="min-h-[48px] px-4 rounded-xl bg-emerald-500/10 border border-emerald-500/40 text-emerald-300 font-bold text-sm flex items-center gap-2 disabled:opacity-50"><Power size={18} />Qayta faollashtirish</button>}
                </div>
              </div>
            ))}
          </div>
          {!staff.some(person => staffView === 'active' ? person.is_active : !person.is_active) && <p className="py-8 text-center text-theme-muted">Bu bo‘limda xodim yo‘q.</p>}
        </div>
      )}

      {/* TAB: THEMES (old 'settings' renamed to 'themes') */}
      {tab === 'themes' && (
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

      {/* TAB: RESTAURANT SETTINGS (Kassa, Xprinter, SMS, Telegram) */}
      {tab === 'settings' && (
        <RestaurantSettingsTab restaurantId={restaurantId} />
      )}

      {/* TAB: DEBTS / NASIYA DAFTARI */}
      {tab === 'debts' && (
        <DebtsTab restaurantId={restaurantId} />
      )}

      {/* TAB: RECEIPTS ARCHIVE */}
      {tab === 'receipts' && (
        <ReceiptsArchiveTab restaurantId={restaurantId} />
      )}

      {/* TAB: PAYMENTS REPORT (Отчет по оплатам) */}
      {tab === 'payments' && (
        <PaymentsReportTab restaurantId={restaurantId} />
      )}

      {/* TAB: WAITER KPI */}
      {tab === 'waiter_kpi' && (
        <WaiterKpiTab restaurantId={restaurantId} />
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

        </section>
      </div>

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

              <div>
                <label className="block text-xs font-semibold text-theme-muted mb-1">
                  Ўзбекча (Кирилл алифбосида):
                </label>
                <input
                  type="text"
                  value={categoryNameCyrillic}
                  onChange={(e) => setCategoryNameCyrillic(e.target.value)}
                  placeholder="masalan: Иссиқ таомлар"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                />
              </div>

              {/* Bosh sahifada ko'rsatish — sukut bo'yicha YO'Q */}
              <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={categoryShowOnLanding}
                    onChange={(e) => setCategoryShowOnLanding(e.target.checked)}
                    className="mt-0.5 w-4 h-4 accent-emerald-500 shrink-0"
                  />
                  <span>
                    <span className="block text-xs font-bold text-emerald-300">
                      👁 Bosh sahifada ko'rsatilsin
                    </span>
                    <span className="block text-[10px] text-theme-muted mt-0.5">
                      Belgilanmasa, bu kategoriya saytning bosh sahifasidagi
                      menyuda chiqmaydi. Ichki kategoriyalar (masalan sigaret)
                      uchun belgilamang. QR orqali ochilgan mijoz menyusida
                      esa barcha kategoriyalar ko'rinaveradi.
                    </span>
                  </span>
                </label>
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

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    Taom Nomi (Ўзбекча Кирилл алифбосида):
                  </label>
                  <input
                    type="text"
                    value={dishNameCyrillic}
                    onChange={(e) => setDishNameCyrillic(e.target.value)}
                    placeholder="masalan: Қозон Кабоб (bo'sh qolsa avtomatik o'giriladi)"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
                  />
                </div>

                <div className="sm:col-span-2 p-3 rounded-2xl bg-amber-500/10 border border-amber-500/30">
                  <label className="block text-xs font-bold text-amber-300 mb-1">
                    🖨️ Oshxona Stansiyasi (Qaysi printerdan chiqadi): *
                  </label>
                  <select
                    value={dishKitchenStation}
                    onChange={(e) => setDishKitchenStation(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-amber-500/40 text-xs text-white focus:outline-none focus:border-amber-400 font-bold"
                    required
                  >
                    <option value="hot_kitchen">🍲 1-Oshxona (Qozon taomlari - osh, sho'rva, qozon kabob...)</option>
                    <option value="cold_kitchen">🐟 2-Oshxona (Baliq, Somsa, mangal, shashlik...)</option>
                    <option value="bar">🥤 Bar (Ichimliklar / Choyxona) [4-Printer]</option>
                    <option value="customer_only">🧾 Kassa (Kassadagi USB printer — suv, non, desert)</option>
                    <option value="all_kitchens">📢 Har ikkala oshxona</option>
                  </select>
                  <span className="text-[10px] text-theme-muted mt-1 block">
                    Ofitsiant buyurtmani oshxonaga yuborganida faqat o'z stansiyasidagi printerdan begunok chiqadi.
                  </span>
                </div>

                {/* Tortiladigan taom: baliq, go'sht, tovuq */}
                <div className="sm:col-span-2 p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={dishIsWeighted}
                      onChange={(e) => setDishIsWeighted(e.target.checked)}
                      className="mt-0.5 w-4 h-4 accent-cyan-500 shrink-0"
                    />
                    <span>
                      <span className="block text-xs font-bold text-cyan-300">
                        ⚖️ Tortiladigan taom (baliq, go'sht, tovuq)
                      </span>
                      <span className="block text-[10px] text-theme-muted mt-0.5">
                        Belgilansa, narx 1 kg uchun bo'ladi. Ofitsiant aniq og'irlikni
                        kiritmaguncha chek chiqmaydi — shunda mijoz chekda nechchi kg
                        olganini va aynan shuning pulini ko'radi.
                      </span>
                    </span>
                  </label>

                  {dishIsWeighted && (
                    <div className="mt-2.5 pl-6.5">
                      <label className="block text-[10px] font-bold text-cyan-300 mb-1">
                        O'lchov birligi:
                      </label>
                      <select
                        value={dishUnit}
                        onChange={(e) => setDishUnit(e.target.value)}
                        className="w-full sm:w-48 px-3 py-2 rounded-xl bg-slate-900 border border-cyan-500/40 text-xs text-white font-bold focus:outline-none focus:border-cyan-400"
                      >
                        <option value="kg">kg — kilogramm (baliq, go'sht)</option>
                        <option value="l">l — litr (quyma ichimlik)</option>
                        <option value="g">g — gramm</option>
                      </select>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-theme-muted mb-1">
                    {dishIsWeighted ? `Narxi — 1 ${dishUnit} uchun (so'm): *` : "Narxi (so'm): *"}
                  </label>
                  <input
                    type="number"
                    value={dishPrice}
                    onChange={(e) => setDishPrice(e.target.value)}
                    placeholder={dishIsWeighted ? `1 ${dishUnit} narxi, masalan: 120000` : 'masalan: 45000'}
                    className={`w-full px-3.5 py-2.5 rounded-xl bg-black/30 border text-xs text-white placeholder-zinc-500 focus:outline-none ${
                      dishIsWeighted
                        ? 'border-cyan-500/40 focus:border-cyan-400'
                        : 'border-theme-border focus:border-theme-primary'
                    }`}
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

                {/* Printer / Oshxona stansiyasi sozlamasi */}
                <div className="sm:col-span-2 p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-1.5">
                  <label className="block text-xs font-bold text-amber-300">
                    🖨️ Qaysi printerdan chiqsin? (Oshxona stansiyasi):
                  </label>
                  <select
                    value={dishKitchenStation}
                    onChange={(e) => setDishKitchenStation(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-amber-500/40 text-xs text-white font-bold focus:outline-none focus:border-amber-400 cursor-pointer"
                  >
                    <option value="hot_kitchen">🫕 1-Oshxona (Qozon taomlari — Osh, Sho'rva, Lag'mon, Qozon kabob...) [2-Printer]</option>
                    <option value="cold_kitchen">🐟 2-Oshxona (Baliq, Somsa, Shashlik, Mangal, Salatlar...) [3-Printer]</option>
                    <option value="bar">🥤 Bar (Ichimliklar, choy) [4-Printer]</option>
                    <option value="customer_only">🧾 Kassa (Kassadagi USB printer — suv, non, desert)</option>
                    <option value="all_kitchens">📢 Barcha oshxonalarga (1- va 2-oshxona ikkalasidan ham chiqarilsin)</option>
                  </select>
                  <p className="text-[10px] text-theme-muted">
                    Ofitsiant zakaz olib "Buyurtmani tasdiqlash"ni bosganda, ushbu taom avtomatik ravishda tanlangan printerdan chop etiladi.
                  </p>
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

      <ThermalReceiptModal
        isOpen={thermalOpen}
        onClose={() => setThermalOpen(false)}
        title={thermalTitle}
        rawText={thermalRawText}
        printDocument={thermalPrintDocument}
        restaurantId={restaurantId}
        paperWidth={80}
      />

      {/* Kassa oynasi — to'lov turi, naqd qaytimi, nasiya */}
      <CheckoutModal
        isOpen={!!checkoutOrder}
        onClose={() => setCheckoutOrder(null)}
        order={checkoutOrder}
        tableLabel={checkoutTableLabel}
        onPaid={(res) => {
          setCheckoutOrder(null);
          if (res?.raw_text) {
            setThermalRawText(res.raw_text);
            setThermalPrintDocument(res.print_document || null);
            setThermalTitle(`Hisob Cheki — ${checkoutTableLabel}`);
            setThermalOpen(true);
          }
          loadAll();
        }}
      />

      {/* Table Bill & Checkout Modal */}
      <BillModal
        isOpen={billModalOpen}
        onClose={() => setBillModalOpen(false)}
        tableId={selectedBillTable?.id}
        tableNumber={selectedBillTable?.number}
        isStaff={true}
        onTableCleared={loadAll}
      />

      {/* Booking / Reservation Modal */}
      <BookingModal
        appearance={tab === 'tables' ? 'tables' : 'default'}
        isOpen={bookingModalOpen}
        onClose={() => setBookingModalOpen(false)}
        table={selectedBookingTable}
        tables={tables}
        onBookingConfirmed={() => {
          setBookingModalOpen(false);
          loadAll();
        }}
      />
      <StaffDismissDialog staff={staffToDismiss} busy={staffActionLoading !== null} error={staffDismissError} onClose={() => { if (staffActionLoading === null) setStaffToDismiss(null); }} onConfirm={confirmDismissStaff} />
    </div>
  );
};

export default AdminDashboard;

