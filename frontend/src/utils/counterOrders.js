export function openCounterOrders(orders, type) {
  if (!['takeaway', 'delivery'].includes(type)) return [];
  return orders.filter(order => order.order_type === type && !order.is_paid &&
    !order.merged_into_order_id && !['paid', 'cancelled', 'completed'].includes(order.status));
}
