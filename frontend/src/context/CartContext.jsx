import React, { createContext, useContext, useState } from 'react';

const CartContext = createContext(null);

export const CartProvider = ({ children }) => {
  const [items, setItems] = useState([]); // [{ item: menuItem, quantity: 1, note: '' }]

  const addToCart = (menuItem, note = '') => {
    setItems((prev) => {
      const existingIndex = prev.findIndex((i) => i.item.id === menuItem.id);
      if (existingIndex > -1) {
        const copy = [...prev];
        copy[existingIndex].quantity += 1;
        if (note) copy[existingIndex].note = note;
        return copy;
      }
      return [...prev, { item: menuItem, quantity: 1, note }];
    });
  };

  const updateQuantity = (menuItemId, change) => {
    setItems((prev) => {
      return prev
        .map((i) => {
          if (i.item.id === menuItemId) {
            const newQty = i.quantity + change;
            return newQty > 0 ? { ...i, quantity: newQty } : null;
          }
          return i;
        })
        .filter(Boolean);
    });
  };

  const updateNote = (menuItemId, note) => {
    setItems((prev) =>
      prev.map((i) => (i.item.id === menuItemId ? { ...i, note } : i))
    );
  };

  const removeFromCart = (menuItemId) => {
    setItems((prev) => prev.filter((i) => i.item.id !== menuItemId));
  };

  const clearCart = () => setItems([]);

  const subtotal = items.reduce(
    (sum, i) => sum + (i.item.price || 0) * i.quantity,
    0
  );

  const totalCount = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <CartContext.Provider
      value={{
        items,
        addToCart,
        updateQuantity,
        updateNote,
        removeFromCart,
        clearCart,
        subtotal,
        totalCount,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => useContext(CartContext);
