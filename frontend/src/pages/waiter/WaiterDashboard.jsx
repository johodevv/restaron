import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import { preloadImages, collectImageUrls } from '../../utils/preloadImages';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { ThermalReceiptModal } from '../../components/ThermalReceiptModal';
import confetti from 'canvas-confetti';
import {
  UtensilsCrossed,
  ShoppingBag,
  Truck,
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
  Check
} from 'lucide-react';

export const WaiterDashboard = () => {
  const { user } = useAuth();
  const { addEventListener, playChime, connected } = useWebSocket();
  const restaurantId = user?.restaurant_id || 1;

  // View mode: 'pos' (Ali Poster stollar zakazi) | 'calls' (Chaqiruvlar) | 'ready' (Oshxonadan tayyor) | 'kpi' (Hisobotim)
  const [activeTab, setActiveTab] = useState('pos');
  const [orderType, setOrderType] = useState('table'); // 'table' | 'takeaway' | 'delivery'

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

  // Checkout modal

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

  // WebSocket real-time updates
  useEffect(() => {
    const unsub = addEventListener('*', (event) => {
      if (event.type === 'call_waiter') {
        if (soundEnabled && playChime) playChime('urgent');
        loadInitialData();
      } else if (event.type === 'order_ready') {
        if (soundEnabled && playChime) playChime('success');
        loadInitialData();
      } else if (
        event.type === 'order_updated' ||
        event.type === 'order_paid' ||
        event.type === 'table_status_updated'
      ) {
        loadInitialData();
        if (selectedTable && event.table_id === selectedTable.id) {
          fetchTableActiveOrder(selectedTable);
        }
      }
    });
    return () => unsub();
  }, [addEventListener, selectedTable, soundEnabled, playChime]);

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
      if (!activeOrder) {
        // Yangi buyurtma ochish
        const payload = {
          restaurant_id: restaurantId,
          table_id: selectedTable?.id,
          order_type: orderType,
          hall_name: selectedTable?.room || 'Zal',
          items: [{ menu_item_id: menuItem.id, quantity: 1 }],
        };
        const newOrd = await api.post('/orders/waiter-create', payload);
        setActiveOrder(newOrd);
        openWeightModalIfNeeded(newOrd, menuItem.id);
        // Stol endi band. Sarlavhadagi belgi ham yangilanishi uchun
        // selectedTable ni ham yangilaymiz — aks holda ro'yxatda "Band",
        // sarlavhada esa "Bo'sh" deb turib, ofitsiantni chalg'itadi.
        setTables((prev) =>
          prev.map((t) => (t.id === selectedTable?.id ? { ...t, status: 'occupied' } : t))
        );
        setSelectedTable((prev) => (prev ? { ...prev, status: 'occupied' } : prev));
      } else {
        // Mavjud buyurtmaga qo'shish
        // Agar taom savatda allaqachon bo'lsa -> sonini +1 qilamiz.
        // LEKIN hajmi belgilangan qator (masalan "Kola 1.5 L") birlashtirilmaydi —
        // aks holda 1 L kola 1.5 L qatoriga qo'shilib ketadi va oshxona
        // qaysi hajm kerakligini bilmay qoladi. Shunday holda yangi qator ochiladi.
        // Tortiladigan taom (har baliq o'z og'irligiga ega) ham,
        // hajmi belgilangan qator ham birlashtirilmaydi.
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

  // Change quantity [- 1 +]
  const handleQtyChange = async (item, delta) => {
    const newQty = item.quantity + delta;
    if (newQty <= 0) {
      // O'chirish
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

  // Delete item from order
  const handleDeleteItem = async (itemId) => {
    try {
      const updated = await api.delete(`/orders/${activeOrder.id}/items/${itemId}`);
      setActiveOrder(updated);
    } catch (err) {
      alert(err.message || 'Xatolik');
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

  // Filter items in right panel
  const activeCategory = categories.find((c) => c.id === selectedCatId);
  const allItems = categories.flatMap((c) => c.items || []);
  const displayedItems = searchItemQuery.trim()
    ? allItems.filter((i) => i.name.toLowerCase().includes(searchItemQuery.toLowerCase()))
    : activeCategory?.items || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none">
      {/* ─── Top Bar (Ali Poster uslubida) ─────────────────────────── */}
      <header className="h-14 bg-emerald-950/80 border-b border-emerald-800/60 px-4 flex items-center justify-between shadow-lg backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 font-black text-emerald-400 tracking-wider text-base">
            <span className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400">
              <UtensilsCrossed className="w-5 h-5" />
            </span>
            <span>Ali Poster POS</span>
          </div>

          {/* Mode Switchers: Stollar | S soboy | Dostavka */}
          <div className="hidden sm:flex items-center bg-black/40 p-1 rounded-xl border border-emerald-800/40 ml-4">
            <button
              onClick={() => {
                setActiveTab('pos');
                setOrderType('table');
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'pos' && orderType === 'table'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <span>Столы</span>
            </button>
            <button
              onClick={() => {
                setActiveTab('pos');
                setOrderType('takeaway');
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'pos' && orderType === 'takeaway'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <ShoppingBag className="w-3.5 h-3.5" />
              <span>С собой</span>
            </button>
            <button
              onClick={() => {
                setActiveTab('pos');
                setOrderType('delivery');
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === 'pos' && orderType === 'delivery'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Truck className="w-3.5 h-3.5" />
              <span>Доставка</span>
            </button>
          </div>
        </div>

        {/* Right Info: Chaqiruvlar badgi, Waiter Name, Sound toggle */}
        <div className="flex items-center gap-3">
          {/* Chaqiruvlar Tab Button */}
          <button
            onClick={() => setActiveTab('calls')}
            className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'calls'
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
            className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'ready'
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
        /* ── POS EKRANI (Ali Poster uslubida yuqori sifatli dizayn) ───────── */
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          {/* ── Chap Panel: Tanlangan Stol va Zakaz (Katta va qulay shriftlar) ─────────── */}
          <div className="w-full lg:w-[480px] xl:w-[500px] bg-slate-900/95 border-r border-slate-800 flex flex-col justify-between shrink-0 shadow-2xl">
            {/* Table Header Bar */}
            <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[11px] text-slate-400 uppercase tracking-wider font-bold block">
                  Joriy stol:
                </span>
                <div className="flex items-center gap-2 mt-0.5">
                  <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                    {selectedTable?.room ? `${selectedTable.room} - ` : ''}
                    {selectedTable?.name || `Stol #${selectedTable?.number || 1}`}
                  </h2>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-black uppercase tracking-wider ${
                      selectedTable?.status === 'occupied'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    }`}
                  >
                    {selectedTable?.status === 'occupied' ? 'Band' : "Bo'sh"}
                  </span>
                </div>
              </div>

              {/* Tanlangan zonadagi stollarni tez almashtirish */}
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

            {/* ─── Zonalar va stollar ─────────────────────────────
                Ilgari hamma stollar bitta ro'yxatda aralashib yotardi.
                Endi "Terrassa" ni bossangiz faqat terrassadagi stollar
                chiqadi. */}
            {zoneNames.length > 0 && (
              <div className="px-3 pt-2.5 pb-1 bg-slate-950/60 border-b border-slate-800">
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1.5">
                  <button
                    onClick={() => setSelectedZone('')}
                    className={`shrink-0 px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95 ${
                      selectedZone === ''
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
                      className={`shrink-0 px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95 ${
                        selectedZone === z
                          ? 'bg-emerald-500 text-slate-950 shadow-md'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      {z} {zoneCount(z)}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-1.5 overflow-x-auto pb-2 pt-0.5">
                  {zoneTables.length === 0 ? (
                    <span className="text-[11px] font-bold text-slate-500 py-1.5">
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
                          className={`shrink-0 min-w-[56px] px-2.5 py-1.5 rounded-xl text-sm font-black border-2 transition-all active:scale-95 ${
                            active
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

            {/* Active Items Table (Kattalashtirilgan qulay jadval) */}
            <div className="flex-1 overflow-y-auto">
              <div className="grid grid-cols-12 text-xs sm:text-sm font-black text-slate-300 bg-slate-950/70 px-4 py-2.5 border-b border-slate-800 uppercase tracking-wider">
                <span className="col-span-5">Taom nomi</span>
                <span className="col-span-3 text-right">Narxi</span>
                <span className="col-span-2 text-center">Soni</span>
                <span className="col-span-2 text-right">Jami</span>
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
                      className="grid grid-cols-12 items-center px-4 py-3 hover:bg-slate-800/50 transition-colors"
                    >
                      {/* Name & time */}
                      <div className="col-span-5 pr-1">
                        <p className="font-extrabold text-white text-sm sm:text-base leading-snug">
                          {it.menu_item_name || 'Taom'}
                        </p>

                        {/* Tortiladigan taom (baliq, go'sht): SUMMASI.
                            Kiritilmaguncha chek chiqmaydi. */}
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
                            className={`mt-1 mb-0.5 px-2 py-1 rounded-lg text-[11px] font-black transition-all active:scale-95 block ${
                              isPriced(it)
                                ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                                : 'bg-red-600 text-white border border-red-400 animate-pulse'
                            }`}
                          >
                            {isPriced(it)
                              ? `💰 ${Math.round(it.total_price || 0).toLocaleString('uz-UZ')} so'm` +
                                (it.weight ? ` · ${it.weight} ${it.unit || 'kg'}` : '')
                              : '💰 NARXI YO\'Q — bosing!'}
                          </button>
                        )}

                        {/* O'lchanadigan taom hajmi: 1.5 L kola, 1.4 kg baliq.
                            Oshxona begunogida va mijoz chekida shu ko'rinadi. */}
                        {!it.is_weighted && (
                        <button
                          onClick={() => {
                            setSizeModalItem(it);
                            setSizeValue(it.portion_size || '');
                          }}
                          title="Hajm / o'lchamni kiritish"
                          className={`mt-1 mb-0.5 px-2 py-1 rounded-lg text-[11px] font-black transition-all active:scale-95 ${
                            it.portion_size
                              ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50'
                              : 'bg-slate-800 text-slate-400 border border-dashed border-slate-600 hover:text-amber-300 hover:border-amber-500/50'
                          }`}
                        >
                          {it.portion_size ? `📏 ${it.portion_size}` : '📏 Hajm'}
                        </button>
                        )}

                        <p className="text-xs font-semibold text-slate-400 font-mono mt-0.5">
                          {it.quantity} dona • {it.item_time || '12:00'} •{' '}
                          {/* Oshxonaga nechtasi yuborilgan va nechtasi hali
                              yuborilmaganini aniq ko'rsatamiz: 2 somsadan
                              1 tasi yuborilgan bo'lsa "1 ♨️ · 1 yangi ✦". */}
                          {(() => {
                            const sent = Math.min(it.sent_quantity || 0, it.quantity);
                            const fresh = Math.max(it.quantity - sent, 0);
                            if (sent > 0 && fresh > 0) {
                              return (
                                <>
                                  <span className="text-amber-400 font-bold">{sent} Oshxonada ♨️</span>
                                  {' · '}
                                  <span className="text-emerald-400 font-bold">{fresh} Yangi ✦</span>
                                </>
                              );
                            }
                            return (
                              <span className={sent > 0 ? 'text-amber-400 font-bold' : 'text-emerald-400'}>
                                {sent > 0 ? 'Oshxonada ♨️' : 'Yangi ✦'}
                              </span>
                            );
                          })()}
                        </p>
                      </div>

                      {/* Unit Price */}
                      <div className="col-span-3 text-right font-bold text-slate-200 text-sm sm:text-base font-mono">
                        {it.unit_price.toLocaleString('uz-UZ')}
                      </div>

                      {/* Quantity Controls [- 1 +] — Katta va qulay sensor tugmalar */}
                      <div className="col-span-2 flex items-center justify-center gap-1.5">
                        <button
                          onClick={() => handleQtyChange(it, -1)}
                          className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-lg transition-transform active:scale-90 shadow-md"
                          title="Kamaytirish"
                        >
                          -
                        </button>
                        <span className="text-sm sm:text-base font-black text-white w-5 text-center font-mono">
                          {it.quantity}
                        </span>
                        <button
                          onClick={() => handleQtyChange(it, 1)}
                          className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-lg transition-transform active:scale-90 shadow-md"
                          title="Ko'paytirish"
                        >
                          +
                        </button>
                      </div>

                      {/* Line Total */}
                      <div className="col-span-2 text-right font-black text-emerald-400 text-sm sm:text-base font-mono">
                        {it.total_price.toLocaleString('uz-UZ')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Bottom Total and Actions */}
            <div className="p-4 bg-slate-950 border-t border-slate-800 shadow-2xl">
              {/* Bildirishnoma: Oshxonaga avtomatik chop etildi */}
              {kitchenSendSuccess && (
                <div className="p-3 mb-3 rounded-2xl bg-emerald-500/20 border-2 border-emerald-500/50 text-emerald-300 font-black text-xs sm:text-sm text-center flex items-center justify-center gap-2 animate-bounce-subtle shadow-lg">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>✅ Buyurtma tasdiqlandi va oshxona printerlariga avtomatik chop etildi!</span>
                </div>
              )}

              {/* Narxi kiritilmagan taom ogohlantirishi — chek chiqmaydi */}
              {(activeOrder?.items || []).some((i) => i.is_weighted && !isPriced(i)) && (
                <div className="p-3 mb-3 rounded-2xl bg-red-950/70 border-2 border-red-600 text-red-200 font-black text-xs sm:text-sm flex items-start gap-2 shadow-lg">
                  <span className="text-lg shrink-0 leading-none">💰</span>
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

              {/* Subtotal & Service fee summary */}
              <div className="space-y-1.5 mb-3.5 bg-slate-900/60 p-3 rounded-2xl border border-slate-800">
                <div className="flex justify-between text-xs sm:text-sm text-slate-300">
                  <span className="font-semibold">Taomlar jami:</span>
                  <span className="font-bold text-white font-mono">
                    {(activeOrder?.subtotal || 0).toLocaleString('uz-UZ')} so'm
                  </span>
                </div>
                <div className="flex justify-between text-xs sm:text-sm text-slate-300">
                  <span className="font-semibold">Xizmat haqi ({activeOrder?.service_fee_percent || 12}%):</span>
                  <span className="font-bold text-amber-300 font-mono">
                    {(activeOrder?.service_fee_amount || 0).toLocaleString('uz-UZ')} so'm
                  </span>
                </div>
                <div className="flex justify-between text-base sm:text-lg font-black text-white pt-2 border-t border-slate-800">
                  <span>Jami hisob:</span>
                  <span className="text-emerald-400 text-xl sm:text-2xl font-mono">
                    {(activeOrder?.total || 0).toLocaleString('uz-UZ')} so'm
                  </span>
                </div>
              </div>

              {/* Oshxonaga izoh. "Chek izohi" olib tashlandi — chek
                  kassada (admin panelda) chiqariladi. */}
              <div className="mb-2.5">
                <button
                  onClick={() => setKitchenNoteModalOpen(true)}
                  className="w-full py-2.5 px-3 rounded-xl bg-teal-600/20 hover:bg-teal-600/30 border border-teal-500/40 text-teal-300 font-bold text-xs sm:text-sm transition-all truncate"
                >
                  💬 Oshxona izohi {kitchenNote ? '✓' : ''}
                </button>
              </div>

              {/* Asosiy POS amali. "To'lov / Hisob" olib tashlandi —
                  to'lovni kassada o'tirgan xodim admin panelda qabul qiladi. */}
              <div className="grid grid-cols-1 gap-2.5">
                <button
                  onClick={() => handleSendToKitchen(false)}
                  disabled={!activeOrder || sendingToKitchen}
                  className="py-4 px-3 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 text-slate-950 font-black text-xs sm:text-sm shadow-xl shadow-amber-500/25 transition-all active:scale-95 flex items-center justify-center gap-1.5"
                >
                  <Printer className="w-5 h-5 shrink-0" />
                  <span>{sendingToKitchen ? 'Chop etilmoqda...' : '🔥 Buyurtmani tasdiqlash'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* ── O'ng Panel: Kategoriyalar va Taomlar Gridi (Katta va qulay kartochkalar) ───── */}
          <div className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
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
                      className={`px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-extrabold shrink-0 transition-all ${
                        active
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

            {/* Dishes Grid — Katta va qulay taom kartalari */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5">
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
                      {/* Image / Thumbnail */}
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
                          {item.price.toLocaleString('uz-UZ')} so'm
                        </span>
                        <span className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-base font-black group-hover:bg-emerald-500 group-hover:text-slate-950 transition-colors shadow-sm">
                          +
                        </span>
                      </div>
                    </div>
                  );
                })}
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
