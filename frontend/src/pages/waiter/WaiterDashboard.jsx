import { createPortal } from 'react-dom';
import { useLanguage } from '../../context/LanguageContext';
import { previewOrderTotals } from '../../utils/posTotals';
import { useDialogFocus } from '../../hooks/useDialogFocus';
import { usePanelHistory } from '../../hooks/usePanelHistory';
import { posLabel } from '../../utils/posLabels';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../../utils/api';
import { latestOrder } from '../../utils/orderSync';
import { createPosMutationQueue } from '../../utils/posMutationQueue';
import { canDeleteOrderItem, canDecreaseOrderItem, kitchenSentQuantity } from '../../utils/kitchenPermissions';
import { convertWeightedInput, weightedUpdatePayload } from '../../utils/weightedItem';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { ThermalReceiptModal } from '../../components/ThermalReceiptModal';
import CheckoutModal from '../../components/CheckoutModal';
import PrinterStatusBanner from '../../components/PrinterStatusBanner';
import WaiterTablePicker from '../../components/WaiterTablePicker';
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
  AlertCircle,
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
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  ShoppingCart
} from 'lucide-react';

export const WaiterDashboard = ({ showModeSwitch: propShowModeSwitch, canCheckout: propCanCheckout, restaurantId: propRestaurantId, onOrderViewChange, compactMenu = false } = {}) => {
  const { lang, getLocalizedName } = useLanguage();
  const label = text => posLabel(text, lang);
  const { user, isAdmin, isCashier, canCheckout: authCanCheckout } = useAuth();
  const { addEventListener, playChime, connected, connectionError, connectionPhase, reconnect, addNotification } = useWebSocket() || {};
  const [showConnectionNotice, setShowConnectionNotice] = useState(false);
  useEffect(() => {
    setShowConnectionNotice(false);
    if (connected !== false) return;
    const timer = setTimeout(() => setShowConnectionNotice(true), 2000);
    return () => clearTimeout(timer);
  }, [connected]);
  const restaurantId = propRestaurantId || user?.restaurant_id || 1;

  // 7. Toast xabarlari (alert o'rniga)
  const showToast = useCallback((message, type = 'info', title = null) => {
    if (typeof addNotification === 'function') {
      addNotification({
        type,
        title: title || (type === 'urgent' ? 'Xatolik' : type === 'warning' ? 'Ogohlantirish' : type === 'success' ? 'Muvaffaqiyatli' : 'Xabar'),
        message: String(message || ''),
      });
    }
  }, [addNotification]);

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
  const [orders, setOrders] = useState([]);
  const [, setTick] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // Active Table & Active Order (Left POS Panel)
  const [selectedTable, setSelectedTable] = useState(null);
  // Stol zonasi (Zal / Terrassa / Ko'cha / VIP). '' — hammasi.
  const [selectedZone, setSelectedZone] = useState('');
  const [transferZone, setTransferZone] = useState('');
  const [showTableBrowser, setShowTableBrowser] = useState(false);
  const [browsingTables, setBrowsingTables] = useState(!isPrivileged);
  const [customerDetailsOpen, setCustomerDetailsOpen] = useState(false);
  const [showOrderPicker, setShowOrderPicker] = useState(false);
  const [orderSearch, setOrderSearch] = useState('');
  const customerDialogRef = useDialogFocus(customerDetailsOpen, () => setCustomerDetailsOpen(false));
  const orderPickerRef = useDialogFocus(showOrderPicker, () => setShowOrderPicker(false));
  const tablePickerRef = useDialogFocus(showTableBrowser, () => setShowTableBrowser(false));
  const [activeOrder, setActiveOrder] = useState(null);
  const [orderLoading, setOrderLoading] = useState(false);
  const [orderReadError, setOrderReadError] = useState(null);
  const initialLoadRef = useRef(false);

  // Tortiladigan taom (baliq, go'sht) og'irligini kiritish oynasi
  const [weightModalItem, setWeightModalItem] = useState(null);
  const [weightValue, setWeightValue] = useState('');
  // Tortiladigan taomning SUMMASI — ofitsiant kg emas, pulini yozadi
  const [priceValue, setPriceValue] = useState('');
  const [weightEditedField, setWeightEditedField] = useState('price');
  const weightSaveLock = useRef(false);
  const [printingBill, setPrintingBill] = useState(false);
  const [savingWeight, setSavingWeight] = useState(false);
  const weightDialogRef = useDialogFocus(!!weightModalItem, () => { if (!weightSaveLock.current) setWeightModalItem(null); });

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
  const [mergePreview, setMergePreview] = useState(null);
  const transferDialogRef = useDialogFocus(transferModalOpen, () => { if (!transferLoading) setTransferModalOpen(false); });

  // Bitta buyurtma uchun ketma-ket so'rovlar navbati va oxirgi so'rov id si
  const orderQueueRef = useRef(Promise.resolve());
  const latestRequestIdRef = useRef(0);
  // activeOrder yo'q holatida yangi buyurtma yaratilayotganda qulf (promise)
  const [mutationStatus, setMutationStatus] = useState({ pending: 0, error: null });
  const mutationQueueRef = useRef(null);
  const mountedRef = useRef(true);
  const selectionKey = orderType === 'table' ? `table:${selectedTable?.id || ''}` : orderType;
  const selectionKeyRef = useRef(selectionKey);
  selectionKeyRef.current = selectionKey;
  const orderTypeRef = useRef(orderType);
  orderTypeRef.current = orderType;
  const activeOrderRef = useRef(activeOrder);
  activeOrderRef.current = activeOrder;
  const fetchVersionRef = useRef(0);
  if (!mutationQueueRef.current) mutationQueueRef.current = createPosMutationQueue({
    execute: async (intent, base, key) => {
      if (intent.barrier) await intent.barrier.catch(() => {});
      if (!mountedRef.current) throw new Error('Panel yopilgan. Hisobni qayta ochib tekshiring.');
      const options = { idempotent: true, headers: { 'Idempotency-Key': key } };
      if (intent.kind === 'add') {
        if (!base || base.status === 'cancelled' || base.is_paid) {
          return api.post('/orders/waiter-create', {
            ...intent.context, items: [{ menu_item_id: intent.menu.id, quantity: intent.quantity }],
          }, options);
        }
        return api.post(`/orders/${base.id}/add-items`, {
          items: [{ menu_item_id: intent.menu.id, quantity: intent.quantity }], send_to_kitchen_immediately: false,
        }, options);
      }
      const item = base?.items?.find(line => line.id === intent.itemId || (String(intent.itemId).startsWith('pending:') && line.menu_item_id === intent.menuId && !line.is_weighted));
      if (!item) throw new Error('Taom o‘zgargan. Bajarilmagan amallarni bekor qilib, hisobni yangilang.');
      return api.patch(`/orders/${base.id}/items/${item.id}/delta`, { delta: intent.delta }, options);
    },
    onChange: (scope, order, pending, error) => {
      if (!mountedRef.current) return;
      setMutationStatus({ pending, error });
      if (selectionKeyRef.current !== scope) return;
      const next = order?.status === 'cancelled' ? null : order;
      activeOrderRef.current = next;
      setActiveOrder(next);
    },
    onConfirmed: (scope, order, intent) => {
      if (!mountedRef.current) return;
      if (order?.table_id) {
        const busy = order.status !== 'cancelled' && !order.is_paid;
        setTables(previous => previous.map(table => table.id === order.table_id ? { ...table, status: busy ? 'occupied' : 'available', is_occupied: busy } : table));
      }
      if (selectionKeyRef.current !== scope) return;
      if (intent.kind === 'add' && intent.menu.is_weighted) openWeightModalIfNeeded(order, intent.menu.id);
    },
  });
  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);
  useEffect(() => { onOrderViewChange?.(activeTab === 'pos' && !browsingTables); }, [activeTab, browsingTables, onOrderViewChange]);
  useEffect(() => () => onOrderViewChange?.(false), [onOrderViewChange]);
  const queueIntent = intent => {
    const queue = mutationQueueRef.current;
    if (queue.error) return;
    const barrier = queue.pending ? null : orderQueueRef.current;
    latestRequestIdRef.current += 1;
    orderQueueRef.current = queue.enqueue(selectionKeyRef.current, activeOrderRef.current, { ...intent, barrier },
      crypto.randomUUID?.() || `pos_${Date.now()}_${Math.random().toString(36).slice(2)}`);
  };

  useEffect(() => {
    latestRequestIdRef.current += 1;
    fetchVersionRef.current += 1;
    setOrderReadError(null);
    setWeightModalItem(null);
    setSizeModalItem(null);
  }, [selectionKey]);


  const handleTransferTable = async (targetTableId) => {
    if (!selectedTable || !targetTableId || mutationQueueRef.current.pending) return;
    setTransferLoading(true);
    try {
      const target = tables.find(table => table.id === targetTableId);
      if (target?.is_occupied || target?.status === 'occupied') {
        const preview = await api.get(`/tables/${selectedTable.id}/merge-preview/${targetTableId}`);
        setMergePreview({ ...preview, source_label: [selectedTable.room, selectedTable.name || `${label('Stol #')}${selectedTable.number}`].filter(Boolean).join(' · '), target_label: [target.room, target.name || `${label('Stol #')}${target.number}`].filter(Boolean).join(' · '), key: crypto.randomUUID?.() || `merge_${Date.now()}` });
        return;
      }
      const res = await api.post(`/tables/${selectedTable.id}/transfer/${targetTableId}`);
      showToast(res.message || "Buyurtma muvaffaqiyatli ko'chirildi! ✅", 'success');
      setTransferModalOpen(false);
      const dest = tables.find((t) => t.id === targetTableId);
      if (dest) setSelectedTable(dest);
      loadInitialData();
    } catch (err) {
      showToast(err.message || "Ko'chirishda xatolik yuz berdi", 'urgent');
    } finally {
      setTransferLoading(false);
    }
  };

  const handleMergeAccounts = async () => {
    if (!mergePreview || transferLoading || mutationQueueRef.current.pending) return;
    setTransferLoading(true);
    try {
      const payload = Object.fromEntries(['source_order_id', 'target_order_id', 'source_version', 'target_version'].map(key => [key, mergePreview[key]]));
      const result = await api.post(`/tables/${mergePreview.source_table_id}/merge/${mergePreview.target_table_id}`, payload,
        { idempotent: true, headers: { 'Idempotency-Key': mergePreview.key } });
      const target = tables.find(table => table.id === mergePreview.target_table_id);
      latestRequestIdRef.current += 1;
      selectionKeyRef.current = `table:${mergePreview.target_table_id}`;
      if (target) setSelectedTable(target);
      activeOrderRef.current = result.order;
      setActiveOrder(result.order);
      setTransferModalOpen(false); setMergePreview(null);
      showToast(label('Hisoblar birlashtirildi'), 'success');
      loadInitialData();
    } catch (error) {
      showToast(error.message, 'urgent');
      if (error.status === 409) { setMergePreview(null); loadInitialData(); }
    } finally { setTransferLoading(false); }
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

  // Back/Forward navigates the panel; it must never send, delete or pay for an order.
  const navigationDialog = receiptModalOpen ? 'receipt' : checkoutModalOpen ? 'checkout'
    : weightModalItem ? 'weight' : sizeModalItem ? 'size' : transferModalOpen ? 'transfer'
    : kitchenNoteModalOpen ? 'note' : showTableBrowser ? 'tables'
    : showOrderPicker ? 'orders' : customerDetailsOpen ? 'customer' : null;
  usePanelHistory(!isPrivileged, {
    tab: activeTab, browsing: browsingTables,
    mobile: browsingTables ? 'menu' : mobileTab,
    table: browsingTables ? null : selectedTable?.id || null,
    dialog: navigationDialog,
    item: navigationDialog === 'weight' ? weightModalItem?.id : navigationDialog === 'size' ? sizeModalItem?.id : null,
  }, state => {
    if (state.table && selectedTable?.id !== state.table) {
      const table = tables.find(table => table.id === state.table);
      if (!table) { setBrowsingTables(true); return; }
      setSelectedTable(table);
    }
    setActiveTab(state.tab);
    setBrowsingTables(state.browsing);
    setMobileTab(state.mobile);
    setReceiptModalOpen(state.dialog === 'receipt');
    setCheckoutModalOpen(state.dialog === 'checkout');
    setTransferModalOpen(state.dialog === 'transfer');
    setKitchenNoteModalOpen(state.dialog === 'note');
    setShowTableBrowser(state.dialog === 'tables');
    setShowOrderPicker(state.dialog === 'orders');
    setCustomerDetailsOpen(state.dialog === 'customer');
    setWeightModalItem(state.dialog === 'weight' ? activeOrder?.items?.find(item => item.id === state.item) || null : null);
    setSizeModalItem(state.dialog === 'size' ? activeOrder?.items?.find(item => item.id === state.item) || null : null);
  }, () => !weightSaveLock.current && !savingSize && !transferLoading && !sendingToKitchen);

  // Waiter KPI today
  const [waiterKpi, setWaiterKpi] = useState({ sales: 0, orders: 0, share: 0 });

  // Har 30 soniyada stol bandlik vaqtini qayta hisoblash (jonli daqiqa oshishi)
  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), 30000);
    return () => clearInterval(timer);
  }, []);

  // 2. Stol qancha vaqtdan beri bandligi (masalan 45 daq) va
  // oshxonaga yuborilmagan taomlar soni (sent_quantity < quantity yig'indisi)
  const getTableOccupiedInfo = useCallback(
    (tbl) => {
      if (!tbl) return { isOccupied: false, durationStr: null, unsentCount: 0 };
      const isBusy = tbl.status === 'occupied' || tbl.is_occupied;
      if (!isBusy) return { isOccupied: false, durationStr: null, unsentCount: 0 };

      let ord = null;
      if (selectedTable?.id === tbl.id && activeOrder) {
        ord = activeOrder;
      } else {
        ord = (orders || []).find(
          (o) =>
            (o.table_id === tbl.id || o.table?.id === tbl.id) &&
            !o.is_paid &&
            o.status !== 'cancelled' &&
            o.status !== 'completed'
        );
      }

      let durationStr = null;
      let unsentCount = 0;

      if (ord) {
        if (ord.created_at) {
          const start = new Date(ord.created_at).getTime();
          const diffMins = Math.max(0, Math.floor((Date.now() - start) / 60000));
          if (diffMins < 60) {
            durationStr = `${diffMins} daq`;
          } else {
            const hrs = Math.floor(diffMins / 60);
            const mins = diffMins % 60;
            durationStr = `${hrs}s ${mins}daq`;
          }
        }

        const items = ord.items || [];
        unsentCount = items.reduce((sum, it) => {
          const qty = Number(it.quantity) || 0;
          const sent = Number(it.sent_quantity) || 0;
          return sum + Math.max(0, qty - sent);
        }, 0);
      }

      return { isOccupied: true, durationStr, unsentCount, order: ord };
    },
    [selectedTable, activeOrder, orders]
  );

  // 3. Load initial data (xatoni ushlaydi, bo'sh ro'yxat bilan jimgina davom etmaydi)
  const loadInitialData = async () => {
    if (initialLoadRef.current) return;
    initialLoadRef.current = true;
    setLoading(true);
    setLoadError(null);
    try {
      const [tablesData, menuData, callsData, ordersData, readyData] = await Promise.all([
        api.get(`/tables/?restaurant_id=${restaurantId}`),
        api.get(`/menu/full/${restaurantId}`),
        api.get(`/orders/calls?restaurant_id=${restaurantId}`),
        api.get(`/orders/?restaurant_id=${restaurantId}&active_only=true&limit=300&include_items=true`),
        api.get(`/orders/?restaurant_id=${restaurantId}&ready_for_delivery=true&limit=300&include_items=true`),
      ]);

      setTables(tablesData || []);
      setCategories(menuData || []);
      // Menyu rasmlarini fonda oldindan yuklaymiz — ofitsiant
      // kategoriyani almashtirganda rasm kutib turmasin.
      if (menuData && menuData.length > 0 && !selectedCatId) {
        setSelectedCatId(previous => previous || menuData[0].id);
      }
      setCalls(callsData || []);
      setOrders(ordersData || []);

      setReadyOrders(readyData || []);

      // Select first table if none selected
      if (isPrivileged && tablesData && tablesData.length > 0) {
        setSelectedTable(previous => previous || tablesData[0]);
      }
      setLoadError(null);
    } catch (err) {
      console.error('Waiter load error:', err);
      setLoadError(err?.message || "Ma'lumot yuklanmadi");
    } finally {
      initialLoadRef.current = false;
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, [restaurantId]);

  // Load active order for selected table (accepts table object or table id)
  const fetchTableActiveOrder = async (tblOrId) => {
    const tableIdToFetch = typeof tblOrId === 'object' ? tblOrId?.id : tblOrId;
    if (!tableIdToFetch) return;
    if (selectionKeyRef.current !== `table:${tableIdToFetch}`) return;
    if (mutationQueueRef.current?.has(`table:${tableIdToFetch}`)) return;
    const version = ++fetchVersionRef.current;
    const mutationVersion = latestRequestIdRef.current;
    const hasCachedOrder = activeOrderRef.current?.table_id === tableIdToFetch;
    if (!hasCachedOrder) setOrderLoading(true);
    try {
      const activeOrders = await api.get(`/orders/table/${tableIdToFetch}/active`);
      if (mutationQueueRef.current?.has(`table:${tableIdToFetch}`) || version !== fetchVersionRef.current || mutationVersion !== latestRequestIdRef.current || selectionKeyRef.current !== `table:${tableIdToFetch}`) return;
      if (activeOrders?.length > 1) {
        setActiveOrder(null);
        setLoadError("Stolda bir nechta eski hisob bor. Kassir tekshirishi kerak");
        return;
      }
      setOrderReadError(null);
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
      if (version === fetchVersionRef.current && selectionKeyRef.current === `table:${tableIdToFetch}`) setOrderReadError(err.message);
    } finally {
      if (version === fetchVersionRef.current) setOrderLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTable && orderType === 'table') {
      if (activeOrderRef.current?.table_id !== selectedTable.id) setActiveOrder(null);
      fetchTableActiveOrder(selectedTable);
    }
  }, [selectedTable?.id, orderType]);

  const selectedTableRef = useRef(selectedTable);
  useEffect(() => {
    selectedTableRef.current = selectedTable;
  }, [selectedTable]);

  // 4. Qayta yuklash: 'restaron:ws-open', 'visibilitychange' (ko'rinadigan) va 'online' hodisalarida
  // Zaxira sifatida sahifa ko'rinib turganda har 30 soniyada tables ro'yxatini yangilash
  useEffect(() => {
    const handleReload = () => {
      loadInitialData();
      if (selectedTableRef.current) {
        fetchTableActiveOrder(selectedTableRef.current);
      }
    };

    const handleWsOpen = () => {
      handleReload();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        handleReload();
      }
    };

    const handleOnline = () => {
      handleReload();
    };

    window.addEventListener('restaron:ws-open', handleWsOpen);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('online', handleOnline);

    const pollInterval = setInterval(async () => {
      if (document.visibilityState === 'visible') {
        try {
          const [freshTables, freshOrders, freshReady, freshCalls] = await Promise.all([
            api.get(`/tables/?restaurant_id=${restaurantId}`),
            api.get(`/orders/?restaurant_id=${restaurantId}&active_only=true&limit=300&include_items=true`),
            api.get(`/orders/?restaurant_id=${restaurantId}&ready_for_delivery=true&limit=300&include_items=true`),
            api.get(`/orders/calls?restaurant_id=${restaurantId}`),
          ]);
          if (Array.isArray(freshTables)) {
            setTables(freshTables);
          }
          if (Array.isArray(freshOrders)) {
            setOrders(freshOrders);
            if (selectedTableRef.current) await fetchTableActiveOrder(selectedTableRef.current);
          }
          if (Array.isArray(freshReady)) setReadyOrders(freshReady);
          if (Array.isArray(freshCalls)) setCalls(freshCalls);
        } catch (_) {}
      }
    }, 30000);

    return () => {
      window.removeEventListener('restaron:ws-open', handleWsOpen);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('online', handleOnline);
      clearInterval(pollInterval);
    };
  }, [restaurantId]);

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
    if (!addEventListener) return;
    const unsub = addEventListener('*', (event) => {
      const eventTableId = event.table_id ?? event.order?.table_id;
      if (['order_updated', 'new_order', 'order_paid', 'order_cancelled', 'table_status_updated'].includes(event.type)
          && mutationQueueRef.current?.has(selectionKeyRef.current)
          && (eventTableId === selectedTable?.id || event.order?.id === activeOrderRef.current?.id)) return;
      if (event.type === 'call_waiter') {
        if (soundEnabled && playChime) playChime('urgent');
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).then((data) => setCalls(data || [])).catch(() => {});
      } else if (event.type === 'call_completed') {
        api.get(`/orders/calls?restaurant_id=${restaurantId}`).then((data) => setCalls(data || [])).catch(() => {});
      } else if (event.type === 'order_ready') {
        if (soundEnabled && playChime) playChime('success');
        api.get(`/orders/?restaurant_id=${restaurantId}&ready_for_delivery=true&limit=300&include_items=true`)
          .then((data) => setReadyOrders(data || []))
          .catch(() => {});
      } else if (event.type === 'order_delivered') {
        setReadyOrders((prev) => prev.filter((o) => o.id !== event.order_id));
      } else if (event.type === 'table_status_updated') {
        const nextStatus = event.new_status || event.status;
        setTables((prev) =>
          prev.map((t) =>
            t.id === eventTableId
              ? {
                  ...t,
                  status: nextStatus || t.status,
                  is_occupied: event.is_occupied !== undefined ? event.is_occupied : (nextStatus === 'occupied'),
                }
              : t
          )
        );
        if (orderType === 'table' && selectedTable && eventTableId === selectedTable.id) {
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
      } else if (event.type === 'order_paid' || event.type === 'order_cancelled') {
        // 2. Stol faqat order_paid, order_cancelled yoki table_status_updated (status=available) kelganda bo'shasin
        const closedId = event.order_id ?? event.order?.id;
        setOrders((prev) => prev.filter((o) => o.id !== closedId));
        if (orderType === 'table' && selectedTable && eventTableId === selectedTable.id) {
          fetchTableActiveOrder(eventTableId);
        } else if (activeOrderRef.current?.id === closedId) {
          setActiveOrder(null);
        }
      } else if (event.type === 'order_updated' || event.type === 'new_order') {
        // 2. 'bekor qilingan' deb faqat event.order?.status === 'cancelled' bo'lganda hisobla
        const isCancelled = event.order?.status === 'cancelled';
        if (event.order) {
          setOrders((prev) => {
            if (isCancelled || event.order.is_paid) return prev.filter((o) => o.id !== event.order.id);
            const existing = prev.find((o) => o.id === event.order.id);
            const updated = latestOrder(existing, event.order);
            return existing ? prev.map((o) => o.id === updated.id ? updated : o) : [...prev, updated];
          });
        }
        if (eventTableId) {
          setTables((prev) =>
            prev.map((t) => {
              if (t.id !== eventTableId) return t;
              return {
                ...t,
                status: isCancelled ? 'available' : 'occupied',
                is_occupied: !isCancelled,
              };
            })
          );
        }
        if (orderType === 'table' && selectedTable && eventTableId === selectedTable.id) {
          if (event.order) {
            if (isCancelled) {
              setActiveOrder(null);
            } else {
              if (activeOrderRef.current && activeOrderRef.current.id !== event.order.id) {
                fetchTableActiveOrder(eventTableId);
              } else {
                setActiveOrder((prev) => latestOrder(prev, event.order));
              }
            }
          } else {
            // event.order yo'q bo'lsa stolni BO'SH qilma: band qoldir va tanlangan stol uchun fetchTableActiveOrder(eventTableId) bilan yangila
            fetchTableActiveOrder(eventTableId);
          }
        } else if (event.order && activeOrderRef.current?.id === event.order.id) {
          setActiveOrder((prev) => isCancelled ? null : latestOrder(prev, event.order));
        }
      } else if (event.type === 'stop_list_updated') {
        // 5. stop_list_updated hodisasini tingla va menyudagi taom mavjudligini yangila (CustomerMenu.jsx shaklida)
        if (event.item_id) {
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
        }
      }
    });
    return () => unsub();
  }, [addEventListener, selectedTable, orderType, soundEnabled, playChime, restaurantId]);

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
      setWeightEditedField('price');
      setWeightValue('');
      setPriceValue('');
    }
  };

  // Tortiladigan taomning narxi kiritilganmi?
  // Summa yozilgan bo'lsa yetarli — kg kiritish SHART EMAS.
  const isPriced = (it) =>
    (it.manual_price !== null && it.manual_price !== undefined) || it.weight > 0;

  // One recoverable queue owns create/add/delta, including rapid first taps.
  const handleAddItem = menuItem => {
    if (orderLoading || orderReadError || mutationQueueRef.current.error || sendingToKitchen) return;
    if (menuItem.is_stop_list || menuItem.is_available === false) {
      showToast(`"${menuItem.name}" hozirda stop-listda (tugagan)`, 'warning'); return;
    }
    if (!selectedTable && orderType === 'table') { showToast('Iltimos, avval stolni tanlang', 'warning'); return; }
    const existing = activeOrderRef.current?.items?.find(item => item.menu_item_id === menuItem.id && !item.is_weighted);
    if (existing?.quantity >= 500) { showToast('Taom miqdori 500 dan oshishi mumkin emas', 'warning'); return; }
    const context = { restaurant_id: restaurantId, order_type: orderType === 'table' ? 'dine_in' : orderType };
    if (orderType === 'table') { context.table_id = selectedTable.id; context.hall_name = selectedTable.room || 'Zal'; }
    else {
      context.customer_name = customerName.trim() || (orderType === 'takeaway' ? 'Olib ketish mijoz' : 'Dastavka mijoz');
      context.customer_phone = customerPhone.trim() || null;
      if (orderType === 'delivery') context.delivery_address = deliveryAddress.trim() || 'Manzil';
    }
    queueIntent({ kind: 'add', menu: menuItem, quantity: 1, context });
  };

  const handleQtyChange = (item, delta) => {
    const current = activeOrderRef.current?.items?.find(line => line.id === item.id);
    if (!current || mutationQueueRef.current.error || sendingToKitchen) return;
    if (delta < 0 && !canDecreaseOrderItem(user, current)) {
      showToast('Oshxonaga yuborilgan taomni ofitsiant yoki admin kamaytiradi.', 'warning'); return;
    }
    if (current.quantity + delta > 500) { showToast('Taom miqdori 500 dan oshishi mumkin emas', 'warning'); return; }
    queueIntent({ kind: 'delta', itemId: current.id, menuId: current.menu_item_id, delta });
  };

  // Delete item from order — Darhol ekrandan olib tashlaydi
  const handleDeleteItem = async (itemId) => {
    if (!activeOrder || mutationQueueRef.current.pending) return;
    const item = activeOrder.items?.find(line => line.id === itemId);
    if (!item || !canDeleteOrderItem(user, item)) {
      showToast('Oshxonaga yuborilgan taomni ofitsiant yoki admin o‘chiradi.', 'warning'); return;
    }
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
        ...previewOrderTotals(prev, sub),
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
      showToast(errMsg, 'urgent');
      if (selectedTable) fetchTableActiveOrder(selectedTable);
    }
  };

  // Tortiladigan taom narxini saqlash.
  // Only the last edited field is sent; the backend derives its counterpart.
  const handleSaveWeight = async () => {
    if (!activeOrder || !weightModalItem || weightSaveLock.current) return;
    let body;
    try { body = weightedUpdatePayload(weightModalItem, weightEditedField, priceValue, weightValue); }
    catch (error) { showToast(error.message, 'warning'); return; }
    weightSaveLock.current = true;
    setSavingWeight(true);
    const scope = selectionKey;
    try {
      await orderQueueRef.current;
      const updated = await api.patch(
        `/orders/${activeOrder.id}/items/${weightModalItem.id}/weight`,
        body
      );
      if (selectionKeyRef.current === scope) setActiveOrder(updated);
      setWeightModalItem(null);
      setWeightValue('');
      setPriceValue('');
    } catch (err) {
      showToast(err.message || 'Narxni saqlashda xatolik', 'urgent');
    } finally {
      weightSaveLock.current = false;
      setSavingWeight(false);
    }
  };

  // O'lchanadigan taom hajmini saqlash ("1.5 L", "1.4 kg")
  const handleSaveSize = async (value) => {
    if (!activeOrder || !sizeModalItem) return;
    setSavingSize(true);
    const scope = selectionKey;
    try {
      await orderQueueRef.current;
      const updated = await api.patch(
        `/orders/${activeOrder.id}/items/${sizeModalItem.id}/size`,
        { portion_size: (value ?? sizeValue).trim() || null }
      );
      if (selectionKeyRef.current === scope) setActiveOrder(updated);
      setSizeModalItem(null);
      setSizeValue('');
    } catch (err) {
      showToast(err.message || 'Hajmni saqlashda xatolik', 'urgent');
    } finally {
      setSavingSize(false);
    }
  };

  // Save notes
  const handleSaveNotes = async () => {
    if (!activeOrder) return;
    const scope = selectionKey;
    try {
      await orderQueueRef.current;
      const updated = await api.patch(`/orders/${activeOrder.id}/notes`, {
        kitchen_note: kitchenNote,
      });
      if (selectionKeyRef.current === scope) setActiveOrder(updated);
      setKitchenNoteModalOpen(false);
    } catch (err) {
      showToast(err.message || 'Xatolik', 'urgent');
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
      showToast("Buyurtmada taomlar yo'q! Avval o'ng tomondan taom qo'shing.", "warning");
      return;
    }
    setSendingToKitchen(true);
    const scope = selectionKey;
    try {
      await orderQueueRef.current;
      if (selectionKeyRef.current !== scope) return;
      const res = await api.post(
        `/orders/${activeOrder.id}/send-to-kitchen${reprint ? '?reprint=true' : ''}`,
        {},
        { idempotent: true }
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

      // 1. Javobdan keyin qisqa tasdiq toasti (konfeti olib tashlangan)
      showToast("Buyurtma oshxonaga muvaffaqiyatli yuborildi", "success", "Oshxona");

      setKitchenSendSuccess(true);
      setTimeout(() => setKitchenSendSuccess(false), 4000);
      if (soundEnabled && playChime) playChime('success');
      if (orderType === 'table') await fetchTableActiveOrder(selectedTable);
      else {
        const fresh = await api.get(`/orders/${activeOrder.id}`);
        if (selectionKeyRef.current === scope) setActiveOrder(fresh);
      }
      api.get(`/orders/?restaurant_id=${restaurantId}&active_only=true&limit=300&include_items=true`).then((d) => setOrders(d || [])).catch(() => {});

      // 2. tickets[].job_id lar bo'yicha GET /receipts/print-jobs?ids=... ni har 1s (max 15s) so'rab turish
      const tickets = res.tickets || [];
      const jobIds = tickets.map((t) => t.job_id).filter(Boolean);

      if (jobIds.length > 0) {
        let secondsPassed = 0;
        let warnedPending = false;

        const pollTimer = setInterval(async () => {
          secondsPassed += 1;
          try {
            const jobs = await api.get(`/receipts/print-jobs?ids=${jobIds.join(',')}`);
            if (Array.isArray(jobs) && jobs.length > 0) {
              const allDone = jobs.every((j) => j.status === 'done');
              const hasPending = jobs.some((j) => j.status === 'pending' || j.status === 'printing');

              // Hammasi done bo'lsa toast: Chek chiqdi
              if (allDone) {
                clearInterval(pollTimer);
                showToast("Chek printerga uzatildi", "success", "Printer");
                return;
              }

              // 8 soniyadan keyin ham pending bo'lsa sariq xabar:
              // Chek hali chiqmadi (printer nomi), tizim qayta urinyapti.
              // Bu holatda 'Qayta chiqarish' tugmasini TAKLIF QILMA (ikki chek chiqib qoladi).
              if (secondsPassed >= 8 && hasPending && !warnedPending) {
                warnedPending = true;
                const pNames = Array.from(
                  new Set(
                    jobs
                      .filter((j) => j.status === 'pending' || j.status === 'printing')
                      .map((j) => j.printer_name)
                      .filter(Boolean)
                  )
                ).join(', ') || 'oshxona printeri';

                showToast(`Chek hali chiqmadi (${pNames}), tizim qayta urinyapti`, "warning", "Kutilmoqda");
              }
            }

            if (secondsPassed >= 15) {
              clearInterval(pollTimer);
            }
          } catch (pollErr) {
            console.warn('Print jobs polling xatosi:', pollErr);
            if (secondsPassed >= 15) {
              clearInterval(pollTimer);
            }
          }
        }, 1000);
      }
    } catch (err) {
      showToast(err.message || 'Oshxonaga yuborishda xatolik yuz berdi', 'urgent');
    } finally {
      setSendingToKitchen(false);
    }
  };


  // Admin zakas olgandan keyin darhol mijoz chekini chiqarish.
  // Ofitsiantda bu tugma yo'q — chekni kassa (admin) chiqaradi.
  const handlePrintBill = async () => {
    if (!selectedTable && orderType === 'table') {
      showToast('Avval stolni tanlang', 'warning');
      return;
    }
    if (!activeOrder || !(activeOrder.items || []).length) {
      showToast("Bu stolda hali zakas yo'q", 'warning');
      return;
    }
    setPrintingBill(true);
    try {
      await orderQueueRef.current;
      const res = await api.post(`/orders/${activeOrder.id}/print-bill`, {});
      if (res.raw_text) {
        setThermalReceiptText(res.raw_text);
        setReceiptModalTitle(
          `Mijoz cheki (${selectedTable?.room || orderType} N#${selectedTable?.number || activeOrder.id})`
        );
      }
      // Server `success` maydonida printerdan chiqdi-chiqmaganini aytadi.
      if (res.success === false) {
        setReceiptModalOpen(true);
        showToast(
          `${res.message || 'Chek printerdan chiqmadi'}. Chek ekranda ochildi — "Chop etish" tugmasi orqali chiqarishingiz mumkin.`,
          'warning'
        );
      } else {
        showToast(`Chek ${res.printer_name || 'kassa printeri'} ga yuborildi`, 'success');
      }
    } catch (err) {
      showToast(err.message || 'Chek chiqarishda xatolik', 'urgent');
    } finally {
      setPrintingBill(false);
    }
  };

  // Action: "Bordim" (Resolve waiter call)
  const handleResolveCall = async (callId) => {
    try {
      await api.post(`/orders/calls/${callId}/resolve`, {});
      // Reconcile with persisted state, including duplicate historical calls.
      setCalls(await api.get(`/orders/calls?restaurant_id=${restaurantId}`));
    } catch (err) {
      showToast(err.message || 'Xatolik', 'urgent');
    }
  };

  // Action: "Yetkazib berdim" (Delivered)
  const handleDeliverOrder = async (orderId) => {
    try {
      await api.patch(`/orders/${orderId}/deliver`, {});
      setReadyOrders((prev) => prev.filter((o) => o.id !== orderId));
      confetti({ particleCount: 50, spread: 50 });
    } catch (err) {
      showToast(err.message || 'Xatolik', 'urgent');
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
    <div className="dunyo-pos relative h-full min-h-0 overflow-hidden bg-slate-950 text-slate-100 flex flex-col font-sans select-none" data-menu-layout={compactMenu ? 'compact' : undefined} data-mobile-view={mobileTab} data-testid="pos-workspace">
      {/* 6. Ulanish yo'q bo'lsa tepada sariq banner: Aloqa yo'q, qayta ulanmoqda */}
      {connected === false && (showConnectionNotice || connectionError) && (
        <div className="bg-amber-500/95 text-slate-950 font-bold px-4 py-2 text-center text-xs sm:text-sm flex items-center justify-center gap-2 shadow-md shrink-0 z-50">
          <RefreshCw className="w-4 h-4 animate-spin text-slate-950 shrink-0" />
          <span>{connectionError || label(connectionPhase === 'connecting' ? 'Jonli aloqa o‘rnatilmoqda...' : "Aloqa yo'q, qayta ulanmoqda...")}</span>
          {!connectionError && <button type="button" onClick={reconnect} className="min-h-[36px] px-2 rounded-lg border border-black/30 shrink-0">{label('Qayta urinish')}</button>}
        </div>
      )}

      {/* 3. Ma'lumot yuklanmadi qizil blok + Qayta urinish tugmasi */}
      {loadError && (
        <div className="bg-red-950/95 border-b border-red-700 text-red-200 px-4 py-2.5 flex items-center justify-between gap-4 shadow-lg shrink-0 z-40">
          <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{label("Ma'lumot yuklanmadi:")}{loadError}</span>
          </div>
          <button
            onClick={() => loadInitialData()}
            className="flex items-center gap-1.5 px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold transition-all shrink-0 active:scale-95 shadow"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>{label("Qayta urinish")}</span>
          </button>
        </div>
      )}

      {/* Printer statusi (navbat to'lib qolsa yoki printer ishlamasa ogohlantirish) */}
      {isPrivileged && <PrinterStatusBanner />}

      {/* ─── Yuqori panel ──────────────────────────────────────────── */}
      {(isPrivileged || activeTab !== 'pos') && <header className="min-h-[52px] py-1 bg-emerald-950/80 border-b border-emerald-800/60 px-2 sm:px-4 flex items-center justify-between shadow-lg backdrop-blur-md shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          {/* "Stollar" — chaqiruvlar yoki tayyor taomlardan POS ekraniga
              qaytish tugmasi. */}
          <button
            onClick={() => {
              setActiveTab('pos');
              setOrderType('table');
              setBrowsingTables(true);
            }}
            className={`min-h-[44px] flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-black transition-all active:scale-95 ${activeTab === 'pos'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'bg-black/40 border border-emerald-800/40 text-slate-300 hover:text-white'
              }`}
          >
            {activeTab === 'pos' && !browsingTables ? <ArrowLeft className="w-4 h-4" /> : <UtensilsCrossed className="w-4 h-4" />}
            <span>{label("Stollar")}</span>
          </button>

        </div>

        {/* Right Info: Chaqiruvlar badgi, Waiter Name, Sound toggle */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Chaqiruvlar Tab Button */}
          <button
            onClick={() => setActiveTab('calls')}
            aria-label={`${label('Chaqiruvlar')}${calls.length ? ` (${calls.length})` : ''}`}
            className={`relative min-w-[44px] min-h-[44px] flex items-center justify-center gap-1 px-2 lg:px-3.5 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === 'calls'
                ? 'bg-amber-500 text-slate-950'
                : calls.length ? 'bg-amber-500/20 border border-amber-500 text-amber-200' : 'bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-850'
              }`}
          >
            <BellRing className="w-4 h-4" />
            <span className="hidden lg:inline">{label("Chaqiruvlar")}</span>
            {calls.length > 0 && (
              <span className="w-6 h-6 rounded-full bg-red-600 text-white text-xs font-black flex items-center justify-center animate-pulse">
                {calls.length}
              </span>
            )}
          </button>

          {/* Tayyor taomlar Tab Button */}
          <button
            onClick={() => setActiveTab('ready')}
            aria-label={`${label('Tayyor')}${readyOrders.length ? ` (${readyOrders.length})` : ''}`}
            className={`relative min-w-[44px] min-h-[44px] flex items-center justify-center gap-1 px-2 lg:px-3.5 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === 'ready'
                ? 'bg-emerald-500 text-slate-950'
                : 'bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-850'
              }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span className="hidden lg:inline">{label("Tayyor")}</span>
            {readyOrders.length > 0 && (
              <span className="w-6 h-6 rounded-full bg-emerald-600 text-white text-xs font-black flex items-center justify-center">
                {readyOrders.length}
              </span>
            )}
          </button>

          {/* Sound toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className="min-w-[44px] min-h-[44px] p-2.5 rounded-xl bg-black/30 border border-slate-800 text-slate-400 hover:text-white flex items-center justify-center"
            title={label("Ovozli signallar")}
          >
            {soundEnabled ? <Volume2 className="w-5 h-5 text-emerald-400" /> : <VolumeX className="w-5 h-5" />}
          </button>

          {/* Waiter Info */}
          <div className="hidden lg:flex items-center gap-2 pl-2 border-l border-emerald-800/60">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-sm font-bold">
              <User className="w-4 h-4" />
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-bold text-white leading-tight">
                {user?.full_name || user?.username || 'Ofitsiant'}
              </p>
              <p className={`text-xs font-semibold ${connected ? 'text-emerald-400/90' : 'text-red-400/90'}`}>
                {connected ? '● Faol' : '○ Nofaol (aloqa yo\'q)'}
              </p>
            </div>
          </div>
        </div>
      </header>}

      {mutationStatus.pending > 0 && <div role={mutationStatus.error ? 'alert' : 'status'} className={`px-3 py-2 text-xs flex flex-wrap items-center gap-2 ${mutationStatus.error ? 'shrink-0 bg-red-950 text-red-200' : 'absolute bottom-16 left-3 z-30 pointer-events-none rounded-lg shadow-lg bg-slate-800 text-slate-200'}`}>
        <span className="flex-1">{label(mutationStatus.error ? 'Saqlash tasdiqlanmadi. Bajarilmagan amallar navbatda.' : 'Saqlanmoqda...')}{mutationStatus.error?.status ? ` ${mutationStatus.error.message}` : ''}</span>
        {mutationStatus.error && <><button type="button" className="min-h-[44px] px-3 rounded-lg bg-emerald-700 font-bold" onClick={() => mutationQueueRef.current.retry()}>{label('Qayta urinish')}</button>
          <button type="button" className="min-h-[44px] px-3 underline" onClick={() => {
            mutationQueueRef.current.discard();
            if (selectedTableRef.current) fetchTableActiveOrder(selectedTableRef.current);
          }}>{label('Navbatni bekor qilish')}</button></>}
      </div>}
      {orderReadError && !browsingTables && <div role="alert" className="shrink-0 flex items-center justify-between gap-2 px-3 py-2 bg-red-950 text-red-200 text-xs">
        <span>{label('Hisob yuklanmadi. Taom qo‘shishdan oldin qayta urining.')}</span>
        <button type="button" className="min-h-[44px] px-3 font-bold underline" onClick={() => fetchTableActiveOrder(selectedTableRef.current)}>{label('Qayta urinish')}</button>
      </div>}

      {/* ─── Main Content Tabs ───────────────────────────────────────── */}
      {activeTab === 'calls' ? (
        /* ── Chaqiruvlar Royxati ── */
        <div className="max-w-4xl mx-auto p-6 flex-1 min-h-0 overflow-y-auto w-full">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <BellRing className="w-5 h-5 text-amber-400" />
              <span>{label("Mijozlardan faol chaqiruvlar (")}{calls.length})</span>
            </h2>
            <button
              onClick={() => setActiveTab('pos')}
              className="text-xs text-slate-400 hover:text-white underline"
            >{label("← POS Ekraniga qaytish")}</button>
          </div>

          {calls.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 text-slate-400">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <p className="font-bold text-white text-base">{label("Hozircha yangi chaqiruvlar yo'q")}</p>
              <p className="text-xs mt-1">{label("Barcha stollarga xizmat ko'rsatilgan")}</p>
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
                      <h4 className="font-bold text-white text-sm">{label("Stol #")}{c.table_number} {c.room ? `(${c.room})` : ''}
                      </h4>
                      <p className="text-xs text-amber-300/90 mt-0.5 font-medium">
                        💬 {c.note || 'Ofitsiant yordami so\'ralmoqda'}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleResolveCall(c.id)}
                    className="min-h-[44px] px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm shadow-md transition-all active:scale-95"
                  >{label("Qabul qildim")}</button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : activeTab === 'ready' ? (
        /* ── Oshxonadan tayyor taomlar ── */
        <div className="max-w-4xl mx-auto p-6 flex-1 min-h-0 overflow-y-auto w-full">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>{label("Oshxonadan tayyor bo'lgan buyurtmalar (")}{readyOrders.length})</span>
            </h2>
            <button
              onClick={() => setActiveTab('pos')}
              className="min-h-[44px] px-3 py-2 text-sm text-slate-400 hover:text-white underline flex items-center"
            >{label("← POS Ekraniga qaytish")}</button>
          </div>

          {readyOrders.length === 0 ? (
            <div className="p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 text-slate-400">
              <p className="font-bold text-white text-base">{label("Hozirda oshxonada tayyor buyurtma yo'q")}</p>
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
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-400 font-mono text-sm font-black">
                        {ord.order_number}
                      </span>
                      <span className="text-base font-extrabold text-white">{label("Stol #")}{ord.table_number || ord.table_id} {ord.room ? `(${ord.room})` : ''}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-slate-300">
                      {(ord.items || []).map((it) => (
                        <span key={it.id} className="mr-3 font-medium">
                          {it.menu_item_name || 'Taom'}{label("x")}{it.quantity}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeliverOrder(ord.id)}
                    className="min-h-[44px] px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-sm shadow-lg shadow-emerald-500/30 transition-all active:scale-95 flex items-center gap-2"
                  >
                    <Check className="w-4 h-4 stroke-[3]" />
                    <span>{label("Yetkazib berdim")}</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : browsingTables && orderType === 'table' ? (
        <WaiterTablePicker headingActions={!isPrivileged && <button type="button" aria-label={`${label('Chaqiruvlar')}${calls.length ? ` (${calls.length})` : ''}`} onClick={() => setActiveTab('calls')} className="relative min-w-[44px] min-h-[44px] rounded-xl bg-slate-800 border border-slate-600 flex items-center justify-center text-slate-200"><BellRing size={20} />{calls.length > 0 && <span className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full px-1.5 text-xs font-bold">{calls.length}</span>}</button>} tables={tables} zone={selectedZone} onZone={setSelectedZone} label={label} loading={loading} onSelect={table => {
          latestRequestIdRef.current += 1;
          selectionKeyRef.current = `table:${table.id}`;
          setActiveOrder(null);
          setSelectedTable(table);
          setBrowsingTables(false);
          setMobileTab('menu');
          setSearchItemQuery('');
          // Reopening the same table must also refresh its bill.
          if (selectedTable?.id === table.id) fetchTableActiveOrder(table);
        }} />
      ) : (
        /* ── POS EKRANI (stol zakazi) ──────────────────────────────── */
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <nav aria-label={label('Buyurtma ko‘rinishi')} className="pos-mobile-navigation lg:hidden shrink-0 flex items-center gap-2 px-2 py-1.5 border-b border-slate-700 bg-slate-950">
            {!isPrivileged && <button type="button" aria-label={label('Stollarga qaytish')} onClick={() => setBrowsingTables(true)} className="min-w-[44px] min-h-[44px] rounded-xl bg-slate-800 flex items-center justify-center"><ArrowLeft size={20} /></button>}
            <span className="flex-1 min-w-0 text-xs font-bold truncate">
              {orderType === 'table' ? [selectedTable?.room, selectedTable?.name || `${label('Stol #')}${selectedTable?.number || ''}`].filter(Boolean).join(' · ') : activeOrder?.order_number || label('+ Yangi zakaz')}
            </span>
            <button type="button" aria-pressed={mobileTab === 'menu'} onClick={() => setMobileTab('menu')} className={`min-h-[44px] px-3 rounded-xl text-sm font-bold ${mobileTab === 'menu' ? 'bg-emerald-700 text-white' : 'bg-slate-800 text-slate-300'}`}>{label('Taomlar')}</button>
            <button type="button" aria-pressed={mobileTab === 'cart'} onClick={() => setMobileTab('cart')} className={`min-h-[44px] px-3 rounded-xl text-sm font-bold ${mobileTab === 'cart' ? 'bg-emerald-700 text-white' : 'bg-slate-800 text-slate-300'}`}>{label('Buyurtma')} ({(activeOrder?.items || []).reduce((sum, item) => sum + item.quantity, 0)})</button>
          </nav>
          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
            {/* ── Chap Panel: Tanlangan Stol va Zakaz (Katta va qulay shriftlar) ─────────── */}
            <div
              data-testid="pos-order-pane"
              className="pos-order-pane w-full lg:w-[35%] lg:min-w-[360px] lg:max-w-[560px] bg-slate-900/95 border-r border-slate-800 flex flex-col shrink-0 h-full pos-order-container overflow-hidden min-h-0"
            >
            <div data-testid="pos-order-toolbar" className="flex items-center gap-1 px-2 py-1.5 shrink-0 border-b border-slate-700 bg-slate-950">
              {!isPrivileged && <button type="button" aria-label={label('Stollarga qaytish')} onClick={() => setBrowsingTables(true)} className="hidden lg:flex min-w-[44px] min-h-[44px] items-center justify-center rounded-lg bg-slate-800"><ArrowLeft size={20} /></button>}
              {showModeSwitch && canCheckout && <select aria-label={label('Buyurtma turi')} value={orderType} onChange={event => {
                const next = event.target.value;
                if (next === orderType) return;
                setOrderType(next); setActiveOrder(null); setCustomerName(''); setCustomerPhone(''); setDeliveryAddress(''); setOrderSearch('');
                if (next === 'table' && selectedTable) fetchTableActiveOrder(selectedTable);
              }} className="w-[100px] min-h-[44px] rounded-lg bg-slate-900 border border-slate-700 px-1 text-xs font-bold shrink-0">
                <option value="table">{label('Stolda')}</option><option value="takeaway">{label('Olib ketish')}</option><option value="delivery">{label('Dastavka')}</option>
              </select>}
              <button data-testid="pos-select-order" aria-label={label(orderType === 'table' ? 'Stol tanlash' : 'Buyurtma tanlash')} aria-haspopup="dialog" onClick={() => orderType === 'table' ? setShowTableBrowser(true) : setShowOrderPicker(true)} className="flex-1 min-w-0 min-h-[44px] px-2 text-left rounded-lg hover:bg-slate-800">
                <strong className="block truncate text-base">{orderType === 'table' ? (selectedTable?.name || `${label('Stol #')}${selectedTable?.number || 1}`) : (activeOrder?.order_number || label('+ Yangi zakaz'))} <span className="text-slate-400">⌄</span></strong>
                <span className="block text-[11px] text-slate-400 truncate">{orderType === 'table' ? [selectedTable?.room, selectedTable?.is_occupied || selectedTable?.status === 'occupied' ? label('Band') : label("Bo'sh")].filter(Boolean).join(' · ') : customerName || label('Buyurtmalar ro‘yxati')}</span>
              </button>
              {orderType !== 'table' && <button aria-label={label('Mijoz ma’lumotlari')} title={label('Mijoz ma’lumotlari')} onClick={() => setCustomerDetailsOpen(true)} className="w-10 min-h-[44px] shrink-0 flex items-center justify-center rounded-lg text-cyan-300 hover:bg-slate-800"><User size={19} /></button>}
              {orderType === 'table' && activeOrder && selectedTable && <button disabled={mutationStatus.pending > 0} aria-label={label('Ko‘chirish / hisoblarni qo‘shish')} title={label('Ko‘chirish / hisoblarni qo‘shish')} onClick={() => { setMergePreview(null); setTransferModalOpen(true); }} className="w-10 min-h-[44px] shrink-0 flex items-center justify-center text-amber-300 hover:bg-slate-800 rounded-lg disabled:opacity-30"><ArrowRightLeft size={19} /></button>}
              <button aria-label={label('💬 Izoh')} title={label('💬 Izoh')} onClick={() => setKitchenNoteModalOpen(true)} className="w-10 min-h-[44px] shrink-0 flex items-center justify-center rounded-lg text-slate-300 hover:bg-slate-800"><MessageSquare size={19} />{kitchenNote && <span className="text-emerald-400">•</span>}</button>
              {canCheckout && <button aria-label={label('🧾 Chek')} title={label('🧾 Chek')} disabled={!activeOrder || printingBill} onClick={handlePrintBill} className="w-10 min-h-[44px] shrink-0 flex items-center justify-center rounded-lg text-slate-300 hover:bg-slate-800 disabled:opacity-30"><Receipt size={19} /></button>}
            </div>

            {/* Active Items Table: flex-1 to'liq balandlik, hech qanday tor max-h cheklovisiz */}
            {activeOrder?.integrity_warning && (
              <p role="alert" className="border-y border-red-500/40 bg-red-950/70 px-4 py-3 text-sm font-bold text-red-200">
                {activeOrder.integrity_warning}
              </p>
            )}
            <div role="region" aria-label={label('Buyurtma taomlari')} data-testid="pos-order-items" className="flex-1 overflow-y-auto custom-scrollbar overflow-x-hidden min-h-0 overscroll-contain">
              <div className="pos-line-grid pos-line-header sticky top-0 z-[1] text-xs sm:text-sm font-bold text-slate-300 bg-slate-950 px-3 sm:px-4 py-2 border-b border-slate-800 uppercase tracking-wider">
                <span>{label("Taom nomi")}</span>
                <span className="text-center">{label("Soni")}</span>
                <span className="text-right">{label("Jami")}</span>
                <span></span>
              </div>

              {orderLoading ? (
                <div className="p-12 text-center text-sm font-bold text-slate-400">{label("Yuklanmoqda...")}</div>
              ) : !activeOrder || !activeOrder.items || activeOrder.items.length === 0 ? (
                <div className="p-12 text-center text-slate-400 space-y-1">
                  <p className="font-extrabold text-white text-base">{label("Ushbu stolda hali zakaz yo'q")}</p>
                  <p className="text-xs text-slate-400">{label("Menyudan taom tanlang")}</p>
                </div>
              ) : (
                <div className="divide-y divide-slate-800/60">
                  {activeOrder.items.map((it) => (
                    <div
                      key={it.id}
                      className="pos-line-grid items-center px-3 py-2 hover:bg-slate-800/50 transition-colors"
                    >
                      {/* Name & time */}
                      <div className="pos-line-name min-w-0">
                        <p className="font-extrabold text-white text-sm sm:text-base leading-tight line-clamp-2">
                          {it.menu_item_name || 'Taom'}
                        </p>
                      </div>
                      <div className="pos-line-details min-w-0">
                        <p className="text-xs font-mono text-slate-400 mt-1">{label('Narxi')}: {it.unit_price.toLocaleString('uz-UZ')}</p>

                        <div className="flex items-center gap-1.5 flex-wrap mt-0.5 text-xs font-semibold text-slate-400 font-mono leading-none">
                          {/* Tortiladigan taom (baliq, go'sht): SUMMASI */}
                          {it.is_weighted && (
                            <button
                              onClick={() => {
                                setWeightModalItem(it);
                                setWeightEditedField(it.manual_price != null || !it.weight ? 'price' : 'weight');
                                setWeightValue(it.weight ? String(it.weight) : '');
                                setPriceValue(
                                  it.manual_price !== null && it.manual_price !== undefined
                                    ? String(it.manual_price)
                                    : it.total_price
                                      ? String(it.total_price)
                                      : ''
                                );
                              }}
                              title={label("Summasini kiritish")}
                              className={`px-2 py-0.5 rounded text-xs font-black transition-all active:scale-95 inline-block ${isPriced(it)
                                  ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50'
                                  : 'bg-red-600 text-white border border-red-400 animate-pulse'
                                }`}
                            >
                              {isPriced(it)
                                ? `💰 ${Number(it.total_price || 0).toLocaleString('uz-UZ', { maximumFractionDigits: 2 })}` +
                                (it.weight ? `·${it.weight}${it.unit || 'kg'}` : '')
                                : label("💰 Narx yo'q")}
                            </button>
                          )}

                          {/* O'lchanadigan taom hajmi */}
                          {!it.is_weighted && (
                            <button
                              disabled={String(it.id).startsWith('pending:')}
                              onClick={() => {
                                setSizeModalItem(it);
                                setSizeValue(it.portion_size || '');
                              }}
                              title={label("Hajm / o'lchamni kiritish")}
                              className={`px-2 py-0.5 rounded text-xs font-black transition-all active:scale-95 inline-block ${it.portion_size
                                  ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50'
                                  : 'bg-slate-800 text-slate-400 border border-dashed border-slate-600 hover:text-amber-300'
                                }`}
                            >
                              {it.portion_size ? `📏 ${it.portion_size}` : label('📏 Hajm')}
                            </button>
                          )}

                          <span className="pos-item-time">{it.item_time || '12:00'}</span>
                          <span className="pos-item-time">•</span>
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
                                {label(sent > 0 ? 'Oshxonada♨️' : 'Yangi✦')}
                              </span>
                            );
                          })()}
                          {kitchenSentQuantity(it) > 0 && !canDeleteOrderItem(user, it) && <span className="text-[10px] text-slate-400">{label('O‘chirish: ofitsiant yoki admin')}</span>}
                        </div>
                      </div>

                      {/* Quantity Controls [- 1 +] */}
                      <div className="pos-line-qty flex items-center justify-center gap-1">
                        <button
                          type="button"
                          onClick={() => handleQtyChange(it, -1)}
                          disabled={!canDecreaseOrderItem(user, it)}
                          className="min-w-[44px] min-h-[44px] rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-base active:scale-90 shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
                          title={canDecreaseOrderItem(user, it) ? label('Kamaytirish') : label('Oshxonaga yuborilgan: ofitsiant yoki admin kamaytiradi')}
                        >
                          -
                        </button>
                        <span className="text-sm sm:text-base font-black text-white min-w-6 text-center font-mono">
                          {it.quantity}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleQtyChange(it, 1)}
                          className="min-w-[44px] min-h-[44px] rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white flex items-center justify-center font-black text-base active:scale-90 shadow-sm"
                          title={label("Ko'paytirish")}
                        >
                          +
                        </button>
                      </div>

                      {/* Line Total */}
                      <div className="pos-line-total text-right font-black text-emerald-400 text-sm sm:text-base font-mono">
                        {it.total_price.toLocaleString('uz-UZ')}
                      </div>

                      {/* Delete (Trash) button */}
                      <div className="pos-line-delete flex justify-end">
                        <button
                          type="button"
                          onClick={() => handleDeleteItem(it.id)}
                          disabled={mutationStatus.pending > 0 || !canDeleteOrderItem(user, it)}
                          className="min-w-[40px] min-h-[44px] rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 active:scale-90 transition-all flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
                          title={canDeleteOrderItem(user, it) ? label("Taomni o'chirish") : label('Oshxonaga yuborilgan: ofitsiant yoki admin o‘chiradi')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div data-testid="pos-order-footer" className={`${canCheckout ? 'pos-payment-footer ' : ''}px-3 py-2 bg-slate-950 border-t border-slate-700 shrink-0 space-y-2`}>
              {kitchenSendSuccess && <p role="status" className="text-xs text-emerald-300 truncate">{label('✅ Buyurtma oshxona navbatiga qabul qilindi')}</p>}
              {(activeOrder?.items || []).some(i => i.is_weighted && !isPriced(i)) && <p className="text-xs text-red-300">{label('Narxi kiritilmagan taom bor:')} {(activeOrder?.items || []).filter(i => i.is_weighted && !isPriced(i)).length}</p>}
              <div className="flex items-center gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] text-slate-400 truncate">{label('Taomlar:')} {(activeOrder?.subtotal || 0).toLocaleString('uz-UZ')}</p>
                  <p aria-label={label('Jami hisob:')} className="text-lg sm:text-xl leading-6 font-bold font-mono text-emerald-400 whitespace-nowrap">{(activeOrder?.total || 0).toLocaleString('uz-UZ')} <span className="text-[10px] font-normal text-slate-400">{label("so'm")}</span></p>
                  <p className="text-[10px] text-slate-400 truncate">{label('Xizmat (')}{activeOrder?.service_fee_percent ?? 12}%): {(activeOrder?.service_fee_amount || 0).toLocaleString('uz-UZ')}</p>
                </div>
                <button onClick={() => handleSendToKitchen(false)} disabled={!activeOrder || sendingToKitchen || Boolean(activeOrder.integrity_warning)} className="pos-kitchen-action shrink-0 min-h-[48px] px-3 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-sm disabled:opacity-35 flex items-center justify-center gap-1">
                  <Send size={18} /><span>{sendingToKitchen ? label('Chop...') : label('Oshxonaga')}</span>
                  {activeOrder && (activeOrder.items || []).some(i => i.quantity > (i.sent_quantity || 0)) && <span className="rounded-md bg-black/15 px-1.5 py-0.5 text-xs">{activeOrder.items.reduce((sum,i) => sum + Math.max(0,i.quantity-(i.sent_quantity||0)),0)}</span>}
                </button>
                {canCheckout && <button onClick={async () => {
                  const scope = selectionKey;
                  await orderQueueRef.current;
                  if (selectionKeyRef.current !== scope || !activeOrderRef.current) return;
                  try {
                    const fresh = await api.get(`/orders/${activeOrderRef.current.id}`);
                    if (selectionKeyRef.current === scope) { setActiveOrder(fresh); setCheckoutModalOpen(true); }
                  } catch (err) { showToast(err.message, 'urgent'); }
                }} disabled={!activeOrder || !activeOrder.items?.length || Boolean(activeOrder.integrity_warning)} className="shrink-0 min-h-[48px] px-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs disabled:opacity-35 flex items-center justify-center gap-1"><CreditCard size={18} />{label("To'lov")}</button>}
              </div>
            </div>
          </div>

          {/* ── O'ng Panel: Kategoriyalar va Taomlar Gridi (Katta va qulay kartochkalar) ───── */}
          <div
            className={`pos-menu-pane flex-1 flex flex-col bg-slate-950 overflow-hidden h-full min-h-0 ${
              mobileTab === 'menu' ? 'flex' : 'hidden lg:flex'
            }`}
          >
            {/* Top Categories Strip */}
            <div className="pos-menu-filters p-3 bg-slate-900/70 border-b border-slate-800 shrink-0">
              {/* 5. Taom ro'yxatida tezkor qidiruv maydoni (nom bo'yicha filtr) */}
              {!compactMenu && <div className="mb-3 relative">
                <Search className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  value={searchItemQuery}
                  onChange={(e) => setSearchItemQuery(e.target.value)}
                  placeholder={label("Taom nomi bo'yicha tezkor qidiruv...")}
                  className="w-full pl-11 pr-10 min-h-[44px] py-2.5 rounded-2xl bg-slate-900 border-2 border-slate-700/80 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-emerald-500 font-medium"
                />
                {searchItemQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchItemQuery('')}
                    className="min-w-[40px] min-h-[40px] absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white flex items-center justify-center transition-colors"
                    title={label("Qidiruvni tozalash")}
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>}

              {!compactMenu && searchItemQuery.trim() && (
                <div className="mb-2 px-1 flex items-center justify-between text-xs sm:text-sm text-slate-400">
                  <span>{label("Qidiruv natijasi:")}{' '}
                    <strong className="text-emerald-400 font-bold">{displayedItems.length}{label("ta")}</strong>{label("taom")}</span>
                  <button
                    type="button"
                    onClick={() => setSearchItemQuery('')}
                    className="text-amber-400 hover:underline font-bold"
                  >{label("Filtrni tozalash")}</button>
                </div>
              )}

              {/* Category buttons list */}
              <div className="pos-menu-categories">
                {categories.map((cat) => {
                  const active = cat.id === selectedCatId && !searchItemQuery.trim();
                  return (
                    <button
                      key={cat.id}
                      onClick={() => {
                        setSelectedCatId(cat.id);
                        setSearchItemQuery('');
                      }}
                      aria-pressed={active}
                      className="pos-menu-category"
                    >
                      <span className="pos-menu-category-name">{getLocalizedName(cat)}</span>
                      <span className="pos-menu-category-count">{(cat.items || []).length}</span>
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
                  const unavailable = isStop || orderLoading || Boolean(orderReadError) || Boolean(mutationStatus.error) || sendingToKitchen;
                  return (
                    <div
                      key={item.id}
                      role="button"
                      tabIndex={unavailable ? -1 : 0}
                      aria-label={getLocalizedName(item)}
                      aria-disabled={unavailable}
                      onClick={() => handleAddItem(item)}
                      onKeyDown={event => { if (!unavailable && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); handleAddItem(item); } }}
                      className={`group relative rounded-3xl bg-slate-900 border-2 border-slate-800 p-3 flex flex-col justify-between hover:border-emerald-500 hover:bg-slate-850 transition-all shadow-lg cursor-pointer select-none active:scale-95 ${
                        unavailable ? 'opacity-50 pointer-events-none' : ''
                      }`}
                    >
                      {/* Thumbnail: Kattaroq rasm */}
                      <div className="pos-product-image h-24 sm:h-32 xl:h-36 w-full rounded-2xl bg-slate-950 overflow-hidden relative mb-2.5 flex items-center justify-center border border-slate-800/80">
                        {item.image_url ? (
                          <img
                            src={item.image_url}
                            alt={getLocalizedName(item)}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                            decoding="async"
                          />
                        ) : (
                          <div className="text-slate-600 flex flex-col items-center">
                            <ImageIcon className="w-8 h-8 mb-1 text-slate-500" />
                            <span className="text-sm font-bold">{label("Taom")}</span>
                          </div>
                        )}

                        {item.is_weighted && (
                          <span className="absolute top-2 left-2 px-2.5 py-1 rounded-lg bg-cyan-600/90 text-white font-black text-xs shadow">{label("⚖️ Tarozida")}</span>
                        )}

                        {isStop && (
                          <span className="absolute inset-x-2 bottom-2 text-center bg-red-600 text-white font-black text-xs py-1 rounded-xl shadow-lg">{label("Tugagan (Stop-list)")}</span>
                        )}
                      </div>

                      {/* Title: Tushunarli va aniq sarlavha */}
                      <h4 className="text-sm sm:text-base font-extrabold text-white group-hover:text-emerald-300 transition-colors line-clamp-2 leading-tight">
                        {getLocalizedName(item)}
                      </h4>

                      {/* Price Badge and Plus button: Kattaroq, aniq ko'rinuvchi narx */}
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                        <span className="px-2 py-1.5 rounded-xl bg-emerald-600 text-white font-bold text-xs sm:text-sm shadow-md font-mono break-words max-w-full">
                          {Math.round(item.price || 0).toLocaleString('uz-UZ')}{' '}{label("so'm")}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <button type="button" onClick={() => setMobileTab('cart')} className="lg:hidden shrink-0 min-h-[56px] px-4 py-2 bg-emerald-700 text-white flex items-center justify-between gap-3 font-bold border-t border-emerald-500">
              <span className="flex items-center gap-2"><ShoppingCart size={20} />{label(orderLoading ? 'Hisob yuklanmoqda...' : 'Buyurtmani ko‘rish')}</span>
              {!orderLoading && <span className="text-right font-mono">{(activeOrder?.total || 0).toLocaleString('uz-UZ')} <span className="text-xs">{label("so'm")}</span></span>}
            </button>
          </div>
        </div>
      </div>
      )}

      {customerDetailsOpen && createPortal(<div className="fixed inset-0 z-[75] bg-black/75 flex items-center justify-center p-3" onClick={event => { if (event.target === event.currentTarget) setCustomerDetailsOpen(false); }}>
        <section ref={customerDialogRef} role="dialog" aria-modal="true" aria-labelledby="pos-customer-title" className="w-full max-w-lg max-h-[85dvh] overflow-y-auto bg-slate-950 text-slate-100 border border-slate-700 rounded-2xl p-4 space-y-4">
          <div className="flex justify-between items-center"><h2 id="pos-customer-title" className="font-bold text-lg">{label('Mijoz ma’lumotlari')}</h2><button aria-label={label('Yopish')} onClick={() => setCustomerDetailsOpen(false)} className="w-11 h-11 flex items-center justify-center rounded-lg hover:bg-slate-800"><X size={22} /></button></div>
          {activeOrder ? <dl className="space-y-3 text-sm">
            <div><dt className="text-slate-400">{label('Mijoz ismi')}</dt><dd className="font-semibold break-words">{activeOrder.customer_name || '—'}</dd></div>
            <div><dt className="text-slate-400">{label('Telefon')}</dt><dd>{activeOrder.customer_phone || '—'}</dd></div>
            {orderType === 'delivery' && <div><dt className="text-slate-400">{label('Manzil')}</dt><dd className="break-words">{activeOrder.delivery_address || '—'}</dd></div>}
          </dl> : <div className="space-y-3">
            <label className="block text-sm text-slate-300">{label('Mijoz ismi')}<input autoComplete="off" value={customerName} onChange={event => setCustomerName(event.target.value)} placeholder={label('Mijoz ismi')} className="block w-full mt-1 px-3 h-12 rounded-xl bg-slate-900 border border-slate-700" /></label>
            <label className="block text-sm text-slate-300">{label('Telefon')}<input type="tel" autoComplete="off" value={customerPhone} onChange={event => setCustomerPhone(event.target.value)} placeholder="+998 90 123 45 67" className="block w-full mt-1 px-3 h-12 rounded-xl bg-slate-900 border border-slate-700" /></label>
            {orderType === 'delivery' && <label className="block text-sm text-slate-300">{label('Manzil')}<textarea value={deliveryAddress} onChange={event => setDeliveryAddress(event.target.value)} rows={2} className="block w-full mt-1 p-3 rounded-xl bg-slate-900 border border-slate-700" /></label>}
          </div>}
          <button onClick={() => setCustomerDetailsOpen(false)} className="w-full min-h-[48px] rounded-xl font-bold bg-emerald-600">{label(activeOrder ? 'Yopish' : 'Davom etish')}</button>
        </section>
      </div>, document.body)}

      {showOrderPicker && createPortal(<div className="fixed inset-0 z-[75] bg-black/75 flex items-center justify-center p-3" onClick={event => { if (event.target === event.currentTarget) setShowOrderPicker(false); }}>
        <section ref={orderPickerRef} role="dialog" aria-modal="true" aria-labelledby="pos-order-picker-title" className="w-full max-w-xl max-h-[85dvh] flex flex-col bg-slate-950 text-slate-100 border border-slate-700 rounded-2xl overflow-hidden">
          <div className="p-4 border-b border-slate-800 shrink-0">
            <div className="flex justify-between items-center mb-3"><h2 id="pos-order-picker-title" className="font-bold text-lg">{label('Buyurtma tanlash')}</h2><button aria-label={label('Yopish')} onClick={() => setShowOrderPicker(false)} className="w-11 h-11 flex items-center justify-center rounded-lg hover:bg-slate-800"><X size={22} /></button></div>
            <input aria-label={label('Buyurtma qidirish')} placeholder={label('Raqam, ism yoki telefon...')} value={orderSearch} onChange={event => setOrderSearch(event.target.value)} className="w-full h-12 rounded-xl px-3 bg-slate-900 border border-slate-700" />
            <button onClick={async () => { const scope = selectionKey; await orderQueueRef.current.catch(() => {}); if (selectionKeyRef.current !== scope) return; latestRequestIdRef.current += 1; setActiveOrder(null); setCustomerName(''); setCustomerPhone(''); setDeliveryAddress(''); setShowOrderPicker(false); setCustomerDetailsOpen(true); }} className="mt-3 w-full min-h-[48px] rounded-xl bg-emerald-600 font-bold">{label('+ Yangi zakaz')}</button>
          </div>
          <div className="p-3 space-y-2 overflow-y-auto min-h-0" data-testid="pos-open-orders">
            {orders.filter(order => order.order_type === orderType && !order.is_paid && !['cancelled', 'completed'].includes(order.status) && `${order.order_number} ${order.customer_name || ''} ${order.customer_phone || ''}`.toLowerCase().includes(orderSearch.trim().toLowerCase())).map(order => <button key={order.id} onClick={async () => {
              const scope = selectionKey; const request = ++latestRequestIdRef.current;
              await orderQueueRef.current.catch(() => {});
              try { const fresh = await api.get(`/orders/${order.id}`); if (selectionKeyRef.current === scope && latestRequestIdRef.current === request) { setActiveOrder(fresh); setCustomerName(fresh.customer_name || ''); setCustomerPhone(fresh.customer_phone || ''); setDeliveryAddress(fresh.delivery_address || ''); setShowOrderPicker(false); } }
              catch (error) { showToast(error.message, 'urgent'); }
            }} className={`w-full min-h-[64px] p-3 text-left rounded-xl border ${activeOrder?.id === order.id ? 'border-amber-400 bg-amber-500/10' : 'border-slate-700 bg-slate-900 hover:border-emerald-500'}`}>
              <span className="flex justify-between gap-3"><strong>{order.order_number}</strong><span className="font-mono text-emerald-400">{Number(order.total || 0).toLocaleString('uz-UZ')}</span></span>
              <span className="block text-sm text-slate-400 truncate mt-1">{order.customer_name || '—'} {order.customer_phone || ''}</span>
            </button>)}
          </div>
        </section>
      </div>, document.body)}

      {showTableBrowser && <div className="fixed inset-0 z-[70] bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6" onClick={event => { if (event.target === event.currentTarget) setShowTableBrowser(false); }}>
        <section ref={tablePickerRef} role="dialog" aria-modal="true" aria-labelledby="pos-table-picker-title" className="w-full max-w-4xl max-h-[85dvh] flex flex-col rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
            <h2 id="pos-table-picker-title" className="text-xl font-bold">{label('Stol tanlash')}</h2>
            <button type="button" aria-label={label('Yopish')} onClick={() => setShowTableBrowser(false)} className="w-11 h-11 flex items-center justify-center rounded-xl hover:bg-slate-800"><X size={22} /></button>
          </div>
          <WaiterTablePicker tables={tables} zone={selectedZone} onZone={setSelectedZone} label={label} loading={loading} onSelect={table => {
            latestRequestIdRef.current += 1; selectionKeyRef.current = `table:${table.id}`;
            setActiveOrder(null); setSelectedTable(table); setShowTableBrowser(false); setMobileTab('menu');
            if (selectedTable?.id === table.id) fetchTableActiveOrder(table);
          }} />
        </section>
      </div>}

      {/* ─── Tortilgan og'irlikni kiritish (baliq 1.35 kg) ──────────── */}
      {weightModalItem && (
        <div className="fixed inset-0 z-[55] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div ref={weightDialogRef} role="dialog" aria-modal="true" aria-label="Tortiladigan taom narxi va og‘irligi" className="bg-slate-900 border-2 border-cyan-600/60 rounded-3xl max-w-md w-full p-5 shadow-2xl max-h-[90dvh] overflow-y-auto">
            <div className="flex items-start justify-between mb-1">
              <div>
                <h3 className="text-base font-black text-white">{label('Narx va og‘irlik')}</h3>
                <p className="text-xs font-bold text-cyan-300 mt-0.5">
                  {weightModalItem.menu_item_name || 'Taom'}
                </p>
              </div>
              <button
                aria-label="Narx oynasini yopish"
                disabled={savingWeight}
                onClick={() => setWeightModalItem(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mb-3">{label('Narx yoki og‘irlikni yozing — ikkinchisi avtomatik hisoblanadi. Oshxonaga yuborilgandan keyin ham tuzatish mumkin.')}</p>
            {weightModalItem.quantity > 1 && <p className="text-xs text-cyan-200 mb-3">Summa — {weightModalItem.quantity} ta uchun jami; og‘irlik — bittasi uchun.</p>}

            <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 mb-3">
              <div className="flex justify-between text-xs text-slate-300 font-semibold">
                <span>1 {weightModalItem.unit || 'kg'} {label("narxi:")}</span>
                <span className="font-mono font-black text-white">
                  {(weightModalItem.unit_price || 0).toLocaleString('uz-UZ')} {label("so'm")}</span>
              </div>
            </div>

            {/* ASOSIY maydon — SUMMA */}
            <label className="block text-xs font-bold text-emerald-400 mb-1.5">{label('Summa (so‘m)')}</label>
            <input
              type="text"
              inputMode="decimal"
              aria-label="Taom summasi"
              disabled={savingWeight}
              autoFocus
              value={priceValue}
              onChange={event => { const values = convertWeightedInput(weightModalItem, 'price', event.target.value); setWeightEditedField('price'); setPriceValue(values.price); setWeightValue(values.weight); }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveWeight();
              }}
              placeholder={label("masalan: 204000")}
              className="w-full p-3.5 rounded-xl bg-slate-950 border-2 border-emerald-600 text-3xl text-white font-mono font-black text-center focus:outline-none focus:border-emerald-400 mb-1"
            />
            {(() => {
              const pr = parseFloat(String(priceValue).replace(',', '.')) || 0;
              if (pr <= 0) return <div className="mb-3" />;
              return (
                <p className="text-center text-sm font-black text-emerald-400 font-mono mb-3">
                  {pr.toLocaleString('uz-UZ', { maximumFractionDigits: 2 })} {label("so'm")}</p>
              );
            })()}

            <label className="block text-xs font-bold text-slate-300 mb-1.5">{label("Og'irlik (")}{weightModalItem.unit || 'kg'})</label>
            <input
              type="text"
              inputMode="decimal"
              aria-label="Taom og‘irligi"
              disabled={savingWeight}
              value={weightValue}
              onChange={(e) => {
                const values = convertWeightedInput(weightModalItem, 'weight', e.target.value);
                setWeightEditedField('weight'); setWeightValue(values.weight); setPriceValue(values.price);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveWeight();
              }}
              placeholder="masalan: 1,5"
              className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-700 text-base text-slate-200 font-mono font-bold text-center focus:outline-none focus:border-cyan-500 mb-4"
            />

            <div className="flex items-center gap-2">
              <button
                disabled={savingWeight}
                onClick={() => setWeightModalItem(null)}
                className="min-h-[44px] px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm font-bold text-slate-300"
              >{label("Keyinroq")}</button>
              <button
                onClick={handleSaveWeight}
                disabled={savingWeight}
                className="min-h-[44px] flex-1 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-sm disabled:opacity-40 active:scale-95 transition-all flex items-center justify-center"
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
                <h3 className="text-base font-black text-white">{label("Hajm / O'lcham")}</h3>
                <p className="text-sm font-bold text-amber-300 mt-0.5">
                  {sizeModalItem.menu_item_name || 'Taom'}
                </p>
              </div>
              <button
                onClick={() => setSizeModalItem(null)}
                className="min-w-[44px] min-h-[44px] text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-slate-400 mb-3">{label("Oshxona va mijoz chekida shu yozuv chiqadi — masalan \"Kola 1.5 L\" yoki \"Baliq 1.4 kg\".")}</p>

            {/* Tez tanlash tugmalari */}
            <div className="mb-3">
              <span className="text-xs font-black text-slate-400 uppercase tracking-wider block mb-1.5">{label("Ichimliklar:")}</span>
              <div className="grid grid-cols-4 gap-1.5 mb-2.5">
                {['0.5 L', '1 L', '1.5 L', '2 L'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleSaveSize(v)}
                    disabled={savingSize}
                    className="min-h-[44px] py-2 rounded-xl bg-slate-800 hover:bg-amber-600 hover:text-slate-950 border border-slate-700 text-sm font-black text-white transition-all active:scale-95 disabled:opacity-40"
                  >
                    {v}
                  </button>
                ))}
              </div>
              <span className="text-xs font-black text-slate-400 uppercase tracking-wider block mb-1.5">{label("Tortiladigan (baliq, go'sht):")}</span>
              <div className="grid grid-cols-4 gap-1.5">
                {['0.5 kg', '1 kg', '1.5 kg', '2 kg'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => handleSaveSize(v)}
                    disabled={savingSize}
                    className="min-h-[44px] py-2 rounded-xl bg-slate-800 hover:bg-amber-600 hover:text-slate-950 border border-slate-700 text-sm font-black text-white transition-all active:scale-95 disabled:opacity-40"
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            {/* Qo'lda yozish */}
            <label className="text-xs font-black text-slate-400 uppercase tracking-wider block mb-1.5">{label("Yoki o'zingiz yozing:")}</label>
            <input
              type="text"
              value={sizeValue}
              onChange={(e) => setSizeValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveSize(sizeValue);
              }}
              placeholder={label("Masalan: 1.75 kg, katta kosa, 0.33 L")}
              maxLength={50}
              className="w-full p-3 min-h-[44px] rounded-xl bg-slate-950 border-2 border-slate-800 text-sm text-white font-bold focus:outline-none focus:border-amber-500 mb-4"
            />

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSaveSize('')}
                disabled={savingSize}
                className="min-h-[44px] px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-red-900/60 text-sm font-bold text-slate-300 disabled:opacity-40"
              >{label("Tozalash")}</button>
              <button
                onClick={() => handleSaveSize(sizeValue)}
                disabled={savingSize}
                className="min-h-[44px] flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-sm disabled:opacity-40 active:scale-95 transition-all flex items-center justify-center"
              >
                {savingSize ? 'Saqlanmoqda...' : 'Saqlash'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Kitchen Note Modal (Комент. к кухne) ───────────────────── */}
      {kitchenNoteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-5 shadow-2xl">
            <h3 className="text-sm font-bold text-white mb-2">{label("Oshxonaga izoh (Комент. к кухне)")}</h3>
            <textarea
              rows={3}
              value={kitchenNote}
              onChange={(e) => setKitchenNote(e.target.value)}
              placeholder={label("Masalan: Achchiq bo'lmasin, piyozsiz...")}
              className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-teal-500 resize-none mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setKitchenNoteModalOpen(false)}
                className="min-h-[44px] px-4 py-2 text-sm text-slate-400 hover:text-white flex items-center"
              >{label("Bekor qilish")}</button>
              <button
                onClick={handleSaveNotes}
                className="min-h-[44px] px-5 py-2 rounded-xl bg-teal-600 text-white font-bold text-sm hover:bg-teal-500 flex items-center"
              >{label("Saqlash")}</button>
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
          <div ref={transferDialogRef} role="dialog" aria-modal="true" aria-labelledby="table-transfer-title" className="bg-slate-900 border border-slate-800 rounded-3xl max-w-4xl w-full p-4 shadow-2xl h-[85dvh] flex flex-col min-h-0">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <ArrowRightLeft className="w-4 h-4 text-amber-400" />
                <h3 id="table-transfer-title" className="text-white font-extrabold text-sm sm:text-base">{label('Ko‘chirish / hisoblarni qo‘shish')}</h3>
              </div>
              <button
                type="button"
                disabled={transferLoading}
                onClick={() => setTransferModalOpen(false)}
                className="min-w-[44px] min-h-[44px] rounded-xl bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {mergePreview ? <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-4 text-slate-200">
              <p className="font-bold text-base">{mergePreview.source_label} → {mergePreview.target_label}</p>
              <p className="text-xs text-slate-400">{mergePreview.source_number} → {mergePreview.target_number}</p>
              <p>{label('Qabul qiluvchi stolning xizmat foizi va ofitsianti qo‘llanadi.')}</p>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-3"><dt>{label('Ofitsiant')}</dt><dd>{mergePreview.waiter_name || '—'}</dd></div>
                <div className="flex justify-between gap-3"><dt>{label('Xizmat haqi')}</dt><dd>{mergePreview.service_fee_percent}%</dd></div>
                <div className="flex justify-between gap-3"><dt>{label('Avvalgi jami')}</dt><dd>{(mergePreview.source_total + mergePreview.target_total).toLocaleString('uz-UZ')}</dd></div>
                <div className="flex justify-between gap-3 text-xl font-bold text-white"><dt>{label('Yangi jami')}</dt><dd>{mergePreview.total.toLocaleString('uz-UZ')}</dd></div>
                <div className="flex justify-between gap-3"><dt>{label('Avans')}</dt><dd>{mergePreview.deposit_amount.toLocaleString('uz-UZ')}</dd></div>
                <div className="flex justify-between gap-3"><dt>{label('To‘lash qoldi')}</dt><dd>{mergePreview.amount_due.toLocaleString('uz-UZ')}</dd></div>
              </dl>
              <button type="button" disabled={transferLoading} onClick={handleMergeAccounts} className="w-full min-h-[48px] rounded-xl bg-emerald-700 font-bold disabled:opacity-40">{label(transferLoading ? 'Saqlanmoqda...' : 'Hisoblarni birlashtirish')}</button>
              <button type="button" disabled={transferLoading} onClick={() => setMergePreview(null)} className="w-full min-h-[44px] underline">{label('Boshqa stol tanlash')}</button>
            </div> : <>
            <p className="text-sm text-slate-300 mb-3">{label('Bo‘sh stolga ko‘chiring yoki band stol hisobiga qo‘shing.')}</p>

            <WaiterTablePicker tables={tables.filter(table => table.id !== selectedTable.id)} zone={transferZone} onZone={setTransferZone} label={label} loading={false} disabled={transferLoading} transfer onSelect={table => handleTransferTable(table.id)} />
            </>}

            <div className="flex justify-end">
              <button
                type="button"
                disabled={transferLoading}
                onClick={() => setTransferModalOpen(false)}
                className="min-h-[44px] px-5 py-2 rounded-xl bg-slate-800 text-sm text-slate-300 font-bold hover:bg-slate-700 flex items-center"
              >{label("Bekor qilish")}</button>
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
