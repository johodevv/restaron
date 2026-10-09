import React, { useState, useEffect, useRef } from 'react';
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
  // Tortilgan og'irlikni tuzatish (1.5 kg deb olingan baliq 1.7 kg chiqsa)
  const [weightEdit, setWeightEdit] = useState(null);   // {order_id, order_item_id, name, unit}
  const [weightValue, setWeightValue] = useState('');
  const [priceValue, setPriceValue] = useState('');
  // Xizmat haqi foizini shu hisob uchun o'zgartirish (VIP 15%, ko'cha 0% ...)
  const [feeEditOpen, setFeeEditOpen] = useState(false);
  const [feeValue, setFeeValue] = useState('');
  const [savingFee, setSavingFee] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const [savingWeight, setSavingWeight] = useState(false);
  const { addEventListener } = useWebSocket();
  // Hisob yopilayotganda kelgan WebSocket xabari eski chekni qaytarib
  // qo'ymasligi uchun qulf.
  const closingRef = useRef(false);

  const fetchBill = async () => {
    if (!tableId || closingRef.current) return;
    try {
      const data = await api.get(`/tables/${tableId}/bill`);
      if (closingRef.current) return;
      setBill(data);
    } catch (err) {
      console.error('Bill load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      closingRef.current = false;
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
  /* Mijozga beriladigan chekda xizmat haqining SUMMASI yozilmaydi —
     faqat foizi ko'rinadi (termal chekdagidek). */
  .bill-fee-amount { display:none; }
  /* Foizni o'zgartirish tugmasi faqat ekran uchun — chekka tushmaydi */
  .bill-fee-box { display:none; }
  .bill-remove-btn { display:none; }
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

  // Mijoz taomni qaytarib bersa — hisobdan olib tashlash.
  // Taom allaqachon oshxonadan chiqqan bo'lishi mumkin, shuning uchun
  // bu amal faqat admin uchun va tasdiqlash so'raladi.
  const handleRemoveItem = async (item) => {
    const ids = item.order_item_ids?.length
      ? item.order_item_ids
      : item.order_item_id
      ? [item.order_item_id]
      : [];
    if (!ids.length) {
      alert("Bu qatorni olib tashlab bo'lmaydi (hisob yopilgan bo'lishi mumkin)");
      return;
    }

    let qty = item.quantity || 1;
    if (qty > 1) {
      const answer = window.prompt(
        `"${item.name}" — hisobda ${qty} ta bor.\n` +
          `Nechtasi qaytarildi? (hammasi uchun ${qty} yozing)`,
        String(qty)
      );
      if (answer === null) return;
      const n = parseInt(String(answer).trim(), 10);
      if (!n || n < 1 || n > qty) {
        alert(`1 dan ${qty} gacha son kiriting`);
        return;
      }
      qty = n;
    } else if (
      !window.confirm(`"${item.name}" hisobdan olib tashlansinmi?`)
    ) {
      return;
    }

    setRemovingId(item.order_item_id ?? ids[0]);
    try {
      await api.post(`/tables/${tableId}/remove-items`, {
        order_item_ids: ids,
        quantity: qty,
      });
      await fetchBill();
    } catch (err) {
      alert(err.message || "Taomni olib tashlashda xatolik");
    } finally {
      setRemovingId(null);
    }
  };

  // Shu stol hisobi uchun xizmat haqi foizini o'zgartirish.
  // Tegilmasa sozlamalardagi foiz (12%) o'z holicha qoladi —
  // har chek chiqarganda qayta kiritib o'tirish shart emas.
  const handleSaveFee = async () => {
    const v = parseFloat(String(feeValue).replace(',', '.'));
    if (isNaN(v) || v < 0 || v > 100) {
      alert('Foizni 0 dan 100 gacha kiriting (masalan: 12)');
      return;
    }
    setSavingFee(true);
    try {
      await api.patch(`/tables/${tableId}/service-fee`, { percent: v });
      setFeeEditOpen(false);
      await fetchBill();
    } catch (err) {
      alert(err.message || "Xizmat haqini o'zgartirishda xatolik");
    } finally {
      setSavingFee(false);
    }
  };

  // Kassir tortiladigan taom NARXINI tuzatadi.
  // Asosiy maydon — summa (baliqning kg i emas, puli).
  const handleSaveWeight = async () => {
    if (!weightEdit) return;
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
      await api.patch(
        `/orders/${weightEdit.order_id}/items/${weightEdit.order_item_id}/weight`,
        body
      );
      setWeightEdit(null);
      setWeightValue('');
      setPriceValue('');
      await fetchBill();
    } catch (err) {
      alert(err.message || 'Narxni saqlashda xatolik');
    } finally {
      setSavingWeight(false);
    }
  };

  const handleCheckoutAndClear = async () => {
    if (!window.confirm(`Stol #${bill?.table_number || tableNumber} hisobini yopish va stolni bo'shatishni tasdiqlaysizmi?`)) {
      return;
    }

    setCheckoutLoading(true);
    closingRef.current = true;
    try {
      await api.post(`/tables/${tableId}/checkout`);
      // Chek ekranda qolib ketmasligi uchun holatni darhol tozalaymiz —
      // keyin oyna qayta ochilsa yangi (bo'sh) hisob yuklanadi.
      setBill(null);
      if (onTableCleared) onTableCleared(tableId);
      onClose();
    } catch (err) {
      closingRef.current = false;
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

  // Og'irlikni tuzatish oynasi
  const weightModal = weightEdit && (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
      <div className="bg-slate-900 border-2 border-cyan-600/60 rounded-3xl max-w-sm w-full p-5 shadow-2xl">
        <div className="flex items-start justify-between mb-1">
          <div>
            <h3 className="text-base font-black text-white">💰 Narxni tuzatish</h3>
            <p className="text-xs font-bold text-cyan-300 mt-0.5">{weightEdit.name}</p>
          </div>
          <button onClick={() => setWeightEdit(null)} className="text-slate-400 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-[11px] text-slate-400 mb-3">
          Tarozidagi <b className="text-white">summani</b> yozing — chek va
          hisob shu zahoti to'g'rilanadi. Og'irlik ixtiyoriy: yozsangiz
          chekda ham ko'rinadi.
        </p>
        <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 mb-3 flex justify-between text-xs font-semibold text-slate-300">
          <span>1 {weightEdit.unit} narxi:</span>
          <span className="font-mono font-black text-white">
            {(weightEdit.unit_price || 0).toLocaleString()} so'm
          </span>
        </div>
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
          onKeyDown={(e) => { if (e.key === 'Enter') handleSaveWeight(); }}
          placeholder="masalan: 204000"
          className="w-full p-3.5 rounded-xl bg-slate-950 border-2 border-emerald-600 text-3xl text-white font-mono font-black text-center focus:outline-none focus:border-emerald-400 mb-1"
        />
        {(() => {
          const pr = parseFloat(String(priceValue).replace(',', '.')) || 0;
          if (pr <= 0) return <div className="mb-3" />;
          return (
            <p className="text-center text-sm font-black text-emerald-400 font-mono mb-3">
              {Math.round(pr).toLocaleString()} so'm
            </p>
          );
        })()}
        <label className="block text-[10px] font-black text-slate-500 uppercase tracking-wider mb-1.5">
          Og'irlik ({weightEdit.unit}) — ixtiyoriy
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
            const w = parseFloat(String(v).replace(',', '.'));
            if (w > 0) setPriceValue(String(Math.round(w * (weightEdit.unit_price || 0))));
          }}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSaveWeight(); }}
          placeholder="masalan: 1.7"
          className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-700 text-base text-slate-200 font-mono font-bold text-center focus:outline-none focus:border-cyan-500 mb-4"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeightEdit(null)}
            className="px-3 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300"
          >
            Bekor
          </button>
          <button
            onClick={handleSaveWeight}
            disabled={savingWeight}
            className="flex-1 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-sm disabled:opacity-40 active:scale-95 transition-all"
          >
            {savingWeight ? 'Saqlanmoqda...' : 'Saqlash va narxni tuzatish'}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
    {weightModal}
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
              {/* ─── Xizmat haqi foizi (TEPADA) ────────────────────
                  Har stol uchun har xil foiz kerak bo'ladi. Tegilmasa
                  sozlamadagi foiz (12%) o'z holicha qoladi — har chek
                  chiqarganda qayta kiritib o'tirish shart emas.
                  Bu blok faqat EKRANDA ko'rinadi, chekka tushmaydi. */}
              {isStaff && (
                <div className="bill-fee-box p-3 rounded-2xl bg-amber-500/10 border border-amber-500/40">
                  {!feeEditOpen ? (
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-xs font-black text-white">
                          Xizmat haqi:{' '}
                          <span className="text-amber-300 font-mono">
                            {bill.service_fee_percent ?? 12}%
                          </span>
                        </div>
                        <div className="text-[10px] text-theme-muted mt-0.5">
                          Shu stol uchun boshqa foiz kerak bo'lsa o'zgartiring.
                          Tegmasangiz shu foiz qolaveradi.
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setFeeValue(String(bill.service_fee_percent ?? 12));
                          setFeeEditOpen(true);
                        }}
                        className="shrink-0 px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black transition-all active:scale-95"
                      >
                        O'zgartirish
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      <div className="text-xs font-black text-white">
                        Shu hisob uchun xizmat haqi foizi
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {[0, 5, 10, 12, 15, 20].map((v) => (
                          <button
                            key={v}
                            type="button"
                            onClick={() => setFeeValue(String(v))}
                            className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95 ${
                              String(v) === String(feeValue)
                                ? 'bg-amber-500 text-slate-950'
                                : 'bg-black/30 border border-theme-border text-slate-300 hover:border-amber-500/60'
                            }`}
                          >
                            {v}%
                          </button>
                        ))}
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.5"
                          inputMode="decimal"
                          autoFocus
                          value={feeValue}
                          onChange={(e) => setFeeValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveFee();
                            if (e.key === 'Escape') setFeeEditOpen(false);
                          }}
                          className="w-24 p-2.5 rounded-xl bg-slate-950 border-2 border-amber-600 text-lg text-white font-mono font-black text-center focus:outline-none focus:border-amber-400"
                        />
                        <span className="text-sm font-black text-amber-300">%</span>
                        <button
                          type="button"
                          onClick={handleSaveFee}
                          disabled={savingFee}
                          className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 text-xs font-black transition-all active:scale-95"
                        >
                          {savingFee ? 'Saqlanmoqda...' : 'Saqlash'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setFeeEditOpen(false)}
                          className="px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300"
                        >
                          Bekor
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

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
                    <div
                      key={`${item.menu_item_id}-${item.portion_size || ''}-${index}`}
                      className="py-2.5 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="flex-1">
                        <div className="font-semibold text-white">
                          <span className="font-bold text-theme-primary mr-1.5">{item.quantity}x</span>
                          {item.name}
                          {item.portion_size && (
                            <span className="ml-1.5 px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-300 text-[10px] font-bold">
                              {item.portion_size}
                            </span>
                          )}
                          {/* Tortiladigan taom: narxini shu yerda tuzatish
                              mumkin (tarozida boshqa summa chiqsa). */}
                          {item.is_weighted && isStaff && item.order_item_id ? (
                            <button
                              onClick={() => {
                                setWeightEdit({
                                  order_id: item.order_id,
                                  order_item_id: item.order_item_id,
                                  name: item.name,
                                  unit: item.unit || 'kg',
                                  unit_price: item.unit_price || 0,
                                });
                                setWeightValue(item.weight ? String(item.weight) : '');
                                setPriceValue(
                                  item.manual_price !== null && item.manual_price !== undefined
                                    ? String(Math.round(item.manual_price))
                                    : item.total_price
                                    ? String(Math.round(item.total_price))
                                    : ''
                                );
                              }}
                              title="Narxni tuzatish"
                              className={`ml-1.5 px-1.5 py-0.5 rounded-md text-[10px] font-bold transition-all ${
                                item.manual_price !== null && item.manual_price !== undefined
                                  ? 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/35'
                                  : item.weight > 0
                                  ? 'bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/35'
                                  : 'bg-red-600 text-white hover:bg-red-500'
                              }`}
                            >
                              {item.manual_price !== null && item.manual_price !== undefined
                                ? `💰 ${Math.round(item.manual_price).toLocaleString()} ✎` +
                                  (item.weight > 0 ? ` · ${item.weight} ${item.unit || 'kg'}` : '')
                                : item.weight > 0
                                ? `⚖️ ${item.weight} ${item.unit || 'kg'} ✎`
                                : '💰 NARXI YO\'Q'}
                            </button>
                          ) : (
                            <>
                              {item.weight > 0 && (
                                <span className="ml-1.5 px-1.5 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 text-[10px] font-bold">
                                  {item.weight} {item.unit || 'kg'}
                                </span>
                              )}
                              {!item.weight &&
                                item.is_weighted &&
                                (item.manual_price === null ||
                                  item.manual_price === undefined) && (
                                  <span className="ml-1.5 px-1.5 py-0.5 rounded-md bg-red-600 text-white text-[10px] font-bold">
                                    NARXI YO'Q
                                  </span>
                                )}
                            </>
                          )}
                        </div>
                        <div className="text-[11px] text-theme-muted">
                          {item.is_weighted &&
                          item.manual_price !== null &&
                          item.manual_price !== undefined
                            ? "Summa qo'lda kiritilgan"
                            : `${(item.unit_price || 0).toLocaleString()} so'm / ${
                                item.weight > 0 ? item.unit || 'kg' : 'dona'
                              }`}
                        </div>
                        {item.special_notes?.length > 0 && (
                          <div className="text-[10px] text-amber-400/90 italic mt-0.5">
                            Izoh: {item.special_notes.join(', ')}
                          </div>
                        )}
                      </div>

                      <div className="text-right shrink-0">
                        <div className="font-bold text-white">
                          {(item.total_price || 0).toLocaleString()} so'm
                        </div>
                        {/* Mijoz taomni qaytarib bersa shu tugma bilan
                            hisobdan olib tashlanadi. Chop etilgan chekka
                            tushmaydi (bill-remove-btn yashiriladi). */}
                        {isStaff && (item.order_item_ids?.length || item.order_item_id) && (
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(item)}
                            disabled={removingId !== null}
                            title="Mijoz qaytardi — hisobdan olib tashlash"
                            className="bill-remove-btn mt-1 px-2 py-1 rounded-lg bg-red-600/20 hover:bg-red-600 text-red-300 hover:text-white border border-red-600/40 text-[10px] font-black transition-all active:scale-95 disabled:opacity-40"
                          >
                            {removingId === (item.order_item_id ?? item.order_item_ids?.[0])
                              ? '...'
                              : '✕ Qaytarildi'}
                          </button>
                        )}
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
                  {/* Summa faqat EKRANDA ko'rinadi (kassir uchun).
                      Chop etilgan chekda esa "bill-fee-amount" yashiriladi —
                      mijoz faqat foizini ko'radi. */}
                  <span className="font-medium text-white bill-fee-amount">
                    {(bill.service_fee_amount || 0).toLocaleString()} so'm
                  </span>
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
                disabled={checkoutLoading || !bill || bill.items.length === 0 || bill.is_paid}
                title={bill?.is_paid ? "Bu hisob allaqachon to'langan" : "Hisobni yopish va stolni bo'shatish"}
                className="py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 active:scale-98"
              >
                {checkoutLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                <span>{bill?.is_paid ? "To'langan (yopilgan)" : "To'landi & Stolni Bo'shatish"}</span>
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
    </>
  );
};

export default BillModal;
