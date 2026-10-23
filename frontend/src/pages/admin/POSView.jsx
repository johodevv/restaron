import React from 'react';
import WaiterDashboard from '../waiter/WaiterDashboard';

// Cashier and waiter use one tested order editor and one mutation queue.
export const POSView = (props) => <WaiterDashboard {...props} />;
export default POSView;
