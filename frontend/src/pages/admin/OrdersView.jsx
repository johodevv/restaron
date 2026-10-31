import React, { useState, useEffect, useMemo } from 'react';
import api from '../../utils/api';
import { useWebSocket } from '../../context/WebSocketContext';
import CheckoutModal from '../../components/CheckoutModal';
import ThermalReceiptModal from '../../components/ThermalReceiptModal';
import OrderCard from '../../components/OrderCard';
import confetti from 'canvas-confetti';
import {
  ShoppingBag,
  Bike,
  Search,
  RefreshCw,
  Plus,
  Phone,
  MapPin,
  Clock,
  CheckCircle2,
  AlertCircle,
  X,
  CreditCard,
  Printer,
  Receipt,
  User,
  Flame,
  Check,
  Send,
  Calendar,
  DollarSign,
  PackageCheck,
  Filter
} from 'lucide-react';

const STATUS_CONFIG = {
  pending: {
    label: 'Kutilmoqda',
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    border: 'border-amber-500/40',
    dot: 'bg-amber-400',
  },
  confirmed: {
    label: 'Tasdiqlangan',
    bg: 'bg-blue-500/15',
    text: 'text-blue-400',
    border: 'border-blue-500/40',
    dot: 'bg-blue-400',
  },
  preparing: {
    label: 'Tayyorlanmoqda',
    bg: 'bg-purple-500/15',
    text: 'text-purple-400',
    border: 'border-purple-500/40',
    dot: 'bg-purple-400',
  },
  ready: {
    label: 'Tayyor',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    dot: 'bg-emerald-400',
  },
  served: {
    label: 'Yetkazildi',
    bg: 'bg-cyan-500/15',
    text: 'text-cyan-400',
    border: 'border-cyan-500/40',
    dot: 'bg-cyan-400',
  },
  paid: {
    label: "To'langan",
    bg: 'bg-emerald-500/20',
    text: 'text-emerald-300',
    border: 'border-emerald-500/50',
    dot: 'bg-emerald-300',
  },
  cancelled: {
    label: 'Bekor qilingan',
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    border: 'border-red-500/40',
    dot: 'bg-red-400',
  },
};

export const OrdersView = ({ restaurantId = 1, initialType = 'takeaway' }) => {
  const [activeType, setActiveType] = useState(initialType); // 'takeaway' | 'delivery'

  useEffect(() => {
    if (initialType) {
      setActiveType(initialType);
    }
  }, [initialType]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'pending' | 'preparing' | 'ready' | 'served' | 'paid'

  // Action / Modal states
  const [selectedOrderForCheckout, setSelectedOrderForCheckout] = useState(null);
  const [thermalOpen, setThermalOpen] = useState(false);
  const [thermalRawText, setThermalRawText] = useState('');
  const [thermalPrintDocument, setThermalPrintDocument] = useState(null);
  const [thermalTitle, setThermalTitle] = useState('Chek');

  // New order modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [categories, setCategories] = useState([]);
  const [newCustomerName, setNewCustomerName] = useState('');
  const [newCustomerPhone, setNewCustomerPhone] = useState('');
  const [newDeliveryAddress, setNewDeliveryAddress] = useState('');
  const [newKitchenNote, setNewKitchenNote] = useState('');
  const [newOrderItems, setNewOrderItems] = useState({}); // { menuItemId: qty }
  const [creatingOrder, setCreatingOrder] = useState(false);

  const { addEventListener } = useWebSocket();

  const isDelivery = activeType === 'delivery';

  // Fetch orders from backend
  const fetchOrders = async () => {
    setLoading(true);
    try {
      const data = await api.get(`/orders/?restaurant_id=${restaurantId}&order_type=${activeType}&limit=100`);
      setOrders(data || []);
    } catch (err) {
      console.error('Error fetching orders:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch menu for creation modal
  const fetchMenu = async () => {
    try {
      const menuData = await api.get(`/menu/full/${restaurantId}`);
      setCategories(menuData || []);
    } catch (err) {
      console.error('Error fetching menu:', err);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [restaurantId, activeType]);

  useEffect(() => {
    if (createModalOpen && categories.length === 0) {
      fetchMenu();
    }
  }, [createModalOpen]);

  // Real-time WebSocket updates
  useEffect(() => {
    const unsubscribe = addEventListener('*', (event) => {
      if (
        event.type === 'new_order' ||
        event.type === 'order_updated' ||
        event.type === 'order_status' ||
        event.type === 'order_status_updated' ||
        event.type === 'bill_paid' ||
        event.type === 'order_ready'
      ) {
        fetchOrders();
      }
    });
    return () => unsubscribe();
  }, [activeType, restaurantId]);

  // Filtered orders
  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      // Status filter
      if (statusFilter !== 'all') {
        const orderStatus = (o.status || '').toLowerCase();
        if (statusFilter === 'paid') {
          if (!o.is_paid && orderStatus !== 'paid') return false;
        } else if (orderStatus !== statusFilter) {
          return false;
        }
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const num = (o.order_number || '').toLowerCase();
        const name = (o.customer_name || '').toLowerCase();
        const phone = (o.customer_phone || '').toLowerCase();
        const addr = (o.delivery_address || '').toLowerCase();
        return num.includes(q) || name.includes(q) || phone.includes(q) || addr.includes(q);
      }
      return true;
    });
  }, [orders, statusFilter, searchQuery]);

  // Counts for tabs/badges
  const stats = useMemo(() => {
    const totalCount = orders.length;
    const pendingCount = orders.filter((o) => o.status === 'pending').length;
    const preparingCount = orders.filter((o) => o.status === 'preparing').length;
    const readyCount = orders.filter((o) => o.status === 'ready').length;
    const servedCount = orders.filter((o) => o.status === 'served').length;
    const totalAmount = orders.reduce((sum, o) => sum + (o.total || 0), 0);
    return { totalCount, pendingCount, preparingCount, readyCount, servedCount, totalAmount };
  }, [orders]);

  // Status transitions
  const handleUpdateStatus = async (orderId, newStatus) => {
    try {
      await api.patch(`/orders/${orderId}/status`, { status: newStatus });
      fetchOrders();
    } catch (err) {
      alert(err.message || 'Statusni yangilashda xatolik');
    }
  };

  // Deliver action
  const handleDeliver = async (orderId) => {
    try {
      await api.patch(`/orders/${orderId}/deliver`, {});
      confetti({ particleCount: 50, spread: 60 });
      fetchOrders();
    } catch (err) {
      alert(err.message || 'Yetkazishda xatolik');
    }
  };

  // Print Bill
  const handlePrintOrder = async (orderId, orderNum) => {
    try {
      const res = await api.post(`/orders/${orderId}/send-to-kitchen?reprint=true`);
      if (res?.raw_text) {
        setThermalRawText(res.raw_text);
        setThermalPrintDocument(res.print_document || null);
        setThermalTitle(`Chek — ${orderNum}`);
        setThermalOpen(true);
      } else {
        alert("Chek printerga yuborildi!");
      }
    } catch (err) {
      alert(err.message || 'Chek chiqarishda xatolik');
    }
  };

  // Open Checkout for order
  const handleOpenCheckout = (order) => {
    setSelectedOrderForCheckout(order);
  };

  // Create new order handler
  const handleCreateOrder = async (e) => {
    e.preventDefault();
    const items = Object.entries(newOrderItems)
      .filter(([_, qty]) => qty > 0)
      .map(([id, qty]) => ({ menu_item_id: Number(id), quantity: qty }));

    if (items.length === 0) {
      alert('Iltimos, kamida bitta taom tanlang');
      return;
    }

    if (!newCustomerName.trim()) {
      alert('Iltimos, mijoz ismini kiriting');
      return;
    }

    if (isDelivery && !newDeliveryAddress.trim()) {
      alert('Iltimos, yetkazib berish manzilini kiriting');
      return;
    }

    setCreatingOrder(true);
    try {
      const payload = {
        restaurant_id: restaurantId,
        order_type: activeType,
        customer_name: newCustomerName.trim(),
        customer_phone: newCustomerPhone.trim() || null,
        delivery_address: isDelivery ? newDeliveryAddress.trim() : null,
        kitchen_note: newKitchenNote.trim() || null,
        items,
      };

      await api.post('/orders/waiter-create', payload);
      confetti({ particleCount: 60, spread: 70 });
      setCreateModalOpen(false);
      setNewCustomerName('');
      setNewCustomerPhone('');
      setNewDeliveryAddress('');
      setNewKitchenNote('');
      setNewOrderItems({});
      fetchOrders();
    } catch (err) {
      alert(err.message || 'Buyurtma yaratishda xatolik');
    } finally {
      setCreatingOrder(false);
    }
  };

  const allMenuItems = useMemo(() => {
    return categories.flatMap((c) => c.items || []);
  }, [categories]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ─── Top Control Strip ──────────────────────────────────────────────── */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/85 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-theme-primary/30 to-theme-primary/10 border border-theme-primary/40 flex items-center justify-center text-theme-primary shadow-lg shadow-theme-primary/20 shrink-0">
            {isDelivery ? <Bike className="w-7 h-7" /> : <ShoppingBag className="w-7 h-7" />}
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full bg-theme-primary/20 text-theme-primary border border-theme-primary/30 text-[10px] font-black uppercase tracking-wider">
                {isDelivery ? '🛵 Yetkazib Berish Bo\'limi' : '🛍️ Olib Ketish (S собой)'}
              </span>
              <span className="text-xs text-theme-muted font-bold">
                Jami: {stats.totalCount} ta buyurtma
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white">
              {isDelivery ? 'Dastavka (Yetkazib berish) Buyurtmalari' : 'Olib Ketish (Takeaway) Buyurtmalari'}
            </h2>
            <p className="text-xs text-theme-muted mt-0.5">
              {isDelivery
                ? 'Mijozlarga uylariga yoki ofislariga yetkazib beriladigan buyurtmalar nazorati va kassa to\'lovi'
                : 'Mijozlar choyxonadan o\'zlari olib ketadigan buyurtmalar va tayyorlanish jarayoni'}
            </p>
          </div>
        </div>

        {/* Switch Type + Add Order + Refresh Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Toggle Type buttons */}
          <div className="p-1 rounded-2xl bg-slate-900/90 border border-slate-700/80 flex items-center">
            <button
              onClick={() => setActiveType('takeaway')}
              className={`px-3.5 py-2 rounded-xl text-xs font-black flex items-center gap-2 transition-all ${
                !isDelivery
                  ? 'bg-amber-500 text-slate-950 shadow-md scale-102'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <ShoppingBag className="w-3.5 h-3.5" />
              <span>Olib ketish</span>
            </button>
            <button
              onClick={() => setActiveType('delivery')}
              className={`px-3.5 py-2 rounded-xl text-xs font-black flex items-center gap-2 transition-all ${
                isDelivery
                  ? 'bg-emerald-500 text-slate-950 shadow-md scale-102'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Bike className="w-3.5 h-3.5" />
              <span>Dastavka</span>
            </button>
          </div>

          <button
            onClick={() => setCreateModalOpen(true)}
            className="px-4 py-2.5 rounded-2xl bg-gradient-to-r from-theme-primary to-emerald-600 hover:from-theme-primary/90 hover:to-emerald-500 text-white font-extrabold text-xs shadow-lg shadow-theme-primary/25 flex items-center gap-2 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Yangi buyurtma</span>
          </button>

          <button
            onClick={fetchOrders}
            className="p-2.5 rounded-2xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white text-xs flex items-center gap-1.5 font-bold transition-all"
            title="Yangilash"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ─── Metric Stat Cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between shadow-md">
          <div>
            <p className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">Kutilmoqda</p>
            <p className="text-2xl font-black text-white mt-1">{stats.pendingCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center font-bold">
            ⏳
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between shadow-md">
          <div>
            <p className="text-[11px] font-bold text-purple-400 uppercase tracking-wider">Tayyorlanmoqda</p>
            <p className="text-2xl font-black text-white mt-1">{stats.preparingCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center font-bold">
            🔥
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between shadow-md">
          <div>
            <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">Tayyor</p>
            <p className="text-2xl font-black text-white mt-1">{stats.readyCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold">
            🚀
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between shadow-md">
          <div>
            <p className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider">Yetkazildi / Berildi</p>
            <p className="text-2xl font-black text-white mt-1">{stats.servedCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center font-bold">
            🛵
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between shadow-md col-span-2 sm:col-span-1">
          <div>
            <p className="text-[11px] font-bold text-theme-primary uppercase tracking-wider">Jami Summa</p>
            <p className="text-lg sm:text-xl font-black text-white mt-1 font-mono">
              {Math.round(stats.totalAmount).toLocaleString('uz-UZ')} <span className="text-xs">so'm</span>
            </p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-theme-primary/10 text-theme-primary flex items-center justify-center font-bold">
            💰
          </div>
        </div>
      </div>

      {/* ─── Search & Status Filters ────────────────────────────────────────── */}
      <div className="p-4 rounded-2xl glass-card border border-theme-border bg-theme-surface/70 flex flex-col md:flex-row md:items-center justify-between gap-3.5">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={
              isDelivery
                ? 'Mijoz ismi, telefon raqami, manzili yoki buyurtma #...'
                : 'Mijoz ismi, telefon raqami yoki buyurtma #...'
            }
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs sm:text-sm text-white placeholder-slate-400 focus:outline-none focus:border-theme-primary"
          />
        </div>

        {/* Status Filter Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
          {[
            { key: 'all', label: 'Barchasi' },
            { key: 'pending', label: 'Kutilmoqda' },
            { key: 'preparing', label: 'Tayyorlanmoqda' },
            { key: 'ready', label: 'Tayyor' },
            { key: 'served', label: 'Yetkazildi' },
            { key: 'paid', label: "To'langan" },
          ].map((st) => (
            <button
              key={st.key}
              onClick={() => setStatusFilter(st.key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-extrabold whitespace-nowrap transition-all ${
                statusFilter === st.key
                  ? 'bg-theme-primary text-white shadow-md'
                  : 'bg-slate-900 border border-slate-800 text-slate-300 hover:text-white'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Orders Grid ────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-theme-primary" />
          <p className="text-sm font-bold">Buyurtmalar yuklanmoqda...</p>
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="p-16 rounded-3xl glass-card border border-dashed border-theme-border text-center flex flex-col items-center justify-center gap-3">
          <div className="w-16 h-16 rounded-2xl bg-slate-900 text-slate-500 flex items-center justify-center">
            {isDelivery ? <Bike className="w-8 h-8" /> : <ShoppingBag className="w-8 h-8" />}
          </div>
          <h3 className="text-base font-extrabold text-white">
            {isDelivery ? 'Dastavka buyurtmalari topilmadi' : 'Olib ketish buyurtmalari topilmadi'}
          </h3>
          <p className="text-xs text-slate-400 max-w-sm">
            {searchQuery
              ? 'Qidiruv bo\'yicha hech qanday buyurtma topilmadi. Qidiruvni tozalab ko\'ring.'
              : 'Hozirda yangi buyurtmalar mavjud emas. Yuqoridagi "Yangi buyurtma" tugmasi orqali yangi zakas qabul qilishingiz mumkin.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5 sm:gap-4 w-full overflow-x-hidden p-1 sm:p-2">
          {filteredOrders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              onConfirm={() => handleUpdateStatus(order.id, 'preparing')}
              onUpdateStatus={handleUpdateStatus}
              onDeliver={handleDeliver}
              onPrint={handlePrintOrder}
              onCheckout={handleOpenCheckout}
            />
          ))}
        </div>
      )}

      {/* ─── Create New Order Modal ─────────────────────────────────────────── */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-theme-primary/20 text-theme-primary flex items-center justify-center font-bold">
                  {isDelivery ? <Bike className="w-5 h-5" /> : <ShoppingBag className="w-5 h-5" />}
                </div>
                <div>
                  <h3 className="text-base font-black text-white">
                    {isDelivery ? 'Yangi Dastavka Buyurtmasi' : 'Yangi Olib Ketish Buyurtmasi'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Mijoz ma'lumotlarini to'ldiring va menyudan taomlarni tanlang
                  </p>
                </div>
              </div>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateOrder} className="space-y-4">
              {/* Customer Name */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">
                  Mijoz ismi (FISH) <span className="text-red-400">*</span>:
                </label>
                <input
                  type="text"
                  required
                  value={newCustomerName}
                  onChange={(e) => setNewCustomerName(e.target.value)}
                  placeholder="Masalan: Alisher Navoiy"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-theme-primary font-medium"
                />
              </div>

              {/* Customer Phone */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">
                  Telefon raqami:
                </label>
                <input
                  type="tel"
                  value={newCustomerPhone}
                  onChange={(e) => setNewCustomerPhone(e.target.value)}
                  placeholder="+998 90 123 45 67"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-theme-primary font-mono"
                />
              </div>

              {/* Delivery Address (only for Delivery) */}
              {isDelivery && (
                <div>
                  <label className="block text-xs font-bold text-amber-300 mb-1">
                    Yetkazib berish manzili <span className="text-red-400">*</span>:
                  </label>
                  <textarea
                    rows={2}
                    required
                    value={newDeliveryAddress}
                    onChange={(e) => setNewDeliveryAddress(e.target.value)}
                    placeholder="Masalan: Xiva shahri, Ichan Qal'a 12-uy (mo'ljal: minoraning orqasi)"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-amber-500/40 text-sm text-white focus:outline-none focus:border-amber-400 font-medium resize-none"
                  />
                </div>
              )}

              {/* Kitchen Note */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">
                  Oshxonaga maxsus izoh:
                </label>
                <input
                  type="text"
                  value={newKitchenNote}
                  onChange={(e) => setNewKitchenNote(e.target.value)}
                  placeholder="Masalan: Issiq qilib o'rab bering, sousi ko'proq bo'lsin..."
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-theme-primary font-medium"
                />
              </div>

              {/* Menu items selector */}
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1.5">
                  Taomlarni tanlash:
                </label>
                <div className="max-h-48 overflow-y-auto space-y-1.5 p-3 rounded-2xl bg-slate-950 border border-slate-800">
                  {allMenuItems.length === 0 ? (
                    <p className="text-xs text-slate-500">Menyu yuklanmoqda...</p>
                  ) : (
                    allMenuItems.map((item) => {
                      const qty = newOrderItems[item.id] || 0;
                      return (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-white"
                        >
                          <div>
                            <span className="font-bold">{item.name}</span>
                            <span className="text-slate-400 font-mono ml-2">
                              {item.price.toLocaleString('uz-UZ')} so'm
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {qty > 0 && (
                              <button
                                type="button"
                                onClick={() =>
                                  setNewOrderItems((prev) => ({
                                    ...prev,
                                    [item.id]: Math.max(0, qty - 1),
                                  }))
                                }
                                className="w-6 h-6 rounded-lg bg-slate-800 text-slate-300 font-bold flex items-center justify-center hover:bg-slate-700"
                              >
                                -
                              </button>
                            )}

                            {qty > 0 && <span className="font-black font-mono w-4 text-center">{qty}</span>}

                            <button
                              type="button"
                              onClick={() =>
                                setNewOrderItems((prev) => ({
                                  ...prev,
                                  [item.id]: qty + 1,
                                }))
                              }
                              className="w-6 h-6 rounded-lg bg-emerald-600 text-white font-bold flex items-center justify-center hover:bg-emerald-500"
                            >
                              +
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-400 hover:text-white"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={creatingOrder}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-theme-primary to-emerald-600 hover:from-theme-primary/90 hover:to-emerald-500 disabled:opacity-40 text-white font-black text-xs shadow-lg shadow-theme-primary/25 transition-all"
                >
                  {creatingOrder ? 'Yaratilmoqda...' : 'Buyurtmani Tasdiqlash'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── Checkout Modal ─────────────────────────────────────────────────── */}
      <CheckoutModal
        isOpen={!!selectedOrderForCheckout}
        onClose={() => setSelectedOrderForCheckout(null)}
        order={selectedOrderForCheckout}
        tableLabel={
          selectedOrderForCheckout
            ? `${selectedOrderForCheckout.order_type === 'delivery' ? '🛵 Dastavka' : '🛍️ Olib ketish'} — ${selectedOrderForCheckout.order_number}`
            : 'Buyurtma'
        }
        onPaid={(res) => {
          setSelectedOrderForCheckout(null);
          if (res?.raw_text) {
            setThermalRawText(res.raw_text);
            setThermalPrintDocument(res.print_document || null);
            setThermalTitle(`Chek — ${selectedOrderForCheckout?.order_number}`);
            setThermalOpen(true);
          }
          confetti({ particleCount: 60, spread: 60 });
          fetchOrders();
        }}
      />

      {/* ─── Thermal Receipt Modal ──────────────────────────────────────────── */}
      <ThermalReceiptModal
        isOpen={thermalOpen}
        onClose={() => setThermalOpen(false)}
        title={thermalTitle}
        rawText={thermalRawText}
        printDocument={thermalPrintDocument}
        restaurantId={restaurantId}
        paperWidth={80}
      />
    </div>
  );
};

export default OrdersView;
