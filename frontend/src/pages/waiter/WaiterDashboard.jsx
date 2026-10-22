import React, { useState, useEffect, useRef } from 'react';
import api from '../../utils/api';
import { preloadImages, collectImageUrls } from '../../utils/preloadImages';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { ThermalReceiptModal } from '../../components/ThermalReceiptModal';
import CheckoutModal from '../../components/CheckoutModal';
import confetti from 'canvas-confetti';
import {
  UtensilsCrossed,
  Plus,
  Minus,
  Trash2,
  Send,
  CreditCard,
  MessageSquare,
  BellRing,
  Clock,
  CheckCircle2,
  Printer,
  Receipt,
  Search,
  User,
  Sparkles,
  RefreshCw,
  X,
  Volume2,
  VolumeX,
  TrendingUp,
  Image as ImageIcon,
  Flame,
  Check,
  ShoppingBag,
  Bike,
  ArrowRightLeft,
  ShoppingCart
} from 'lucide-react';

export const WaiterDashboard = ({ showModeSwitch: propShowModeSwitch, canCheckout: propCanCheckout } = {}) => {
  const { user, isAdmin, isCashier, canCheckout: authCanCheckout } = useAuth();
  const { addEventListener, playChime, connected } = useWebSocket();
  const restaurantId = user?.restaurant_id || 1;

  // Vakolatlarni qat'iy ajratish:
  // Ofitsiant (waiter) roli hech qachon rejim almashtira olmaydi va to'lov (checkout) qila olmaydi!
  const isPrivileged = user?.role === 'admin' || user?.role === 'cashier' || user?.role === 'developer';
  const canCheckout = propCanCheckout !== undefined ? propCanCheckout : isPrivileged;
  const showModeSwitch = propShowModeSwitch !== undefined ? propShowModeSwitch : isPrivileged;

  // Ekran: 'pos' (stollar zakazi) | 'calls' (Chaqiruvlar) | 'ready' (Oshxonadan tayyor)
  const [activeTab, setActiveTab] = useState('pos');
  // Rejim: 'table' (Stolda) | 'takeaway' (Olib ketish) | 'delivery' (Dastavka)
  // Ofitsiantda doimo 'table' bo'lib turadi va rejim almashtirgich ko'rinmaydi.
  const [orderType, setOrderType] = useState('table');
  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [deliveryAddress, setDeliveryAddress] = useState('');
  // Mobil ekranda Savat va Menyu orasida qulay o'tish holati ('menu' | 'cart')
  const [mobileTab, setMobileTab] = useState('menu');

  // Data states
  const [tables, setTables] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCatId, setSelectedCatId] = useState(null);
  const [searchItemQuery, setSearchItemQuery] = useState('');
  const [calls, setCalls] = useState([]);
  const [readyOrders, setReadyOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  // Active Table & Active Order (Left POS Panel)
  const [selectedTable, setSelectedTable] = useState(null);
  // Stol zonasi (Zal / Terrassa / Ko'cha / VIP). '' — hammasi.
  const [selectedZone, setSelectedZone] = useState('');
  const [activeOrder, setActiveOrder] = useState(null);
  const [orderLoading, setOrderLoading] = useState(false);

  // Tortiladigan taom (baliq, go'sht) og'irligini kiritish oynasi
  const [weightModalItem, setWeightModalItem] = useState(null);
  const [weightValue, setWeightValue] = useState('');
  // Tortiladigan taomning SUMMASI — ofitsiant kg emas, pulini yozadi
  const [priceValue, setPriceValue] = useState('');
  const [printingBill, setPrintingBill] = useState(false);
  const [savingWeight, setSavingWeight] = useState(false);

  // O'lchanadigan taom hajmi (1.5 L kola, 1.4 kg baliq) uchun oyna
  const [sizeModalItem, setSizeModalItem] = useState(null);
  const [sizeValue, setSizeValue] = useState('');
  const [savingSize, setSavingSize] = useState(false);

  // POS Order items in local state (for fast reactive UI before sync)
  const [kitchenNote, setKitchenNote] = useState('');
  const [kitchenNoteModalOpen, setKitchenNoteModalOpen] = useState(false);
  const [kitchenSendSuccess, setKitchenSendSuccess] = useState(false);
  const [sendingToKitchen, setSendingToKitchen] = useState(false);

  // Table transfer modal (Stolni ko'chirish — Aliposter 1.0.0.0 andozasi)
  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [transferLoading, setTransferLoading] = useState(false);

  // Bitta buyurtma uchun ketma-ket so'rovlar navbati va oxirgi so'rov id si
  const orderQueueRef = useRef(Promise.resolve());
  const latestRequestIdRef = useRef(0);
  // activeOrder yo'q holatida yangi buyurtma yaratilayotganda qulf (promise)
  const creatingOrderRef = useRef(null);

  const handleTransferTable = async (targetTableId) => {
    if (!selectedTable || !targetTableId) return;
    setTransferLoading(true);
    try {
      const res = await api.post(`/tables/${selectedTable.id}/transfer/${targetTableId}`);
      alert(res.message || "Buyurtma muvaffaqiyatli ko'chirildi! ✅");
      setTransferModalOpen(false);
      const dest = tables.find((t) => t.id === targetTableId);
      if (dest) setSelectedTable(dest);
      loadInitialData();
    } catch (err) {
      alert(err.message || "Ko'chirishda xatolik yuz berdi");
    } finally {
      setTransferLoading(false);
    }
  };

  // Checkout modal
  const [checkoutModalOpen, setCheckoutModalOpen] = useState(false);

  const handleCheckoutPaid = (res) => {
    setCheckoutModalOpen(false);
    if (res?.raw_text) {
      setThermalReceiptText(res.raw_text);
      setReceiptModalTitle(`Kassa Cheki #${res?.order_id || activeOrder?.id || ''}`);
      setReceiptModalOpen(true);
    }
    if (selectedTable) {
      setTables((prev) =>
        prev.map((t) =>
          t.id === selectedTable.id
            ? { ...t, is_occupied: false, status: 'available', active_order_id: null }
            : t
        )
      );
      setSelectedTable((prev) =>
        prev ? { ...prev, is_occupied: false, status: 'available', active_order_id: null } : null
      );
    }
    setActiveOrder(null);
    confetti({ particleCount: 50, spread: 60, origin: { y: 0.8 } });
    loadInitialData();
  };

  // Xprinter Thermal Receipt Modal
  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [thermalReceiptText, setThermalReceiptText] = useState('');
  const [receiptModalTitle, setReceiptModalTitle] = useState('Chek (Xprinter)');

  // Sound toggle
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Waiter KPI today
  const [waiterKpi, setWaiterKpi] = useState({ sales: 0, orders: 0, share: 0 });

  // ─── Stol zonalari (Zal / Terrassa / Ko'cha / VIP) ───────────
  // Ilgari hamma stollar bitta ro'yxatda aralashib yotardi.
  // Endi zonani bossangiz faqat o'sha zonaning stollari chiqadi.
  const zoneNames = React.useMemo(() => {
    const seen = [];
    (tables || []).forEach((t) => {
      const z = (t.room || '').trim();
      if (z && !seen.includes(z)) seen.push(z);
    });
    return seen.sort((a, b) => a.localeCompare(b, 'uz'));
  }, [tables]);

  const zoneTables = React.useMemo(() => {
    if (!selectedZone) return tables || [];
    return (tables || []).filter((t) => (t.room || '').trim() === selectedZone);
  }, [tables, selectedZone]);

  const zoneCount = (z) =>
    z ? (tables || []).filter((t) => (t.room || '').trim() === z).length : (tables || []).length;

  // Load initial data
  const loadInitialData = async () => {
    try {
      const [tablesData, menuData, callsData, ordersData] = await Promise.all([
        api.get(`/tables/?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/menu/full/${restaurantId}`).catch(() => []),
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).catch(() => []),
        api.get(`/orders/?restaurant_id=${restaurantId}`).catch(() => []),
      ]);

      setTables(tablesData || []);
      setCategories(menuData || []);
      // Menyu rasmlarini fonda oldindan yuklaymiz — ofitsiant
      // kategoriyani almashtirganda rasm kutib turmasin.
      preloadImages(collectImageUrls(menuData || []));
      if (menuData && menuData.length > 0 && !selectedCatId) {
        setSelectedCatId(menuData[0].id);
      }
      setCalls(callsData || []);

      const ready = (ordersData || []).filter((o) => o.status === 'ready');
      setReadyOrders(ready);

      // Select first table if none selected
      if (!selectedTable && tablesData && tablesData.length > 0) {
        setSelectedTable(tablesData[0]);
      }
    } catch (err) {
      console.error('Waiter load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, [restaurantId]);

  // Load active order for selected table
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
    if (selectedTable) {
      fetchTableActiveOrder(selectedTable);
    }
  }, [selectedTable?.id]);

  // Stollar ro'yxati yangilanganda tanlangan stolning holatini ham
  // yangilab turamiz (boshqa qurilmada stol yopilgan bo'lishi mumkin).
  useEffect(() => {
    if (!selectedTable) return;
    const fresh = tables.find((t) => t.id === selectedTable.id);
    if (fresh && fresh.status !== selectedTable.status) {
      setSelectedTable(fresh);
    }
  }, [tables]);

  // WebSocket real-time updates (Granular & Zero-overhead, avoids full-page network refetches)
  useEffect(() => {
    const unsub = addEventListener('*', (event) => {
      if (event.type === 'call_waiter') {
        if (soundEnabled && playChime) playChime('urgent');
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).then((data) => setCalls(data || [])).catch(() => {});
      } else if (event.type === 'order_ready') {
        if (soundEnabled && playChime) playChime('success');
        api.get(`/orders/?restaurant_id=${restaurantId}`)
          .then((data) => setReadyOrders((data || []).filter((o) => o.status === 'ready')))
          .catch(() => {});
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
        if (selectedTable && event.table_id === selectedTable.id) {
          setSelectedTable((prev) =>
            prev
              ? {
                  ...prev,
                  status: nextStatus || prev.status,
                  is_occupied: event.is_occupied !== undefined ? event.is_occupied : (nextStatus === 'occupied'),
                }
              : null
          );
          if (nextStatus === 'available') {
            setActiveOrder(null);
          }
        }
      } else if (event.type === 'order_paid') {
        setTables((prev) =>
          prev.map((t) =>
            t.id === event.table_id
              ? { ...t, status: 'available', is_occupied: false }
              : t
          )
        );
        if (selectedTable && event.table_id === selectedTable.id) {
          setSelectedTable((prev) => (prev ? { ...prev, status: 'available', is_occupied: false } : null));
          setActiveOrder(null);
        }
      } else if (event.type === 'order_updated' || event.type === 'new_order') {
        const isCancelled = event.order?.status === 'cancelled' || !event.order?.items || event.order?.items?.length === 0;
        if (event.table_id) {
          setTables((prev) =>
            prev.map((t) =>
              t.id === event.table_id ? { ...t, status: isCancelled ? 'available' : 'occupied', is_occupied: !isCancelled } : t
            )
          );
        }
        if (selectedTable && event.table_id === selectedTable.id) {
          if (event.order) {
            if (isCancelled) {
              setActiveOrder(null);
            } else {
              setActiveOrder(event.order);
            }
          } else {
            fetchTableActiveOrder(selectedTable);
          }
        }
      }
    });
    return () => unsub();
  }, [addEventListener, selectedTable, soundEnabled, playChime, restaurantId]);

  // Tortiladigan taom qo'shilsa — og'irlik oynasini darhol ochamiz.
  // Ofitsiant baliqni tarozida tortib, aniq og'irligini kiritadi.
  const openWeightModalIfNeeded = (order, menuItemId) => {
    const line = (order?.items || [])
      .filter(
        (i) =>
          i.menu_item_id === menuItemId &&
          i.is_weighted &&
          !i.weight &&
          (i.manual_price === null || i.manual_price === undefined)
      )
      .pop();
    if (line) {
      setWeightModalItem(line);
      setWeightValue('');
      setPriceValue('');
    }
  };

  // Tortiladigan taomning narxi kiritilganmi?
  // Summa yozilgan bo'lsa yetarli — kg kiritish SHART EMAS.
  const isPriced = (it) =>
    (it.manual_price !== null && it.manual_price !== undefined) || it.weight > 0;

  // Add Item to Table (Click on food card)
  // Add Item to Table (Click on food card) — Tezkor va Optimistik
  const handleAddItem = async (menuItem) => {
    if (menuItem.is_stop_list || menuItem.is_available === false) {
      alert(`"${menuItem.name}" hozirda stop-listda (tugagan)`);
      return;
    }

    if (!selectedTable && orderType === 'table') {
      alert('Iltimos, avval stolni tanlang');
      return;
    }

    try {
      let currentOrd = activeOrder;

      // 3. activeOrder yo'q holatida yangi buyurtma ochilayotganda creatingOrderRef qulfi:
      // ikkinchi bosish birinchi javob kelguncha kutsin, keyin add-items yo'liga o'tsin.
      if (!currentOrd && creatingOrderRef.current) {
        try {
          currentOrd = await creatingOrderRef.current;
        } catch (_) {
          currentOrd = null;
        }
      }

      if (!currentOrd) {
        const createPromise = (async () => {
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
              payload.delivery_address = deliveryAddress.trim() || "Manzil";
            }
          }
          return await api.post('/orders/waiter-create', payload);
        })();

        creatingOrderRef.current = createPromise;
        let newOrd;
        try {
          newOrd = await createPromise;
        } finally {
          creatingOrderRef.current = null;
        }

        if (newOrd) {
          setActiveOrder(newOrd);
          openWeightModalIfNeeded(newOrd, menuItem.id);
          if (orderType === 'table') {
            setTables((prev) =>
              prev.map((t) => (t.id === selectedTable?.id ? { ...t, status: 'occupied' } : t))
            );
            setSelectedTable((prev) => (prev ? { ...prev, status: 'occupied' } : prev));
          }
        }
        return;
      }

      // Mavjud buyurtmaga taom qo'shish
      const orderId = currentOrd.id;
      const existingItem = (currentOrd.items || []).find(
        (i) => Number(i.menu_item_id) === Number(menuItem.id) && !i.is_weighted
      );

      if (existingItem) {
        // 1. Optimistik yangilanish
        const targetQty = existingItem.quantity + 1;
        setActiveOrder((prev) => {
          if (!prev) return prev;
          const updatedItems = (prev.items || []).map((it) =>
            it.id === existingItem.id
              ? {
                  ...it,
                  quantity: targetQty,
                  total_price: (it.unit_price || menuItem.price) * targetQty,
                }
              : it
          );
          const sub = updatedItems.reduce((acc, it) => acc + (it.total_price || 0), 0);
          return {
            ...prev,
            items: updatedItems,
            subtotal: sub,
            total: sub + (prev.service_fee_amount || 0) - (prev.discount || 0),
          };
        });

        // 2. Yangi PATCH delta endpointini navbat bilan chaqirish
        const reqId = ++latestRequestIdRef.current;
        orderQueueRef.current = orderQueueRef.current
          .catch(() => {})
          .then(async () => {
            const updated = await api.patch(
              `/orders/${orderId}/items/${existingItem.id}/delta`,
              { delta: 1 }
            );
            if (reqId === latestRequestIdRef.current && updated) {
              setActiveOrder(updated);
            }
            return updated;
          });
        await orderQueueRef.current;
      } else {
        // Yangi taom qo'shish
        const reqId = ++latestRequestIdRef.current;
        orderQueueRef.current = orderQueueRef.current
          .catch(() => {})
          .then(async () => {
            const updated = await api.post(`/orders/${orderId}/add-items`, {
              items: [{ menu_item_id: menuItem.id, quantity: 1 }],
              send_to_kitchen_immediately: false,
            });
            if (reqId === latestRequestIdRef.current && updated) {
              setActiveOrder(updated);
              openWeightModalIfNeeded(updated, menuItem.id);
            }
            return updated;
          });
        await orderQueueRef.current;
      }
    } catch (err) {
      console.warn("Taom qo'shishda xatolik:", err);
      const errMsg = err?.response?.data?.detail || err?.message || "Taom qo'shishda xatolik yuz berdi";
      alert(errMsg);
      if (selectedTable) fetchTableActiveOrder(selectedTable);
    }
  };

  // Change quantity [- 1 +] — Optimistik va sezgir (PATCH /delta orqali)
  const handleQtyChange = async (item, delta) => {
    if (!activeOrder || !item || delta === 0) return;
    const newQty = item.quantity + delta;

    // 1. Darhol ekranni yangilaymiz (0ms kechikish)
    setActiveOrder((prev) => {
      if (!prev) return prev;
      if (newQty <= 0) {
        const filtered = (prev.items || []).filter((it) => it.id !== item.id);
        if (filtered.length === 0) return null;
        const sub = filtered.reduce((acc, it) => acc + (it.total_price || 0), 0);
        return {
          ...prev,
          items: filtered,
          subtotal: sub,
          total: sub + (prev.service_fee_amount || 0) - (prev.discount || 0),
        };
      }
      const updatedItems = (prev.items || []).map((it) =>
        it.id === item.id
          ? {
              ...it,
              quantity: newQty,
              total_price: (it.unit_price || 0) * newQty,
            }
          : it
      );
      const sub = updatedItems.reduce((acc, it) => acc + (it.total_price || 0), 0);
      return {
        ...prev,
        items: updatedItems,
        subtotal: sub,
        total: sub + (prev.service_fee_amount || 0) - (prev.discount || 0),
      };
    });

    try {
      const orderId = activeOrder.id;
      const reqId = ++latestRequestIdRef.current;
      orderQueueRef.current = orderQueueRef.current
        .catch(() => {})
        .then(async () => {
          const updated = await api.patch(
            `/orders/${orderId}/items/${item.id}/delta`,
            { delta }
          );
          if (reqId === latestRequestIdRef.current && updated) {
            if (updated.status === 'cancelled' || !updated.items || updated.items.length === 0) {
              setActiveOrder(null);
            } else {
              setActiveOrder(updated);
            }
          }
          return updated;
        });
      await orderQueueRef.current;
    } catch (err) {
      console.warn('Soni yangilashda xatolik:', err);
      const errMsg = err?.response?.data?.detail || err?.message || "Taom sonini o'zgartirishda xatolik yuz berdi";
      alert(errMsg);
      if (selectedTable) fetchTableActiveOrder(selectedTable);
    }
  };

  // Delete item from order — Darhol ekrandan olib tashlaydi
  const handleDeleteItem = async (itemId) => {
    if (!activeOrder) return;
    const orderId = activeOrder.id;

    // 1. Darhol ekrandan o'chiramiz (0ms javob)
    setActiveOrder((prev) => {
      if (!prev) return null;
      const filtered = (prev.items || []).filter((i) => i.id !== itemId);
      if (filtered.length === 0) {
        return null; // Savatda taom qolmasa butunlay yopamiz
      }
      const sub = filtered.reduce((acc, it) => acc + (it.total_price || 0), 0);
      return {
        ...prev,
        items: filtered,
        subtotal: sub,
        total: sub + (prev.service_fee_amount || 0) - (prev.discount || 0),
      };
    });

    try {
      const reqId = ++latestRequestIdRef.current;
      orderQueueRef.current = orderQueueRef.current
        .catch(() => {})
        .then(async () => {
          const updated = await api.delete(`/orders/${orderId}/items/${itemId}`);
          if (reqId === latestRequestIdRef.current && updated) {
            if (updated.status === 'cancelled' || !updated.items || updated.items.length === 0) {
              setActiveOrder(null);
            } else {
              const cleanItems = (updated.items || []).filter((i) => i.id !== itemId);
              if (cleanItems.length === 0) {
                setActiveOrder(null);
              } else {
                setActiveOrder({
                  ...updated,
                  items: cleanItems,
                });
              }
            }
          }
          return updated;
        });
      await orderQueueRef.current;
    } catch (err) {
      const errMsg = err?.response?.data?.detail || err?.message || "Taomni o'chirishda xatolik yuz berdi";
      if (typeof errMsg === 'string' && errMsg.toLowerCase().includes('topilmadi')) {
        return;
      }
      console.warn("Taomni o'chirishda xatolik:", err);
      alert(errMsg);
      if (selectedTable) fetchTableActiveOrder(selectedTable);
    }
  };

  // Tortiladigan taom narxini saqlash.
  // ASOSIY yo'l — ofitsiant SUMMANI yozadi (baliqning kg i emas, puli).
  // Og'irlik ixtiyoriy: yozilsa chekda va oshxona begunogida ko'rinadi.
  const handleSaveWeight = async () => {
    if (!activeOrder || !weightModalItem) return;
    const w = parseFloat(String(weightValue).replace(',', '.'));
    const pr = parseFloat(String(priceValue).replace(/[^0-9.,]/g, '').replace(',', '.'));
    const hasPrice = !isNaN(pr) && pr >= 0 && String(priceValue).trim() !== '';
    const hasWeight = !isNaN(w) && w > 0;
    if (!hasPrice && !hasWeight) {
      alert('Summani kiriting (masalan: 204000)');
      return;
    }
    setSavingWeight(true);
    try {
      const body = {};
      if (hasPrice) body.price = Math.round(pr);
      if (hasWeight) body.weight = w;
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

  // O'lchanadigan taom hajmini saqlash ("1.5 L", "1.4 kg")
  const handleSaveSize = async (value) => {
    if (!activeOrder || !sizeModalItem) return;
    setSavingSize(true);
    try {
      const updated = await api.patch(
        `/orders/${activeOrder.id}/items/${sizeModalItem.id}/size`,
        { portion_size: (value ?? sizeValue).trim() || null }
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

  // Save notes
  const handleSaveNotes = async () => {
    if (!activeOrder) return;
    try {
      const updated = await api.patch(`/orders/${activeOrder.id}/notes`, {
        kitchen_note: kitchenNote,
      });
      setActiveOrder(updated);
      setKitchenNoteModalOpen(false);
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // Action: "🔥 Buyurtmani tasdiqlash" (Send to kitchen -> auto-print on 1- & 2-kitchen printers)
  //
  // MUHIM: oshxonaga faqat YANGI qo'shilgan taomlar chiqadi. Ofitsiant
  // 1 somsa yuborgandan keyin yana 1 somsa qo'shsa, oshxonada "1 somsa"
  // chiqadi — "2 somsa" emas. Tugma bo'sh bosilsa hech narsa chiqmaydi;
  // begunok printerdan chiqmagan bo'lsa "qayta chiqarish" so'raladi.
  const handleSendToKitchen = async (reprint = false) => {
    if (!activeOrder || !activeOrder.items || activeOrder.items.length === 0) {
      alert("Buyurtmada taomlar yo'q! Avval o'ng tomondan taom qo'shing.");
      return;
    }
    setSendingToKitchen(true);
    try {
      const res = await api.post(
        `/orders/${activeOrder.id}/send-to-kitchen${reprint ? '?reprint=true' : ''}`,
        {}
      );

      // Yangi taom yo'q: oshxonaga qayta-qayta bir xil begunok chiqib
      // ketmasligi uchun hech narsa chop etilmadi.
      if (res.nothing_new) {
        const yes = window.confirm(
          "Yangi taom yo'q — barchasi oshxonaga allaqachon yuborilgan.\n\n" +
          'Begunok printerdan chiqmaganmi? "OK" bosing — butun buyurtma ' +
          'TAKROR begunok sifatida qayta chiqadi.'
        );
        setSendingToKitchen(false);
        if (yes) await handleSendToKitchen(true);
        return;
      }

      // Printerga chiqmagan begunoklar bormi?
      const tickets = res.tickets || [];
      const failed = tickets.filter((t) => !t.printed);

      if (res.raw_text) {
        setThermalReceiptText(res.raw_text);
        setReceiptModalTitle(
          `Oshxona Begunogi (${selectedTable?.room || 'Zal'} N#${selectedTable?.number || ''})`
        );
        // Printerdan chiqmagan bo'lsa -- chekni EKRANDA ko'rsatamiz, aks holda
        // ofitsiant begunok chiqmaganini bilmay qoladi.
        if (failed.length > 0) {
          setReceiptModalOpen(true);
          const sabab = failed[0].print_error || 'printer topilmadi';
          alert(
            `Begunok printerdan chiqmadi (${failed.map((t) => t.printer_name).join(', ')}).\n` +
            `Sabab: ${sabab}\n\n` +
            `Chek ekranda ochildi - "Chop etish" tugmasi orqali chiqarishingiz mumkin.`
          );
        }
      }
      setKitchenSendSuccess(true);
      setTimeout(() => setKitchenSendSuccess(false), 4000);
      confetti({ particleCount: 75, spread: 70, origin: { y: 0.7 } });
      if (soundEnabled && playChime) playChime('success');
      await fetchTableActiveOrder(selectedTable);
    } catch (err) {
      alert(err.message || 'Oshxonaga yuborishda xatolik yuz berdi');
    } finally {
      setSendingToKitchen(false);
    }
  };


  // Admin zakas olgandan keyin darhol mijoz chekini chiqarish.
  // Ofitsiantda bu tugma yo'q — chekni kassa (admin) chiqaradi.
  const handlePrintBill = async () => {
    if (!selectedTable) {
      alert('Avval stolni tanlang');
      return;
    }
    if (!activeOrder || !(activeOrder.items || []).length) {
      alert("Bu stolda hali zakas yo'q");
      return;
    }
    setPrintingBill(true);
    try {
      const res = await api.post(`/tables/${selectedTable.id}/print-bill`, {});
      if (res.raw_text) {
        setThermalReceiptText(res.raw_text);
        setReceiptModalTitle(
          `Mijoz cheki (${selectedTable.room || 'Zal'} N#${selectedTable.number})`
        );
      }
      // Server `success` maydonida printerdan chiqdi-chiqmaganini aytadi.
      if (res.success === false) {
        setReceiptModalOpen(true);
        alert(
          `${res.message || 'Chek printerdan chiqmadi'}\n\n` +
          `Chek ekranda ochildi — "Chop etish" tugmasi orqali chiqarishingiz mumkin.`
        );
      } else {
        alert(`✅ Chek ${res.printer_name || 'kassa printeri'} ga yuborildi`);
      }
    } catch (err) {
      alert(err.message || 'Chek chiqarishda xatolik');
    } finally {
      setPrintingBill(false);
    }
  };

  // Action: "Bordim" (Resolve waiter call)
  const handleResolveCall = async (callId) => {
    try {
      await api.post(`/orders/calls/${callId}/resolve`, {});
      setCalls((prev) => prev.filter((c) => c.id !== callId));
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // Action: "Yetkazib berdim" (Delivered)
  const handleDeliverOrder = async (orderId) => {
    try {
      await api.patch(`/orders/${orderId}/deliver`, {});
      setReadyOrders((prev) => prev.filter((o) => o.id !== orderId));
      confetti({ particleCount: 50, spread: 50 });
    } catch (err) {
      alert(err.message || 'Xatolik');
    }
  };

  // Filter items in right panel with reliable fallback
  const activeCategory = categories.find((c) => c.id === selectedCatId) || categories[0];
  const allItems = categories.flatMap((c) => c.items || []);
  const displayedItems = searchItemQuery.trim()
    ? allItems.filter(
      (i) =>
        (i.name && i.name.toLowerCase().includes(searchItemQuery.toLowerCase())) ||
        (i.name_cyrillic && i.name_cyrillic.toLowerCase().includes(searchItemQuery.toLowerCase()))
    )
    : activeCategory?.items && activeCategory.items.length > 0
      ? activeCategory.items
      : allItems;

  return (
    <div className="h-[calc(100vh-64px)] max-h-[calc(100vh-64px)] overflow-hidden bg-slate-950 text-slate-100 flex flex-col font-sans select-none">
      {/* ─── Yuqori panel ──────────────────────────────────────────── */}
      <header className="h-14 bg-emerald-950/80 border-b border-emerald-800/60 px-4 flex items-center justify-between shadow-lg backdrop-blur-md shrink-0">
        <div className="flex items-center gap-3">
          {/* "Stollar" — chaqiruvlar yoki tayyor taomlardan POS ekraniga
              qaytish tugmasi. Olib tashlangan: begona nom va bu
              restoranda ishlatilmaydigan "С собой" / "Доставка". */}
          <button
            onClick={() => {
              setActiveTab('pos');
              setOrderType('table');
            }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-black transition-all active:scale-95 ${activeTab === 'pos'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'bg-black/40 border border-emerald-800/40 text-slate-300 hover:text-white'
              }`}
          >
            <UtensilsCrossed className="w-4 h-4" />
            <span>Stollar</span>
          </button>
        </div>

        {/* Right Info: Chaqiruvlar badgi, Waiter Name, Sound toggle */}
        <div className="flex items-center gap-3">
          {/* Chaqiruvlar Tab Button */}
          <button
            onClick={() => setActiveTab('calls')}
            className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${activeTab === 'calls'
                ? 'bg-amber-500 text-slate-950'
                : 'bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-850'
              }`}
          >
            <BellRing className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Chaqiruvlar</span>
            {calls.length > 0 && (
              <span className="w-5 h-5 rounded-full bg-red-600 text-white text-[10px] font-black flex items-center justify-center animate-pulse">
                {calls.length}
              </span>
            )}
          </button>

          {/* Tayyor taomlar Tab Button */}
          <button
            onClick={() => setActiveTab('ready')}
            className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${activeTab === 'ready'
                ? 'bg-emerald-500 text-slate-950'
                : 'bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-850'
              }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Tayyor</span>
            {readyOrders.length > 0 && (
              <span className="w-5 h-5 rounded-full bg-emerald-600 text-white text-[10px] font-black flex items-center justify-center">
                {readyOrders.length}
              </span>
            )}
          </button>

          {/* Sound toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className="p-2 rounded-xl bg-black/30 border border-slate-800 text-slate-400 hover:text-white"
            title="Ovozli signallar"
          >
            {soundEnabled ? <Volume2 className="w-4 h-4 text-emerald-400" /> : <VolumeX className="w-4 h-4" />}
          </button>

          {/* Waiter Info */}
          <div className="flex items-center gap-2 pl-2 border-l border-emerald-800/60">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">
              <User className="w-4 h-4" />
            </div>
            <div className="hidden md:block text-left">
              <p className="text-xs font-bold text-white leading-tight">
                {user?.full_name || user?.username || 'Ofitsiant'}
              </p>
              {/* Haqiqiy holat: WebSocket ulanishi bor bo'lsa "Faol" */}
              <p className={`text-[10px] font-semibold ${connected ? 'text-emerald-400/90' : 'text-red-400/90'}`}>
                {connected ? '● Faol' : '○ Nofaol (aloqa yo\'q)'}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* ─── Main Content Tabs ───────────────────────────────────────── */}
      {activeTab === 'calls' ? (
        /* ── Chaqiruvlar Royxati ── */
        <div className="max-w-4xl mx-auto p-6 flex-1 w-full">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <BellRing className="w-5 h-5 text-amber-400" />
              <span>Mijozlardan faol chaqiruvlar ({calls.length})</span>
            </h2>
            <button
              onClick={() => setActiveTab('pos')}
              className="text-xs text-slate-400 hover:text-white underline"
            >
              ← POS Ekraniga qaytish
            </button>
          </div>

          {calls.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 text-slate-400">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <p className="font-bold text-white text-base">Hozircha yangi chaqiruvlar yo'q</p>
              <p className="text-xs mt-1">Barcha stollarga xizmat ko'rsatilgan</p>
            </div>
          ) : (
            <div className="grid gap-3">
              {calls.map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-2xl bg-slate-900 border border-amber-500/30 flex items-center justify-between shadow-lg animate-in slide-in-from-top-2"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center font-black text-sm">
                      #{c.table_number}
                    </div>
                    <div>
                      <h4 className="font-bold text-white text-sm">
                        Stol #{c.table_number} {c.room ? `(${c.room})` : ''}
                      </h4>
                      <p className="text-xs text-amber-300/90 mt-0.5 font-medium">
                        💬 {c.note || 'Ofitsiant yordami so\'ralmoqda'}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleResolveCall(c.id)}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-all active:scale-95"
                  >
                    Bordim (Yakunlash)
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : activeTab === 'ready' ? (
        /* ── Oshxonadan tayyor taomlar ── */
        <div className="max-w-4xl mx-auto p-6 flex-1 w-full">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Oshxonadan tayyor bo'lgan buyurtmalar ({readyOrders.length})</span>
            </h2>
            <button
              onClick={() => setActiveTab('pos')}
              className="text-xs text-slate-400 hover:text-white underline"
            >
              ← POS Ekraniga qaytish
            </button>
          </div>

          {readyOrders.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 text-slate-400">
              <p className="font-bold text-white text-base">Hozirda oshxonada tayyor buyurtma yo'q</p>
            </div>
          ) : (
            <div className="grid gap-3">
              {readyOrders.map((ord) => (
                <div
                  key={ord.id}
                  className="p-5 rounded-2xl bg-slate-900 border border-emerald-500/40 flex items-center justify-between shadow-xl"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-400 font-mono text-xs font-black">
                        {ord.order_number}
                      </span>
                      <span className="text-sm font-extrabold text-white">
                        Stol #{ord.table_number || ord.table_id} {ord.room ? `(${ord.room})` : ''}
                      </span>
                    </div>
                    <div className="mt-2 text-xs text-slate-300">
                      {(ord.items || []).map((it) => (
                        <span key={it.id} className="mr-3 font-medium">
                          {it.menu_item_name || 'Taom'} x{it.quantity}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeliverOrder(ord.id)}
                    className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-lg shadow-emerald-500/30 transition-all active:scale-95 flex items-center gap-2"
                  >
                    <Check className="w-4 h-4 stroke-[3]" />
                    <span>Yetkazib berdim</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* ── POS EKRANI (stol zakazi) ──────────────────────────────── */
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* ── Mobil Ko'rinish uchun Tablar (Faqat mobil ekranda chiqadi) ── */}
          <div className="lg:hidden flex items-center gap-1.5 p-2 bg-slate-950 border-b border-slate-800 shrink-0">
            <button
              type="button"
              onClick={() => setMobileTab('menu')}
              className={`flex-1 py-2 px-3 rounded-xl font-black text-xs flex items-center justify-center gap-1.5 transition-all ${
                mobileTab === 'menu'
                  ? 'bg-emerald-600 text-white shadow-md ring-1 ring-emerald-400'
                  : 'bg-slate-900 text-slate-400 border border-slate-800'
              }`}
            >
              <UtensilsCrossed className="w-4 h-4" />
              <span>Taomlar ({displayedItems.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setMobileTab('cart')}
              className={`flex-1 py-2 px-3 rounded-xl font-black text-xs flex items-center justify-center gap-1.5 transition-all ${
                mobileTab === 'cart'
                  ? 'bg-emerald-600 text-white shadow-md ring-1 ring-emerald-400'
                  : 'bg-slate-900 text-slate-400 border border-slate-800'
              }`}
            >
              <ShoppingCart className="w-4 h-4" />
              <span>Savat {activeOrder?.items?.length ? `(${activeOrder.items.length})` : ''}</span>
            </button>
          </div>

          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
            {/* ── Chap Panel: Tanlangan Stol va Zakaz (Katta va qulay shriftlar) ─────────── */}
            <div
              className={`w-full lg:w-[460px] xl:w-[480px] bg-slate-900/95 border-r border-slate-800 flex flex-col shrink-0 shadow-2xl h-full overflow-hidden min-h-0 ${
                mobileTab === 'cart' ? 'flex' : 'hidden lg:flex'
              }`}
            >
            {/* 
              Rejim almashtirgich (Faqat Admin / Kassir uchun):
              🟢 "Stolda" | 🛍️ "Olib ketish" | 🛵 "Dastavka"
              Ofitsiantda (role === 'waiter') bu rejimlar BUTUNLAY YASHIRILADI.
            */}
            {showModeSwitch && canCheckout && (
              <div className="p-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setOrderType('table');
                    if (selectedTable) fetchTableActiveOrder(selectedTable);
                  }}
                  className={`flex-1 py-1.5 px-2.5 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-1.5 ${orderType === 'table'
                      ? 'bg-emerald-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                    }`}
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  <span>🟢 Stolda</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setOrderType('takeaway');
                    setActiveOrder(null);
                  }}
                  className={`flex-1 py-1.5 px-2.5 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-1.5 ${orderType === 'takeaway'
                      ? 'bg-amber-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                    }`}
                >
                  <ShoppingBag className="w-3.5 h-3.5 text-amber-300" />
                  <span>🛍️ Olib ketish</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setOrderType('delivery');
                    setActiveOrder(null);
                  }}
                  className={`flex-1 py-1.5 px-2.5 rounded-xl text-xs font-black transition-all flex items-center justify-center gap-1.5 ${orderType === 'delivery'
                      ? 'bg-cyan-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                    }`}
                >
                  <Bike className="w-3.5 h-3.5 text-cyan-300" />
                  <span>🛵 Dastavka</span>
                </button>
              </div>
            )}

            {/* Olib ketish / Dastavka mijoz maydonlari */}
            {showModeSwitch && canCheckout && orderType !== 'table' && (
              <div className="p-3 bg-slate-950/90 border-b border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-white flex items-center gap-1.5">
                    {orderType === 'takeaway' ? (
                      <>
                        <ShoppingBag className="w-3.5 h-3.5 text-amber-400" />
                        <span>Olib ketish mijoz rekvizitlari:</span>
                      </>
                    ) : (
                      <>
                        <Bike className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Yetkazib berish (Dastavka) rekvizitlari:</span>
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
                      className="text-[10px] text-amber-400 underline font-bold"
                    >
                      + Yangi zakaz
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Mijoz ismi"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400"
                  />
                  <input
                    type="text"
                    placeholder="+998 90 123 45 67"
                    value={customerPhone}
                    onChange={(e) => setCustomerPhone(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-400"
                  />
                </div>

                {orderType === 'delivery' && (
                  <input
                    type="text"
                    placeholder="Yetkazib berish manzili (ko'cha, uy...)"
                    value={deliveryAddress}
                    onChange={(e) => setDeliveryAddress(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-cyan-400"
                  />
                )}
              </div>
            )}

            {/* Table Header Bar */}
            <div className="px-3.5 py-2 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between shrink-0">
              <div>
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-bold block">
                  Joriy stol:
                </span>
                <div className="flex items-center gap-2 mt-0.5">
                  <h2 className="text-lg sm:text-xl font-black text-white tracking-tight">
                    {selectedTable?.room ? `${selectedTable.room} - ` : ''}
                    {selectedTable?.name || `Stol #${selectedTable?.number || 1}`}
                  </h2>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-black uppercase tracking-wider ${selectedTable?.status === 'occupied'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      }`}
                  >
                    {selectedTable?.status === 'occupied' ? 'Band' : "Bo'sh"}
                  </span>
                </div>
              </div>

              {/* Stolni ko'chirish va stollarni tanlash */}
              <div className="flex items-center gap-2">
                {activeOrder && selectedTable && (
                  <button
                    type="button"
                    onClick={() => setTransferModalOpen(true)}
                    className="px-2.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-black text-amber-300 border border-slate-700 hover:border-amber-400 transition-all active:scale-95 flex items-center gap-1.5 shadow-sm"
                    title="Stolni ko'chirish (Transfer)"
                  >
                    <ArrowRightLeft className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Ko'chirish</span>
                  </button>
                )}

                <select
                  value={selectedTable?.id || ''}
                  onChange={(e) => {
                    const t = tables.find((x) => x.id === parseInt(e.target.value));
                    if (t) setSelectedTable(t);
                  }}
                  className="bg-slate-800 border-2 border-slate-700 hover:border-emerald-500 text-sm font-bold text-white rounded-xl px-3 py-2 focus:outline-none focus:border-emerald-500 shadow-sm"
                >
                  {zoneTables.map((tbl) => (
                    <option key={tbl.id} value={tbl.id}>
                      {tbl.room ? `${tbl.room} ` : ''}#{tbl.number} (
                      {tbl.status === 'occupied' ? 'Band' : 'Bo\'sh'})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* ─── Zonalar va stollar ─────────────────────────────
                Ilgari hamma stollar bitta ro'yxatda aralashib yotardi.
                Endi "Terrassa" ni bossangiz faqat terrassadagi stollar
                chiqadi. */}
            {zoneNames.length > 0 && (
              <div className="px-3 py-1.5 bg-slate-950/60 border-b border-slate-800 shrink-0">
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                  <button
                    onClick={() => setSelectedZone('')}
                    className={`shrink-0 px-2.5 py-1 rounded-xl text-xs font-black transition-all active:scale-95 ${selectedZone === ''
                        ? 'bg-emerald-500 text-slate-950 shadow-md'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                      }`}
                  >
                    Hammasi {zoneCount('')}
                  </button>
                  {zoneNames.map((z) => (
                    <button
                      key={z}
                      onClick={() => setSelectedZone(z)}
                      className={`shrink-0 px-2.5 py-1 rounded-xl text-xs font-black transition-all active:scale-95 ${selectedZone === z
                          ? 'bg-emerald-500 text-slate-950 shadow-md'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                        }`}
                    >
                      {z} {zoneCount(z)}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 pt-0.5">
                  {zoneTables.length === 0 ? (
                    <span className="text-[11px] font-bold text-slate-500 py-1">
                      Bu zonada stol yo'q
                    </span>
                  ) : (
                    zoneTables.map((tbl) => {
                      const active = selectedTable?.id === tbl.id;
                      const busy = tbl.status === 'occupied';
                      return (
                        <button
                          key={tbl.id}
                          onClick={() => setSelectedTable(tbl)}
                          title={`${tbl.room || ''} #${tbl.number}`}
                          className={`shrink-0 min-w-[48px] px-2 py-1 rounded-xl text-xs sm:text-sm font-black border-2 transition-all active:scale-95 ${active
                              ? 'bg-white text-slate-950 border-white shadow-lg'
                              : busy
                                ? 'bg-red-500/20 text-red-300 border-red-500/50 hover:border-red-400'
                                : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 hover:border-emerald-400'
                            }`}
                        >
                          #{tbl.number}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* Mobil uchun Menyuga qaytish / Taom qo'shish tugmasi */}
            <div className="lg:hidden px-3 py-1.5 bg-slate-950/90 border-b border-slate-800 shrink-0">
              <button
                type="button"
                onClick={() => setMobileTab('menu')}
                className="w-full py-2 px-3 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 font-bold text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>+ Yana taom qo'shish (Menyuga o'tish)</span>
              </button>
            </div>

            {/* Active Items Table: flex-1 to'liq balandlik, hech qanday tor max-h cheklovisiz */}
            <div className="flex-1 overflow-y-auto custom-scrollbar overflow-x-hidden min-h-0">
              <div className="grid grid-cols-12 text-xs sm:text-sm font-black text-slate-300 bg-slate-950/70 px-3 sm:px-4 py-2.5 border-b border-slate-800 uppercase tracking-wider">
                <span className="col-span-5">Taom nomi</span>
                <span className="col-span-2 text-right">Narxi</span>
                <span className="col-span-2 text-center">Soni</span>
                <span className="col-span-2 text-right">Jami</span>
                <span className="col-span-1 text-center"></span>
              </div>

              {orderLoading ? (
                <div className="p-12 text-center text-sm font-bold text-slate-400">Yuklanmoqda...</div>
              ) : !activeOrder || !activeOrder.items || activeOrder.items.length === 0 ? (
                <div className="p-12 text-center text-slate-400 space-y-1">
                  <p className="font-extrabold text-white text-base">Ushbu stolda hali zakaz yo'q</p>
                  <p className="text-xs text-slate-400">O'ng tomondagi menyudan taomlarni bosing</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-800/60">
                  {activeOrder.items.map((it) => (
                    <div
                      key={it.id}
                      className="grid grid-cols-12 items-center px-2.5 sm:px-3 py-1.5 hover:bg-slate-800/50 transition-colors"
                    >
                      {/* Name & time */}
                      <div className="col-span-5 pr-1 min-w-0">
                        <p className="font-extrabold text-white text-xs sm:text-sm leading-tight truncate">
                          {it.menu_item_name || 'Taom'}
                        </p>

                        <div className="flex items-center gap-1 flex-wrap mt-0.5 text-[10px] sm:text-[11px] font-semibold text-slate-400 font-mono leading-none">
                          {/* Tortiladigan taom (baliq, go'sht): SUMMASI */}
                          {it.is_weighted && (
                            <button
                              onClick={() => {
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
                              title="Summasini kiritish"
                              className={`px-1.5 py-0.5 rounded text-[10px] font-black transition-all active:scale-95 inline-block ${isPriced(it)
                                  ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                                  : 'bg-red-600 text-white border border-red-400 animate-pulse'
                                }`}
                            >
                              {isPriced(it)
                                ? `💰 ${Math.round(it.total_price || 0).toLocaleString('uz-UZ')}` +
                                (it.weight ? `·${it.weight}${it.unit || 'kg'}` : '')
                                : '💰 Narx yo\'q'}
                            </button>
                          )}

                          {/* O'lchanadigan taom hajmi */}
                          {!it.is_weighted && (
                            <button
                              onClick={() => {
                                setSizeModalItem(it);
                                setSizeValue(it.portion_size || '');
                              }}
                              title="Hajm / o'lchamni kiritish"
                              className={`px-1.5 py-0.5 rounded text-[10px] font-black transition-all active:scale-95 inline-block ${it.portion_size
                                  ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50'
                                  : 'bg-slate-800 text-slate-400 border border-dashed border-slate-600 hover:text-amber-300'
                                }`}
                            >
                              {it.portion_size ? `📏 ${it.portion_size}` : '📏 Hajm'}
                            </button>
                          )}

                          <span>{it.item_time || '12:00'}</span>
                          <span>•</span>
                          {(() => {
                            const sent = Math.min(it.sent_quantity || 0, it.quantity);
                            const fresh = Math.max(it.quantity - sent, 0);
                            if (sent > 0 && fresh > 0) {
                              return (
                                <>
                                  <span className="text-amber-400 font-bold">{sent}♨️</span>
                                  <span>·</span>
                                  <span className="text-emerald-400 font-bold">{fresh}✦</span>
                                </>
                              );
                            }
                            return (
                              <span className={sent > 0 ? 'text-amber-400 font-bold' : 'text-emerald-400'}>
                                {sent > 0 ? 'Oshxonada♨️' : 'Yangi✦'}
                              </span>
                            );
                          })()}
                        </div>
                      </div>

                      {/* Unit Price */}
                      <div className="col-span-2 text-right font-bold text-slate-300 text-xs sm:text-sm font-mono truncate">
                        {it.unit_price.toLocaleString('uz-UZ')}
                      </div>

                      {/* Quantity Controls [- 1 +] */}
                      <div className="col-span-2 flex items-center justify-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleQtyChange(it, -1)}
                          className="w-7 h-7 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-sm active:scale-90 shadow-sm"
                          title="Kamaytirish"
                        >
                          -
                        </button>
                        <span className="text-xs sm:text-sm font-black text-white w-5 text-center font-mono">
                          {it.quantity}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleQtyChange(it, 1)}
                          className="w-7 h-7 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-sm active:scale-90 shadow-sm"
                          title="Ko'paytirish"
                        >
                          +
                        </button>
                      </div>

                      {/* Line Total */}
                      <div className="col-span-2 text-right font-black text-emerald-400 text-xs sm:text-sm font-mono">
                        {it.total_price.toLocaleString('uz-UZ')}
                      </div>

                      {/* Delete (Trash) button */}
                      <div className="col-span-1 flex justify-end">
                        <button
                          type="button"
                          onClick={() => handleDeleteItem(it.id)}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 active:scale-90 transition-all"
                          title="Taomni o'chirish"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Bottom Total and Actions */}
            <div className="p-2 sm:p-2.5 bg-slate-950 border-t border-slate-800 shadow-2xl shrink-0 space-y-1.5">
              {/* Bildirishnoma: Oshxonaga avtomatik chop etildi */}
              {kitchenSendSuccess && (
                <div className="p-1.5 mb-1 rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 font-black text-xs text-center flex items-center justify-center gap-1.5 animate-bounce-subtle shadow-md">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>✅ Buyurtma tasdiqlandi va oshxona printerlariga avtomatik chop etildi!</span>
                </div>
              )}

              {/* Narxi kiritilmagan taom ogohlantirishi — chek chiqmaydi */}
              {(activeOrder?.items || []).some((i) => i.is_weighted && !isPriced(i)) && (
                <div className="p-1.5 mb-1 rounded-xl bg-red-950/70 border border-red-600 text-red-200 font-black text-xs flex items-start gap-1.5 shadow-md">
                  <span className="text-xs shrink-0 leading-none">💰</span>
                  <span>
                    Narxi kiritilmagan taom bor:{' '}
                    {(activeOrder?.items || [])
                      .filter((i) => i.is_weighted && !isPriced(i))
                      .map((i) => i.menu_item_name)
                      .join(', ')}
                    . Summasi yozilmaguncha chek chiqmaydi.
                  </span>
                </div>
              )}

              {/* Subtotal & Service fee & Total compact summary (Ixcham 2 qator) */}
              <div className="bg-slate-900/80 px-2.5 py-1.5 rounded-xl border border-slate-800 text-xs">
                <div className="flex items-center justify-between text-slate-300 pb-1 border-b border-slate-800/80 text-[11px] sm:text-xs font-medium">
                  <span>Taomlar: <strong className="text-white font-mono">{(activeOrder?.subtotal || 0).toLocaleString('uz-UZ')}</strong></span>
                  <span>Xizmat ({activeOrder?.service_fee_percent || 12}%): <strong className="text-amber-300 font-mono">{(activeOrder?.service_fee_amount || 0).toLocaleString('uz-UZ')}</strong></span>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="font-black text-white text-xs uppercase tracking-wider">Jami hisob:</span>
                  <span className="text-emerald-400 text-base sm:text-lg font-mono font-black">
                    {(activeOrder?.total || 0).toLocaleString('uz-UZ')} so'm
                  </span>
                </div>
              </div>

              {/* ── Action Buttons: 2x2 ixcham grid ── */}
              <div className="grid grid-cols-2 gap-1.5 pt-0.5">
                {/* Oshxonaga yuborish (Buyurtmani tasdiqlash) */}
                <button
                  onClick={() => handleSendToKitchen(false)}
                  disabled={!activeOrder || sendingToKitchen}
                  className={`min-h-[38px] py-1 px-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs sm:text-sm shadow-md transition-all active:scale-95 flex items-center justify-center gap-1.5 ${!canCheckout && !isAdmin ? 'col-span-2' : ''}`}
                >
                  <Printer className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{sendingToKitchen ? 'Chop...' : '🔥 Tasdiqlash'}</span>
                </button>

                {/* To'landi va stolni bo'shatish (Checkout) — FAKAT Admin yoki Kassir */}
                {canCheckout && (
                  <button
                    onClick={() => setCheckoutModalOpen(true)}
                    disabled={!activeOrder || (activeOrder?.items || []).length === 0}
                    className="min-h-[38px] py-1 px-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-black text-xs sm:text-sm shadow-md transition-all active:scale-95 flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">✅ To'landi</span>
                  </button>
                )}

                {/* Oshxona izohi */}
                <button
                  onClick={() => setKitchenNoteModalOpen(true)}
                  className={`min-h-[32px] py-1 px-2 rounded-xl bg-teal-600/20 hover:bg-teal-600/30 border border-teal-500/40 text-teal-300 font-bold text-[11px] sm:text-xs transition-all truncate flex items-center justify-center gap-1 ${!canCheckout && !isAdmin ? 'col-span-2' : ''}`}
                >
                  <span>💬 Izoh</span>
                  {kitchenNote && <span className="text-teal-200">✓</span>}
                </button>

                {/* Admin zakas olgandan keyin chekni darhol chiqaradi */}
                {isAdmin && (
                  <button
                    onClick={handlePrintBill}
                    disabled={!activeOrder || printingBill}
                    className="min-h-[32px] py-1 px-2 rounded-xl bg-sky-600/20 hover:bg-sky-600/30 border border-sky-500/40 disabled:opacity-40 text-sky-300 font-bold text-[11px] sm:text-xs transition-all active:scale-95 flex items-center justify-center gap-1"
                  >
                    <Receipt className="w-3 h-3 shrink-0" />
                    <span className="truncate">{printingBill ? 'Chop...' : '🧾 Chek'}</span>
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* ── O'ng Panel: Kategoriyalar va Taomlar Gridi (Katta va qulay kartochkalar) ───── */}
          <div
            className={`flex-1 flex flex-col bg-slate-950 overflow-hidden h-full min-h-0 ${
              mobileTab === 'menu' ? 'flex' : 'hidden lg:flex'
            }`}
          >
            {/* Mobil uchun joriy stol indikatori va tanlash */}
            <div className="lg:hidden flex items-center justify-between px-3 py-2 bg-slate-900 border-b border-slate-800 shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 uppercase font-black tracking-wider">Stol:</span>
                <span className="text-xs sm:text-sm font-black text-white">
                  {selectedTable?.room ? `${selectedTable.room} - ` : ''}
                  {selectedTable?.name || `Stol #${selectedTable?.number || 1}`}
                </span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-black uppercase ${
                    selectedTable?.status === 'occupied'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                      : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  }`}
                >
                  {selectedTable?.status === 'occupied' ? 'Band' : "Bo'sh"}
                </span>
              </div>

              <select
                value={selectedTable?.id || ''}
                onChange={(e) => {
                  const t = tables.find((x) => x.id === parseInt(e.target.value));
                  if (t) setSelectedTable(t);
                }}
                className="bg-slate-800 text-xs font-bold text-white rounded-xl px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:border-emerald-500"
              >
                {tables.map((tbl) => (
                  <option key={tbl.id} value={tbl.id}>
                    {tbl.room ? `${tbl.room} ` : ''}#{tbl.number} ({tbl.status === 'occupied' ? 'Band' : "Bo'sh"})
                  </option>
                ))}
              </select>
            </div>

            {/* Top Categories Strip */}
            <div className="p-3.5 bg-slate-900/70 border-b border-slate-800">
              {/* Search bar */}
              <div className="mb-3 relative">
                <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchItemQuery}
                  onChange={(e) => setSearchItemQuery(e.target.value)}
                  placeholder="Menyudan taom qidirish..."
                  className="w-full pl-11 pr-4 py-2.5 rounded-2xl bg-slate-900 border-2 border-slate-700/80 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500 font-medium"
                />
              </div>

              {/* Category buttons list */}
              <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
                {categories.map((cat) => {
                  const active = cat.id === selectedCatId;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => {
                        setSelectedCatId(cat.id);
                        setSearchItemQuery('');
                      }}
                      className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-extrabold shrink-0 transition-all ${active
                          ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 scale-102'
                          : 'bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
                        }`}
                    >
                      {cat.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Dishes Grid — Katta rasmli, chiroyli va tushunarli menyu kartalari */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-4">
              <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 sm:gap-3.5">
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
                      {/* Thumbnail: Kattaroq rasm */}
                      <div className="h-28 sm:h-32 xl:h-36 w-full rounded-2xl bg-slate-950 overflow-hidden relative mb-2.5 flex items-center justify-center border border-slate-800/80">
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

                      {/* Title: Tushunarli va aniq sarlavha */}
                      <h4 className="text-sm sm:text-base font-extrabold text-white group-hover:text-emerald-300 transition-colors line-clamp-2 leading-tight">
                        {item.name}
                      </h4>

                      {/* Price Badge and Plus button: Kattaroq, aniq ko'rinuvchi narx */}
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className="px-2.5 sm:px-3 py-1.5 rounded-xl bg-emerald-600 text-white font-black text-xs sm:text-sm shadow-md font-mono">
                          {Math.round(item.price || 0).toLocaleString('uz-UZ')} so'm
                        </span>
                        <span className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-base font-black group-hover:bg-emerald-500 group-hover:text-slate-950 transition-colors shadow-sm shrink-0">
                          +
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Mobil pastki savat ko'rish suzuvchi paneli */}
            <div className="lg:hidden p-2.5 bg-slate-950/95 border-t border-slate-800 shrink-0">
              <button
                type="button"
                onClick={() => setMobileTab('cart')}
                className="w-full py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 active:scale-98 text-white font-black text-xs sm:text-sm flex items-center justify-between shadow-lg shadow-emerald-950/50"
              >
                <div className="flex items-center gap-2">
                  <ShoppingCart className="w-4 h-4" />
                  <span>Savat: {activeOrder?.items?.length || 0} ta taom</span>
                </div>
                <div className="flex items-center gap-1.5 font-mono text-emerald-200">
                  <span>
                    {Math.round(
                      activeOrder?.total ||
                        (activeOrder?.items || []).reduce((acc, it) => acc + (it.total_price || 0), 0)
                    ).toLocaleString('uz-UZ')}{' '}
                    so'm
                  </span>
                  <span>➔</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* ─── Tortilgan og'irlikni kiritish (baliq 1.35 kg) ──────────── */}
      {weightModalItem && (
        <div className="fixed inset-0 z-[55] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border-2 border-cyan-600/60 rounded-3xl max-w-md w-full p-5 shadow-2xl">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h3 className="text-base font-black text-white">💰 Narxini kiritish</h3>
                <p className="text-xs font-bold text-cyan-300 mt-0.5">
                  {weightModalItem.menu_item_name || 'Taom'}
                </p>
              </div>
              <button
                onClick={() => setWeightModalItem(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-[11px] text-slate-400 mb-3">
              Mahsulotni tarozida torting va <b className="text-white">summasini</b> yozing.
              Chekda aynan shu summa chiqadi — mijoz bilan nizo bo'lmaydi.
            </p>

            <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 mb-3">
              <div className="flex justify-between text-xs text-slate-300 font-semibold">
                <span>1 {weightModalItem.unit || 'kg'} narxi:</span>
                <span className="font-mono font-black text-white">
                  {(weightModalItem.unit_price || 0).toLocaleString('uz-UZ')} so'm
                </span>
              </div>
            </div>

            {/* ASOSIY maydon — SUMMA */}
            <label className="block text-[10px] font-black text-emerald-400 uppercase tracking-wider mb-1.5">
              Summa (so'm) — shuni yozing:
            </label>
            <input
              type="number"
              step="1"
              min="0"
              inputMode="numeric"
              autoFocus
              value={priceValue}
              onChange={(e) => setPriceValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveWeight();
              }}
              placeholder="masalan: 204000"
              className="w-full p-3.5 rounded-xl bg-slate-950 border-2 border-emerald-600 text-3xl text-white font-mono font-black text-center focus:outline-none focus:border-emerald-400 mb-1"
            />
            {(() => {
              const pr = parseFloat(String(priceValue).replace(',', '.')) || 0;
              if (pr <= 0) return <div className="mb-3" />;
              return (
                <p className="text-center text-sm font-black text-emerald-400 font-mono mb-3">
                  {Math.round(pr).toLocaleString('uz-UZ')} so'm
                </p>
              );
            })()}

            {/* IXTIYORIY — og'irlik. Oshxona nechchi kg ekanini bilishi uchun */}
            <label className="block text-[10px] font-black text-slate-500 uppercase tracking-wider mb-1.5">
              Og'irlik ({weightModalItem.unit || 'kg'}) — ixtiyoriy
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              inputMode="decimal"
              value={weightValue}
              onChange={(e) => {
                const v = e.target.value;
                setWeightValue(v);
                // Og'irlik yozilsa summani TAKLIF qilamiz — ofitsiant
                // xohlasa uni qo'lda tuzatadi.
                const w = parseFloat(String(v).replace(',', '.'));
                if (w > 0) {
                  setPriceValue(String(Math.round(w * (weightModalItem.unit_price || 0))));
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveWeight();
              }}
              placeholder="masalan: 1.7 (yozsangiz chekda ko'rinadi)"
              className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-700 text-base text-slate-200 font-mono font-bold text-center focus:outline-none focus:border-cyan-500 mb-4"
            />

            <div className="flex items-center gap-2">
              <button
                onClick={() => setWeightModalItem(null)}
                className="px-3 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300"
              >
                Keyinroq
              </button>
              <button
                onClick={handleSaveWeight}
                disabled={savingWeight}
                className="flex-1 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-sm disabled:opacity-40 active:scale-95 transition-all"
              >
                {savingWeight ? 'Saqlanmoqda...' : 'Saqlash'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Hajm / O'lcham oynasi (1.5 L kola, 1.4 kg baliq) ───────── */}
      {sizeModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border-2 border-slate-800 rounded-3xl max-w-md w-full p-5 shadow-2xl">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h3 className="text-base font-black text-white">Hajm / O'lcham</h3>
                <p className="text-xs font-bold text-amber-300 mt-0.5">
                  {sizeModalItem.menu_item_name || 'Taom'}
                </p>
              </div>
              <button
                onClick={() => setSizeModalItem(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Oshxona va mijoz chekida shu yozuv chiqadi — masalan "Kola 1.5 L"
              yoki "Baliq 1.4 kg".
            </p>

            {/* Tez tanlash tugmalari */}
            <div className="mb-3">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider block mb-1.5">
                Ichimliklar:
              </span>
              <div className="grid grid-cols-4 gap-1.5 mb-2.5">
                {['0.5 L', '1 L', '1.5 L', '2 L'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleSaveSize(v)}
                    disabled={savingSize}
                    className="py-2.5 rounded-xl bg-slate-800 hover:bg-amber-600 hover:text-slate-950 border border-slate-700 text-sm font-black text-white transition-all active:scale-95 disabled:opacity-40"
                  >
                    {v}
                  </button>
                ))}
              </div>
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider block mb-1.5">
                Tortiladigan (baliq, go'sht):
              </span>
              <div className="grid grid-cols-4 gap-1.5">
                {['0.5 kg', '1 kg', '1.5 kg', '2 kg'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleSaveSize(v)}
                    disabled={savingSize}
                    className="py-2.5 rounded-xl bg-slate-800 hover:bg-amber-600 hover:text-slate-950 border border-slate-700 text-sm font-black text-white transition-all active:scale-95 disabled:opacity-40"
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            {/* Qo'lda yozish */}
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider block mb-1.5">
              Yoki o'zingiz yozing:
            </label>
            <input
              type="text"
              value={sizeValue}
              onChange={(e) => setSizeValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveSize(sizeValue);
              }}
              placeholder="Masalan: 1.75 kg, katta kosa, 0.33 L"
              maxLength={50}
              className="w-full p-3 rounded-xl bg-slate-950 border-2 border-slate-800 text-sm text-white font-bold focus:outline-none focus:border-amber-500 mb-4"
            />

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSaveSize('')}
                disabled={savingSize}
                className="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-red-900/60 text-xs font-bold text-slate-300 disabled:opacity-40"
              >
                Tozalash
              </button>
              <button
                onClick={() => handleSaveSize(sizeValue)}
                disabled={savingSize}
                className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-sm disabled:opacity-40 active:scale-95 transition-all"
              >
                {savingSize ? 'Saqlanmoqda...' : 'Saqlash'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Kitchen Note Modal (Комент. к кухне) ───────────────────── */}
      {kitchenNoteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 shadow-2xl">
            <h3 className="text-sm font-bold text-white mb-2">Oshxonaga izoh (Комент. к кухне)</h3>
            <textarea
              rows={3}
              value={kitchenNote}
              onChange={(e) => setKitchenNote(e.target.value)}
              placeholder="Masalan: Achchiq bo'lmasin, piyozsiz..."
              className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-teal-500 resize-none mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setKitchenNoteModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
              >
                Bekor qilish
              </button>
              <button
                onClick={handleSaveNotes}
                className="px-4 py-1.5 rounded-xl bg-teal-600 text-white font-bold text-xs hover:bg-teal-500"
              >
                Saqlash
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Kassa To'lov Oynasi (CheckoutModal) — Faqat Admin/Kassir uchun ─── */}
      {canCheckout && (
        <CheckoutModal
          isOpen={checkoutModalOpen}
          onClose={() => setCheckoutModalOpen(false)}
          order={activeOrder}
          tableLabel={selectedTable ? `${selectedTable.room ? selectedTable.room + ' - ' : ''}Stol #${selectedTable.number}` : "Stol buyurtmasi"}
          onPaid={handleCheckoutPaid}
        />
      )}

      {/* ─── Stolni ko'chirish modali (Aliposter 1.0.0.0 andozasi) ─── */}
      {transferModalOpen && selectedTable && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-5 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-amber-400" />
                <h3 className="text-white font-extrabold text-sm sm:text-base">
                  Stol #{selectedTable.number} ni ko'chirish
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setTransferModalOpen(false)}
                className="w-7 h-7 rounded-lg bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-3">
              Buyurtmani qaysi stolga ko'chirmoqchisiz? Kerakli stolni tanlang:
            </p>

            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-64 overflow-y-auto custom-scrollbar p-1 mb-4">
              {tables
                .filter((t) => t.id !== selectedTable.id)
                .map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    disabled={transferLoading}
                    onClick={() => handleTransferTable(t.id)}
                    className={`p-2.5 rounded-xl text-center border font-black text-xs transition-all active:scale-95 flex flex-col items-center justify-center gap-1 ${
                      t.status === 'occupied'
                        ? 'bg-amber-950/40 border-amber-800/60 text-amber-300 hover:bg-amber-900/60'
                        : 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300 hover:bg-emerald-900/60'
                    }`}
                  >
                    <span className="font-extrabold text-sm text-white">#{t.number}</span>
                    <span className="text-[10px] text-slate-400 truncate max-w-full">{t.room || 'Zal'}</span>
                    <span className="text-[9px] uppercase font-bold opacity-75">
                      {t.status === 'occupied' ? 'Bandga qo\'shish' : 'Bo\'sh stol'}
                    </span>
                  </button>
                ))}
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setTransferModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-xs text-slate-300 font-bold hover:bg-slate-700"
              >
                Bekor qilish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Xprinter Thermal Receipt Modal ─────────────────────────── */}
      <ThermalReceiptModal
        isOpen={receiptModalOpen}
        onClose={() => setReceiptModalOpen(false)}
        title={receiptModalTitle}
        rawText={thermalReceiptText}
        paperWidth={80}
      />
    </div>
  );
};

export default WaiterDashboard;
