import React, { useLayoutEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { ShoppingCart, Table, Settings, LayoutDashboard, Archive, Users, Wallet, UtensilsCrossed, FileSpreadsheet, Trophy, Palette, Star, RefreshCw } from 'lucide-react';

const sections = [
  { title: 'Savdo va hisob', items: [['overview', 'Xulosa', LayoutDashboard], ['receipts', 'Cheklar arxivi', Archive], ['debts', 'Qarzlar', Wallet], ['payments', 'Kassa hisoboti', FileSpreadsheet]] },
  { title: 'Restoran', items: [['menu', 'Menyu va taomlar', UtensilsCrossed], ['staff', 'Xodimlar', Users], ['waiter_kpi', 'Ofitsiantlar KPI', Trophy], ['reviews', 'Baholar', Star]] },
  { title: 'Sozlash', items: [['settings', 'Restoran sozlamalari', Settings], ['themes', 'Dizayn va temalar', Palette]] },
];
const allowed = (role, key) => role !== 'cashier' || ['pos', 'receipts', 'debts', 'payments'].includes(key);
function NavButton({ id, title, icon: Icon, tab, onNavigate }) {
  return <button type="button" data-tab={id} id={`admin-tab-${id}`} aria-current={tab === id ? 'page' : undefined} onClick={() => onNavigate(id)} className="admin-nav-button"><Icon size={20} /><span>{title}</span></button>;
}
export function AdminPrimaryNavigation({ tab, onNavigate, role, onRefresh }) {
  const [headerSlot, setHeaderSlot] = useState(null);
  useLayoutEffect(() => {
    setHeaderSlot(document.getElementById('admin-primary-navigation-slot'));
  }, []);
  const management = !['pos', 'tables'].includes(tab);
  const navigation = <nav aria-label="Asosiy boshqaruv" className="admin-primary-nav">
    <NavButton id="pos" title="Buyurtma olish" icon={ShoppingCart} tab={tab} onNavigate={onNavigate} />
    {allowed(role, 'tables') && <NavButton id="tables" title="Stollar va QR" icon={Table} tab={tab} onNavigate={onNavigate} />}
    <button type="button" aria-current={management ? 'page' : undefined} onClick={() => onNavigate(role === 'cashier' ? 'receipts' : 'overview')} className="admin-nav-button"><Settings size={20} /><span>Boshqaruv</span></button>
    {onRefresh && <button type="button" aria-label="Ma’lumotlarni yangilash" title="Yangilash" onClick={onRefresh} className="admin-nav-button ml-auto"><RefreshCw size={20} /></button>}
  </nav>;
  return headerSlot ? createPortal(navigation, headerSlot) : navigation;
}
export function AdminSectionNavigation({ tab, onNavigate, role }) {
  if (['pos', 'tables'].includes(tab)) return null;
  return <nav aria-label="Boshqaruv bo‘limlari" className="admin-section-nav">
    {sections.map(group => {
      const items = group.items.filter(([key]) => allowed(role, key));
      return items.length > 0 && <div key={group.title}><p>{group.title}</p>{items.map(([key, title, icon]) => <NavButton key={key} id={key} title={title} icon={icon} tab={tab} onNavigate={onNavigate} />)}</div>;
    })}
  </nav>;
}
