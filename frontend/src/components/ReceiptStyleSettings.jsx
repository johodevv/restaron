import React, { useEffect, useState } from 'react';
import api from '../utils/api';
import ThermalReceiptModal from './ThermalReceiptModal';

const defaults = kind => ({ font_family: 'Arial', font_size: kind === 'kitchen' ? 16 : 10.5,
  font_bold: kind === 'kitchen', total_size: 13.5, total_bold: true, header_size: kind === 'kitchen' ? 16 : 14,
  header_bold: true, order_size: kind === 'kitchen' ? 16 : 20, order_bold: true,
  meta_size: kind === 'kitchen' ? 12 : 10.5, meta_bold: false, row_gap: 2 });
export const receiptAppearance = (kind, options) => ({ ...defaults(kind), ...options });

export default function ReceiptStyleSettings({ value, onChange, paperWidth, restaurantId, header, footer }) {
  const [fonts, setFonts] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const refreshFonts = () => api.get('/receipts/templates/fonts').then(setFonts).catch(e => setError(e.message));
  useEffect(() => { refreshFonts(); }, []);
  const change = (kind, patch) => onChange({ ...value, [kind]: { ...value[kind], ...patch } });
  const showPreview = async kind => {
    setError(''); setBusy(true);
    try {
      const selected = value[kind];
      const result = await api.post('/receipts/templates/preview', {
        kind, style: selected.style, appearance: { ...defaults(kind), ...selected.options },
        paper_width: Number(paperWidth), restaurant_id: restaurantId,
        header: header || 'Dunyo Choyxonasi', footer: footer || 'Tashrifingiz uchun rahmat!',
      });
      setPreview({ ...result, kind });
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  return <div className="rounded-2xl border border-theme-border p-4 space-y-4 mb-5">
    <div className="flex items-center justify-between gap-3">
      <h3 className="font-bold text-base">Chek uslubini tanlash</h3>
      <button type="button" onClick={refreshFonts} className="text-sm underline">Shriftlarni qayta tekshirish</button>
    </div>
    <p className="text-sm text-theme-muted">Mijoz hisobi va oshxona uchun alohida tanlang. O‘zgarishlar saqlangandan keyin yangi cheklarga qo‘llanadi. Arxivdagi cheklar o‘z ko‘rinishini saqlaydi.</p>
    <div className="grid gap-4 lg:grid-cols-2">
      {['customer', 'kitchen'].map(kind => {
        const selected = value[kind];
        const options = { ...defaults(kind), ...selected.options };
        const updateOption = (key, next) => change(kind, { options: { ...options, [key]: next } });
        return <fieldset key={kind} className="min-w-0 border border-theme-border rounded-xl p-4 space-y-3">
          <legend className="px-2 font-bold">{kind === 'customer' ? 'Mijoz hisobi' : 'Oshxona va bar cheki'}</legend>
          <label className="block text-sm">Uslub
            <select aria-label="Uslub" value={selected.style} onChange={e => change(kind, { style: e.target.value })} className="w-full mt-1 bg-theme-surface border border-theme-border rounded-lg p-2">
              <option value="dunyo">Dunyo — hozirgi chek</option>
              <option value="aliposter">AliPoster uslubida — grafik chek</option>
            </select>
          </label>
          {selected.style === 'aliposter' && <>
            <label className="block text-sm">Shrift
              <select aria-label="Shrift" value={options.font_family} onChange={e => updateOption('font_family', e.target.value)} className="w-full mt-1 bg-theme-surface border border-theme-border rounded-lg p-2">
                {['Arial', 'Mercury'].map(font => <option key={font} value={font}>{font}{fonts && (!fonts[font]?.regular || !fonts[font]?.bold) ? ' — serverga o‘rnatilmagan' : ''}</option>)}
              </select>
            </label>
            {fonts && (!fonts[options.font_family]?.regular || !fonts[options.font_family]?.bold) && <p role="alert" className="text-sm text-amber-300">{options.font_family} Regular/Bold fayllari topilmadi. Shrift o‘rnatilmaguncha bu tanlovda namuna va saqlash bajarilmaydi. Boshqa shriftga avtomatik almashtirilmaydi.</p>}
            <div className="grid grid-cols-[1fr_5rem_5rem] gap-2 items-center text-sm">
              <span>Yozuv</span><span>pt</span><span>Qalin</span>
              {[['font', 'Taomlar', 30], ['meta', 'Sana va izoh', 30], ['header', 'Sarlavha', 36], ['order', 'Hisob raqami', 40], ...(kind === 'customer' ? [['total', 'Jami va hisoblar', 36]] : [])].map(([prefix, label, max]) => <React.Fragment key={prefix}>
                <label htmlFor={`${kind}-${prefix}`}>{label}</label>
                <input id={`${kind}-${prefix}`} type="number" min="7" max={max} step="0.5" value={options[`${prefix}_size`]} onChange={e => updateOption(`${prefix}_size`, e.target.value === '' ? '' : Number(e.target.value))} className="w-full bg-theme-surface border border-theme-border rounded p-2" />
                <input aria-label={`${label} qalin — ${kind}`} type="checkbox" checked={options[`${prefix}_bold`]} onChange={e => updateOption(`${prefix}_bold`, e.target.checked)} className="w-5 h-5" />
              </React.Fragment>)}
            </div>
            <label className="flex items-center justify-between gap-2 text-sm">Qatorlar orasidagi qo‘shimcha masofa (pt)
              <input type="number" min="0" max="12" step="0.5" value={options.row_gap} onChange={e => updateOption('row_gap', e.target.value === '' ? '' : Number(e.target.value))} className="w-20 bg-theme-surface border border-theme-border rounded p-2" />
            </label>
            <button type="button" onClick={() => change(kind, { options: defaults(kind) })} className="text-sm underline">Standart o‘lchamlarga qaytarish</button>
          </>}
          <button type="button" disabled={busy} onClick={() => showPreview(kind)} className="block min-h-11 px-4 rounded-lg border border-emerald-500 text-emerald-300 font-semibold disabled:opacity-50">{busy ? 'Tayyorlanmoqda…' : 'Namuna chekni ko‘rish'}</button>
        </fieldset>;
      })}
    </div>
    <p className="text-sm text-theme-muted">AliPoster mijoz shabloni: asosiy yozuv 10,5 pt, hisoblar 13,5 pt. Oshxona: taom 16 pt, sana/izoh 12 pt. Dunyo uslubining yirik shrift va harf oralig‘i sozlamalari pastda qoladi. Qog‘ozdagi aniqlik printer va termoqog‘ozga ham bog‘liq.</p>
    {error && <p role="alert" className="text-red-300 whitespace-pre-wrap">{error}</p>}
    {preview && <ThermalReceiptModal isOpen onClose={() => setPreview(null)} title={preview.kind === 'customer' ? 'Mijoz — namuna' : 'Oshxona — namuna'} rawText={preview.raw_text} printDocument={preview.print_document} imageData={preview.image} paperWidth={Number(paperWidth)} restaurantId={restaurantId} />}
  </div>;
}
