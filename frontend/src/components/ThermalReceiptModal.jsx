import React from 'react';
import { Printer, X, Copy, Check, FileText } from 'lucide-react';

export const ThermalReceiptModal = ({
  isOpen,
  onClose,
  title = "Chek (Xprinter)",
  rawText = "",
  paperWidth = 80,
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!isOpen || !rawText) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(rawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 bg-slate-800/80 border-b border-slate-700/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-mono">
              <Printer className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm leading-tight">{title}</h3>
              <p className="text-xs text-slate-400">Xprinter ({paperWidth}mm format)</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Thermal Receipt Paper Preview */}
        <div className="p-4 overflow-y-auto flex-1 bg-slate-950/60 flex justify-center">
          <div
            id="thermal-receipt-print-area"
            className="w-full bg-white text-black p-5 rounded-sm shadow-md font-mono text-[12.5px] leading-tight select-text whitespace-pre overflow-x-auto border-t-4 border-dashed border-slate-300"
            style={{ maxWidth: paperWidth >= 80 ? '340px' : '260px' }}
          >
            {rawText}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 bg-slate-800/80 border-t border-slate-700/60 flex items-center justify-between gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-300 bg-slate-700/60 hover:bg-slate-700 rounded-xl transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? "Nusxalandi" : "Nusxa olish"}
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-xl transition-colors"
            >
              Yopish
            </button>
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-xl shadow-lg shadow-emerald-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Printer className="w-4 h-4" />
              Chop etish (Print)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ThermalReceiptModal;
