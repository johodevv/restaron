const rounded = (value, places) => Number(value.toFixed(places));
export const parseWeightedNumber = value => {
  const text = String(value ?? '').trim().replace(/\s/g, '').replace(',', '.');
  return text && /^\d+(?:\.\d+)?$/.test(text) ? Number(text) : NaN;
};

export function convertWeightedInput(item, edited, value) {
  const number = parseWeightedNumber(value);
  const rate = Number(item?.unit_price) * Math.max(1, Number(item?.quantity) || 1);
  const valid = Number.isFinite(number) && number >= 0 && Number.isFinite(rate) && rate > 0;
  if (edited === 'weight') return { weight: value, price: valid ? String(rounded(number * rate, 2)) : '' };
  return { price: value, weight: valid ? String(rounded(number / rate, 3)) : '' };
}

export function weightedUpdatePayload(item, edited, price, weight) {
  if (!(Number(item?.unit_price) > 0)) throw new Error('Bir kilogramm yoki litr narxi belgilanmagan. Adminga murojaat qiling.');
  const number = parseWeightedNumber(edited === 'weight' ? weight : price);
  if (!Number.isFinite(number) || (edited === 'weight' ? number <= 0 || number > 1000 : number < 0 || number > 1_000_000_000)) {
    throw new Error(edited === 'weight' ? 'Og‘irlikni to‘g‘ri kiriting (masalan: 1,5).' : 'Summani to‘g‘ri kiriting (masalan: 75 000).');
  }
  // Send only the edited field. A rounded preview of kg must not change an
  // exact manually entered amount when the server saves it.
  return edited === 'weight' ? { weight: number } : { price: rounded(number, 2) };
}
