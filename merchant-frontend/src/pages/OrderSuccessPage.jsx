/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const OrderSuccessPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { order, payment, customerInfo } = location.state || {};

  // Redirect if no order data
  React.useEffect(() => {
    if (!order) {
      navigate('/');
    }
  }, [order, navigate]);

  if (!order) {
    return null;
  }

  const subtotal = (order.items || []).reduce((sum, item) => sum + ((item.price || item.unit_price || 0) * (item.quantity || 0)), 0);
  const shipping = 9.99;
  const tax = subtotal * 0.08;

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        {/* Success Header */}
        <div style={styles.successHeader}>
          <div style={styles.checkmark}>✓</div>
          <h1 style={styles.successTitle}>Order Confirmed!</h1>
          <p style={styles.successSubtitle}>
            Thank you for your order. We'll send you shipping confirmation when your order ships.
          </p>
        </div>

        {/* Order Details Card */}
        <div style={styles.orderCard}>
          <div style={styles.orderHeader}>
            <div>
              <h2 style={styles.orderNumber}>Order #{order.order_number}</h2>
              <p style={styles.orderDate}>
                Order placed on {new Date(order.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </p>
            </div>
            <div style={styles.orderStatus}>
              {order.status.toUpperCase()}
            </div>
          </div>

          {/* Payment Information */}
          {payment && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Payment Information</h3>
              <div style={styles.infoGrid}>
                <div>
                  <p style={styles.label}>Payment Method</p>
                  <p style={styles.value}>{payment.card_brand} ending in {payment.last_four}</p>
                </div>
                <div>
                  <p style={styles.label}>Payment Status</p>
                  <p style={styles.value}>{payment.status.toUpperCase()}</p>
                </div>
                {payment.transaction_id && (
                  <div>
                    <p style={styles.label}>Transaction ID</p>
                    <p style={styles.value}>{payment.transaction_id}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Customer Information */}
          {customerInfo && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Contact Information</h3>
              <div style={styles.infoGrid}>
                <div>
                  <p style={styles.label}>Email</p>
                  <p style={styles.value}>{customerInfo.email}</p>
                </div>
                {customerInfo.phone && (
                  <div>
                    <p style={styles.label}>Phone</p>
                    <p style={styles.value}>{customerInfo.phone}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Shipping Information */}
          {customerInfo && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Shipping Address</h3>
              <div style={styles.address}>
                <p>{customerInfo.firstName} {customerInfo.lastName}</p>
                {customerInfo.company && <p>{customerInfo.company}</p>}
                <p>{customerInfo.address1}</p>
                {customerInfo.address2 && <p>{customerInfo.address2}</p>}
                <p>{customerInfo.city}, {customerInfo.state} {customerInfo.zipCode}</p>
                <p>{customerInfo.country}</p>
              </div>
            </div>
          )}

          {/* Order Items */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Order Items</h3>
            <div style={styles.orderItems}>
              {(order.items || []).map(item => (
                <div key={item.id} style={styles.orderItem}>
                  <img 
                    src={(item.product && item.product.image_url) || '/placeholder/80/80'} 
                    alt={(item.product && item.product.name) || item.product_name || 'Product'}
                    style={styles.itemImage}
                  />
                  <div style={styles.itemDetails}>
                    <h4 style={styles.itemName}>{(item.product && item.product.name) || item.product_name || 'Product'}</h4>
                    <p style={styles.itemDescription}>{(item.product && item.product.description) || ''}</p>
                    <p style={styles.itemPrice}>
                      ${(item.price || item.unit_price || 0).toFixed(2)} each × {item.quantity || 0}
                    </p>
                  </div>
                  <div style={styles.itemTotal}>
                    ${((item.price || item.unit_price || 0) * (item.quantity || 0)).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Order Summary */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Order Summary</h3>
            <div style={styles.orderSummary}>
              <div style={styles.summaryRow}>
                <span>Subtotal</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              <div style={styles.summaryRow}>
                <span>Shipping</span>
                <span>${shipping.toFixed(2)}</span>
              </div>
              <div style={styles.summaryRow}>
                <span>Tax</span>
                <span>${tax.toFixed(2)}</span>
              </div>
              <div style={styles.summaryRowTotal}>
                <span>Total</span>
                <span>${order.total_amount.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Special Instructions */}
          {customerInfo?.specialInstructions && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>Special Instructions</h3>
              <p style={styles.instructions}>{customerInfo.specialInstructions}</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div style={styles.actions}>
          <button 
            onClick={() => navigate('/')}
            style={styles.continueButton}
          >
            Continue Shopping
          </button>
          <button 
            onClick={() => navigate('/orders')}
            style={styles.ordersButton}
          >
            View All Orders
          </button>
        </div>

        {/* Additional Information */}
        <div style={styles.additionalInfo}>
          <div style={styles.infoCard}>
            <h4 style={styles.infoTitle}>What's Next?</h4>
            <ul style={styles.infoList}>
              <li>You'll receive an email confirmation shortly</li>
              <li>We'll notify you when your order ships</li>
              <li>Estimated delivery: 5-7 business days</li>
              <li>Track your order anytime in your order history</li>
            </ul>
          </div>
          
          <div style={styles.infoCard}>
            <h4 style={styles.infoTitle}>Need Help?</h4>
            <ul style={styles.infoList}>
              <li>Contact customer support: support@example.com</li>
              <li>Call us: 1-800-MERCHANT</li>
              <li>View our return policy</li>
              <li>FAQ and help center</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f8f9fa',
    padding: '2rem 0',
  },
  content: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '0 1rem',
  },
  successHeader: {
    textAlign: 'center',
    marginBottom: '3rem',
  },
  checkmark: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    backgroundColor: '#27ae60',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '3rem',
    margin: '0 auto 2rem auto',
    fontWeight: 'bold',
  },
  successTitle: {
    fontSize: '2.5rem',
    color: '#27ae60',
    margin: '0 0 1rem 0',
    fontWeight: 'bold',
  },
  successSubtitle: {
    fontSize: '1.2rem',
    color: '#666',
    margin: 0,
    lineHeight: '1.5',
  },
  orderCard: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '2rem',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
    marginBottom: '2rem',
  },
  orderHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '2rem',
    paddingBottom: '1rem',
    borderBottom: '2px solid #eee',
  },
  orderNumber: {
    fontSize: '1.5rem',
    color: '#2c3e50',
    margin: '0 0 0.5rem 0',
    fontWeight: 'bold',
  },
  orderDate: {
    color: '#666',
    margin: 0,
    fontSize: '0.9rem',
  },
  orderStatus: {
    backgroundColor: '#3498db',
    color: 'white',
    padding: '0.5rem 1rem',
    borderRadius: '20px',
    fontSize: '0.8rem',
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  section: {
    marginBottom: '2rem',
    paddingBottom: '1rem',
    borderBottom: '1px solid #eee',
  },
  sectionTitle: {
    fontSize: '1.2rem',
    color: '#2c3e50',
    margin: '0 0 1rem 0',
    fontWeight: 'bold',
  },
  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
  },
  label: {
    fontSize: '0.9rem',
    color: '#666',
    margin: '0 0 0.25rem 0',
    fontWeight: '500',
  },
  value: {
    fontSize: '1rem',
    color: '#2c3e50',
    margin: 0,
  },
  address: {
    lineHeight: '1.6',
  },
  orderItems: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  orderItem: {
    display: 'flex',
    gap: '1rem',
    padding: '1rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
  },
  itemImage: {
    width: '80px',
    height: '80px',
    objectFit: 'cover',
    borderRadius: '8px',
  },
  itemDetails: {
    flex: 1,
  },
  itemName: {
    fontSize: '1.1rem',
    color: '#2c3e50',
    margin: '0 0 0.5rem 0',
    fontWeight: 'bold',
  },
  itemDescription: {
    fontSize: '0.9rem',
    color: '#666',
    margin: '0 0 0.5rem 0',
    lineHeight: '1.4',
  },
  itemPrice: {
    fontSize: '0.9rem',
    color: '#666',
    margin: 0,
  },
  itemTotal: {
    fontSize: '1.2rem',
    fontWeight: 'bold',
    color: '#e74c3c',
    alignSelf: 'flex-start',
  },
  orderSummary: {
    backgroundColor: '#f8f9fa',
    padding: '1rem',
    borderRadius: '8px',
  },
  summaryRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '0.5rem',
    fontSize: '0.9rem',
    color: '#666',
  },
  summaryRowTotal: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '1.2rem',
    fontWeight: 'bold',
    color: '#2c3e50',
    borderTop: '1px solid #ddd',
    paddingTop: '0.5rem',
    marginTop: '0.5rem',
  },
  instructions: {
    backgroundColor: '#f8f9fa',
    padding: '1rem',
    borderRadius: '8px',
    fontSize: '0.9rem',
    color: '#666',
    fontStyle: 'italic',
    margin: 0,
  },
  actions: {
    display: 'flex',
    gap: '1rem',
    justifyContent: 'center',
    marginBottom: '3rem',
  },
  continueButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: 'bold',
    transition: 'background-color 0.3s',
  },
  ordersButton: {
    backgroundColor: '#95a5a6',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '1rem',
    fontWeight: 'bold',
    transition: 'background-color 0.3s',
  },
  additionalInfo: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '2rem',
  },
  infoCard: {
    backgroundColor: 'white',
    padding: '1.5rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  infoTitle: {
    fontSize: '1.1rem',
    color: '#2c3e50',
    margin: '0 0 1rem 0',
    fontWeight: 'bold',
  },
  infoList: {
    margin: 0,
    paddingLeft: '1.2rem',
  },
};

export default OrderSuccessPage;
