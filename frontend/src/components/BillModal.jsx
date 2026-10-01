import React, { useState, useEffect } from 'react';
import api from '../utils/api';
import { useWebSocket } from '../context/WebSocketContext';
import {
  Receipt,
  X,
  Printer,
  CheckCircle2,
  Clock,
  User,
  UtensilsCrossed,
  BellRing,
  RefreshCw,
  Sparkles,
  Phone,
  MapPin
} from 'lucide-react';

export const BillModal = ({
  isOpen,
  onClose,
  tableId,
  tableNumber,
  isStaff = false,
  onTableCleared,
}) => {
  const [bill, setBill] = useState(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [printingThermal, setPrintingThermal] = useState(false);
  const [callLoading, setCallLoading] = useState(false);
  const [callSuccess, setCallSuccess] = useState(false);
  const { addEventListener } = useWebSocket();

  const fetchBill = async () => {
    if (!tableId) return;
    try {
      const data = await api.get(`/tables/${tableId}/bill`);
      setBill(data);
    } catch (err) {
      console.error('Bill load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchBill();
    }
  }, [isOpen, tableId]);

  useEffect(() => {
    if (!isOpen) return;

    const unsubscribe = addEventListener('*', (event) => {
      if (
        event.table_id === tableId ||
        event.type === 'new_order' ||
        event.type === 'order_status_updated' ||
        event.type === 'table_cleared' ||
        event.type === 'bill_paid'
      ) {
        fetchBill();
      }
    });

    return () => unsubscribe();
  }, [isOpen, tableId]);

  if (!isOpen) return null;

  // "Ekran / PDF" — oddiy A4 varaqqa chop etish.
  // window.print() ishlatilmaydi, chunki asosiy hujjatning @page sozlamasi
  // 80mm termal chek uchun. Shuning uchun hisobni alohida oynada,
  // o'zining A4 uslubi bilan chop etamiz.
  const handlePrint = () => {
    const node = document.getElementById('printable-bill');
    if (!node) return;
    const win = window.open('', '_blank', 'width=820,height=900');
    if (!win) {
      alert("Chop etish oynasi ochilmadi. Brauzerda pop-up oynalarga ruxsat bering.");
      return;
    }
    win.document.write(`<!doctype html><html lang="uz"><head><meta charset="utf-8">
<title>Hisob — Stol #${bill?.table_number ?? ''}</title>
<style>
  @page { size: A4; margin: 14mm; }
  * { box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; color:#000; background:#fff;
         margin:0; font-size:12pt; line-height:1.45; }
  h1 { font-size:16pt; margin:0 0 10px; }
  .row { display:flex; justify-content:space-between; gap:12px; padding:3px 0; }
  .muted { color:#444; }
  .total { font-size:14pt; font-weight:bold; border-top:2px solid #000;
           margin-top:10px; padding-top:8px; }
  svg { display:none; }
</style></head><body>
<h1>Hisob — Stol #${bill?.table_number ?? ''}</h1>
${node.innerHTML}
</body></html>`);
    win.document.close();
    win.focus();
    // Kontent to'liq yuklangach chop etamiz
    setTimeout(() => {
      win.print();
      win.close();
    }, 350);
  };

  const handlePrintThermal = async () => {
    if (!tableId) return;
    setPrintingThermal(true);
    try {
      const res = await api.post(`/tables/${tableId}/print-bill`);
      alert(`✅ Chek ${res.printer_name || 'Printer 1'} ga muvaffaqiyatli yuborildi!`);
    } catch (err) {
      alert(`❌ Chek chiqarishda xatolik: ` + (err.message || ''));
    } finally {
      setPrintingThermal(false);
    }
  };

  const handleCheckoutAndClear = async () => {
    if (!window.confirm(`Stol #${bill?.table_number || tableNumber} hisobini yopish va stolni bo'shatishni tasdiqlaysizmi?`)) {
      return;
    }

    setCheckoutLoading(true);
    try {
      await api.post(`/tables/${tableId}/checkout`);
      if (onTableCleared) onTableCleared(tableId);
      onClose();
    } catch (err) {
      alert(err.message || 'Hisobni yopishda xatolik yuz berdi');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleCallForBill = async () => {
    setCallLoading(true);
    try {
      await api.post('/orders/call-waiter', {
        table_id: tableId,
        note: '🧾 Hisob-kitob qilish (Chek so\'ralmoqda)',
      });
      setCallSuccess(true);
      setTimeout(() => setCallSuccess(false), 3000);
    } catch (err) {
      alert(err.message || 'Xatolik yuz berdi');
    } finally {
      setCallLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fade-in overflow-y-auto">
      {/* Printable Receipt Box (Hidden on screen except modal, styled for print) */}
      <div className="relative w-full max-w-lg rounded-3xl glass-card border border-theme-border bg-theme-surface p-5 sm:p-7 shadow-2xl text-theme-text my-8 max-h-[90vh] flex flex-col justify-between">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-theme-border/60">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-theme-primary/15 border border-theme-primary/30 flex items-center justify-center text-theme-primary">
              <Receipt className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                <span>Stol #{bill?.table_number || tableNumber} Hisob Cheki</span>
                {bill?.is_paid ? (
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    To'langan
                  </span>
                ) : (
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    To'lanmagan
                  </span>
                )}
              </h3>
              <p className="text-xs text-theme-muted">
                {bill?.room || 'Asosiy zal'} • {new Date().toLocaleDateString('uz-UZ')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={fetchBill}
              title="Yangilash"
              className="p-2 rounded-xl text-theme-muted hover:text-white hover:bg-white/10 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              title="Yopish"
              className="p-2 rounded-xl text-theme-muted hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1 scrollbar-thin">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center text-theme-muted">
              <RefreshCw className="w-7 h-7 animate-spin mb-2 text-theme-primary" />
              <p className="text-xs font-semibold">Chek ma'lumotlari yuklanmoqda...</p>
            </div>
          ) : !bill || bill.items.length === 0 ? (
            <div className="py-12 text-center text-theme-muted space-y-2">
              <UtensilsCrossed className="w-10 h-10 mx-auto opacity-30" />
              <p className="text-sm font-semibold text-white">Ushbu stolda hali buyurtmalar yo'q</p>
              <p className="text-xs">Mijoz taom buyurtma qilgandan so'ng hisob bu yerda paydo bo'ladi.</p>
            </div>
          ) : (
            <div id="printable-bill" className="space-y-4">
              {/* Receipt info header */}
              <div className="p-3.5 rounded-2xl bg-black/20 border border-theme-border/40 text-xs space-y-1 text-theme-muted">
                <div className="flex justify-between font-medium">
                  <span>Restoran:</span>
                  <span className="text-white font-bold">{bill.restaurant_name}</span>
                </div>
                {bill.restaurant_phone && (
                  <div className="flex justify-between">
                    <span>Telefon:</span>
                    <span className="text-white">{bill.restaurant_phone}</span>
                  </div>
                )}
                {bill.waiter_name && (
                  <div className="flex justify-between">
                    <span>Ofitsiant:</span>
                    <span className="text-white">{bill.waiter_name}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Buyurtmalar soni:</span>
                  <span className="text-white">{bill.orders_count} ta ({bill.order_numbers.join(', ')})</span>
                </div>
              </div>

              {/* Items Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-theme-muted uppercase tracking-wider">
                  Buyurtma qilingan taomlar
                </h4>

                <div className="divide-y divide-theme-border/30 bg-black/10 rounded-2xl border border-theme-border/40 p-3">
                  {bill.items.map((item, index) => (
                    <div key={item.menu_item_id || index} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                      <div className="flex-1">
                        <div className="font-semibold text-white">
                          <span className="font-bold text-theme-primary mr-1.5">{item.quantity}x</span>
                          {item.name}
                        </div>
                        <div className="text-[11px] text-theme-muted">
                          {(item.unit_price || 0).toLocaleString()} so'm / dona
                        </div>
                        {item.special_notes?.length > 0 && (
                          <div className="text-[10px] text-amber-400/90 italic mt-0.5">
                            Izoh: {item.special_notes.join(', ')}
                          </div>
                        )}
                      </div>

                      <div className="font-bold text-white text-right">
                        {(item.total_price || 0).toLocaleString()} so'm
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Financial Calculation */}
              <div className="p-4 rounded-2xl bg-gradient-to-b from-theme-surface/90 to-black/40 border border-theme-border/60 space-y-2 text-xs">
                <div className="flex justify-between text-theme-muted">
                  <span>Taomlar jami (Subtotal):</span>
                  <span className="font-medium text-white">{(bill.subtotal || 0).toLocaleString()} so'm</span>
                </div>
                <div className="flex justify-between text-theme-muted">
                  <span>Xizmat haqi ({bill.service_fee_percent || 10}%):</span>
                  <span className="font-medium text-white">{(bill.service_fee_amount || 0).toLocaleString()} so'm</span>
                </div>
                {bill.discount > 0 && (
                  <div className="flex justify-between text-emerald-400">
                    <span>Chegirma:</span>
                    <span>-{(bill.discount || 0).toLocaleString()} so'm</span>
                  </div>
                )}
                <div className="pt-2 border-t border-theme-border/60 flex justify-between items-center text-sm font-bold">
                  <span className="text-white text-base">Jami to'lov:</span>
                  <span className="text-lg font-black text-theme-primary">
                    {(bill.grand_total || 0).toLocaleString()} so'm
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Action Footer */}
        <div className="pt-4 border-t border-theme-border/60 space-y-2">
          {callSuccess && (
            <div className="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold text-center flex items-center justify-center gap-1.5 animate-fade-in">
              <CheckCircle2 className="w-4 h-4" />
              <span>Ofitsiantga hisob-kitob qilish xabari yuborildi!</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <button
              onClick={handlePrintThermal}
              disabled={printingThermal || !bill || bill.items.length === 0}
              className="py-3 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-black text-xs flex items-center justify-center gap-1.5 transition-all shadow-md active:scale-95 disabled:opacity-40"
            >
              <Printer className={`w-4 h-4 ${printingThermal ? 'animate-spin' : ''}`} />
              <span>{printingThermal ? 'Chop etilmoqda...' : '🖨️ Printer 1 (Kassa)'}</span>
            </button>

            <button
              onClick={handlePrint}
              disabled={!bill || bill.items.length === 0}
              className="py-3 px-3 rounded-xl border border-theme-border hover:border-theme-primary/60 bg-white/5 hover:bg-white/10 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-all disabled:opacity-40"
            >
              <Printer className="w-4 h-4" />
              <span>Ekran / PDF</span>
            </button>

            {isStaff ? (
              <button
                onClick={handleCheckoutAndClear}
                disabled={checkoutLoading || !bill || bill.items.length === 0}
                className="py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-98"
              >
                {checkoutLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                <span>To'landi & Stolni Bo'shatish</span>
              </button>
            ) : (
              <button
                onClick={handleCallForBill}
                disabled={callLoading || !bill || bill.items.length === 0}
                className="py-3 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold text-xs shadow-lg shadow-orange-500/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-98"
              >
                {callLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <BellRing className="w-4 h-4 animate-bounce-subtle" />
                )}
                <span>Ofitsiantdan hisobni so'rash</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BillModal;
