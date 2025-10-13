/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ordersAPI } from '../services/api';

const OrdersPage = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchEmail, setSearchEmail] = useState('');

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async (customerEmail = '') => {
    setLoading(true);
    setError(null);
    try {
      const params = customerEmail ? { customer_email: customerEmail } : {};
      const response = await ordersAPI.getOrders(params);
      setOrders(response.data.orders);
    } catch (err) {
      setError('Failed to load orders. Please try again.');
      console.error('Error loading orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadOrders(searchEmail);
  };

  const handleCancelOrder = async (orderId) => {
    if (!window.confirm('Are you sure you want to cancel this order?')) {
      return;
    }

    try {
      await ordersAPI.cancelOrder(orderId);
      loadOrders(searchEmail); // Reload orders
    } catch (err) {
      alert('Failed to cancel order. Please try again.');
      console.error('Error canceling order:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return '#f39c12';
      case 'confirmed': return '#3498db';
      case 'shipped': return '#9b59b6';
      case 'delivered': return '#27ae60';
      case 'cancelled': return '#e74c3c';
      default: return '#95a5a6';
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading orders...</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Orders</h1>

      <form onSubmit={handleSearch} style={styles.searchForm}>
        <input
          type="email"
          placeholder="Search by email address..."
          value={searchEmail}
          onChange={(e) => setSearchEmail(e.target.value)}
          style={styles.searchInput}
        />
        <button type="submit" style={styles.searchButton}>
          Search
        </button>
        <button 
          type="button" 
          onClick={() => {
            setSearchEmail('');
            loadOrders('');
          }}
          style={styles.clearButton}
        >
          Show All
        </button>
      </form>

      {error && <div style={styles.error}>{error}</div>}

      {orders.length === 0 ? (
        <div style={styles.noOrders}>
          No orders found.
        </div>
      ) : (
        <div style={styles.ordersGrid}>
          {orders.map(order => (
            <div key={order.id} style={styles.orderCard}>
              <div style={styles.orderHeader}>
                <div>
                  <h3 style={styles.orderNumber}>Order #{order.order_number}</h3>
                  <p style={styles.orderDate}>
                    {new Date(order.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div 
                  style={{
                    ...styles.status,
                    backgroundColor: getStatusColor(order.status)
                  }}
                >
                  {order.status.toUpperCase()}
                </div>
              </div>

              <div style={styles.customerInfo}>
                <p><strong>Customer:</strong> {order.customer_name}</p>
                <p><strong>Email:</strong> {order.customer_email}</p>
              </div>

              <div style={styles.orderItems}>
                <h4>Items:</h4>
                {order.items.map(item => (
                  <div key={item.id} style={styles.orderItem}>
                    <span>{item.product.name}</span>
                    <span>Qty: {item.quantity}</span>
                    <span>${(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
              </div>

              <div style={styles.orderFooter}>
                <div style={styles.totalAmount}>
                  Total: ${order.total_amount.toFixed(2)}
                </div>
                {(order.status === 'pending' || order.status === 'confirmed') && (
                  <button 
                    onClick={() => handleCancelOrder(order.id)}
                    style={styles.cancelButton}
                  >
                    Cancel Order
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Order Detail Page Component
export const OrderDetailPage = () => {
  const { orderNumber } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadOrder();
  }, [orderNumber]);

  const loadOrder = async () => {
    try {
      const response = await ordersAPI.getOrderByNumber(orderNumber);
      setOrder(response.data);
    } catch (err) {
      setError('Order not found.');
      console.error('Error loading order:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading order...</div>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          {error}
          <button onClick={() => navigate('/')} style={styles.homeButton}>
            Go Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <button onClick={() => navigate(-1)} style={styles.backButton}>
        ← Back
      </button>
      
      <div style={styles.orderConfirmation}>
        <h1 style={styles.confirmationTitle}>Order Confirmed!</h1>
        <p style={styles.confirmationText}>
          Thank you for your order. We'll send you an email confirmation shortly.
        </p>
        
        <div style={styles.orderDetails}>
          <h2>Order Details</h2>
          <p><strong>Order Number:</strong> {order.order_number}</p>
          <p><strong>Date:</strong> {new Date(order.created_at).toLocaleDateString()}</p>
          <p><strong>Status:</strong> {order.status.toUpperCase()}</p>
          <p><strong>Customer:</strong> {order.customer_name}</p>
          <p><strong>Email:</strong> {order.customer_email}</p>
          
          <div style={styles.orderItems}>
            <h3>Items Ordered:</h3>
            {order.items.map(item => (
              <div key={item.id} style={styles.orderItem}>
                <span>{item.product.name}</span>
                <span>Qty: {item.quantity}</span>
                <span>${(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
          
          <div style={styles.orderTotal}>
            <strong>Total: ${order.total_amount.toFixed(2)}</strong>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '2rem 1rem',
  },
  title: {
    fontSize: '2rem',
    marginBottom: '2rem',
    color: '#2c3e50',
  },
  searchForm: {
    display: 'flex',
    gap: '0.5rem',
    marginBottom: '2rem',
    backgroundColor: 'white',
    padding: '1rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  searchInput: {
    flex: 1,
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
  },
  searchButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '0.75rem 1.5rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  clearButton: {
    backgroundColor: '#95a5a6',
    color: 'white',
    border: 'none',
    padding: '0.75rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  loading: {
    textAlign: 'center',
    fontSize: '1.2rem',
    color: '#666',
    padding: '3rem',
  },
  error: {
    textAlign: 'center',
    color: '#e74c3c',
    padding: '2rem',
    backgroundColor: '#fdf2f2',
    borderRadius: '8px',
    border: '1px solid #fecaca',
    marginBottom: '2rem',
  },
  noOrders: {
    textAlign: 'center',
    color: '#666',
    padding: '3rem',
    fontSize: '1.1rem',
  },
  ordersGrid: {
    display: 'grid',
    gap: '1.5rem',
  },
  orderCard: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    border: '1px solid #eee',
  },
  orderHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1rem',
  },
  orderNumber: {
    margin: '0 0 0.25rem 0',
    color: '#2c3e50',
    fontSize: '1.3rem',
  },
  orderDate: {
    margin: 0,
    color: '#666',
    fontSize: '0.9rem',
  },
  status: {
    color: 'white',
    padding: '0.25rem 0.75rem',
    borderRadius: '20px',
    fontSize: '0.8rem',
    fontWeight: 'bold',
  },
  customerInfo: {
    marginBottom: '1rem',
    fontSize: '0.9rem',
    color: '#666',
  },
  orderItems: {
    marginBottom: '1rem',
  },
  orderItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '0.5rem 0',
    borderBottom: '1px solid #f0f0f0',
    fontSize: '0.9rem',
  },
  orderFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '1rem',
    borderTop: '1px solid #eee',
  },
  totalAmount: {
    fontSize: '1.2rem',
    fontWeight: 'bold',
    color: '#e74c3c',
  },
  cancelButton: {
    backgroundColor: '#e74c3c',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  backButton: {
    backgroundColor: '#95a5a6',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
    marginBottom: '2rem',
  },
  orderConfirmation: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '2rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    textAlign: 'center',
  },
  confirmationTitle: {
    color: '#27ae60',
    fontSize: '2.5rem',
    marginBottom: '1rem',
  },
  confirmationText: {
    fontSize: '1.1rem',
    color: '#666',
    marginBottom: '2rem',
  },
  orderDetails: {
    textAlign: 'left',
    marginTop: '2rem',
  },
  orderTotal: {
    fontSize: '1.3rem',
    marginTop: '1rem',
    paddingTop: '1rem',
    borderTop: '2px solid #eee',
  },
  homeButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '0.75rem 1.5rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
    marginTop: '1rem',
  },
};

export default OrdersPage;
