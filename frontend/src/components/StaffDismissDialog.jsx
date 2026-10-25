import React from 'react';
import { createPortal } from 'react-dom';
import { useDialogFocus } from '../hooks/useDialogFocus';

export default function StaffDismissDialog({ staff, busy, onClose, onConfirm, error }) {
  const dialogRef = useDialogFocus(Boolean(staff), () => { if (!busy) onClose(); });
  if (!staff) return null;
  return createPortal(<div className="fixed inset-0 z-[90] bg-black/75 flex items-center justify-center p-4">
    <section ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="dismiss-staff-title" aria-describedby="dismiss-staff-description" className="w-full max-w-md rounded-2xl border border-slate-600 bg-slate-900 text-slate-100 p-5 shadow-2xl">
      <h2 id="dismiss-staff-title" className="text-xl font-bold">Xodimni bo‘shatish</h2>
      <p className="mt-3 text-base font-semibold break-words">{staff.full_name || staff.username}</p>
      <p id="dismiss-staff-description" className="mt-3 text-sm text-slate-300 leading-relaxed">Xodimning tizimga kirishi yopiladi. Buyurtmalari, hisoblari va ish tarixi saqlanadi. Xodimni keyin “Nofaol” bo‘limidan qayta faollashtirish mumkin.</p>
      {error && <p role="alert" className="mt-3 text-sm text-red-300">{error}</p>}
      <div className="mt-5 flex flex-wrap gap-3">
        <button type="button" disabled={busy} onClick={onClose} className="flex-1 min-h-[48px] px-4 rounded-xl border border-slate-600 bg-slate-800 font-semibold disabled:opacity-50">Bekor qilish</button>
        <button type="button" disabled={busy} onClick={onConfirm} className="flex-1 min-h-[48px] px-4 rounded-xl bg-red-600 hover:bg-red-500 font-bold disabled:opacity-50">{busy ? 'Bajarilmoqda...' : 'Bo‘shatishni tasdiqlash'}</button>
      </div>
    </section>
  </div>, document.body);
}
