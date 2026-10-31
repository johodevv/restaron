import React, { useMemo, useEffect } from 'react';
import { tablePickerDirectory } from '../utils/tableDirectory';

export default function WaiterTablePicker({ tables, zone, onZone, onSelect, label, loading, disabled = false, transfer = false, headingActions, occupiedOnly = false, onOccupiedOnlyChange }) {
  const showingOccupied = !!onOccupiedOnlyChange && occupiedOnly;
  const directory = useMemo(() => tablePickerDirectory(tables, zone, showingOccupied), [tables, zone, showingOccupied]);
  useEffect(() => {
    if (!directory.zoneOptions.length) return;
    if (!directory.zoneOptions.some(option => option.value === zone)) onZone(directory.zoneOptions[0].value);
  }, [directory.zoneOptions.map(option => option.value).join('\n'), zone, onZone]);
  return <section className="flex-1 flex flex-col min-h-0 overflow-hidden bg-slate-950" aria-label={label('Stollar')} data-testid="waiter-table-picker">
    <div className="px-4 pt-4 pb-3 shrink-0">
      <div className="flex items-center justify-between gap-2"><h1 className="text-xl font-bold">{label('Stol tanlang')}</h1>{headingActions}</div>
      <p className="text-sm text-slate-400 mt-1">{label('Avval zona, keyin stolni tanlang')}</p>
    </div>
    <div className="flex flex-col lg:flex-row flex-1 min-h-0 overflow-hidden">
      <nav aria-label={label('Zonalar')} className="flex lg:flex-col gap-2 px-4 pb-3 overflow-x-auto lg:w-52 lg:overflow-y-auto lg:shrink-0 border-b lg:border-b-0 lg:border-r border-slate-800">
        {onOccupiedOnlyChange && <button type="button" aria-pressed={showingOccupied} onClick={() => onOccupiedOnlyChange(true)} className={`min-h-[52px] shrink-0 px-4 rounded-xl font-bold text-base flex items-center justify-between gap-3 border ${showingOccupied ? 'bg-emerald-700 border-emerald-400 text-white' : 'bg-slate-800 border-slate-700 text-slate-200'}`}>
          <span>{label('Band stollar')}</span><span className="text-xs opacity-75">{directory.occupiedCount}</span>
        </button>}
        {directory.zoneOptions.map(option => <button key={option.value} type="button" aria-pressed={!showingOccupied && zone === option.value} onClick={() => { onOccupiedOnlyChange?.(false); onZone(option.value); }} className={`min-h-[52px] shrink-0 px-4 rounded-xl font-bold text-base flex items-center justify-between gap-3 border ${!showingOccupied && zone === option.value ? 'bg-emerald-700 border-emerald-400 text-white' : 'bg-slate-800 border-slate-700 text-slate-200'}`}>
          <span>{label(option.label)}</span><span className="text-xs opacity-75">{option.count}</span>
        </button>)}
      </nav>
      <div className="flex flex-col flex-1 min-h-0 min-w-0">
        <div className="p-4 pb-2 shrink-0">
          <p className="text-sm text-slate-300 font-semibold">{showingOccupied ? label('Band stollar') : directory.zoneOptions.find(option => option.value === zone)?.label || label('Zonalar')} · {directory.matches.length} {label('ta stol')}</p>
        </div>
        <div className="overflow-y-auto overscroll-contain p-4 pt-2 min-h-0" data-testid="waiter-zone-tables">
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-5 gap-3">
            {(zone || showingOccupied) && directory.matches.map(table => {
              const busy = table.is_occupied || table.status === 'occupied';
              const maintenance = table.status === 'maintenance';
              const reserved = table.status === 'reserved';
              return <button type="button" key={table.id} data-table-id={table.id} disabled={maintenance || disabled} onClick={() => onSelect(table)} className={`min-h-[112px] p-4 rounded-2xl text-left border-2 active:scale-[.98] ${maintenance ? 'bg-slate-800 border-slate-600 opacity-50' : busy ? 'bg-slate-800 border-red-500' : reserved ? 'bg-slate-800 border-amber-500' : 'bg-slate-800 border-emerald-500'}`}>
                <strong className="block text-2xl text-white">{table.name || `${label('Stol #')}${table.number}`}</strong>
                {showingOccupied && <span className="block mt-1 text-sm text-slate-300 break-words">{table.room?.trim() || label('Zonasiz')}</span>}
                <span className={`block mt-2 text-sm font-semibold ${busy ? 'text-red-300' : reserved ? 'text-amber-300' : 'text-emerald-300'}`}>{label(maintenance ? 'Ta’mirda' : busy ? (transfer ? 'Bandga qo‘shish' : 'Band') : reserved ? 'Bron qilingan' : "Bo'sh")}</span>
              </button>;
            })}
          </div>
          {!directory.matches.length && <p className="py-10 text-center text-slate-400">{label(loading ? 'Yuklanmoqda...' : showingOccupied ? 'Band stol yo‘q' : "Bu zonada stol yo'q")}</p>}
        </div>
      </div>
    </div>
  </section>;
}
