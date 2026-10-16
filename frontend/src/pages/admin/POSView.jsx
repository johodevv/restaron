import React, { useState, useEffect, useMemo } from 'react';
import api from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import OrderCart, { isItemPriced } from '../../components/OrderCart';
import CheckoutModal from '../../components/CheckoutModal';
import ThermalReceiptModal from '../../components/ThermalReceiptModal';
import {
  ShoppingCart,
  ShoppingBag,
  Bike,
  UtensilsCrossed,
  Search,
  Plus,
  Minus,
  Trash2,
  Printer,
  Receipt,
  CheckCircle2,
  User,
  Image as ImageIcon,
  Flame,
  Check,
  AlertTriangle,
  X,
  Layers,
  MapPin,
  Phone,
  CreditCard,
  Sparkles
} from 'lucide-react';
import confetti from 'canvas-confetti';

/**
 * POSView — RestAron POS va Kassa Komponenti.
 * 
 * VAKOLATLARNI AJRATISH:
 * - Admin / Kassir:
 *   * 🟢 "Stolda" (Dine-in)
 *   * 🛍️ "Olib ketish" (Takeaway / Sobo)
 *   * 🛵 "Dastavka" (Delivery)
 *   rejimlarini almashtirish tugmalari to'liq ko'rinadi.
 *   * Savatning pastida "To'landi va stolni bo'shatish" (Checkout) tugmasi faol.
 * - Ofitsiant (waiter):
 *   * Rejim almashtirgich BUTUNLAY YASHIRILADI (faqat stollar qoladi).
 *   * Checkout tugmasi BUTUNLAY YASHIRILADI (faqat oshxonaga buyurtma yuborish qoladi).
 */
export const POSView = ({
  showModeSwitch: propShowModeSwitch,
  canCheckout: propCanCheckout,
  restaurantId: propRestaurantId,
}) => {
  const { user, isAdmin, isCashier, canCheckout: authCanCheckout } = useAuth();
  const { connected } = useWebSocket();
  const restaurantId = propRestaurantId || user?.restaurant_id || 1;

  // Foydalanuvchi roli bo'yicha ruxsatlarni aniqlash:
  // Ofitsiant (waiter) hech qachon rejim almashtira olmaydi va checkout qila olmaydi!
  const isPrivileged = user?.role === 'admin' || user?.role === 'cashier' || user?.role === 'developer';
  const canCheckout = propCanCheckout !== undefined ? propCanCheckout : isPrivileged;
  const showModeSwitch = propShowModeSwitch !== undefined ? propShowModeSwitch : isPrivileged;

  // Rejim: 'table' (Stolda) | 'takeaway' (Olib ketish) | 'delivery' (Dastavka)
  // Agar ofitsiant bo'lsa faqat 'table' bo'ladi.
  const [orderType, setOrderType] = useState('table');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');

  // Ma'lumotlar holati
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCatId, setSelectedCatId] = useState(null);
  const [searchItemQuery, setSearchItemQuery] = useState('');
  const [loading, setLoading] = useState(true);

  // Tanlangan stol va faol buyurtma
  const [selectedTable, setSelectedTable] = useState(null);
  const [selectedZone, setSelectedZone] = useState('');
  const [activeOrder, setActiveOrder] = useState(null);
  const [orderLoading, setOrderLoading] = useState(false);

  // Tarozidagi taom (narxi / og'irligi) oynasi
  const [weightModalItem, setWeightModalItem] = useState(null);
  const [weightValue, setWeightValue] = useState('');
  const [priceValue, setPriceValue] = useState('');
  const [savingWeight, setSavingWeight] = useState(false);

  // Hajmli taom (1.5 L, 1 L) oynasi
  const [sizeModalItem, setSizeModalItem] = useState(null);
  const [sizeValue, setSizeValue] = useState('');
  const [savingSize, setSavingSize] = useState(false);

  // Oshxona izohi va yuborish holatlari
  const [kitchenNote, setKitchenNote] = useState('');
  const [kitchenNoteModalOpen, setKitchenNoteModalOpen] = useState(false);
  const [kitchenSendSuccess, setKitchenSendSuccess] = useState(false);
  const [sendingToKitchen, setSendingToKitchen] = useState(false);
  const [printingBill, setPrintingBill] = useState(false);

  // Kassa / To'lov (Checkout) oynasi
  const [checkoutModalOpen, setCheckoutModalOpen] = useState(false);
  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [thermalReceiptText, setThermalReceiptText] = useState('');
  const [receiptModalTitle, setReceiptModalTitle] = useState('Kassa Cheki');

  // Stol zonalari (Zal, Terrassa, Ko'cha, VIP)
  const zoneNames = useMemo(() => {
    const seen = [];
    (tables || []).forEach((t) => {
      const z = (t.room || '').trim();
      if (z && !seen.includes(z)) seen.push(z);
    });
    return seen.sort((a, b) => a.localeCompare(b, 'uz'));
  }, [tables]);

  const zoneTables = useMemo(() => {
    if (!selectedZone) return tables || [];
    return (tables || []).filter((t) => (t.room || '').trim() === selectedZone);
  }, [tables, selectedZone]);

  // Boshlang'ich ma'lumotlarni yuklash
  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [tablesData, menuData] = await Promise.all([
        api.get(`/tables/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/menu/full/${restaurantId}`).catch(() => []),
      ]);

      const tbls = tablesData || [];
      const mnu = menuData || [];
      setTables(tbls);
      setCategories(mnu);

      if (mnu.length > 0 && !selectedCatId) {
        setSelectedCatId(mnu[0].id);
      }

      if (tbls.length > 0 && !selectedTable) {
        setSelectedTable(tbls[0]);
      }
    } catch (err) {
      console.error('POSView loadInitialData error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, [restaurantId]);

  // Tanlangan stolning faol buyurtmasini yuklash
  const fetchTableActiveOrder = async (tbl) => {
    if (!tbl) return;
    setOrderLoading(true);
    try {
      const activeOrders = await api.get(`/orders/table/${tbl.id}/active`).catch(() => []);
      if (activeOrders && activeOrders.length > 0) {
        const ord = activeOrders[0];
        setActiveOrder(ord);
        setKitchenNote(ord.kitchen_note || '');
      } else {
        setActiveOrder(null);
        setKitchenNote('');
      }
    } catch (err) {
      console.error('Fetch table order error:', err);
      setActiveOrder(null);
    } finally {
      setOrderLoading(false);
    }
  };

  useEffect(() => {
    if (orderType === 'table' && selectedTable) {
      fetchTableActiveOrder(selectedTable);
    }
  }, [selectedTable?.id, orderType]);

  // Tarozidagi taom qo'shilganda modalni avtomatik ochish
  const openWeightModalIfNeeded = (ord, menuItemId) => {
    if (!ord || !ord.items) return;
    const added = ord.items.find((i) => i.menu_item_id === menuItemId && i.is_weighted && !isItemPriced(i));
    if (added) {
      setWeightModalItem(added);
      setWeightValue(added.weight ? String(added.weight) : '');
      setPriceValue(
        added.manual_price !== null && added.manual_price !== undefined
          ? String(Math.round(added.manual_price))
          : added.total_price
          ? String(Math.round(added.total_price))
          : ''
      );
    }
  };

  // Taom qo'shish
  const handleAddItem = async (menuItem) => {
    if (menuItem.is_stop_list || menuItem.is_available === false) {
      alert(`"${menuItem.name}" hozirda stop-listda (tugagan)`);
      return;
    }

    if (orderType === 'table' && !selectedTable) {
      alert('Iltimos, avval stolni tanlang');
      return;
    }

    try {
      if (!activeOrder) {
        // Yangi buyurtma ochish
        const payload = {
          restaurant_id: restaurantId,
          order_type: orderType === 'table' ? 'dine_in' : orderType,
          items: [{ menu_item_id: menuItem.id, quantity: 1 }],
        };
        if (orderType === 'table') {
          payload.table_id = selectedTable?.id;
          payload.hall_name = selectedTable?.room || 'Zal';
        } else {
          payload.customer_name = customerName.trim() || (orderType === 'takeaway' ? 'Olib ketish mijoz' : 'Dastavka mijoz');
          payload.customer_phone = customerPhone.trim() || null;
          if (orderType === 'delivery') {
            payload.delivery_address = deliveryAddress.trim() || 'Manzil';
          }
        }

        const newOrd = await api.post('/orders/waiter-create', payload);
        setActiveOrder(newOrd);
        openWeightModalIfNeeded(newOrd, menuItem.id);

        if (orderType === 'table' && selectedTable) {
          setTables((prev) =>
            prev.map((t) => (t.id === selectedTable.id ? { ...t, status: 'occupied', is_occupied: true } : t))
          );
          setSelectedTable((prev) => (prev ? { ...prev, status: 'occupied', is_occupied: true } : prev));
        }
      } else {
        // Mavjud buyurtmaga qo'shish
        const existingItem = (activeOrder.items || []).find(
          (i) => i.menu_item_id === menuItem.id && !i.portion_size && !i.is_weighted
        );

        if (existingItem) {
          const updated = await api.patch(
            `/orders/${activeOrder.id}/items/${existingItem.id}/quantity`,
            { quantity: existingItem.quantity + 1 }
          );
          setActiveOrder(updated);
        } else {
          const updated = await api.post(`/orders/${activeOrder.id}/add-items`, {
            items: [{ menu_item_id: menuItem.id, quantity: 1 }],
            send_to_kitchen_immediately: false,
          });
          setActiveOrder(updated);
          openWeightModalIfNeeded(updated, menuItem.id);
        }
      }
    } catch (err) {
      alert(err.message || "Taom qo'shishda xatolik");
    }
  };

  // Soni o'zgartirish (+ / -)
  const handleQtyChange = async (item, delta) => {
    if (!activeOrder) return;
    const newQty = (item.quantity || 1) + delta;
    if (newQty <= 0) {
      handleDeleteItem(item.id);
      return;
    }
    try {
      const updated = await api.patch(`/orders/${activeOrder.id}/items/${item.id}/quantity`, {
        quantity: newQty,
      });
      setActiveOrder(updated);
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // Taomni o'chirish
  const handleDeleteItem = async (itemId) => {
    if (!activeOrder) return;
    try {
      const updated = await api.delete(`/orders/${activeOrder.id}/items/${itemId}`);
      setActiveOrder(updated);
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // Tarozidagi taom narxini saqlash
  const handleSaveWeight = async () => {
    if (!activeOrder || !weightModalItem) return;
    const w = parseFloat(String(weightValue).replace(',', '.'));
    const pr = parseFloat(String(priceValue).replace(/[^0-9.,]/g, '').replace(',', '.'));
    const hasPrice = !isNaN(pr) && pr >= 0 && String(priceValue).trim() !== '';
    const hasWeight = !isNaN(w) && w > 0;

    if (!hasPrice && !hasWeight) {
      alert('Summani kiriting (masalan: 235000)');
      return;
    }

    setSavingWeight(true);
    try {
      const body = {};
      if (hasPrice) body.price = pr;
      if (hasWeight) body.weight = w;
      if (weightModalItem.unit) body.unit = weightModalItem.unit;

      const updated = await api.patch(
        `/orders/${activeOrder.id}/items/${weightModalItem.id}/weight`,
        body
      );
      setActiveOrder(updated);
      setWeightModalItem(null);
      setWeightValue('');
      setPriceValue('');
    } catch (err) {
      alert(err.message || 'Narxni saqlashda xatolik');
    } finally {
      setSavingWeight(false);
    }
  };

  // Taom hajmini saqlash (1.5 L kola, va h.k.)
  const handleSaveSize = async () => {
    if (!activeOrder || !sizeModalItem) return;
    setSavingSize(true);
    try {
      const updated = await api.patch(
        `/orders/${activeOrder.id}/items/${sizeModalItem.id}/portion-size`,
        { portion_size: sizeValue.trim() || null }
      );
      setActiveOrder(updated);
      setSizeModalItem(null);
      setSizeValue('');
    } catch (err) {
      alert(err.message || 'Hajmni saqlashda xatolik');
    } finally {
      setSavingSize(false);
    }
  };

  // Oshxonaga yuborish (Buyurtmani tasdiqlash)
  const handleSendToKitchen = async () => {
    if (!activeOrder) return;
    setSendingToKitchen(true);
    try {
      await api.post(`/orders/${activeOrder.id}/send-to-kitchen`, {});
      setKitchenSendSuccess(true);
      confetti({ particleCount: 40, spread: 45 });
      setTimeout(() => setKitchenSendSuccess(false), 5000);
      if (orderType === 'table' && selectedTable) {
        fetchTableActiveOrder(selectedTable);
      }
    } catch (err) {
      alert(err.message || 'Oshxonaga yuborishda xatolik');
    } finally {
      setSendingToKitchen(false);
    }
  };

  // Hisob chekini chiqarish
  const handlePrintBill = async () => {
    if (!activeOrder) return;
    setPrintingBill(true);
    try {
      const res = await api.post(`/orders/${activeOrder.id}/bill`, {});
      if (res?.raw_text) {
        setThermalReceiptText(res.raw_text);
        setReceiptModalTitle(`Hisob Cheki #${activeOrder.order_number || activeOrder.id}`);
        setReceiptModalOpen(true);
      }
    } catch (err) {
      alert(err.message || 'Chek chiqarishda xatolik');
    } finally {
      setPrintingBill(false);
    }
  };

  // To'lov muvaffaqiyatli qabul qilingach (Checkout Paid)
  const handleCheckoutPaid = (res) => {
    setCheckoutModalOpen(false);
    confetti({ particleCount: 80, spread: 70 });
    if (res?.raw_text) {
      setThermalReceiptText(res.raw_text);
      setReceiptModalTitle(`Kassa Cheki #${res?.order_id || activeOrder?.id || ''}`);
      setReceiptModalOpen(true);
    }
    // Stolni bo'shatamiz
    if (orderType === 'table' && selectedTable) {
      setTables((prev) =>
        prev.map((t) =>
          t.id === selectedTable.id
            ? { ...t, is_occupied: false, status: 'available', active_order_id: null }
            : t
        )
      );
      setSelectedTable((prev) =>
        prev ? { ...prev, is_occupied: false, status: 'available', active_order_id: null } : prev
      );
    }
    setActiveOrder(null);
    setCustomerName('');
    setCustomerPhone('');
    setDeliveryAddress('');
  };

  // Menyu taomlarini saralash
  const activeCategory = categories.find((c) => c.id === selectedCatId) || categories[0];
  const allItems = useMemo(() => categories.flatMap((c) => c.items || []), [categories]);

  const displayedItems = useMemo(() => {
    if (searchItemQuery.trim()) {
      const q = searchItemQuery.toLowerCase();
      return allItems.filter(
        (i) =>
          (i.name && i.name.toLowerCase().includes(q)) ||
          (i.name_cyrillic && i.name_cyrillic.toLowerCase().includes(q))
      );
    }
    return activeCategory?.items && activeCategory.items.length > 0
      ? activeCategory.items
      : allItems;
  }, [searchItemQuery, allItems, activeCategory]);

  return (
    <div className="flex flex-col h-[calc(100vh-130px)] min-h-[600px] bg-slate-950 text-slate-100 rounded-3xl border border-slate-800 overflow-hidden shadow-2xl font-sans select-none">
      {/* 
        ── 1. Rejim almashtirgich (Faqat Admin / Kassir uchun) ──
        🟢 "Stolda" | 🛍️ "Olib ketish" | 🛵 "Dastavka"
        Ofitsiant (waiter) rolida bu qism BUTUNLAY YASHIRILADI!
      */}
      {showModeSwitch && canCheckout && (
        <div className="p-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-2 flex-1">
            <button
              type="button"
              id="mode-btn-table"
              onClick={() => {
                setOrderType('table');
                if (selectedTable) fetchTableActiveOrder(selectedTable);
              }}
              className={`flex-1 py-2 px-3 rounded-2xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 ${
                orderType === 'table'
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 ring-2 ring-emerald-400'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <UtensilsCrossed className="w-4 h-4 text-emerald-300" />
              <span>🟢 Stolda</span>
            </button>

            <button
              type="button"
              id="mode-btn-takeaway"
              onClick={() => {
                setOrderType('takeaway');
                setActiveOrder(null);
              }}
              className={`flex-1 py-2 px-3 rounded-2xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 ${
                orderType === 'takeaway'
                  ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/30 ring-2 ring-amber-400'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <ShoppingBag className="w-4 h-4 text-amber-300" />
              <span>🛍️ Olib ketish (Sobo)</span>
            </button>

            <button
              type="button"
              id="mode-btn-delivery"
              onClick={() => {
                setOrderType('delivery');
                setActiveOrder(null);
              }}
              className={`flex-1 py-2 px-3 rounded-2xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 ${
                orderType === 'delivery'
                  ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30 ring-2 ring-cyan-400'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <Bike className="w-4 h-4 text-cyan-300" />
              <span>🛵 Dastavka</span>
            </button>
          </div>

          <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-800 text-xs font-bold text-slate-400">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
            <span>{connected ? 'Kassa onlayn' : 'Oflayn'}</span>
          </div>
        </div>
      )}

      {/* 
        ── 2. Olib ketish va Dastavka Mijoz Ma'lumotlari Maydoni ──
      */}
      {showModeSwitch && canCheckout && orderType !== 'table' && (
        <div className="p-3 bg-slate-900/90 border-b border-slate-800 space-y-2 shrink-0 animate-fade-in">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-white flex items-center gap-1.5">
              {orderType === 'takeaway' ? (
                <>
                  <ShoppingBag className="w-4 h-4 text-amber-400" />
                  <span>Olib ketish (Takeaway) mijoz ma'lumotlari:</span>
                </>
              ) : (
                <>
                  <Bike className="w-4 h-4 text-cyan-400" />
                  <span>Yetkazib berish (Dastavka) mijoz ma'lumotlari:</span>
                </>
              )}
            </span>
            {activeOrder && (
              <button
                type="button"
                onClick={() => {
                  setActiveOrder(null);
                  setCustomerName('');
                  setCustomerPhone('');
                  setDeliveryAddress('');
                }}
                className="text-xs text-amber-400 hover:text-amber-300 underline font-bold"
              >
                + Yangi buyurtma
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
            <input
              type="text"
              placeholder="Mijoz ismi..."
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400 font-medium"
            />
            <input
              type="text"
              placeholder="+998 90 123 45 67"
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400 font-medium"
            />
            {orderType === 'delivery' && (
              <input
                type="text"
                placeholder="Yetkazib berish manzili..."
                value={deliveryAddress}
                onChange={(e) => setDeliveryAddress(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-cyan-400 font-medium col-span-1 sm:col-span-2 md:col-span-1"
              />
            )}
          </div>
        </div>
      )}

      {/* 
        ── 3. Asosiy Ekran: Chapda Savat, O'ngda Menyu ──
      */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* ── Chap Panel: Tanlangan Stol va Buyurtma Savati (OrderCart) ── */}
        <div className="w-full lg:w-[460px] xl:w-[490px] bg-slate-900 border-r border-slate-800 flex flex-col justify-between shrink-0 shadow-xl overflow-hidden">
          {/* Stol tanlash (faqat 'table' rejimida) */}
          {orderType === 'table' && (
            <div className="p-3 bg-slate-950 border-b border-slate-800 shrink-0 space-y-2">
              {/* Zonalarni tanlash */}
              <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
                <button
                  type="button"
                  onClick={() => setSelectedZone('')}
                  className={`px-3 py-1 rounded-xl text-xs font-black shrink-0 transition-all ${
                    selectedZone === ''
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-850 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  Barchasi ({tables.length})
                </button>
                {zoneNames.map((z) => (
                  <button
                    key={z}
                    type="button"
                    onClick={() => setSelectedZone(z)}
                    className={`px-3 py-1 rounded-xl text-xs font-black shrink-0 transition-all ${
                      selectedZone === z
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-850 text-slate-400 hover:text-white border border-slate-800'
                    }`}
                  >
                    {z}
                  </button>
                ))}
              </div>

              {/* Stollar qatori */}
              <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-1">
                {zoneTables.map((tbl) => {
                  const isSel = selectedTable?.id === tbl.id;
                  const isOcc = tbl.is_occupied || tbl.status === 'occupied';
                  return (
                    <button
                      key={tbl.id}
                      type="button"
                      id={`pos-table-btn-${tbl.number}`}
                      onClick={() => {
                        setSelectedTable(tbl);
                        fetchTableActiveOrder(tbl);
                      }}
                      className={`min-w-[46px] h-9 px-2 rounded-xl text-xs font-black transition-all shrink-0 flex items-center justify-center gap-1 ${
                        isSel
                          ? 'bg-emerald-500 text-slate-950 ring-2 ring-emerald-300 scale-105 shadow-md'
                          : isOcc
                          ? 'bg-red-500/25 text-red-300 border border-red-500/50'
                          : 'bg-slate-850 text-slate-300 border border-slate-700 hover:border-slate-500'
                      }`}
                    >
                      #{tbl.number}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Sarlavha: Joriy stol yoki Rejim nomi */}
          <div className="px-4 py-3 bg-slate-950/70 border-b border-slate-800 flex items-center justify-between shrink-0">
            <div>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-extrabold block">
                {orderType === 'table' ? 'Joriy stol:' : 'Buyurtma turi:'}
              </span>
              <h3 className="text-lg font-black text-white tracking-tight flex items-center gap-2">
                {orderType === 'table' ? (
                  <>
                    <span>{selectedTable?.room ? `${selectedTable.room} - ` : ''}Stol #{selectedTable?.number || 1}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-black uppercase ${
                      selectedTable?.status === 'occupied' ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                    }`}>
                      {selectedTable?.status === 'occupied' ? 'Band' : "Bo'sh"}
                    </span>
                  </>
                ) : orderType === 'takeaway' ? (
                  <span className="text-amber-400">🛍️ Olib ketish (Sobo)</span>
                ) : (
                  <span className="text-cyan-400">🛵 Dastavka (Yetkazib berish)</span>
                )}
              </h3>
            </div>

            {activeOrder && (
              <span className="px-2.5 py-1 rounded-xl bg-slate-800 border border-slate-700 text-xs font-mono font-bold text-amber-300">
                #{activeOrder.order_number || activeOrder.id}
              </span>
            )}
          </div>

          {/* 
            ── ORDER CART INTEGRATSIYASI ──
            Savat to'liq OrderCart komponenti orqali render qilinadi.
            pastida "To'landi va stolni bo'shatish" tugmasi faqat canCheckout bo'lganda chiqadi.
          */}
          <OrderCart
            order={activeOrder}
            table={selectedTable}
            orderType={orderType === 'table' ? 'dine_in' : orderType}
            customerInfo={{ name: customerName, phone: customerPhone, address: deliveryAddress }}
            orderLoading={orderLoading}
            sendingToKitchen={sendingToKitchen}
            printingBill={printingBill}
            canCheckout={canCheckout}
            kitchenNote={kitchenNote}
            kitchenSendSuccess={kitchenSendSuccess}
            onSendToKitchen={handleSendToKitchen}
            onPrintBill={handlePrintBill}
            onCheckout={() => setCheckoutModalOpen(true)}
            onUpdateQuantity={handleQtyChange}
            onRemoveItem={handleDeleteItem}
            onOpenWeightModal={(it) => {
              setWeightModalItem(it);
              setWeightValue(it.weight ? String(it.weight) : '');
              setPriceValue(
                it.manual_price !== null && it.manual_price !== undefined
                  ? String(Math.round(it.manual_price))
                  : it.total_price
                  ? String(Math.round(it.total_price))
                  : ''
              );
            }}
            onOpenSizeModal={(it) => {
              setSizeModalItem(it);
              setSizeValue(it.portion_size || '');
            }}
            onOpenKitchenNote={() => setKitchenNoteModalOpen(true)}
          />
        </div>

        {/* ── O'ng Panel: Kategoriyalar va Taomlar Gridi ── */}
        <div className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
          {/* Qidiruv va Kategoriyalar */}
          <div className="p-3.5 bg-slate-900/80 border-b border-slate-800 shrink-0 space-y-3">
            <div className="relative">
              <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchItemQuery}
                onChange={(e) => setSearchItemQuery(e.target.value)}
                placeholder="Menyudan taom qidirish..."
                className="w-full pl-11 pr-4 py-2.5 rounded-2xl bg-slate-900 border-2 border-slate-700/80 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500 font-medium"
              />
            </div>

            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
              {categories.map((cat) => {
                const active = cat.id === selectedCatId;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => {
                      setSelectedCatId(cat.id);
                      setSearchItemQuery('');
                    }}
                    className={`px-4 py-2 rounded-2xl text-xs sm:text-sm font-extrabold shrink-0 transition-all ${
                      active
                        ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 scale-102 ring-2 ring-emerald-400'
                        : 'bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
                    }`}
                  >
                    {cat.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Taomlar Gridi */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5">
            {displayedItems.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-2">
                <UtensilsCrossed className="w-12 h-12 opacity-30" />
                <p className="font-bold text-base text-white">Taomlar topilmadi</p>
                <p className="text-xs">Boshqa so'z bilan qidiring yoki kategoriyani almashtiring</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3.5 sm:gap-4">
                {displayedItems.map((item) => {
                  const isStop = item.is_stop_list || item.is_available === false;
                  return (
                    <div
                      key={item.id}
                      onClick={() => handleAddItem(item)}
                      className={`group relative rounded-3xl bg-slate-900 border-2 border-slate-800 p-3 flex flex-col justify-between hover:border-emerald-500 hover:bg-slate-850 transition-all shadow-lg cursor-pointer select-none active:scale-95 ${
                        isStop ? 'opacity-50 grayscale pointer-events-none' : ''
                      }`}
                    >
                      {/* Thumbnail */}
                      <div className="h-32 sm:h-36 w-full rounded-2xl bg-slate-950 overflow-hidden relative mb-2.5 flex items-center justify-center">
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={item.name}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                          />
                        ) : (
                          <div className="text-slate-600 flex flex-col items-center">
                            <ImageIcon className="w-8 h-8 mb-1 text-slate-500" />
                            <span className="text-xs font-bold">Taom</span>
                          </div>
                        )}

                        {item.is_weighted && (
                          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-lg bg-cyan-600/90 text-white font-black text-[10px] shadow">
                            ⚖️ Tarozida
                          </span>
                        )}

                        {isStop && (
                          <span className="absolute inset-x-2 bottom-2 text-center bg-red-600 text-white font-black text-xs py-1 rounded-xl shadow-lg">
                            Tugagan (Stop-list)
                          </span>
                        )}
                      </div>

                      {/* Title */}
                      <h4 className="text-sm sm:text-base font-extrabold text-white group-hover:text-emerald-300 transition-colors line-clamp-2 leading-tight">
                        {item.name}
                      </h4>

                      {/* Price Badge and Plus button */}
                      <div className="mt-3 flex items-center justify-between">
                        <span className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white font-black text-xs sm:text-sm shadow-md font-mono">
                          {Math.round(item.price || 0).toLocaleString('uz-UZ')} so'm
                        </span>
                        <span className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-base font-black group-hover:bg-emerald-500 group-hover:text-slate-950 transition-colors shadow-sm">
                          +
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 
        ── 4. Modallar: Weight, Size, Kitchen Note, Checkout, Thermal ──
      */}

      {/* Tarozidagi mahsulot narxini kiritish (Stress testi o'tadigan joy) */}
      {weightModalItem && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border-2 border-cyan-600/60 rounded-3xl max-w-md w-full p-5 shadow-2xl">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="text-base font-black text-white">💰 Narxini kiritish</h3>
                <p className="text-xs font-bold text-cyan-300 mt-0.5">
                  {weightModalItem.menu_item_name || weightModalItem.name || 'Taom'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setWeightModalItem(null)}
                className="p-1 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 mb-3">
              Ushbu taomning jami summasini so'mda yozing:
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-black text-white block mb-1">
                  Jami summa (so'm):
                </label>
                <input
                  type="text"
                  autoFocus
                  placeholder="204000"
                  value={priceValue}
                  onChange={(e) => setPriceValue(e.target.value)}
                  className="w-full px-4 py-3 rounded-2xl bg-slate-950 border-2 border-cyan-500 text-lg font-black text-cyan-300 focus:outline-none font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">
                  Og'irligi (ixtiyoriy, masalan 1.35 kg):
                </label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="1.35"
                  value={weightValue}
                  onChange={(e) => setWeightValue(e.target.value)}
                  className="w-full px-4 py-2 rounded-2xl bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setWeightModalItem(null)}
                  className="flex-1 py-3 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs"
                >
                  Bekor qilish
                </button>
                <button
                  type="button"
                  onClick={handleSaveWeight}
                  disabled={savingWeight}
                  className="flex-1 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-black text-xs shadow-lg shadow-cyan-600/30"
                >
                  {savingWeight ? 'Saqlanmoqda...' : 'Saqlash'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hajm / O'lcham oynasi */}
      {sizeModalItem && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-sm w-full p-5 shadow-2xl">
            <h3 className="text-sm font-black text-white mb-2">📏 Taom hajmi yoki o'lchami</h3>
            <p className="text-xs text-slate-400 mb-3">
              Masalan: 1.5 L, 1 L, 0.5 L, katta porsiya
            </p>
            <input
              type="text"
              autoFocus
              placeholder="1.5 L"
              value={sizeValue}
              onChange={(e) => setSizeValue(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-sm text-white focus:outline-none focus:border-emerald-500 mb-3"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setSizeModalItem(null)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs"
              >
                Bekor
              </button>
              <button
                type="button"
                onClick={handleSaveSize}
                disabled={savingSize}
                className="flex-1 py-2 rounded-xl bg-emerald-600 text-white font-black text-xs"
              >
                {savingSize ? 'Saqlanmoqda...' : 'Saqlash'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Oshxona izohi oynasi */}
      {kitchenNoteModalOpen && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl max-w-sm w-full p-5 shadow-2xl">
            <h3 className="text-sm font-black text-white mb-2">💬 Oshxona uchun umumiy izoh</h3>
            <textarea
              rows={3}
              autoFocus
              placeholder="Masalan: Achchiq bo'lmasin, piyozsiz..."
              value={kitchenNote}
              onChange={(e) => setKitchenNote(e.target.value)}
              className="w-full p-3 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-teal-500 mb-3"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setKitchenNoteModalOpen(false)}
                className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs"
              >
                Yopish
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (activeOrder) {
                    try {
                      await api.patch(`/orders/${activeOrder.id}`, { kitchen_note: kitchenNote });
                    } catch (e) {
                      console.error(e);
                    }
                  }
                  setKitchenNoteModalOpen(false);
                }}
                className="flex-1 py-2 rounded-xl bg-teal-600 text-white font-black text-xs"
              >
                Saqlash
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 
        CheckoutModal — POST /orders/{order_id}/checkout bajaradi
      */}
      {checkoutModalOpen && activeOrder && (
        <CheckoutModal
          isOpen={checkoutModalOpen}
          onClose={() => setCheckoutModalOpen(false)}
          order={activeOrder}
          tableLabel={
            orderType === 'table'
              ? `Stol #${selectedTable?.number || activeOrder.table_number || ''}`
              : orderType === 'takeaway'
              ? `🛍️ Olib ketish (${customerName || 'Mijoz'})`
              : `🛵 Dastavka (${customerName || 'Mijoz'})`
          }
          onPaid={handleCheckoutPaid}
        />
      )}

      {/* Thermal Chek ko'rish / chiqarish oynasi */}
      {receiptModalOpen && (
        <ThermalReceiptModal
          isOpen={receiptModalOpen}
          onClose={() => setReceiptModalOpen(false)}
          rawText={thermalReceiptText}
          title={receiptModalTitle}
        />
      )}
    </div>
  );
};

export default POSView;
