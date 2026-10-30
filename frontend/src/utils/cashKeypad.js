// Edit the displayed cash amount only; payment validation stays in checkout.
export function cashKeypadValue(value, key) {
  const current = String(value ?? '').replace(',', '.');
  if (key === 'clear') return '';
  if (key === 'backspace') return current.slice(0, -1);
  if (!/^\d*(?:\.\d*)?$/.test(current)) return value;
  if (key === '.') return current.includes('.') ? current : `${current || '0'}.`;
  if (!/^(?:\d|00)$/.test(key)) return value;
  return /^0+$/.test(current) ? key === '00' ? '0' : key : current + key;
}

export function cashIsInsufficient(value, total) {
  const text = String(value ?? '').replace(/\s/g, '');
  // Empty retains the existing exact-amount shortcut; explicit zero does not.
  return text !== '' && (Number.parseFloat(text) || 0) < total;
}
