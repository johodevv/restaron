export function receiptLines(text) {
  let amountNext = false;
  return String(text).split('\n').map(line => {
    const value = line.trim();
    const heading = /^(ЖАМИ:|ЖАМИ Т[ЎУ]ЛОВ:|[ҚК]ОЛГАН Т[ЎУ]ЛОВ:)/.test(value);
    const total = heading || (amountNext && /^[\d\s.,]+$/.test(value));
    amountNext = heading && value.endsWith(':');
    return { text: line, total, table: /^[┌├└│]/.test(value) };
  });
}
