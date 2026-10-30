import React, { useState, useEffect, Suspense, lazy } from 'react';
import { useAuth } from './context/AuthContext';
import { useTheme } from './context/ThemeContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { CartProvider } from './context/CartContext';
import api from './utils/api';

// Components
import Navbar from './components/Navbar';
import ToastContainer from './components/ToastContainer';
import BillModal from './components/BillModal';

// Lazy-loaded Pages (Admin, Waiter, Customer, Kitchen/POS)
const CustomerMenu = lazy(() => import('./pages/customer/CustomerMenu'));
const CartDrawer = lazy(() => import('./pages/customer/CartDrawer'));
const CallWaiterModal = lazy(() => import('./pages/customer/CallWaiterModal'));
const OrderTracker = lazy(() => import('./pages/customer/OrderTracker'));
const ReviewModal = lazy(() => import('./pages/customer/ReviewModal'));
const WaiterDashboard = lazy(() => import('./pages/waiter/WaiterDashboard'));
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const DeveloperDashboard = lazy(() => import('./pages/developer/DeveloperDashboard'));
const Login = lazy(() => import('./pages/auth/Login'));
const DunyoLanding = lazy(() => import('./pages/customer/DunyoLanding'));
const TableWaitingVerification = lazy(() => import('./pages/customer/TableWaitingVerification'));
const KitchenDashboard = lazy(() => import('./pages/kitchen/KitchenDashboard'));

const PageLoader = () => (
  <div className="min-h-[40vh] flex items-center justify-center">
    <div className="w-9 h-9 border-3 border-amber-500 border-t-transparent rounded-full animate-spin" />
  </div>
);

export const App = () => {
  const { user, isWaiter, isChef, isAdmin, isCashier, isDev, loading: authLoading } = useAuth();
  const [currentView, setCurrentView] = useState('menu'); // 'menu' | 'tracker' | 'login'
  const [activeOrderId, setActiveOrderId] = useState(null);
  const [reviewOrder, setReviewOrder] = useState(null);

  // Table information from QR token in URL
  const [tableInfo, setTableInfo] = useState(null);
  const [tableUnlocked, setTableUnlocked] = useState(false);
  const [loadingTable, setLoadingTable] = useState(true);

  // Modals & Drawers
  const [cartOpen, setCartOpen] = useState(false);
  const [callWaiterOpen, setCallWaiterOpen] = useState(false);
  const [billOpen, setBillOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);

  useEffect(() => {
    // Auth yuklanayotgan bo'lsa kutamiz
    if (authLoading) return;

    // Xodim (admin/waiter/chef) login bo'lgan — QR scan kerak emas, darhol ishga tushsin
    if (user) {
      setTableInfo(null);
      setTableUnlocked(false);
      setLoadingTable(false);
      return;
    }

    // URL dan ?table=TOKEN ni tekshirish (faqat mijozlar uchun)
    const params = new URLSearchParams(window.location.search);
    const qrToken = params.get('table');

    // 8 soniyadan keyin qolib ketishining oldini olish
    const timeout = setTimeout(() => setLoadingTable(false), 8000);

    const resolveTable = async () => {
      let currentTable = null;
      if (qrToken) {
        try {
          const tableData = await api.get(`/tables/scan/${qrToken}`);
          currentTable = tableData;
          setTableInfo(tableData);
          // Ruxsatsiz to'g'ridan-to'g'ri kirish (direct access)
          setTableUnlocked(tableData.is_unlocked !== false);
        } catch (e) {
          console.warn('QR token topilmadi:', e);
          setTableInfo(null);
          setTableUnlocked(false);
        }
      } else {
        // Stol skaner qilinmagan -> Asosiy Landing sahifaga kiradi
        setTableInfo(null);
        setTableUnlocked(false);
      }

      // Check active orders specifically for THIS table
      if (currentTable?.id) {
        try {
          const qrParam = currentTable?.qr_token ? `?qr_token=${encodeURIComponent(currentTable.qr_token)}` : '';
          const activeOrders = await api.get(`/orders/table/${currentTable.id}/active${qrParam}`);
          if (activeOrders && activeOrders.length > 0) {
            setActiveOrderId(activeOrders[0].id);
          } else {
            setActiveOrderId(null);
          }
        } catch (err) {
          console.warn('Faol buyurtmalarni yuklab bo\'lmadi:', err);
          setActiveOrderId(null);
        }
      }

      clearTimeout(timeout);
      setLoadingTable(false);
    };

    resolveTable();
    return () => clearTimeout(timeout);
  }, [authLoading, user]);

  const handleSelectTable = async (table) => {
    setTableInfo(table);
    setTableUnlocked(true);
    const url = new URL(window.location);
    url.searchParams.set('table', table.qr_token || table.number);
    window.history.pushState({}, '', url);

    if (table?.id) {
      try {
        const qrParam = table?.qr_token ? `?qr_token=${encodeURIComponent(table.qr_token)}` : '';
        const activeOrders = await api.get(`/orders/table/${table.id}/active${qrParam}`);
        if (activeOrders && activeOrders.length > 0) {
          setActiveOrderId(activeOrders[0].id);
        } else {
          setActiveOrderId(null);
        }
      } catch (err) {
        setActiveOrderId(null);
      }
    }
    setCurrentView('menu');
  };

  const handleReturnToLanding = () => {
    setTableInfo(null);
    const url = new URL(window.location);
    url.searchParams.delete('table');
    window.history.pushState({}, '', url);
    setCurrentView('menu');
  };

  const handleOrderCreated = (order) => {
    if (order && order.id) {
      setActiveOrderId(order.id);
      setCurrentView('tracker');
    }
  };

  const handleOpenReview = (order) => {
    setReviewOrder(order);
    setReviewOpen(true);
  };

  const restaurantId = user?.restaurant_id || tableInfo?.restaurant_id || 1;
  const { setActiveThemes } = useTheme();
  useEffect(() => {
    let cancelled = false;
    api.get(`/restaurants/${restaurantId}`).then(data => {
      if (!cancelled && data.settings?.active_themes?.length) setActiveThemes(data.settings.active_themes);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [restaurantId, user?.id]);

  // Xodim login bo'lgan — loadingTable ni kutmaydi (darhol dashboard ko'rsatiladi)
  // Mijoz — auth va tableInfo ikkalasini kutadi
  const showLoading = authLoading || (!user && loadingTable);

  if (showLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-theme-bg text-theme-muted">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-semibold tracking-wider uppercase text-theme-text">
            Dunyo Choyxonasi Yuklanmoqda...
          </p>
        </div>
      </div>
    );
  }

  return (
    <WebSocketProvider restaurantId={restaurantId} tableId={tableInfo?.id}>
      <CartProvider>
        <div className="min-h-screen bg-theme-bg text-theme-text transition-colors duration-300">
          <ToastContainer />

          {/* If user clicked Login */}
          {currentView === 'login' && !user && (
            <Suspense fallback={<PageLoader />}>
              <Login
                onSuccess={() => setCurrentView('menu')}
                onBackToMenu={() => setCurrentView('menu')}
              />
            </Suspense>
          )}

          {/* If Logged in as Staff */}
          {user && (
            <div className="staff-app-shell h-[100dvh] flex flex-col overflow-hidden">
              <div className="shrink-0">
                <Navbar currentView={currentView} onNavigate={setCurrentView} />
              </div>
              <main className="flex-1 min-h-0 overflow-auto">
                <Suspense fallback={<PageLoader />}>
                  {/* Ofitsiant faqat zaldagi stollarga xizmat ko'rsatish panelini oladi */}
                  {isWaiter && <WaiterDashboard />}
                  {isChef && <KitchenDashboard />}
                  {/* Admin va Kassir boshqaruv, kassa, POS, Olib ketish va Dastavka panelini oladi */}
                  {isDev ? <DeveloperDashboard /> : ((isAdmin || isCashier) && <AdminDashboard />)}
                  {!isWaiter && !isChef && !isAdmin && !isCashier && !isDev && (
                    <div className="max-w-md mx-auto mt-20 p-6 rounded-2xl bg-theme-card border border-theme-border text-center space-y-2">
                      <p className="text-lg font-bold text-theme-text">Bu hisob uchun panel yo'q</p>
                      <p className="text-sm text-theme-muted">
                        Oshpaz paneli olib tashlangan — buyurtmalar to'g'ridan-to'g'ri
                        oshxona printeriga chiqadi. Admin bilan bog'laning.
                      </p>
                    </div>
                  )}
                </Suspense>
              </main>
            </div>
          )}

          {/* If Not Logged In and NO Table Selected -> Landing Page */}
          {!user && currentView !== 'login' && !tableInfo && (
            <div>
              <Suspense fallback={<PageLoader />}>
                <DunyoLanding
                  onSelectTable={handleSelectTable}
                  onOpenLogin={() => setCurrentView('login')}
                />
              </Suspense>
            </div>
          )}

          {/* If Not Logged In and Table IS Selected */}
          {!user && currentView !== 'login' && tableInfo && (
            <div>
              <Suspense fallback={<PageLoader />}>
                {!tableUnlocked && !tableInfo.is_unlocked ? (
                  <TableWaitingVerification
                    tableInfo={tableInfo}
                    onUnlocked={() => setTableUnlocked(true)}
                    onReturnToLanding={handleReturnToLanding}
                  />
                ) : (
                  <div>
                    <Navbar
                      tableInfo={tableInfo}
                      onOpenCart={() => setCartOpen(true)}
                      onOpenCallWaiter={() => setCallWaiterOpen(true)}
                      onOpenBill={() => setBillOpen(true)}
                      currentView={currentView}
                      onNavigate={(view) => {
                        if (view === 'landing') handleReturnToLanding();
                        else setCurrentView(view);
                      }}
                      onReturnToLanding={handleReturnToLanding}
                      activeOrderId={activeOrderId}
                    />

                    <main>
                      {currentView === 'tracker' && activeOrderId ? (
                        <OrderTracker
                          orderId={activeOrderId}
                          qrToken={tableInfo?.qr_token}
                          onOpenReview={handleOpenReview}
                          onOpenBill={() => setBillOpen(true)}
                          onBackToMenu={() => setCurrentView('menu')}
                        />
                      ) : (
                        <CustomerMenu
                          restaurantId={restaurantId}
                          tableInfo={tableInfo}
                          onOpenCart={() => setCartOpen(true)}
                          onOpenCallWaiter={() => setCallWaiterOpen(true)}
                          onOpenBill={() => setBillOpen(true)}
                          onReturnToLanding={handleReturnToLanding}
                        />
                      )}
                    </main>

                    {/* Customer Modals */}
                    <CartDrawer
                      isOpen={cartOpen}
                      onClose={() => setCartOpen(false)}
                      tableId={tableInfo?.id}
                      onOrderCreated={handleOrderCreated}
                    />

                    <CallWaiterModal
                      isOpen={callWaiterOpen}
                      onClose={() => setCallWaiterOpen(false)}
                      tableId={tableInfo?.id}
                      tableNumber={tableInfo?.number}
                    />

                    <BillModal
                      isOpen={billOpen}
                      onClose={() => setBillOpen(false)}
                      tableId={tableInfo?.id}
                      tableNumber={tableInfo?.number}
                      qrToken={tableInfo?.qr_token}
                      isStaff={false}
                    />

                    <ReviewModal
                      qrToken={tableInfo?.qr_token}
                      isOpen={reviewOpen}
                      onClose={() => setReviewOpen(false)}
                      order={reviewOrder}
                    />
                  </div>
                )}
              </Suspense>
            </div>
          )}
        </div>
      </CartProvider>
    </WebSocketProvider>
  );
};

export default App;
