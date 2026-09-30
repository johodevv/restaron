import React, { useState } from 'react';
import { Printer, X, Copy, Check, Zap, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../utils/api';

export const ThermalReceiptModal = ({
  isOpen,
  onClose,
  title = "Chek (Xprinter)",
  rawText = "",
  paperWidth = 80,
}) => {
  const [copied, setCopied] = useState(false);
  const [usbPrinting, setUsbPrinting] = useState(false);
  const [usbStatus, setUsbStatus] = useState(null); // { success: boolean, message: string }

  if (!isOpen || !rawText) return null;

  const handleBrowserPrint = () => {
    window.print();
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(rawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleUsbDirectPrint = async () => {
    setUsbPrinting(true);
    setUsbStatus(null);
    try {
      const res = await api.post('/receipts/print-raw-usb', {
        text: rawText,
        cut_paper: true,
      });
      if (res && res.success) {
        setUsbStatus({
          success: true,
          message: res.message || 'Xprinterga to\'g\'ridan-to\'g\'ri yuborildi!',
        });
      } else {
        // Bulutli server (Render/Linux) bo'lsa, brauzer orqali chiqarish
        setUsbStatus({
          success: true,
          message: "Brauzer orqali Xprinter'ga yuborilmoqda...",
        });
        setTimeout(() => window.print(), 300);
      }
    } catch (err) {
      // Bulutli server (Render Linux)
      setUsbStatus({
        success: true,
        message: "Brauzer orqali Xprinter'ga yuborilmoqda...",
      });
      setTimeout(() => window.print(), 300);
    } finally {
      setUsbPrinting(false);
      setTimeout(() => setUsbStatus(null), 3000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 bg-slate-800/80 border-b border-slate-700/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-mono">
              <Printer className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-white font-bold text-sm leading-tight">{title}</h3>
              <p className="text-[11px] text-slate-400">Xprinter ({paperWidth}mm termal qog'oz)</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-xl hover:bg-slate-700/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status notification toast */}
        {usbStatus && (
          <div
            className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b ${
              usbStatus.success
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                : 'bg-red-950/80 text-red-300 border-red-800'
            }`}
          >
            {usbStatus.success ? (
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            )}
            <span>{usbStatus.message}</span>
          </div>
        )}

        {/* Thermal Receipt Paper Preview */}
        <div className="p-4 overflow-y-auto flex-1 bg-slate-950/70 flex justify-center">
          <div
            id="thermal-receipt-print-area"
            className="w-full bg-white text-black p-5 rounded shadow-lg font-mono text-[12px] leading-tight select-text whitespace-pre overflow-x-auto border-t-4 border-dashed border-slate-300"
            style={{ maxWidth: paperWidth >= 80 ? '340px' : '260px' }}
          >
            {rawText}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 bg-slate-800/80 border-t border-slate-700/60 flex flex-wrap items-center justify-between gap-2.5">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-300 bg-slate-700/60 hover:bg-slate-700 rounded-xl transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Nusxalandi' : 'Nusxa'}</span>
          </button>

          <div className="flex items-center gap-2">
            {/* Direct USB Print (No dialog) */}
            <button
              onClick={handleUsbDirectPrint}
              disabled={usbPrinting}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-xl shadow-md transition-all active:scale-95"
              title="USB orqali ulangan Xprinterga to'g'ridan-to'g'ri chop etish"
            >
              <Zap className="w-3.5 h-3.5 text-amber-300" />
              <span>{usbPrinting ? 'Yuborilmoqda...' : 'USB Xprinter'}</span>
            </button>

            {/* Standard Browser Print */}
            <button
              onClick={handleBrowserPrint}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-xl shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Chop etish</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThermalReceiptModal;
