import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { useTheme } from './context/ThemeContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { CartProvider } from './context/CartContext';
import api from './utils/api';

// Components
import Navbar from './components/Navbar';
import ToastContainer from './components/ToastContainer';
import BillModal from './components/BillModal';

// Pages
import CustomerMenu from './pages/customer/CustomerMenu';
import CartDrawer from './pages/customer/CartDrawer';
import CallWaiterModal from './pages/customer/CallWaiterModal';
import OrderTracker from './pages/customer/OrderTracker';
import ReviewModal from './pages/customer/ReviewModal';
import WaiterDashboard from './pages/waiter/WaiterDashboard';
import ChefDashboard from './pages/chef/ChefDashboard';
import AdminDashboard from './pages/admin/AdminDashboard';
import DeveloperDashboard from './pages/developer/DeveloperDashboard';
import Login from './pages/auth/Login';

import DunyoLanding from './pages/customer/DunyoLanding';

export const App = () => {
  const { user, isWaiter, isChef, isAdmin, isDev, loading: authLoading } = useAuth();
  const [currentView, setCurrentView] = useState('menu'); // 'menu' | 'tracker' | 'login'
  const [activeOrderId, setActiveOrderId] = useState(null);
  const [reviewOrder, setReviewOrder] = useState(null);

  // Table information from QR token in URL
  const [tableInfo, setTableInfo] = useState(null);
  const [loadingTable, setLoadingTable] = useState(true);

  // Modals & Drawers
  const [cartOpen, setCartOpen] = useState(false);
  const [callWaiterOpen, setCallWaiterOpen] = useState(false);
  const [billOpen, setBillOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);

  useEffect(() => {
    // URL dan ?table=TOKEN ni tekshirish
    const params = new URLSearchParams(window.location.search);
    const qrToken = params.get('table');

    const resolveTable = async () => {
      let currentTable = null;
      if (qrToken) {
        try {
          const tableData = await api.get(`/tables/scan/${qrToken}`);
          currentTable = tableData;
          setTableInfo(tableData);
        } catch (e) {
          console.warn('QR token topilmadi:', e);
          setTableInfo(null);
        }
      } else {
        // Stol skaner qilinmagan -> Asosiy Landing sahifaga kiradi
        setTableInfo(null);
      }

      // Check active orders specifically for THIS table
      if (currentTable?.id) {
        try {
          const activeOrders = await api.get(`/orders/table/${currentTable.id}/active`);
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

      setLoadingTable(false);
    };

    resolveTable();
  }, []);

  const handleSelectTable = async (table) => {
    setTableInfo(table);
    const url = new URL(window.location);
    url.searchParams.set('table', table.qr_token || table.number);
    window.history.pushState({}, '', url);

    if (table?.id) {
      try {
        const activeOrders = await api.get(`/orders/table/${table.id}/active`);
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

  if (authLoading || loadingTable) {
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
            <Login
              onSuccess={() => setCurrentView('menu')}
              onBackToMenu={() => setCurrentView('menu')}
            />
          )}

          {/* If Logged in as Staff */}
          {user && (
            <div>
              <Navbar
                currentView={currentView}
                onNavigate={setCurrentView}
              />
              <main>
                {isWaiter && <WaiterDashboard />}
                {isChef && <ChefDashboard />}
                {isDev ? <DeveloperDashboard /> : (isAdmin && <AdminDashboard />)}
              </main>
            </div>
          )}

          {/* If Not Logged In and NO Table Selected -> Landing Page */}
          {!user && currentView !== 'login' && !tableInfo && (
            <div>
              <DunyoLanding
                onSelectTable={handleSelectTable}
                onOpenLogin={() => setCurrentView('login')}
              />
            </div>
          )}

          {/* If Not Logged In and Table IS Selected -> Table Menu */}
          {!user && currentView !== 'login' && tableInfo && (
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
                isStaff={false}
              />

              <ReviewModal
                isOpen={reviewOpen}
                onClose={() => setReviewOpen(false)}
                order={reviewOrder}
              />
            </div>
          )}
        </div>
      </CartProvider>
    </WebSocketProvider>
  );
};

export default App;
