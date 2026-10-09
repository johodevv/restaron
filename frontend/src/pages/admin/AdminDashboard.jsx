import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { useWebSocket } from '../../context/WebSocketContext';
import BillModal from '../../components/BillModal';
import CheckoutModal from '../../components/CheckoutModal';
import ThermalReceiptModal from '../../components/ThermalReceiptModal';
import { DebtsTab } from './DebtsTab';
import { ReceiptsArchiveTab } from './ReceiptsArchiveTab';
import { PaymentsReportTab } from './PaymentsReportTab';
import { WaiterKpiTab } from './WaiterKpiTab';
import { RestaurantSettingsTab } from './RestaurantSettingsTab';
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
  CreditCard,
  MapPin
} from 'lucide-react';

export const AdminDashboard = () => {
  const { user } = useAuth();
  const { activeThemes, setActiveThemes, allThemes } = useTheme();
  const { addEventListener, playChime } = useWebSocket();
  const [activePrintAlert, setActivePrintAlert] = useState(null);
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
  // Kassa: to'lovni admin panelda qabul qilamiz (kassada o'tirgan xodim shu yerda ishlaydi)
  const [checkoutOrder, setCheckoutOrder] = useState(null);
  const [checkoutTableLabel, setCheckoutTableLabel] = useState('');
  const [thermalOpen, setThermalOpen] = useState(false);
  const [thermalRawText, setThermalRawText] = useState('');
  const [thermalTitle, setThermalTitle] = useState('Chek');
  const [selectedBillTable, setSelectedBillTable] = useState(null);
  const [staffActionLoading, setStaffActionLoading] = useState(null);

  // Network & Host Settings for QR codes
  const [lanInfo, setLanInfo] = useState(null);
  const [qrBaseUrl, setQrBaseUrl] = useState(() => {
    const saved = localStorage.getItem('restaron_qr_base_url');
    if (saved && !saved.includes('localhost') && !saved.includes('192.168.')) {
      return saved;
    }
    return window.location.origin;
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

  // Zonalar (stol kategoriyalari): Zal, Terrassa, 2-qavat, VIP
  const [zones, setZones] = useState([]);
  // Stollar bo'limi filtrlari: zona va holat (bo'sh / band)
  const [tableZoneFilter, setTableZoneFilter] = useState('');     // '' = hammasi
  const [tableStatusFilter, setTableStatusFilter] = useState(''); // '' | available | occupied | reserved
  const [newZoneName, setNewZoneName] = useState('');
  const [zoneBusy, setZoneBusy] = useState(false);
  const [editingZoneId, setEditingZoneId] = useState(null);
  const [editingZoneName, setEditingZoneName] = useState('');

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
      const [statsData, menuData, tablesData, staffData, callsData, reviewsData, lanData, zonesData] = await Promise.all([
        api.get(`/stats/dashboard?restaurant_id=${restaurantId}`).catch(() => null),
        api.get(`/menu/full/${restaurantId}`).catch(() => []),
        api.get(`/tables/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/users/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/reviews/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get('/stats/lan-info').catch(() => null),
        api.get(`/tables/zones?restaurant_id=${restaurantId}`).catch(() => []),
      ]);

      setStats(statsData);
      setCategories(menuData || []);
      setTables(tablesData || []);
      setZones(zonesData || []);
      setStaff(staffData || []);
      setWaiterCalls(callsData || []);
      setReviews(reviewsData || []);

      if (lanData) {
        setLanInfo(lanData);
        // If Cloudflare tunnel is active, always use the public URL for QR codes
        if (lanData.public_url && lanData.mode === 'internet') {
          setQrBaseUrl(lanData.public_url);
          localStorage.setItem('restaron_qr_base_url', lanData.public_url);
        } else {
          const savedUrl = localStorage.getItem('restaron_qr_base_url');
          if (!savedUrl && lanData.suggested_frontend_url) {
            setQrBaseUrl(lanData.suggested_frontend_url);
            localStorage.setItem('restaron_qr_base_url', lanData.suggested_frontend_url);
          }
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
        event.type === 'table_guest_arrived' ||
        event.type === 'table_unlocked' ||
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

  // Handle Table Unlock (Tasdiqlash)
  const handleUnlockTable = async (tableId) => {
    try {
      await api.post(`/tables/${tableId}/unlock`, {});
      await loadAll();
    } catch (err) {
      alert(err.message || 'Stolni tasdiqlashda xatolik yuz berdi');
    }
  };

  // Handle Table Lock (Qayta qulflash / Yangi PIN)
  const handleLockTable = async (tableId) => {
    try {
      await api.post(`/tables/${tableId}/lock`, {});
      await loadAll();
    } catch (err) {
      alert(err.message || 'Stolni qulflashda xatolik yuz berdi');
    }
  };


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

  // ─── TABLES MANAGEMENT ──────────────────────────────────────────
  // ─── Zonalar (stol kategoriyalari) ───────────────────────────
  const reloadZones = async () => {
    try {
      setZones(await api.get(`/tables/zones?restaurant_id=${restaurantId}`));
    } catch (err) {
      console.error('Zonalarni yuklashda xatolik:', err);
    }
  };

  const handleCreateZone = async (e) => {
    e.preventDefault();
    const name = newZoneName.trim();
    if (!name) return;
    setZoneBusy(true);
    try {
      await api.post('/tables/zones', { restaurant_id: restaurantId, name });
      setNewZoneName('');
      await reloadZones();
    } catch (err) {
      alert(err.message || "Zona qo'shishda xatolik");
    } finally {
      setZoneBusy(false);
    }
  };

  const handleRenameZone = async (zoneId) => {
    const name = editingZoneName.trim();
    if (!name) return;
    setZoneBusy(true);
    try {
      await api.patch(`/tables/zones/${zoneId}`, { name });
      setEditingZoneId(null);
      setEditingZoneName('');
      // Stollarning zona nomi ham o'zgargani uchun hammasini qayta yuklaymiz
      await loadAll();
    } catch (err) {
      alert(err.message || 'Zona nomini o\'zgartirishda xatolik');
    } finally {
      setZoneBusy(false);
    }
  };

  const handleDeleteZone = async (zone) => {
    if (!window.confirm(`"${zone.name}" zonasini o'chirasizmi?`)) return;
    setZoneBusy(true);
    try {
      await api.delete(`/tables/zones/${zone.id}`);
      await reloadZones();
    } catch (err) {
      alert(err.message || "Zonani o'chirishda xatolik");
    } finally {
      setZoneBusy(false);
    }
  };

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

  // ─── Stollar: zona va holat bo'yicha filtr ──────────────────────
  // "Terrassa" ni bossangiz faqat terrassadagi stollar chiqadi,
  // "Band" ni bossangiz faqat band stollar.
  const tableStatusOf = (t) => (t.status || '').toLowerCase();

  const zoneNameOf = (t) => (t.room || '').trim();

  // Zona ro'yxati: sozlamadagi zonalar + stollarda uchraydigan zonalar
  const tableZoneOptions = (() => {
    const names = zones.map((z) => z.name);
    tables.forEach((t) => {
      const z = zoneNameOf(t);
      if (z && !names.includes(z)) names.push(z);
    });
    const opts = names.map((n) => ({
      value: n,
      label: n,
      count: tables.filter((t) => zoneNameOf(t) === n).length,
    }));
    const noZone = tables.filter((t) => !zoneNameOf(t)).length;
    if (noZone > 0) {
      opts.push({ value: '__nozone__', label: 'Zonasiz', count: noZone });
    }
    return opts.filter((o) => o.count > 0);
  })();

  const zoneMatches = (t) =>
    !tableZoneFilter ||
    (tableZoneFilter === '__nozone__' ? !zoneNameOf(t) : zoneNameOf(t) === tableZoneFilter);

  const statusMatches = (t) =>
    !tableStatusFilter || tableStatusOf(t) === tableStatusFilter;

  const filteredTables = tables.filter((t) => zoneMatches(t) && statusMatches(t));

  // Tanlangan holat bo'yicha sanoqlar (zona filtri hisobga olinadi)
  const statusCounts = (() => {
    const inZone = tables.filter(zoneMatches);
    return {
      all: inZone.length,
      available: inZone.filter((t) => tableStatusOf(t) === 'available').length,
      occupied: inZone.filter((t) => tableStatusOf(t) === 'occupied').length,
      reserved: inZone.filter((t) => tableStatusOf(t) === 'reserved').length,
    };
  })();

  // Stollarni zonalar bo'yicha guruhlash. Zonalar ro'yxatidagi tartib
  // saqlanadi; zonasiz stollar oxirida alohida guruhda chiqadi.
  const tableGroups = (() => {
    const groups = [];
    const used = new Set();
    for (const z of zones) {
      const items = filteredTables.filter((t) => zoneNameOf(t) === z.name);
      items.forEach((t) => used.add(t.id));
      groups.push({ key: `z${z.id}`, name: z.name, items });
    }
    const rest = filteredTables.filter((t) => !used.has(t.id));
    if (rest.length > 0) {
      groups.push({ key: 'nozone', name: 'Zonasiz stollar', items: rest });
    }
    return groups.filter((g) => g.items.length > 0);
  })();

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

      {/* Internet URL Status Banner */}
      {lanInfo && (
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
      )}


      {activePrintAlert && (
        <div className="p-4 rounded-3xl bg-gradient-to-r from-amber-500/20 via-orange-500/20 to-amber-500/20 border-2 border-amber-500/50 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500 text-slate-950 flex items-center justify-center font-black shrink-0 shadow-lg text-lg">
              🖨️
            </div>
            <div>
              <div className="text-sm font-extrabold text-white flex items-center gap-2">
                <span>Yangi buyurtma! Oshxona printerlariga chiqarildi</span>
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
                    await api.post('/receipts/print-raw-usb', { text: activePrintAlert.raw_text });
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

      {/* Tabs — Full Navigation Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none no-scrollbar">
        {[
          { key: 'overview', label: 'Xulosa', icon: LayoutDashboard },
          { key: 'menu', label: 'Menyu & Taomlar', icon: UtensilsCrossed },
          { key: 'tables', label: 'Stollar & QR', icon: TableIcon },
          { key: 'staff', label: 'Xodimlar', icon: Users },
          { key: 'debts', label: 'Qarzlar (Nasiya)', icon: Wallet },
          { key: 'receipts', label: 'Cheklar Arxivi', icon: Archive },
          { key: 'payments', label: 'Kassa Hisoboti', icon: FileSpreadsheet },
          { key: 'waiter_kpi', label: 'Ofitsiantlar KPI', icon: Trophy },
          { key: 'themes', label: 'Dizayn & Temalar', icon: Palette },
          { key: 'settings', label: 'Sozlamalar', icon: Settings },
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
          {/* Active Guest Verification Alerts (Ofitsiant/Admin tasdiqlashi kerak) */}
          {tables.filter(t => !t.is_unlocked && t.current_pin).length > 0 && (
            <div className="p-5 rounded-3xl bg-amber-500/15 border-2 border-amber-500/50 shadow-xl shadow-amber-500/10 space-y-3 animate-fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                  <Sparkles className="w-5 h-5 text-amber-400 animate-bounce-subtle" />
                  <span>Yangi mehmonlar ({tables.filter(t => !t.is_unlocked && t.current_pin).length} ta stol tasdiqlashni kutmoqda!)</span>
                </div>
                <span className="text-[11px] uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-amber-500 text-black">
                  Stolga borish lozim
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
                {tables.filter(t => !t.is_unlocked && t.current_pin).map((t) => (
                  <div
                    key={t.id}
                    className="p-4 rounded-2xl bg-black/40 border border-amber-500/40 flex items-center justify-between gap-3 text-xs shadow-md"
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
                      className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold text-xs shadow-md active:scale-95 transition-all flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Tasdiqlash</span>
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

                {lanInfo?.public_url && qrBaseUrl !== lanInfo.public_url && (
                  <button
                    onClick={() => handleResetToAutoIp(lanInfo.public_url)}
                    className="text-[11px] text-emerald-400 underline font-semibold ml-2"
                  >
                    🌐 Internet URL ga o'rnatish ({lanInfo.public_url.replace('https://', '').substring(0, 30)}...)
                  </button>
                )}

                {lanInfo?.local_url && qrBaseUrl !== lanInfo.local_url && (
                  <button
                    onClick={() => handleResetToAutoIp(lanInfo.local_url)}
                    className="text-[11px] text-blue-400 underline font-semibold ml-2"
                  >
                    📡 Lokal IP ga o'rnatish ({lanInfo.local_url})
                  </button>
                )}

                {qrBaseUrl !== window.location.origin && (
                  <button
                    onClick={() => handleResetToAutoIp(window.location.origin)}
                    className="text-[11px] text-amber-400 underline font-semibold ml-2"
                  >
                    🖥 Hozirgi manzilga o'rnatish ({window.location.origin})
                  </button>
                )}
              </div>
            )}
          </div>

          {/* ─── Zonalar (Stol kategoriyalari): Zal, Terrassa, 2-qavat ─── */}
          <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80 shadow-lg space-y-3.5">
            <div>
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <MapPin className="w-4 h-4 text-theme-primary" />
                <span>Zonalar (stollar kategoriyasi)</span>
              </h3>
              <p className="text-[11px] text-theme-muted mt-1">
                Restorandagi joylar: Zal, Terrassa, 2-qavat, VIP xona. Har bir
                stolni o'z zonasiga biriktirasiz — chek va oshxona begunogida
                zona nomi chiqadi.
              </p>
            </div>

            <form onSubmit={handleCreateZone} className="flex flex-col sm:flex-row gap-2.5">
              <input
                type="text"
                value={newZoneName}
                onChange={(e) => setNewZoneName(e.target.value)}
                placeholder="Yangi zona nomi (masalan: Terrassa)"
                maxLength={100}
                className="w-full sm:flex-1 px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-theme-primary"
              />
              <button
                type="submit"
                disabled={zoneBusy || !newZoneName.trim()}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover disabled:opacity-40 text-white text-xs font-bold shadow-glow whitespace-nowrap"
              >
                + Zona qo'shish
              </button>
            </form>

            {zones.length === 0 ? (
              <p className="text-[11px] text-theme-muted italic">
                Hali zona qo'shilmagan. Yuqoridagi maydonga nom yozib qo'shing.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {zones.map((z) => (
                  <div
                    key={z.id}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl bg-black/30 border border-theme-border"
                  >
                    {editingZoneId === z.id ? (
                      <>
                        <input
                          type="text"
                          value={editingZoneName}
                          onChange={(e) => setEditingZoneName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRenameZone(z.id);
                            if (e.key === 'Escape') setEditingZoneId(null);
                          }}
                          autoFocus
                          maxLength={100}
                          className="w-36 px-2 py-1 rounded-lg bg-black/50 border border-theme-primary/60 text-xs text-white focus:outline-none"
                        />
                        <button
                          onClick={() => handleRenameZone(z.id)}
                          disabled={zoneBusy}
                          title="Saqlash"
                          className="text-emerald-400 hover:text-emerald-300 disabled:opacity-40"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingZoneId(null)}
                          title="Bekor qilish"
                          className="text-zinc-500 hover:text-white"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </>
                    ) : (
                      <>
                        <span className="text-xs font-bold text-white">{z.name}</span>
                        <span className="text-[10px] font-bold text-theme-muted px-1.5 py-0.5 rounded-md bg-white/5">
                          {z.tables_count} stol
                        </span>
                        <button
                          onClick={() => {
                            setEditingZoneId(z.id);
                            setEditingZoneName(z.name);
                          }}
                          title="Nomini o'zgartirish"
                          className="text-zinc-500 hover:text-theme-primary"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteZone(z)}
                          disabled={zoneBusy}
                          title="Zonani o'chirish"
                          className="text-zinc-500 hover:text-red-400 disabled:opacity-40"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                ))}
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
            <select
              value={newTableRoom}
              onChange={(e) => setNewTableRoom(e.target.value)}
              title="Stol qaysi zonada turadi"
              className="w-full sm:flex-1 px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-theme-primary"
            >
              <option value="">— Zonasiz —</option>
              {zones.map((z) => (
                <option key={z.id} value={z.name}>
                  {z.name}
                </option>
              ))}
            </select>
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

          {/* ─── Filtrlar: zona va holat ───────────────────────────
              "Terrassa" ni bossangiz faqat terrassadagi stollar,
              "Band" ni bossangiz faqat band stollar chiqadi. */}
          <div className="space-y-2.5 pt-1">
            {tableZoneOptions.length > 0 && (
              <div>
                <span className="block text-[10px] font-black text-theme-muted uppercase tracking-wider mb-1.5">
                  Zona bo'yicha
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setTableZoneFilter('')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95 ${
                      tableZoneFilter === ''
                        ? 'bg-theme-primary text-white shadow-glow'
                        : 'bg-black/30 border border-theme-border text-slate-300 hover:border-theme-primary/50'
                    }`}
                  >
                    Hammasi {tables.length}
                  </button>
                  {tableZoneOptions.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => setTableZoneFilter(o.value)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95 ${
                        tableZoneFilter === o.value
                          ? 'bg-theme-primary text-white shadow-glow'
                          : 'bg-black/30 border border-theme-border text-slate-300 hover:border-theme-primary/50'
                      }`}
                    >
                      {o.label} {o.count}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <span className="block text-[10px] font-black text-theme-muted uppercase tracking-wider mb-1.5">
                Holati bo'yicha
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { v: '', label: 'Hammasi', n: statusCounts.all, cls: 'bg-theme-primary text-white shadow-glow' },
                  { v: 'available', label: "Bo'sh", n: statusCounts.available, cls: 'bg-emerald-500 text-slate-950 shadow-md' },
                  { v: 'occupied', label: 'Band', n: statusCounts.occupied, cls: 'bg-red-500 text-white shadow-md' },
                  { v: 'reserved', label: 'Rezerv', n: statusCounts.reserved, cls: 'bg-amber-500 text-slate-950 shadow-md' },
                ].map((o) => (
                  <button
                    key={o.v || 'all'}
                    type="button"
                    onClick={() => setTableStatusFilter(o.v)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95 ${
                      tableStatusFilter === o.v
                        ? o.cls
                        : 'bg-black/30 border border-theme-border text-slate-300 hover:border-theme-primary/50'
                    }`}
                  >
                    {o.label} {o.n}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Tables Grid — zonalar bo'yicha guruhlangan */}
          {tableGroups.length === 0 && (
            <div className="p-8 rounded-3xl glass-card border border-theme-border text-center space-y-1">
              <p className="text-sm font-black text-white">Bu filtrga mos stol yo'q</p>
              <p className="text-xs text-theme-muted">
                Yuqoridagi "Hammasi" tugmasini bosib barcha stollarni ko'ring.
              </p>
            </div>
          )}
          {tableGroups.map((group) => (
          <div key={group.key} className="space-y-3">
            <div className="flex items-center gap-2 pt-2">
              <MapPin className="w-4 h-4 text-theme-primary shrink-0" />
              <h3 className="text-sm font-black text-white uppercase tracking-wide">
                {group.name}
              </h3>
              <span className="text-[10px] font-bold text-theme-muted px-2 py-0.5 rounded-md bg-white/5">
                {group.items.length} stol
              </span>
              <div className="flex-1 h-px bg-theme-border/60" />
            </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {group.items.map((t) => {
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
                            !t.is_unlocked && t.current_pin
                              ? 'bg-amber-500/30 text-amber-300 border border-amber-500/50 animate-pulse'
                              : isOccupied
                              ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                              : isReserved
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {!t.is_unlocked && t.current_pin ? '🔒 Kod Kutilmoqda' : (isOccupied ? 'Band' : isReserved ? 'Bron' : "Bo'sh")}
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

                  {/* If table is locked with pin */}
                  {!t.is_unlocked && t.current_pin && (
                    <div className="p-3 rounded-2xl bg-amber-500/15 border border-amber-500/40 text-center space-y-1.5">
                      <span className="text-[10px] uppercase text-amber-300 font-bold block">Mijoz Kirdi (Kodi):</span>
                      <span className="text-xl font-mono font-black text-amber-300 block">{t.current_pin}</span>
                      <button
                        onClick={() => handleUnlockTable(t.id)}
                        className="w-full py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-black font-extrabold text-xs shadow-md active:scale-95 transition-all flex items-center justify-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Ulanishni Tasdiqlash</span>
                      </button>
                    </div>
                  )}

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

                    {/* View Bill & Direct Print Button */}
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => handleOpenBill(t)}
                        className="w-full py-2.5 rounded-xl bg-theme-primary/15 hover:bg-theme-primary/25 border border-theme-primary/30 text-theme-primary text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-sm"
                      >
                        <Receipt className="w-3.5 h-3.5" />
                        <span>Hisobni ko'rish</span>
                      </button>

                      <button
                        onClick={() => handleDirectPrintBill(t.id, t.number)}
                        className="w-full py-2.5 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/40 text-blue-300 text-xs font-bold flex items-center justify-center gap-1.5 transition-all shadow-sm active:scale-95"
                        title="Mijoz hisob chekini to'g'ridan-to'g'ri Printer 1 ga chiqarish"
                      >
                        <Printer className="w-3.5 h-3.5" />
                        <span>Chek (Printer 1)</span>
                      </button>
                    </div>

                    {/* Kassa — to'lovni qabul qilish (ofitsiant panelidan ko'chirildi) */}
                    <button
                      onClick={() => handleOpenCheckout(t)}
                      className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-black flex items-center justify-center gap-1.5 transition-all shadow-lg shadow-emerald-600/25 active:scale-95"
                      title="To'lovni qabul qilish va hisobni yopish"
                    >
                      <CreditCard className="w-4 h-4" />
                      <span>To'lov / Hisob (Kassa)</span>
                    </button>

                    {t.is_unlocked && (
                      <button
                        onClick={() => handleLockTable(t.id)}
                        className="w-full py-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>Qayta Qulflash (Yangi PIN)</span>
                      </button>
                    )}

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
          ))}
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

      <ThermalReceiptModal
        isOpen={thermalOpen}
        onClose={() => setThermalOpen(false)}
        title={thermalTitle}
        rawText={thermalRawText}
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
    </div>
  );
};

export default AdminDashboard;

