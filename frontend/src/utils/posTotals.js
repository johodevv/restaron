// Preview the same percentage calculation as the server while a mutation is queued.
// The successful API response remains authoritative.
export function previewOrderTotals(order, subtotal) {
  const cents = value => Math.round((value + Number.EPSILON) * 100) / 100;
  const fee = cents(subtotal * (Number(order.service_fee_percent) || 0) / 100);
  return { subtotal, service_fee_amount: fee, total: cents(subtotal + fee - (Number(order.discount) || 0)) };
}
