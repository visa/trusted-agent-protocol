/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';

const CartPage = () => {
  const { cart, updateCartItem, removeFromCart, clearCart, getCartTotal } = useCart();
  const navigate = useNavigate();

  const handleQuantityChange = (productId, newQuantity) => {
    if (newQuantity > 0) {
      updateCartItem(productId, newQuantity);
    }
  };

  const handleRemoveItem = (productId) => {
    removeFromCart(productId);
  };

  const handleProceedToCheckout = () => {
    navigate('/checkout');
  };

  if (!cart || !cart.items || cart.items.length === 0) {
    return (
      <div style={styles.container}>
        <h1 style={styles.title}>Your Cart</h1>
        <div style={styles.emptyCart}>
          <p>Your cart is empty</p>
          <button 
            onClick={() => navigate('/')}
            style={styles.shopButton}
          >
            Continue Shopping
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Your Cart</h1>

      <div style={styles.cartContent}>
        <div style={styles.cartItems}>
          {cart.items.map(item => (
            <div key={item.id} style={styles.cartItem}>
              <img 
                src={item.product.image_url || '/placeholder/100/100'} 
                alt={item.product.name}
                style={styles.itemImage}
              />
              <div style={styles.itemDetails}>
                <h3 style={styles.itemName}>{item.product.name}</h3>
                <p style={styles.itemPrice}>${item.product.price.toFixed(2)} each</p>
              </div>
              <div style={styles.quantityControls}>
                <button 
                  onClick={() => handleQuantityChange(item.product.id, item.quantity - 1)}
                  style={styles.quantityButton}
                >
                  -
                </button>
                <span style={styles.quantity}>{item.quantity}</span>
                <button 
                  onClick={() => handleQuantityChange(item.product.id, item.quantity + 1)}
                  style={styles.quantityButton}
                >
                  +
                </button>
              </div>
              <div style={styles.itemTotal}>
                ${(item.product.price * item.quantity).toFixed(2)}
              </div>
              <button 
                onClick={() => handleRemoveItem(item.product.id)}
                style={styles.removeButton}
              >
                Remove
              </button>
            </div>
          ))}
          
          <div style={styles.cartActions}>
            <button onClick={clearCart} style={styles.clearButton}>
              Clear Cart
            </button>
          </div>
        </div>

        <div style={styles.checkoutSection}>
          <div style={styles.orderSummary}>
            <h3>Order Summary</h3>
            <div style={styles.totalAmount}>
              Total: ${getCartTotal().toFixed(2)}
            </div>
            <div style={styles.disclaimer}>
              Taxes, Discounts and shipping calculated at checkout
            </div>
            <button 
              onClick={handleProceedToCheckout}
              style={styles.checkoutButton}
            >
              Proceed to Checkout
            </button>
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
  emptyCart: {
    textAlign: 'center',
    padding: '3rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
  },
  shopButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '0.75rem 1.5rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
    marginTop: '1rem',
  },
  cartContent: {
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '2rem',
  },
  cartItems: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '1rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  cartItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '1rem',
    borderBottom: '1px solid #eee',
    gap: '1rem',
  },
  itemImage: {
    width: '80px',
    height: '80px',
    objectFit: 'cover',
    borderRadius: '4px',
  },
  itemDetails: {
    flex: 1,
  },
  itemName: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.1rem',
    color: '#2c3e50',
  },
  itemPrice: {
    margin: 0,
    color: '#666',
  },
  quantityControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  quantityButton: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    border: '1px solid #ddd',
    backgroundColor: 'white',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  quantity: {
    minWidth: '40px',
    textAlign: 'center',
    fontSize: '1.1rem',
    fontWeight: 'bold',
  },
  itemTotal: {
    fontSize: '1.2rem',
    fontWeight: 'bold',
    color: '#e74c3c',
    minWidth: '80px',
    textAlign: 'right',
  },
  removeButton: {
    backgroundColor: '#e74c3c',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem',
  },
  cartActions: {
    padding: '1rem',
    textAlign: 'right',
    borderTop: '1px solid #eee',
  },
  clearButton: {
    backgroundColor: '#95a5a6',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  checkoutSection: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '1rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    height: 'fit-content',
  },
  orderSummary: {
    paddingBottom: '1rem',
    borderBottom: '1px solid #eee',
  },
  totalAmount: {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    color: '#e74c3c',
    marginTop: '1rem',
    marginBottom: '0.5rem',
  },
  disclaimer: {
    fontSize: '0.8rem',
    color: '#666',
    fontStyle: 'italic',
    marginBottom: '1.5rem',
    textAlign: 'left',
  },
  checkoutButton: {
    backgroundColor: '#27ae60',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1.1rem',
    fontWeight: 'bold',
    width: '100%',
  },
};

export default CartPage;
