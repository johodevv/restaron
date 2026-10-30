import React from 'react';
import { Delete } from 'lucide-react';
import { cashKeypadValue } from '../utils/cashKeypad';

export default function CashKeypad({ value, onChange, disabled }) {
  return <div className="cash-keypad" role="group" aria-label="Naqd summa klaviaturasi">
    {['1','2','3','4','5','6','7','8','9','00','0','backspace'].map(key => <button type="button" key={key} className={key === 'backspace' ? 'cash-backspace' : ''} disabled={disabled} aria-label={key === 'backspace' ? 'Oxirgi raqamni o‘chirish' : `Naqd summa: ${key}`} onClick={() => onChange(cashKeypadValue(value, key))}>{key === 'backspace' ? <Delete size={22} /> : key}</button>)}
  </div>;
}
