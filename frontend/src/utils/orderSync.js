// Late network events must not replace a newer server version in the cart.
export function latestOrder(current, incoming) {
  if (!incoming) return current;
  if (current && current.id !== incoming.id) return current;
  if (current && Number(current.version || 0) > Number(incoming.version || 0)) return current;
  return incoming;
}
