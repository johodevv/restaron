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
  Search,
  Eye,
  Sparkles,
  CheckCircle2
} from 'lucide-react';

const toCyrillicJS = (str) => {
  if (!str) return '';
  let s = String(str);
  const multi = [
    [/sh/gi, 'ш'], [/ch/gi, 'ч'], [/yo/gi, 'ё'], [/yu/gi, 'ю'], [/ya/gi, 'я'], [/ye/gi, 'е'],
    [/o['‘`’]/gi, 'ў'], [/g['‘`’]/gi, 'ғ']
  ];
  multi.forEach(([re, cyr]) => { s = s.replace(re, cyr); });
  const map = {
    a: 'а', b: 'б', d: 'д', e: 'е', f: 'ф', g: 'г', h: 'ҳ', i: 'и', j: 'ж',
    k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', q: 'қ', r: 'р', s: 'с',
    t: 'т', u: 'у', v: 'в', x: 'х', y: 'й', z: 'з',
    A: 'А', B: 'Б', D: 'Д', E: 'Е', F: 'Ф', G: 'Г', H: 'Ҳ', I: 'И', J: 'Ж',
    K: 'К', L: 'Л', M: 'М', N: 'Н', O: 'О', P: 'П', Q: 'Қ', R: 'Р', S: 'С',
    T: 'Т', U: 'У', V: 'В', X: 'Х', Y: 'Й', Z: 'З'
  };
  return s.split('').map(c => map[c] || c).join('');
};

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
  const [printerCodepage, setPrinterCodepage] = useState(17);
  // Chek shrifti o'lchami: keksa odamlar o'qiy olishi uchun
  const [printerFontSize, setPrinterFontSize] = useState('katta');
  // Harflar orasidagi masofa (nuqta) va qatorlar orasi
  const [printerCharSpacing, setPrinterCharSpacing] = useState(1);
  const [printerLineSpacing, setPrinterLineSpacing] = useState('oddiy');
  // Ishlab turgan kod versiyasi (yangilanganini tekshirish uchun)
  const [appVersion, setAppVersion] = useState(null);
  // 4-Printer: BAR (choy, suv, ichimliklar)
  const [printerBarName, setPrinterBarName] = useState('');
  const [barTitle, setBarTitle] = useState('BAR (Ichimliklar)');
  const [testingCodepage, setTestingCodepage] = useState(false);
  const [archiveRetentionYears, setArchiveRetentionYears] = useState(3);
  const [receiptHeader, setReceiptHeader] = useState('RestAron Restaurant');
  const [receiptFooter, setReceiptFooter] = useState('Tashrif buyurganingiz uchun rahmat!');
  const [receiptAddress, setReceiptAddress] = useState('');
  const [receiptPhone, setReceiptPhone] = useState('');
  const [receiptWifiPass, setReceiptWifiPass] = useState('');
  const [previewTab, setPreviewTab] = useState('bill'); // 'bill' | 'k1' | 'k2'
  const [receiptCyrillic, setReceiptCyrillic] = useState(true);

  // Feature toggles
  const [allowOrdersFromQr, setAllowOrdersFromQr] = useState(false);
  const [allowDebtPayment, setAllowDebtPayment] = useState(true);
  const [enableTelegramNotifications, setEnableTelegramNotifications] = useState(false);
  const [enableSmsReminders, setEnableSmsReminders] = useState(false);

  // 3-Printer Configuration
  const [printerCustomerName, setPrinterCustomerName] = useState('X-Q80A');
  const [printerKitchen1Name, setPrinterKitchen1Name] = useState('192.168.1.201');
  const [printerKitchen2Name, setPrinterKitchen2Name] = useState('192.168.1.202');
  const [kitchen1Title, setKitchen1Title] = useState('1-Oshxona (Qozon taomlari)');
  const [kitchen2Title, setKitchen2Title] = useState('2-Oshxona (Baliq / Somsa)');
  const [autoPrintKitchen, setAutoPrintKitchen] = useState(true);
  const [autoPrintCustomerBill, setAutoPrintCustomerBill] = useState(true);
  const [directQrAccess, setDirectQrAccess] = useState(true);
  const [enableChefKds, setEnableChefKds] = useState(false);

  // Printer detection and test states
  const [detectedPrinters, setDetectedPrinters] = useState([]);
  const [detectingPrinters, setDetectingPrinters] = useState(false);
  const [lanPrinters, setLanPrinters] = useState([]);
  const [scanningLan, setScanningLan] = useState(false);
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

  // LAN kabeli bilan ulangan printerlarni tarmoqdan qidirish (9100-port)
  // Qaysi kirill kod sahifasi to'g'ri ekanini aniqlash uchun sinov cheki
  const handleCodepageTest = async () => {
    setTestingCodepage(true);
    try {
      const res = await api.post('/receipts/printers/codepage-test', {});
      if (res?.success) {
        alert(
          "Sinov cheki chiqarildi.\n\n" +
          "Qog'ozga qarang: har qatorda [raqam] va kirill alifbosi bor.\n" +
          "QAYSI QATOR TO'G'RI o'qilsa, o'sha raqamni pastdagi\n" +
          "\"Kirill kod sahifasi\" maydoniga yozing va Saqlang."
        );
      } else {
        alert('Chop etib bo\'lmadi: ' + (res?.message || ''));
      }
    } catch (e) {
      alert('Xatolik: ' + (e.message || ''));
    } finally {
      setTestingCodepage(false);
    }
  };

  const handleScanLan = async () => {
    setScanningLan(true);
    setLanPrinters([]);
    try {
      const res = await api.get('/receipts/printers/scan-network');
      setLanPrinters(res?.printers || []);
      if (!res?.printers?.length) {
        alert(
          "Tarmoqdan printer topilmadi.\n\n" +
          "Tekshiring:\n" +
          "- Printer yoqilganmi va LAN kabeli routerga ulanganmi?\n" +
          "- Printer va server BIR XIL Wi-Fi/tarmoqda turibdimi?\n" +
          "- Printerda tarmoq (Ethernet) moduli bormi?"
        );
      }
    } catch (e) {
      alert('Tarmoqni skanerlashda xatolik: ' + (e.message || ''));
    } finally {
      setScanningLan(false);
    }
  };

  const handleTestPrint = async (printerKey, printerName, title) => {
    if (!printerName) {
      alert("Iltimos printer nomini kiriting yoki ro'yxatdan tanlang");
      return;
    }
    setTestPrintLoading((prev) => ({ ...prev, [printerKey]: true }));
    try {
      await api.post('/receipts/print-raw-usb', {
        // Namuna chek serverda yasaladi: qator kengligi tanlangan
        // shriftga aniq moslanadi va admin qog'ozda AYNAN mijozga
        // beriladigan chekni ko'radi.
        text: '',
        sample_receipt: true,
        printer_name: printerName,
        cut_paper: true,
        restaurant_id: restaurantId,
        // Hozir tanlangan shrift bilan chiqsin — admin natijani
        // qog'ozda darhol ko'rishi uchun (saqlashdan oldin ham).
        font_size: printerFontSize,
        char_spacing: printerCharSpacing,
        line_spacing: printerLineSpacing,
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
        setPrinterCodepage(s.printer_codepage || 17);
        setPrinterFontSize(s.printer_font_size || 'katta');
        setPrinterCharSpacing(
          s.printer_char_spacing === null || s.printer_char_spacing === undefined
            ? 1
            : s.printer_char_spacing
        );
        setPrinterLineSpacing(s.printer_line_spacing || 'oddiy');
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
        setPrinterCustomerName(s.printer_customer_name || 'X-Q80A');
        setPrinterKitchen1Name(s.printer_kitchen1_name || '192.168.1.201');
        setPrinterKitchen2Name(s.printer_kitchen2_name || '192.168.1.202');
        setKitchen1Title(s.kitchen1_title || '1-Oshxona (Qozon taomlari)');
        setKitchen2Title(s.kitchen2_title || '2-Oshxona (Baliq / Somsa)');
        setPrinterBarName(s.printer_bar_name || '');
        setBarTitle(s.bar_title || 'BAR (Ichimliklar)');
        setAutoPrintKitchen(s.auto_print_kitchen ?? true);
        setAutoPrintCustomerBill(s.auto_print_customer_bill ?? true);
        setDirectQrAccess(s.direct_qr_access ?? true);
        setEnableChefKds(s.enable_chef_kds ?? false);
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

  // Serverdan versiyani olamiz. /health — API prefiksisiz manzil.
  useEffect(() => {
    fetch('/health')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setAppVersion(d))
      .catch(() => {});
  }, []);

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
        printer_codepage: parseInt(printerCodepage) || 17,
        printer_font_size: printerFontSize,
        printer_char_spacing: printerCharSpacing,
        printer_line_spacing: printerLineSpacing,
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
        printer_bar_name: printerBarName.trim(),
        bar_title: barTitle.trim() || undefined,
        auto_print_kitchen: autoPrintKitchen,
        auto_print_customer_bill: autoPrintCustomerBill,
        direct_qr_access: directQrAccess,
        enable_chef_kds: enableChefKds,
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

      {/* Dastur versiyasi — yangilanish yetib kelganini tekshirish uchun */}
      {appVersion && (
        <div className="p-3.5 rounded-2xl bg-black/30 border border-theme-border/70 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-base">🔖</span>
            <div>
              <div className="text-xs font-bold text-white">Dastur versiyasi</div>
              <div className="text-[11px] text-theme-muted">
                Yangilagandan keyin bu raqam o'zgarishi kerak. O'zgarmasa —
                yangilanish server'ga yetib bormagan.
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-mono font-black text-theme-primary text-sm">
              {appVersion.version || 'nomalum'}
            </div>
            {appVersion.updated_at && (
              <div className="text-[10px] text-theme-muted font-mono">
                {appVersion.updated_at}
              </div>
            )}
          </div>
        </div>
      )}

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

        {/* Chek Shabloni va Jonli Ko'rinish */}
        <div className="pt-5 border-t border-theme-border/60 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-400" />
                <span>🧾 Chek Shabloni & Jonli Ko'rinishi (Live Preview)</span>
              </h4>
              <p className="text-[11px] text-theme-muted">
                Admin paneldan chek matnlarini, sarlavhani va pastki qismini o'zgartiring. Chek real vaqtda yangilanadi.
              </p>
            </div>

            {/* Kirill alifbosi toggle */}
            <button
              type="button"
              onClick={() => setReceiptCyrillic(!receiptCyrillic)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 ${
                receiptCyrillic
                  ? 'bg-blue-600/20 border-blue-400 text-blue-300 shadow-sm'
                  : 'bg-black/30 border-theme-border text-zinc-400'
              }`}
            >
              <span>{receiptCyrillic ? '🔤 Kirillcha (Ўзбек / Рус)' : '🔤 Lotincha'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Chap tomon: Shablon Maydonlari */}
            <div className="lg:col-span-7 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                    Restoran Sarlavhasi (Header):
                  </label>
                  <input
                    type="text"
                    placeholder="Masalan: RestAron Chorsu"
                    value={receiptHeader}
                    onChange={(e) => setReceiptHeader(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                    Pastki Matn / Tilak (Footer):
                  </label>
                  <input
                    type="text"
                    placeholder="Masalan: Tashrifingiz uchun rahmat! Yana keling!"
                    value={receiptFooter}
                    onChange={(e) => setReceiptFooter(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                    Chekdagi Manzil:
                  </label>
                  <input
                    type="text"
                    placeholder="Toshkent sh., Navoiy ko'chasi, 21-uy"
                    value={receiptAddress}
                    onChange={(e) => setReceiptAddress(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-theme-border text-xs text-white focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                    Chekdagi Telefon:
                  </label>
                  <input
                    type="text"
                    placeholder="+998 71 200 00 00"
                    value={receiptPhone}
                    onChange={(e) => setReceiptPhone(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                    Wi-Fi Login va Paroli (Mijoz chekida ko'rinadi):
                  </label>
                  <input
                    type="text"
                    placeholder="Masalan: Wi-Fi: RestAron_Guest | Parol: 88889999"
                    value={receiptWifiPass}
                    onChange={(e) => setReceiptWifiPass(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-theme-border text-xs text-white font-mono focus:outline-none focus:border-blue-400"
                  />
                </div>
              </div>

              {/* Shablondagi qo'shimcha parametrlar */}
              <div className="p-3.5 rounded-2xl bg-black/30 border border-theme-border/60 text-xs space-y-2">
                <span className="text-[11px] font-bold text-white block">💡 Chek sozlamalari ko'rsatmasi:</span>
                <ul className="text-[11px] text-theme-muted space-y-1 list-disc list-inside">
                  <li>Chekdagi barcha matnlar Xprinter termal printerlariga mos ravishda <strong>kirill harflarida (CP866)</strong> chop etiladi.</li>
                  <li>Oshxona begunog'i (2 va 3-printer) da taom nomi, miqdori va maxsus izohi chiqadi.</li>
                  <li>Mijoz chekida (1-printer) esa har bir taom narxi, umumiy hisob, {serviceFeePercent}% servis va yakuniy summa ko'rsatiladi.</li>
                </ul>
              </div>
            </div>

            {/* O'ng tomon: Jonli Termal Chek Qog'ozi (Live Paper Preview) */}
            <div className="lg:col-span-5 bg-zinc-950 p-4 rounded-3xl border border-theme-border/80 shadow-2xl space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-white/10">
                <span className="text-xs font-bold text-zinc-300 flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-blue-400" />
                  <span>Jonli Chek Ko'rinishi ({printerPaperWidth}mm):</span>
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                  {receiptCyrillic ? 'КИРИЛЛ' : 'LOTIN'}
                </span>
              </div>

              {/* Tab selector for 3 printers */}
              <div className="flex gap-1 bg-black/50 p-1 rounded-xl border border-white/10">
                <button
                  type="button"
                  onClick={() => setPreviewTab('bill')}
                  className={`flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all ${
                    previewTab === 'bill'
                      ? 'bg-emerald-500 text-slate-950 shadow'
                      : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  🧾 1-Mijoz Cheki
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewTab('k1')}
                  className={`flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all ${
                    previewTab === 'k1'
                      ? 'bg-amber-500 text-slate-950 shadow'
                      : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  🫕 1-Oshxona
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewTab('k2')}
                  className={`flex-1 py-1.5 text-[10px] font-bold rounded-lg transition-all ${
                    previewTab === 'k2'
                      ? 'bg-cyan-500 text-slate-950 shadow'
                      : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  🐟 2-Oshxona
                </button>
              </div>

              {/* Realistik Oq Termal Qog'oz */}
              <div className="bg-white text-zinc-900 p-4 sm:p-5 rounded-lg shadow-xl font-mono text-[11px] leading-tight select-none border-t-4 border-b-4 border-dashed border-zinc-300">
                {previewTab === 'bill' && (
                  <div className="space-y-1 text-center">
                    <div className="font-extrabold text-sm tracking-wider uppercase text-zinc-900">
                      {receiptCyrillic ? toCyrillicJS(receiptHeader || 'RestAron') : (receiptHeader || 'RestAron')}
                    </div>
                    {receiptAddress && (
                      <div className="text-[10px] text-zinc-600">
                        {receiptCyrillic ? toCyrillicJS(receiptAddress) : receiptAddress}
                      </div>
                    )}
                    {receiptPhone && (
                      <div className="text-[10px] text-zinc-600">
                        Тел: {receiptPhone}
                      </div>
                    )}
                    {receiptWifiPass && (
                      <div className="text-[10px] text-zinc-600 font-semibold">
                        Wi-Fi: {receiptWifiPass}
                      </div>
                    )}
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                    <div className="flex justify-between text-[10px] font-bold text-left">
                      <span>Стол: Зал № 5</span>
                      <span>Чек: № ORD-1024</span>
                    </div>
                    <div className="flex justify-between text-[10px] text-zinc-600 text-left">
                      <span>Официант: Зафарбек</span>
                      <span>{new Date().toLocaleDateString()} 12:45</span>
                    </div>
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                    <div className="text-left font-bold text-xs mb-1">
                      {receiptCyrillic ? 'Таомлар:' : 'Taomlar:'}
                    </div>
                    <div className="space-y-1 text-left text-[11px]">
                      <div>
                        <div>1. {receiptCyrillic ? 'Ош (Тўй оши)' : 'Osh (To\'y oshi)'}</div>
                        <div className="flex justify-between text-zinc-600">
                          <span>   2 х 45 000</span>
                          <span className="font-bold text-zinc-900">90 000</span>
                        </div>
                      </div>
                      <div>
                        <div>2. {receiptCyrillic ? 'Қозон кабоб' : 'Qozon kabob'}</div>
                        <div className="flex justify-between text-zinc-600">
                          <span>   1 х 85 000</span>
                          <span className="font-bold text-zinc-900">85 000</span>
                        </div>
                      </div>
                      <div>
                        <div>3. {receiptCyrillic ? 'Аччиқ-чучук салати' : 'Achchiq-chuchuk salati'}</div>
                        <div className="flex justify-between text-zinc-600">
                          <span>   2 х 15 000</span>
                          <span className="font-bold text-zinc-900">30 000</span>
                        </div>
                      </div>
                      <div>
                        <div>4. {receiptCyrillic ? 'Тандир нон' : 'Tandir non'}</div>
                        <div className="flex justify-between text-zinc-600">
                          <span>   2 х 6 000</span>
                          <span className="font-bold text-zinc-900">12 000</span>
                        </div>
                      </div>
                    </div>
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                    <div className="space-y-0.5 text-left text-[11px]">
                      <div className="flex justify-between">
                        <span>{receiptCyrillic ? 'Жами (Итого):' : 'Jami:'}</span>
                        <span>217 000</span>
                      </div>
                      <div className="flex justify-between text-zinc-700">
                        <span>{receiptCyrillic ? `Хизмат ҳақи (${serviceFeePercent}%):` : `Xizmat haqi (${serviceFeePercent}%):`}</span>
                        <span>{(217000 * (Number(serviceFeePercent) / 100)).toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="my-2 border-b-2 border-zinc-900" />
                    <div className="flex justify-between font-black text-xs text-left">
                      <span>{receiptCyrillic ? 'ЖАМИ ТЎЛОВ:' : 'JAMI TO\'LOV:'}</span>
                      <span className="text-sm">{(217000 * (1 + Number(serviceFeePercent) / 100)).toLocaleString()} сўм</span>
                    </div>
                    <div className="my-2 border-b-2 border-zinc-900" />
                    <div className="text-[10px] text-zinc-600 mt-2 italic text-center">
                      {receiptCyrillic ? toCyrillicJS(receiptFooter || 'Ташрифингиз учун раҳмат!') : (receiptFooter || 'Tashrifingiz uchun rahmat!')}
                    </div>
                  </div>
                )}

                {previewTab === 'k1' && (
                  <div className="space-y-1 text-center">
                    <div className="font-extrabold text-xs tracking-wider uppercase text-amber-700">
                      *** {receiptCyrillic ? toCyrillicJS(kitchen1Title).toUpperCase() : kitchen1Title.toUpperCase()} ***
                    </div>
                    <div className="font-bold text-xs uppercase text-zinc-900">
                      {receiptCyrillic ? 'ЗАЛ' : 'ZAL'}
                    </div>
                    <div className="text-[10px] font-bold">Стол: № 5</div>
                    <div className="text-[10px] text-zinc-600">Официант: Зафарбек</div>
                    <div className="text-[10px] text-zinc-600">{new Date().toLocaleTimeString()}</div>
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                    <div className="flex justify-between text-[10px] font-bold text-left">
                      <span>ТАОМ</span>
                      <span>СОНИ</span>
                    </div>
                    <div className="my-1 border-b border-dashed border-zinc-300" />
                    <div className="space-y-1 text-left text-[11px]">
                      <div className="flex justify-between font-bold">
                        <span>{receiptCyrillic ? 'Ош (Тўй оши)' : 'Osh (To\'y oshi)'}</span>
                        <span>2 та</span>
                      </div>
                      <div className="flex justify-between font-bold">
                        <span>{receiptCyrillic ? 'Қозон кабоб' : 'Qozon kabob'}</span>
                        <span>1 та</span>
                      </div>
                      <div className="text-[10px] text-zinc-500 italic">  * кам ёғли бўлсин</div>
                    </div>
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                  </div>
                )}

                {previewTab === 'k2' && (
                  <div className="space-y-1 text-center">
                    <div className="font-extrabold text-xs tracking-wider uppercase text-cyan-700">
                      *** {receiptCyrillic ? toCyrillicJS(kitchen2Title).toUpperCase() : kitchen2Title.toUpperCase()} ***
                    </div>
                    <div className="font-bold text-xs uppercase text-zinc-900">
                      {receiptCyrillic ? 'ЗАЛ' : 'ZAL'}
                    </div>
                    <div className="text-[10px] font-bold">Стол: № 5</div>
                    <div className="text-[10px] text-zinc-600">Официант: Зафарбек</div>
                    <div className="text-[10px] text-zinc-600">{new Date().toLocaleTimeString()}</div>
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                    <div className="flex justify-between text-[10px] font-bold text-left">
                      <span>ТАОМ</span>
                      <span>СОНИ</span>
                    </div>
                    <div className="my-1 border-b border-dashed border-zinc-300" />
                    <div className="space-y-1 text-left text-[11px]">
                      <div className="flex justify-between font-bold">
                        <span>{receiptCyrillic ? 'Гўштли сомса' : 'Go\'shtli somsa'}</span>
                        <span>4 та</span>
                      </div>
                      <div className="flex justify-between font-bold">
                        <span>{receiptCyrillic ? 'Судак балиқ қовурма' : 'Sudak baliq qovurma'}</span>
                        <span>1 та</span>
                      </div>
                      <div className="text-[10px] text-zinc-500 italic">  * лимон ва соус билан</div>
                    </div>
                    <div className="my-2 border-b border-dashed border-zinc-400" />
                  </div>
                )}
              </div>
            </div>
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

          {/* Kirill kod sahifasi */}
          <div className="p-3.5 rounded-2xl bg-black/30 border border-theme-border/50 space-y-2.5">
            <div className="text-xs font-bold text-white">Kirill kod sahifasi (chek harflari)</div>
            <div className="text-[11px] text-theme-muted">
              Chek tushunarsiz belgilar yoki ieroglif (yaponcha/xitoycha) bo'lib chiqsa,
              shu raqamni o'zgartiring. Ko'pchilik printerlarda <b>17</b>. Qaysi raqam
              to'g'ri ekanini bilish uchun sinov chekini chiqaring.
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="number"
                value={printerCodepage}
                onChange={(e) => setPrinterCodepage(e.target.value)}
                className="w-24 px-3 py-2 rounded-xl bg-black/40 border border-theme-border text-sm text-white font-mono"
              />
              <button
                type="button"
                onClick={handleCodepageTest}
                disabled={testingCodepage}
                className="px-4 py-2 rounded-xl bg-purple-500 hover:bg-purple-400 text-white font-bold text-xs flex items-center gap-1.5 shadow-md disabled:opacity-50"
              >
                <Printer className={`w-3.5 h-3.5 ${testingCodepage ? 'animate-spin' : ''}`} />
                <span>{testingCodepage ? 'Chiqarilmoqda...' : 'Kod sahifalarini sinash'}</span>
              </button>
            </div>
          </div>

          {/* LAN printerlarni qidirish */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl bg-black/30 border border-theme-border/50">
            <div className="min-w-0">
              <div className="text-xs font-bold text-white">Tarmoqdagi (LAN) printerlarni qidirish</div>
              <div className="text-[11px] text-theme-muted mt-0.5">
                LAN kabeli bilan routerga ulangan printerlarning IP manzilini topadi (5-15 soniya).
              </div>
            </div>
            <button
              type="button"
              onClick={handleScanLan}
              disabled={scanningLan}
              className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs shrink-0 flex items-center gap-1.5 transition-all shadow-md disabled:opacity-50"
            >
              <Search className={`w-3.5 h-3.5 ${scanningLan ? 'animate-spin' : ''}`} />
              <span>{scanningLan ? 'Tarmoq skanerlanmoqda...' : 'Tarmoqdan qidirish'}</span>
            </button>
          </div>

          {lanPrinters.length > 0 && (
            <div className="p-3.5 rounded-2xl bg-sky-500/10 border border-sky-500/30">
              <span className="text-[11px] font-bold text-sky-300 block mb-2">
                Tarmoqda topilgan printerlar (bosib nusxalang, so'ng pastdagi maydonga qo'ying):
              </span>
              <div className="flex flex-wrap gap-2">
                {lanPrinters.map((p) => (
                  <span
                    key={p.ip}
                    className="px-2.5 py-1 rounded-lg bg-sky-400/20 hover:bg-sky-400/30 text-white text-xs font-mono font-bold cursor-pointer border border-sky-400/30"
                    title="Bosib IP manzilni nusxalang"
                    onClick={() => {
                      navigator.clipboard?.writeText(p.ip);
                      alert(`'${p.ip}' nusxalandi! Endi printer maydoniga qo'ying.`);
                    }}
                  >
                    🌐 {p.ip}
                  </span>
                ))}
              </div>
            </div>
          )}

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

          {/* 3 ta Printerni kompyuterga ulash bo'yicha ko'rsatma */}
          <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/30 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-300">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>💡 3 ta Printerni Noutbukka Qanday Ulash Mumkin? (USB port yetishmasa)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-theme-muted pt-1">
              <div className="p-3 rounded-xl bg-black/40 border border-theme-border/60 space-y-1">
                <div className="font-bold text-white flex items-center gap-1.5 text-xs">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 font-bold flex items-center justify-center text-[10px]">1</span>
                  <span>LAN / Ethernet IP orqali (Tavsiya etiladi)</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  1-Printer (Kassa) noutbukka USB kabel bilan ulanadi. 2-va 3-printerlar (Oshxona va Somsa) orqasidagi tarmoq (LAN RJ-45) kabeli orqali Wi-Fi routerga ulanadi. Noutbukka sim ulash shart emas! Sozlamada printerning IP manzilini yozasiz (masalan: <code className="text-amber-300 font-mono">192.168.1.201</code>). Tizim buyurtmani bevosita tarmoqdan oshxonaga yuboradi.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-black/40 border border-theme-border/60 space-y-1">
                <div className="font-bold text-white flex items-center gap-1.5 text-xs">
                  <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-[10px]">2</span>
                  <span>USB Hub (Ko'paytirgich) orqali</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  Agar printerlaringiz faqat USB bo'lsa: 4 portli arzon <strong>USB Hub</strong> (30-50 ming so'm) olinadi. Noutbukning 1 dona USB portiga tiqilib, 3 ta printerning barchasi unga ulanadi. Windows kompyuter ularni alohida taniydi (<code className="text-emerald-300 font-mono">XP-Q80A</code>, <code className="text-emerald-300 font-mono">XP-Q80A (Copy 1)</code>, va h.k.).
                </p>
              </div>
            </div>
          </div>

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
                    placeholder="Masalan: X-Q80A (USB) yoki 192.168.1.201 (LAN)"
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

            {/* 4-Printer: BAR (choy, suv, ichimliklar) */}
            <div className="p-4 rounded-2xl bg-black/40 border border-purple-500/30 flex flex-col justify-between space-y-3 shadow-lg">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-black uppercase tracking-wider">
                    4-Printer • BAR
                  </span>
                  <span className="text-base">🥤</span>
                </div>
                <div className="text-sm font-bold text-white">Bar / Ichimliklar Stansiyasi</div>
                <p className="text-[11px] text-theme-muted leading-relaxed">
                  Taom kartasida "🥤 Bar" stansiyasi tanlangan bo'lsa (suv, choy,
                  ichimliklar) begunok shu printerdan chiqadi. Bo'sh qoldirilsa —
                  kassa printeridan chiqadi. Oshxonaga hech qachon yuborilmaydi.
                </p>

                <div className="pt-2 space-y-2">
                  <div>
                    <label className="block text-[11px] font-semibold text-theme-muted mb-1">Bar nomi:</label>
                    <input
                      type="text"
                      placeholder="BAR (Ichimliklar)"
                      value={barTitle}
                      onChange={(e) => setBarTitle(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-theme-border text-xs text-white focus:outline-none focus:border-purple-400"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-theme-muted mb-1">
                      Printer nomi yoki IP (bo'sh = kassa printeri):
                    </label>
                    <input
                      type="text"
                      placeholder="Masalan: XP-80 Bar yoki 192.168.1.203"
                      value={printerBarName}
                      onChange={(e) => setPrinterBarName(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-purple-500/40 text-xs text-white font-mono focus:outline-none focus:border-purple-400"
                    />
                    {detectedPrinters.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {detectedPrinters.map(p => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => setPrinterBarName(p)}
                            className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 border border-purple-500/20"
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
                disabled={testPrintLoading.p4}
                onClick={() => handleTestPrint('p4', printerBarName || printerCustomerName, barTitle || 'BAR')}
                className="w-full py-2 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/40 text-purple-300 text-xs font-bold transition-all flex items-center justify-center gap-1.5 active:scale-95"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>{testPrintLoading.p4 ? 'Chop etilmoqda...' : 'Test chop etish'}</span>
              </button>
            </div>
          </div>

          {/* Chek shrifti o'lchami — keksa odamlar uchun */}
          <div className="pt-3 border-t border-theme-border/50">
            <label className="block text-xs font-bold text-white mb-1">
              🔍 Chek shrifti o'lchami
            </label>
            <p className="text-[11px] text-theme-muted mb-2.5">
              Tanlang va pastdagi printerning <b>"Test chop etish"</b> tugmasini
              bosing — natijani qog'ozda darhol ko'rasiz. Hamma variant
              <b> qalin (bold)</b> chiqadi.
              <br />
              <b className="text-amber-300">
                Yozuv xira chiqsa — "Faqat balandroq" ni tanlamang:
              </b>{' '}
              harf bo'yiga cho'zilganda chiziqlari ingichka qolib xira
              ko'rinadi. <b>"KATTA"</b> yoki <b>"Kengroq"</b> da harf eni ham
              kattalashadi, shuning uchun to'q va aniq chiqadi.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {[
                { id: 'normal', nom: 'Oddiy', izoh: 'Eng kichik (1x1) — 48 belgi' },
                { id: 'baland', nom: 'Faqat balandroq', izoh: '1x2 — xira chiqishi mumkin' },
                { id: 'keng', nom: 'Kengroq', izoh: '2x1 — eng TO\'Q, 24 belgi' },
                { id: 'katta', nom: 'KATTA ✓', izoh: '2x2 — katta va to\'q, 24 belgi' },
                { id: 'juda_katta', nom: 'ENG KATTA', izoh: '3x3 — juda yirik, 16 belgi' },
              ].map((v) => (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setPrinterFontSize(v.id)}
                  className={`py-2.5 px-3 rounded-xl border text-left transition-all ${
                    printerFontSize === v.id
                      ? 'bg-theme-primary text-white border-theme-primary shadow-md'
                      : 'bg-slate-900 border-theme-border text-slate-300 hover:border-theme-primary/50'
                  }`}
                >
                  <span className="block text-xs font-black">{v.nom}</span>
                  <span className="block text-[10px] opacity-80 mt-0.5">{v.izoh}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Harflar orasidagi masofa — keksa odamlar o'qishi uchun */}
          <div className="pt-3 border-t border-theme-border/50">
            <label className="block text-xs font-bold text-white mb-1">
              ↔️ Harflar orasidagi masofa
            </label>
            <p className="text-[11px] text-theme-muted mb-2.5">
              Termal printerda harflar bir-biriga yopishib chiqadi. Bu yerdan
              har harf orasiga bo'sh joy qo'shiladi — yozuv yoyilib, ancha
              oson o'qiladi. <b>Eslatma:</b> masofa oshsa bir qatorga
              sig'adigan belgilar kamayadi (chek biroz uzunroq chiqadi).
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { v: 0, nom: 'Yopishgan', izoh: "0 nuqta — eng zich" },
                { v: 1, nom: 'Oz ✓', izoh: '1 nuqta' },
                { v: 2, nom: "O'rtacha", izoh: '2 nuqta' },
                { v: 3, nom: 'Keng', izoh: '3 nuqta' },
              ].map((o) => (
                <button
                  key={o.v}
                  type="button"
                  onClick={() => setPrinterCharSpacing(o.v)}
                  className={`py-2.5 px-3 rounded-xl border text-left transition-all ${
                    printerCharSpacing === o.v
                      ? 'bg-theme-primary text-white border-theme-primary shadow-md'
                      : 'bg-slate-900 border-theme-border text-slate-300 hover:border-theme-primary/50'
                  }`}
                >
                  <span className="block text-xs font-black">{o.nom}</span>
                  <span className="block text-[10px] opacity-80 mt-0.5">{o.izoh}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Qatorlar orasidagi masofa */}
          <div className="pt-3 border-t border-theme-border/50">
            <label className="block text-xs font-bold text-white mb-1">
              ↕️ Qatorlar orasidagi masofa
            </label>
            <p className="text-[11px] text-theme-muted mb-2.5">
              Qatorlar bir-biriga yaqin bo'lsa chek siqilib ko'rinadi.
              Bu yerdan oraliqni kengaytirasiz.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { id: 'zich', nom: 'Zich', izoh: 'Printer o\'zi hal qiladi' },
                { id: 'oddiy', nom: 'Oddiy ✓', izoh: 'Standart oraliq' },
                { id: 'keng', nom: 'Keng', izoh: 'Kengroq oraliq' },
                { id: 'juda_keng', nom: 'Juda keng', izoh: 'Eng keng oraliq' },
              ].map((o) => (
                <button
                  key={o.id}
                  type="button"
                  onClick={() => setPrinterLineSpacing(o.id)}
                  className={`py-2.5 px-3 rounded-xl border text-left transition-all ${
                    printerLineSpacing === o.id
                      ? 'bg-theme-primary text-white border-theme-primary shadow-md'
                      : 'bg-slate-900 border-theme-border text-slate-300 hover:border-theme-primary/50'
                  }`}
                >
                  <span className="block text-xs font-black">{o.nom}</span>
                  <span className="block text-[10px] opacity-80 mt-0.5">{o.izoh}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Avtomatlashtirish togglelari */}
          <div className="pt-3 border-t border-theme-border/50 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Toggle
              checked={autoPrintKitchen}
              onChange={setAutoPrintKitchen}
              label="Oshxonaga avtomatik chop etish"
              description="Ofitsiant 'Buyurtmani tasdiqlash' bosganda tegishli 1 va 2-oshxona printerlariga to'g'ridan-to'g'ri chop etiladi."
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
            <Toggle
              checked={enableChefKds}
              onChange={setEnableChefKds}
              label="Oshpaz KDS Ekrani (Planshet)"
              description="O'chirilsa: oshxonaga planshet shart emas, ofitsiant zakaz olganda buyurtmalar avtomatik printerlardan begunok qog'ozda chiqadi."
              icon={UtensilsCrossed}
              color="amber-400"
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
