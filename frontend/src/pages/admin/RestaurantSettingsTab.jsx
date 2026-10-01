import React, { useState, useEffect } from 'react';
import api from '../../utils/api';
import {
  Settings,
  Percent,
  Printer,
  Archive,
  MessageSquare,
  Send,
  Bell,
  ToggleLeft,
  ToggleRight,
  Save,
  CheckCircle,
  RefreshCw,
  Globe,
  Wifi,
  Phone,
  MapPin,
  FileText,
  ShieldCheck,
  AlertTriangle,
  Bot,
  Smartphone,
  UtensilsCrossed,
  Flame,
  Receipt,
  Search
} from 'lucide-react';

const Toggle = ({ checked, onChange, label, description, icon: Icon, color = 'theme-primary' }) => (
  <div className="flex items-center justify-between p-4 rounded-2xl bg-black/30 border border-theme-border/70 gap-4">
    <div className="flex items-start gap-3 flex-1">
      {Icon && (
        <div className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0 text-${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      )}
      <div>
        <div className="text-xs font-bold text-white">{label}</div>
        {description && <div className="text-[11px] text-theme-muted mt-0.5 leading-relaxed">{description}</div>}
      </div>
    </div>
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`shrink-0 transition-all ${checked ? 'text-emerald-400' : 'text-zinc-600'}`}
    >
      {checked ? <ToggleRight className="w-8 h-8" /> : <ToggleLeft className="w-8 h-8" />}
    </button>
  </div>
);

const SettingsSection = ({ title, icon: Icon, children, accentColor = 'text-theme-primary' }) => (
  <div className="p-5 rounded-3xl glass-card border border-theme-border bg-theme-surface/80 shadow-xl space-y-4">
    <div className={`flex items-center gap-2 font-bold text-sm ${accentColor}`}>
      <Icon className="w-4 h-4" />
      <span>{title}</span>
    </div>
    {children}
  </div>
);

export const RestaurantSettingsTab = ({ restaurantId }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedOk, setSavedOk] = useState(false);

  // Settings fields
  const [serviceFeePercent, setServiceFeePercent] = useState(12);
  const [printerPaperWidth, setPrinterPaperWidth] = useState(80);
  const [archiveRetentionYears, setArchiveRetentionYears] = useState(3);
  const [receiptHeader, setReceiptHeader] = useState('RestAron Restaurant');
  const [receiptFooter, setReceiptFooter] = useState('Tashrif buyurganingiz uchun rahmat!');
  const [receiptAddress, setReceiptAddress] = useState('');
  const [receiptPhone, setReceiptPhone] = useState('');
  const [receiptWifiPass, setReceiptWifiPass] = useState('');

  // Feature toggles
  const [allowOrdersFromQr, setAllowOrdersFromQr] = useState(false);
  const [allowDebtPayment, setAllowDebtPayment] = useState(true);
  const [enableTelegramNotifications, setEnableTelegramNotifications] = useState(false);
  const [enableSmsReminders, setEnableSmsReminders] = useState(false);

  // 3-Printer Configuration
  const [printerCustomerName, setPrinterCustomerName] = useState('XP-Q80A');
  const [printerKitchen1Name, setPrinterKitchen1Name] = useState('XP-Q80A');
  const [printerKitchen2Name, setPrinterKitchen2Name] = useState('XP-Q80A');
  const [kitchen1Title, setKitchen1Title] = useState('1-Oshxona (Qozon taomlari)');
  const [kitchen2Title, setKitchen2Title] = useState('2-Oshxona (Baliq / Somsa)');
  const [autoPrintKitchen, setAutoPrintKitchen] = useState(true);
  const [autoPrintCustomerBill, setAutoPrintCustomerBill] = useState(true);
  const [directQrAccess, setDirectQrAccess] = useState(true);

  // Printer detection and test states
  const [detectedPrinters, setDetectedPrinters] = useState([]);
  const [detectingPrinters, setDetectingPrinters] = useState(false);
  const [testPrintLoading, setTestPrintLoading] = useState({});

  // Integrations
  const [telegramBotToken, setTelegramBotToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [smsProviderApiKey, setSmsProviderApiKey] = useState('');
  const [smsTemplate, setSmsTemplate] = useState(
    "Hurmatli {name}, {restaurant} restoranidagi {amount} so'm qarzingizni to'lashingizni so'raymiz. Muddat: {due_date}"
  );

  // Restaurant info
  const [restaurantName, setRestaurantName] = useState('');
  const [restaurantDescription, setRestaurantDescription] = useState('');
  const [restaurantAddress, setRestaurantAddress] = useState('');
  const [restaurantPhone, setRestaurantPhone] = useState('');

  const handleDetectPrinters = async () => {
    setDetectingPrinters(true);
    try {
      const res = await api.get('/receipts/printers/installed');
      if (res && res.printers) {
        setDetectedPrinters(res.printers);
      }
    } catch (e) {
      alert("Printerlarni aniqlashda xatolik: " + (e.message || ''));
    } finally {
      setDetectingPrinters(false);
    }
  };

  const handleTestPrint = async (printerKey, printerName, title) => {
    if (!printerName) {
      alert("Iltimos printer nomini kiriting yoki ro'yxatdan tanlang");
      return;
    }
    setTestPrintLoading((prev) => ({ ...prev, [printerKey]: true }));
    try {
      const sampleText = `================================\n   ${title.toUpperCase()}\n   RestAron Test Chop Etish\n================================\nPrinter: ${printerName}\nSana: ${new Date().toLocaleString()}\nHolat: Ulanish muvaffaqiyatli!\n================================\n\n\n`;
      await api.post('/receipts/print-raw-usb', {
        text: sampleText,
        printer_name: printerName,
        cut_paper: true,
      });
      alert(`✅ ${printerName} printeriga test cheki muvaffaqiyatli yuborildi!`);
    } catch (err) {
      alert(`❌ Chop etishda xatolik (${printerName}): ` + (err.message || 'Printer ulanmagan yoki Windows drayveri topilmadi'));
    } finally {
      setTestPrintLoading((prev) => ({ ...prev, [printerKey]: false }));
    }
  };

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const data = await api.get(`/restaurants/${restaurantId}`);
      if (data) {
        setRestaurantName(data.name || '');
        setRestaurantDescription(data.description || '');
        setRestaurantAddress(data.address || '');
        setRestaurantPhone(data.phone || '');
      }
      const s = data?.settings;
      if (s) {
        setServiceFeePercent(s.service_fee_percent ?? 12);
        setPrinterPaperWidth(s.printer_paper_width ?? 80);
        setArchiveRetentionYears(s.archive_retention_years ?? 3);
        setReceiptHeader(s.receipt_header || 'RestAron Restaurant');
        setReceiptFooter(s.receipt_footer || 'Tashrif buyurganingiz uchun rahmat!');
        setReceiptAddress(s.receipt_address || '');
        setReceiptPhone(s.receipt_phone || '');
        setReceiptWifiPass(s.receipt_wifi_pass || '');
        setAllowOrdersFromQr(s.allow_orders_from_qr ?? false);
        setAllowDebtPayment(s.allow_debt_payment ?? true);
        setEnableTelegramNotifications(s.enable_telegram_notifications ?? false);
        setEnableSmsReminders(s.enable_sms_reminders ?? false);
        setTelegramBotToken(s.telegram_bot_token || '');
        setTelegramChatId(s.telegram_chat_id || '');
        setSmsProviderApiKey(s.sms_provider_api_key || '');
        setSmsTemplate(s.sms_template || smsTemplate);

        // 3-Printer settings
        setPrinterCustomerName(s.printer_customer_name || 'XP-Q80A');
        setPrinterKitchen1Name(s.printer_kitchen1_name || 'XP-Q80A');
        setPrinterKitchen2Name(s.printer_kitchen2_name || 'XP-Q80A');
        setKitchen1Title(s.kitchen1_title || '1-Oshxona (Qozon taomlari)');
        setKitchen2Title(s.kitchen2_title || '2-Oshxona (Baliq / Somsa)');
        setAutoPrintKitchen(s.auto_print_kitchen ?? true);
        setAutoPrintCustomerBill(s.auto_print_customer_bill ?? true);
        setDirectQrAccess(s.direct_qr_access ?? true);
      }
    } catch (err) {
      console.error('Error fetching settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, [restaurantId]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSavedOk(false);
    try {
      // Update restaurant info
      await api.patch(`/restaurants/${restaurantId}`, {
        name: restaurantName.trim() || undefined,
        description: restaurantDescription.trim() || undefined,
        address: restaurantAddress.trim() || undefined,
        phone: restaurantPhone.trim() || undefined,
      });

      // Update settings
      await api.patch(`/restaurants/${restaurantId}/settings`, {
        service_fee_percent: parseFloat(serviceFeePercent) || 12,
        printer_paper_width: parseInt(printerPaperWidth) || 80,
        archive_retention_years: parseInt(archiveRetentionYears) || 3,
        receipt_header: receiptHeader.trim() || undefined,
        receipt_footer: receiptFooter.trim() || undefined,
        receipt_address: receiptAddress.trim() || undefined,
        receipt_phone: receiptPhone.trim() || undefined,
        receipt_wifi_pass: receiptWifiPass.trim() || undefined,
        allow_orders_from_qr: allowOrdersFromQr,
        allow_debt_payment: allowDebtPayment,
        enable_telegram_notifications: enableTelegramNotifications,
        telegram_bot_token: telegramBotToken.trim() || undefined,
        telegram_chat_id: telegramChatId.trim() || undefined,
        enable_sms_reminders: enableSmsReminders,
        sms_provider_api_key: smsProviderApiKey.trim() || undefined,
        sms_template: smsTemplate.trim() || undefined,
        // 3-Printer and Routing
        printer_customer_name: printerCustomerName.trim() || undefined,
        printer_kitchen1_name: printerKitchen1Name.trim() || undefined,
        printer_kitchen2_name: printerKitchen2Name.trim() || undefined,
        kitchen1_title: kitchen1Title.trim() || undefined,
        kitchen2_title: kitchen2Title.trim() || undefined,
        auto_print_kitchen: autoPrintKitchen,
        auto_print_customer_bill: autoPrintCustomerBill,
        direct_qr_access: directQrAccess,
      });

      setSavedOk(true);
      setTimeout(() => setSavedOk(false), 3500);
    } catch (err) {
      alert(err.message || 'Sozlamalarni saqlashda xatolik yuz berdi');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-theme-muted">
        <RefreshCw className="w-6 h-6 animate-spin mr-2 text-theme-primary" />
        <span className="text-sm">Sozlamalar yuklanmoqda...</span>
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="p-6 rounded-3xl glass-card border border-theme-border bg-theme-surface/85 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-theme-primary text-xs font-bold uppercase tracking-wider mb-1">
            <Settings className="w-4 h-4" />
            <span>Restoran Sozlamalari</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-white">
            Kassa, Chek & Integratsiya Sozlamalari
          </h2>
          <p className="text-xs text-theme-muted mt-1">
            Xizmat haqi foizi, Xprinter konfiguratsiyasi, SMS va Telegram bot integratsiyalari, va boshqa muhim sozlamalar.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {savedOk && (
            <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold animate-fade-in">
              <CheckCircle className="w-4 h-4" />
              <span>Saqlandi!</span>
            </div>
          )}
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center gap-2 disabled:opacity-50 transition-all active:scale-95"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saqlanmoqda...' : 'Sozlamalarni Saqlash'}</span>
          </button>
        </div>
      </div>

      {/* ─── Section 1: Restoran Ma'lumotlari ─────────────────────────── */}
      <SettingsSection title="Restoran Ma'lumotlari" icon={Globe}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Restoran Nomi:</label>
            <input
              type="text"
              value={restaurantName}
              onChange={(e) => setRestaurantName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-theme-primary"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Telefon Raqami:</label>
            <input
              type="text"
              placeholder="+998 ..."
              value={restaurantPhone}
              onChange={(e) => setRestaurantPhone(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-theme-primary"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Manzil:</label>
            <input
              type="text"
              placeholder="Masalan: Toshkent, Chilonzor ko'chasi 12"
              value={restaurantAddress}
              onChange={(e) => setRestaurantAddress(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-theme-primary"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Tavsif (ixtiyoriy):</label>
            <textarea
              rows={2}
              value={restaurantDescription}
              onChange={(e) => setRestaurantDescription(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-theme-primary resize-none"
            />
          </div>
        </div>
      </SettingsSection>

      {/* ─── Section 2: Xizmat Haqi va Kassa ─────────────────────────── */}
      <SettingsSection title="💰 Xizmat Haqi (Service Fee) & Kassa Sozlamalari" icon={Percent} accentColor="text-amber-400">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Service Fee with live preview like Ali Poster */}
          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-theme-muted mb-2">
              Xizmat Haqi Foizi (Service Fee %):
            </label>
            <div className="flex items-center gap-4">
              <div className="relative flex-1 max-w-[160px]">
                <input
                  type="number"
                  min="0"
                  max="30"
                  step="0.5"
                  value={serviceFeePercent}
                  onChange={(e) => setServiceFeePercent(e.target.value)}
                  className="w-full pl-4 pr-8 py-3 rounded-xl bg-black/40 border-2 border-amber-500/50 text-xl font-black text-amber-300 text-center font-mono focus:outline-none focus:border-amber-400"
                />
                <span className="absolute right-3 top-3 text-amber-400 font-black text-xl">%</span>
              </div>
              <div className="text-xs text-theme-muted space-y-1">
                <div>Masalan: 100 000 so'm buyurtmaga</div>
                <div className="text-amber-300 font-bold font-mono">
                  + {Math.round(100000 * (parseFloat(serviceFeePercent) || 0) / 100).toLocaleString()} so'm xizmat haqi
                </div>
                <div className="text-white font-bold font-mono">
                  = {Math.round(100000 * (1 + (parseFloat(serviceFeePercent) || 0) / 100)).toLocaleString()} so'm jami
                </div>
              </div>
            </div>
            <p className="text-[11px] text-theme-muted mt-2 leading-relaxed">
              Har bir hisob chekiga avtomatik qo'shiladi. Faqat shu sahifadan o'zgartiring (masalan 12% → 13%).
            </p>
          </div>

          {/* Quick presets */}
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-2">Tezkor Foizlar:</label>
            <div className="grid grid-cols-2 gap-2">
              {[0, 5, 10, 12, 13, 15].map((pct) => (
                <button
                  key={pct}
                  type="button"
                  onClick={() => setServiceFeePercent(pct)}
                  className={`py-2 rounded-xl text-xs font-black font-mono border transition-all ${
                    Number(serviceFeePercent) === pct
                      ? 'bg-amber-500 text-black border-amber-400 shadow-lg'
                      : 'bg-black/30 border-theme-border text-zinc-300 hover:border-amber-400/50'
                  }`}
                >
                  {pct}%
                </button>
              ))}
            </div>
          </div>
        </div>
      </SettingsSection>

      {/* ─── Section 3: Xprinter (Thermal Printer) ────────────────────── */}
      <SettingsSection title="🖨️ Xprinter Termoprinter Sozlamalari" icon={Printer} accentColor="text-blue-400">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Paper Width */}
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-2">
              Qog'oz Kengligi (mm):
            </label>
            <div className="flex items-center gap-2.5">
              {[58, 80].map((w) => (
                <button
                  key={w}
                  type="button"
                  onClick={() => setPrinterPaperWidth(w)}
                  className={`flex-1 py-3 rounded-xl text-sm font-black font-mono border transition-all ${
                    Number(printerPaperWidth) === w
                      ? 'bg-blue-600/20 border-blue-400 text-blue-300 shadow-md shadow-blue-500/10'
                      : 'bg-black/30 border-theme-border text-zinc-400 hover:border-blue-400/40'
                  }`}
                >
                  {w}mm
                </button>
              ))}
            </div>
            <p className="text-[11px] text-theme-muted mt-2">
              58mm — kichik cheklar. 80mm — standart termal cheklar.
            </p>
          </div>

          {/* Archive Retention */}
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-2">
              Arxiv Saqlash Muddati (yil):
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 5, 7].map((yr) => (
                <button
                  key={yr}
                  type="button"
                  onClick={() => setArchiveRetentionYears(yr)}
                  className={`flex-1 py-2.5 rounded-xl text-xs font-black font-mono border transition-all ${
                    Number(archiveRetentionYears) === yr
                      ? 'bg-blue-600/20 border-blue-400 text-blue-300 shadow-md'
                      : 'bg-black/30 border-theme-border text-zinc-400 hover:border-blue-400/40'
                  }`}
                >
                  {yr}y
                </button>
              ))}
            </div>
            <p className="text-[11px] text-theme-muted mt-2">
              Standart: 3 yil. Soliq talablari uchun 5 yil tavsiya etiladi.
            </p>
          </div>
        </div>

        {/* Chek Shabloni */}
        <div className="pt-4 border-t border-theme-border/50 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Chek Sarlavhasi (Header):</label>
            <input
              type="text"
              placeholder="Masalan: Ali Restoran"
              value={receiptHeader}
              onChange={(e) => setReceiptHeader(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Chek Oxiri (Footer):</label>
            <input
              type="text"
              placeholder="Masalan: Tashrif uchun rahmat!"
              value={receiptFooter}
              onChange={(e) => setReceiptFooter(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Chekdagi Manzil:</label>
            <input
              type="text"
              placeholder="Toshkent shahar, ..."
              value={receiptAddress}
              onChange={(e) => setReceiptAddress(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white focus:outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Chekdagi Telefon:</label>
            <input
              type="text"
              placeholder="+998 ..."
              value={receiptPhone}
              onChange={(e) => setReceiptPhone(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-[11px] font-semibold text-theme-muted mb-1">Wi-Fi Paroli (Chekda ko'rinadi):</label>
            <input
              type="text"
              placeholder="Masalan: restaurant_wifi_2024"
              value={receiptWifiPass}
              onChange={(e) => setReceiptWifiPass(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
            />
          </div>
        </div>
      </SettingsSection>

      {/* ─── Section 3.5: 3 ta Chek Printerlari va Oshxona Routing ───────────────── */}
      <SettingsSection title="🖨️ 3 ta Chek Printerlari va Oshxona Routing Sozlamasi" icon={Printer} accentColor="text-amber-400">
        <div className="space-y-4">
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="text-xs font-bold text-amber-300">Tizimga ulangan Windows printerlarni aniqlash</div>
              <div className="text-[11px] text-theme-muted mt-0.5">
                Kompyuteringizga USB orqali ulangan barcha Xprinter yoki kassa printerlarini avtomatik qidiradi.
              </div>
            </div>
            <button
              type="button"
              onClick={handleDetectPrinters}
              disabled={detectingPrinters}
              className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shrink-0 flex items-center gap-1.5 transition-all shadow-md disabled:opacity-50"
            >
              <Search className={`w-3.5 h-3.5 ${detectingPrinters ? 'animate-spin' : ''}`} />
              <span>{detectingPrinters ? 'Qidirilmoqda...' : 'Printerlarni aniqlash'}</span>
            </button>
          </div>

          {detectedPrinters.length > 0 && (
            <div className="p-3.5 rounded-2xl bg-black/40 border border-theme-border/60">
              <span className="text-[11px] font-bold text-theme-muted block mb-2">Kompyuterda topilgan printerlar (bosib tanlang):</span>
              <div className="flex flex-wrap gap-2">
                {detectedPrinters.map((p) => (
                  <span
                    key={p}
                    className="px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-mono font-bold flex items-center gap-1.5 cursor-pointer border border-white/10"
                    title="Bosib printer nomini nusxalang"
                    onClick={() => {
                      navigator.clipboard?.writeText(p);
                      alert(`'${p}' nusxalandi!`);
                    }}
                  >
                    <span>🖨️ {p}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 3 ta printer kartalari */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-2">
            {/* 1-Printer: Mijoz kassa cheki */}
            <div className="p-4 rounded-2xl bg-black/40 border border-emerald-500/30 flex flex-col justify-between space-y-3 shadow-lg">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-wider">
                    1-Printer • Mijoz Cheki
                  </span>
                  <Receipt className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-sm font-bold text-white">Mijozlar Hisob Cheki (Kassa)</div>
                <p className="text-[11px] text-theme-muted leading-relaxed">
                  Mijoz nimalar yeganini narxi, servis haqi va to'lov summasi bilan kassa oldida chiqaradigan printer.
                </p>

                <div className="pt-2">
                  <label className="block text-[11px] font-semibold text-theme-muted mb-1">Printer nomi (Windows):</label>
                  <input
                    type="text"
                    placeholder="Masalan: XP-Q80A yoki Xprinter"
                    value={printerCustomerName}
                    onChange={(e) => setPrinterCustomerName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-emerald-500/40 text-xs text-white font-mono focus:outline-none focus:border-emerald-400"
                  />
                  {detectedPrinters.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {detectedPrinters.map(p => (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setPrinterCustomerName(p)}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 border border-emerald-500/20"
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <button
                type="button"
                disabled={testPrintLoading.p1}
                onClick={() => handleTestPrint('p1', printerCustomerName, '1-Printer (Mijozlar Cheki)')}
                className="w-full py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold transition-all flex items-center justify-center gap-1.5 active:scale-95"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>{testPrintLoading.p1 ? 'Chop etilmoqda...' : 'Test chop etish'}</span>
              </button>
            </div>

            {/* 2-Printer: 1-Oshxona (Qozon) */}
            <div className="p-4 rounded-2xl bg-black/40 border border-amber-500/30 flex flex-col justify-between space-y-3 shadow-lg">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-[10px] font-black uppercase tracking-wider">
                    2-Printer • 1-Oshxona
                  </span>
                  <UtensilsCrossed className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-sm font-bold text-white">Qozonda Pishadigan Taomlar</div>
                <p className="text-[11px] text-theme-muted leading-relaxed">
                  Oshxonadagi 1-printer. Faqat qozonda pishiriladigan taomlar (osh, sho'rva, qozon kabob...) buyurtmalari chiqadi.
                </p>

                <div className="pt-2 space-y-2">
                  <div>
                    <label className="block text-[11px] font-semibold text-theme-muted mb-1">Oshxona nomi:</label>
                    <input
                      type="text"
                      placeholder="1-Oshxona (Qozon taomlari)"
                      value={kitchen1Title}
                      onChange={(e) => setKitchen1Title(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-theme-border text-xs text-white focus:outline-none focus:border-amber-400"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-theme-muted mb-1">Printer nomi (Windows):</label>
                    <input
                      type="text"
                      placeholder="Masalan: XP-80 Kitchen 1"
                      value={printerKitchen1Name}
                      onChange={(e) => setPrinterKitchen1Name(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-amber-500/40 text-xs text-white font-mono focus:outline-none focus:border-amber-400"
                    />
                    {detectedPrinters.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {detectedPrinters.map(p => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => setPrinterKitchen1Name(p)}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 border border-amber-500/20"
                          >
                            {p}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <button
                type="button"
                disabled={testPrintLoading.p2}
                onClick={() => handleTestPrint('p2', printerKitchen1Name, kitchen1Title || '1-Oshxona (Qozon)')}
                className="w-full py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-bold transition-all flex items-center justify-center gap-1.5 active:scale-95"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>{testPrintLoading.p2 ? 'Chop etilmoqda...' : 'Test chop etish'}</span>
              </button>
            </div>

            {/* 3-Printer: 2-Oshxona (Baliq va Somsa) */}
            <div className="p-4 rounded-2xl bg-black/40 border border-blue-500/30 flex flex-col justify-between space-y-3 shadow-lg">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 text-[10px] font-black uppercase tracking-wider">
                    3-Printer • 2-Oshxona
                  </span>
                  <Flame className="w-4 h-4 text-blue-400" />
                </div>
                <div className="text-sm font-bold text-white">Baliq va Somsa Stansiyasi</div>
                <p className="text-[11px] text-theme-muted leading-relaxed">
                  Oshxonadagi 2-printer. Faqat qozonda pishmaydigan taomlar (baliq, somsa, mangal...) buyurtmalari chiqadi.
                </p>

                <div className="pt-2 space-y-2">
                  <div>
                    <label className="block text-[11px] font-semibold text-theme-muted mb-1">Oshxona nomi:</label>
                    <input
                      type="text"
                      placeholder="2-Oshxona (Baliq / Somsa)"
                      value={kitchen2Title}
                      onChange={(e) => setKitchen2Title(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-theme-border text-xs text-white focus:outline-none focus:border-blue-400"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-theme-muted mb-1">Printer nomi (Windows):</label>
                    <input
                      type="text"
                      placeholder="Masalan: XP-80 Kitchen 2"
                      value={printerKitchen2Name}
                      onChange={(e) => setPrinterKitchen2Name(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-blue-500/40 text-xs text-white font-mono focus:outline-none focus:border-blue-400"
                    />
                    {detectedPrinters.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {detectedPrinters.map(p => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => setPrinterKitchen2Name(p)}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 hover:bg-blue-500/20 border border-blue-500/20"
                          >
                            {p}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <button
                type="button"
                disabled={testPrintLoading.p3}
                onClick={() => handleTestPrint('p3', printerKitchen2Name, kitchen2Title || '2-Oshxona (Baliq/Somsa)')}
                className="w-full py-2 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 text-blue-300 text-xs font-bold transition-all flex items-center justify-center gap-1.5 active:scale-95"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>{testPrintLoading.p3 ? 'Chop etilmoqda...' : 'Test chop etish'}</span>
              </button>
            </div>
          </div>

          {/* Avtomatlashtirish togglelari */}
          <div className="pt-3 border-t border-theme-border/50 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Toggle
              checked={autoPrintKitchen}
              onChange={setAutoPrintKitchen}
              label="Oshxonaga avtomatik chop etish"
              description="Ofitsiant 'На кухню' bosganda tegishli 1 va 2-oshxona printerlariga to'g'ridan-to'g'ri chop etiladi."
              icon={Printer}
              color="amber-400"
            />
            <Toggle
              checked={autoPrintCustomerBill}
              onChange={setAutoPrintCustomerBill}
              label="Mijoz chekini avtomatik chop etish"
              description="Kassada to'lov amalga oshirilganda 1-printerdan mijoz hisob cheki avtomatik chiqadi."
              icon={Receipt}
              color="emerald-400"
            />
          </div>
        </div>
      </SettingsSection>

      {/* ─── Section 4: Xususiyat Togglelari ─────────────────────────── */}
      <SettingsSection title="⚙️ Funksiya va Huquq Sozlamalari" icon={ShieldCheck} accentColor="text-emerald-400">
        <div className="space-y-2">
          <Toggle
            checked={directQrAccess}
            onChange={setDirectQrAccess}
            label="QR kod skanerlanganda ruxsatsiz to'g'ridan-to'g'ri kirish"
            description="Mijoz stolga o'tirib QR kodni skaner qilganda hech qanday ruxsatsiz yoki PIN kodi kutilmasdan to'g'ridan-to'g'ri menyuga kiradi."
            icon={Globe}
            color="emerald-400"
          />
          <Toggle
            checked={allowOrdersFromQr}
            onChange={setAllowOrdersFromQr}
            label="QR Kod orqali Buyurtma berish"
            description="Mijozlar QR menyudan to'g'ridan-to'g'ri buyurtma bera oladi. O'chirilsa — faqat ko'rish (View-only) rejimi ishlaydi."
            icon={Globe}
          />
          <Toggle
            checked={allowDebtPayment}
            onChange={setAllowDebtPayment}
            label="Nasiya (Qarz) to'lov usuli"
            description="Ofitsiantlar checkout paytida 'Nasiya' to'lov turini tanlay oladi va qarz daftariga kiritiladi."
            icon={FileText}
            color="amber-400"
          />
        </div>
      </SettingsSection>

      {/* ─── Section 5: Telegram Bot ──────────────────────────────────── */}
      <SettingsSection title="🤖 Telegram Bot Bildirgi (Xodimlar Guruhi)" icon={Bot} accentColor="text-cyan-400">
        <Toggle
          checked={enableTelegramNotifications}
          onChange={setEnableTelegramNotifications}
          label="Telegram bildirishnomalarni yoqish"
          description="Mijoz ofitsiant chaqirganda yoki chek so'raganda, xodimlarning Telegram guruhiga avtomatik xabar boradi."
          icon={Bell}
          color="cyan-400"
        />
        {enableTelegramNotifications && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 animate-fade-in">
            <div>
              <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                Bot Token (BotFather'dan):
              </label>
              <input
                type="text"
                placeholder="123456789:ABC-DEF..."
                value={telegramBotToken}
                onChange={(e) => setTelegramBotToken(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                Guruh / Chat ID (-100...):
              </label>
              <input
                type="text"
                placeholder="-1001234567890"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-cyan-400"
              />
            </div>
          </div>
        )}
      </SettingsSection>

      {/* ─── Section 6: SMS Eslatmalar ────────────────────────────────── */}
      <SettingsSection title="📲 SMS Eslatmalar (Nasiya Daftari)" icon={Smartphone} accentColor="text-purple-400">
        <Toggle
          checked={enableSmsReminders}
          onChange={setEnableSmsReminders}
          label="SMS eslatmalarni yoqish (Eskiz yoki boshqa provider)"
          description="Qarzdorlarga qo'lda yoki avtomatik SMS yuborish imkoniyati. SMS provayderdan API kaliti kerak bo'ladi."
          icon={Send}
          color="purple-400"
        />
        {enableSmsReminders && (
          <div className="space-y-3 pt-2 animate-fade-in">
            <div>
              <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                SMS Provayder API Kaliti (Eskiz.uz yoki boshqa):
              </label>
              <input
                type="password"
                placeholder="Eskiz API key yoki boshqa provayder token..."
                value={smsProviderApiKey}
                onChange={(e) => setSmsProviderApiKey(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-purple-400"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                SMS Shablon matni:
              </label>
              <textarea
                rows={3}
                value={smsTemplate}
                onChange={(e) => setSmsTemplate(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/30 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-purple-400 resize-none"
              />
              <p className="text-[11px] text-theme-muted mt-1">
                O'zgaruvchilar: <code className="text-purple-300">{'{name}'}</code> (mijoz ismi), <code className="text-purple-300">{'{restaurant}'}</code>, <code className="text-purple-300">{'{amount}'}</code>, <code className="text-purple-300">{'{due_date}'}</code>
              </p>
            </div>
          </div>
        )}
      </SettingsSection>

      {/* ─── Save Button (bottom sticky) ───────────────────────────────── */}
      <div className="sticky bottom-4 z-10">
        <div className="p-3 rounded-2xl bg-black/80 backdrop-blur-md border border-theme-border/70 flex items-center justify-between gap-4">
          <div className="text-xs text-theme-muted">
            Barcha o'zgartirishlar saqlangandan so'ng darhol kuchga kiradi.
          </div>
          <div className="flex items-center gap-2.5">
            {savedOk && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold">
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Saqlandi!</span>
              </div>
            )}
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 rounded-xl bg-theme-primary hover:bg-theme-primary-hover text-white text-xs font-bold shadow-glow flex items-center gap-2 disabled:opacity-50 active:scale-95 transition-all"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saqlanmoqda...' : 'Saqlash'}</span>
            </button>
          </div>
        </div>
      </div>
    </form>
  );
};

export default RestaurantSettingsTab;
