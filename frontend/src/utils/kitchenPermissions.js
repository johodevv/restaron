export const canCancelKitchenItems = user => ['admin', 'developer'].includes(user?.role);

export function kitchenSentQuantity(item) {
  const quantity = Math.max(0, Number(item?.quantity) || 0);
  const sent = Math.max(0, Number(item?.sent_quantity) || 0, Number(item?.prepared_quantity) || 0);
  if (sent) return Math.min(quantity, sent);
  return item?.sent_to_kitchen || item?.sent_to_kitchen_at ? quantity : 0;
}

export const canDeleteOrderItem = (user, item) => (canCancelKitchenItems(user) || user?.role === 'waiter') || kitchenSentQuantity(item) === 0;
export const canDecreaseOrderItem = (user, item) => (canCancelKitchenItems(user) || user?.role === 'waiter') || Number(item?.quantity) > kitchenSentQuantity(item);
