/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { ordersAPI } from '../services/api';

const CheckoutPage = () => {
  const { cart, sessionId, getCartTotal, clearCart } = useCart();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    // Contact Information
    email: '',
    phone: '',
    
    // Shipping Address
    firstName: '',
    lastName: '',
    company: '',
    address1: '',
    address2: '',
    city: '',
    state: '',
    zipCode: '',
    country: 'United States',
    
    // Billing Address
    billingDifferent: false,
    billingFirstName: '',
    billingLastName: '',
    billingCompany: '',
    billingAddress1: '',
    billingAddress2: '',
    billingCity: '',
    billingState: '',
    billingZipCode: '',
    billingCountry: 'United States',
    
    // Payment
    paymentMethod: 'credit_card',
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    nameOnCard: '',
    
    // Additional Options
    specialInstructions: '',
    newsletter: false,
  });

  // Redirect if cart is empty
  React.useEffect(() => {
    if (!cart || !cart.items || cart.items.length === 0) {
      navigate('/cart');
    }
  }, [cart, navigate]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const validateForm = () => {
    const required = ['email', 'firstName', 'lastName', 'address1', 'city', 'state', 'zipCode'];
    
    // Add billing address fields if billing is different
    if (formData.billingDifferent) {
      required.push('billingFirstName', 'billingLastName', 'billingAddress1', 'billingCity', 'billingState', 'billingZipCode');
    }
    
    // Add payment fields
    required.push('cardNumber', 'expiryDate', 'cvv', 'nameOnCard');
    
    const missing = required.filter(field => !formData[field].trim());
    
    if (missing.length > 0) {
      setError(`Please fill in the following required fields: ${missing.join(', ')}`);
      return false;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    
    // Basic card number validation (remove spaces and check length)
    const cardNumber = formData.cardNumber.replace(/\s/g, '');
    if (cardNumber.length < 13 || cardNumber.length > 19) {
      setError('Please enter a valid card number');
      return false;
    }
    
    // Expiry date validation (MM/YY or MM/YYYY format)
    const expiryRegex = /^(0[1-9]|1[0-2])\/([0-9]{2}|[0-9]{4})$/;
    if (!expiryRegex.test(formData.expiryDate)) {
      setError('Please enter expiry date in MM/YY format');
      return false;
    }
    
    // CVV validation
    const cvv = formData.cvv.trim();
    if (cvv.length < 3 || cvv.length > 4) {
      setError('Please enter a valid CVV (3-4 digits)');
      return false;
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Format shipping address
      const shippingAddress = `${formData.firstName} ${formData.lastName}\n${formData.company ? formData.company + '\n' : ''}${formData.address1}\n${formData.address2 ? formData.address2 + '\n' : ''}${formData.city}, ${formData.state} ${formData.zipCode}\n${formData.country}`;
      
      // Format billing address if different
      let billingAddress = null;
      if (formData.billingDifferent) {
        billingAddress = `${formData.billingFirstName} ${formData.billingLastName}\n${formData.billingCompany ? formData.billingCompany + '\n' : ''}${formData.billingAddress1}\n${formData.billingAddress2 ? formData.billingAddress2 + '\n' : ''}${formData.billingCity}, ${formData.billingState} ${formData.billingZipCode}\n${formData.billingCountry}`;
      }
      
      const checkoutData = {
        customer_name: `${formData.firstName} ${formData.lastName}`,
        customer_email: formData.email,
        shipping_address: shippingAddress,
        billing_address: billingAddress,
        phone: formData.phone,
        special_instructions: formData.specialInstructions || null,
        payment_method: formData.paymentMethod,
        billing_different: formData.billingDifferent,
        // Payment information
        card_number: formData.cardNumber,
        expiry_date: formData.expiryDate,
        cvv: formData.cvv,
        name_on_card: formData.nameOnCard,
        // Additional contact info
        newsletter: formData.newsletter,
        // Full form data for reference
        form_data: formData
      };
      
      const response = await ordersAPI.checkout(sessionId, checkoutData);
      
      // Clear the cart after successful checkout
      await clearCart();
      
      // Navigate to success page with order details
      navigate('/order-success', { 
        state: { 
          order: response.data.order,
          payment: response.data.payment,
          customerInfo: formData 
        }
      });
      
    } catch (err) {
      setError('Failed to process your order. Please try again.');
      console.error('Checkout error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!cart || !cart.items || cart.items.length === 0) {
    return null; // Will redirect via useEffect
  }

  const subtotal = getCartTotal();
  const shipping = 9.99; // Fixed shipping for demo
  const tax = subtotal * 0.08; // 8% tax
  const total = subtotal + shipping + tax;

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        {/* Header */}
        <div style={styles.header}>
          <button onClick={() => navigate('/cart')} style={styles.backButton}>
            ← Back to Cart
          </button>
          <h1 style={styles.title}>Checkout</h1>
        </div>

        <div style={styles.mainContent}>
          {/* Checkout Form */}
          <div style={styles.formSection}>
            <form onSubmit={handleSubmit}>
              {error && <div style={styles.error}>{error}</div>}
              
              {/* Contact Information */}
              <div style={styles.section}>
                <h2 style={styles.sectionTitle}>Contact Information</h2>
                <div style={styles.row}>
                  <input
                    type="email"
                    name="email"
                    placeholder="Email address *"
                    value={formData.email}
                    onChange={handleInputChange}
                    style={styles.input}
                    required
                  />
                  <input
                    type="tel"
                    name="phone"
                    placeholder="Phone number"
                    value={formData.phone}
                    onChange={handleInputChange}
                    style={styles.input}
                  />
                </div>
                <label style={styles.checkbox}>
                  <input
                    type="checkbox"
                    name="newsletter"
                    checked={formData.newsletter}
                    onChange={handleInputChange}
                  />
                  Email me with news and offers
                </label>
              </div>

              {/* Shipping Address */}
              <div style={styles.section}>
                <h2 style={styles.sectionTitle}>Shipping Address</h2>
                <div style={styles.row}>
                  <input
                    type="text"
                    name="firstName"
                    placeholder="First name *"
                    value={formData.firstName}
                    onChange={handleInputChange}
                    style={styles.input}
                    required
                  />
                  <input
                    type="text"
                    name="lastName"
                    placeholder="Last name *"
                    value={formData.lastName}
                    onChange={handleInputChange}
                    style={styles.input}
                    required
                  />
                </div>
                <input
                  type="text"
                  name="company"
                  placeholder="Company (optional)"
                  value={formData.company}
                  onChange={handleInputChange}
                  style={styles.input}
                />
                <input
                  type="text"
                  name="address1"
                  placeholder="Address *"
                  value={formData.address1}
                  onChange={handleInputChange}
                  style={styles.input}
                  required
                />
                <input
                  type="text"
                  name="address2"
                  placeholder="Apartment, suite, etc. (optional)"
                  value={formData.address2}
                  onChange={handleInputChange}
                  style={styles.input}
                />
                <div style={styles.row}>
                  <input
                    type="text"
                    name="city"
                    placeholder="City *"
                    value={formData.city}
                    onChange={handleInputChange}
                    style={styles.input}
                    required
                  />
                  <select
                    name="state"
                    value={formData.state}
                    onChange={handleInputChange}
                    style={styles.input}
                    required
                  >
                    <option value="">State *</option>
                    <option value="CA">California</option>
                    <option value="NY">New York</option>
                    <option value="TX">Texas</option>
                    <option value="FL">Florida</option>
                    {/* Add more states as needed */}
                  </select>
                  <input
                    type="text"
                    name="zipCode"
                    placeholder="ZIP code *"
                    value={formData.zipCode}
                    onChange={handleInputChange}
                    style={styles.input}
                    required
                  />
                </div>
                <select
                  name="country"
                  value={formData.country}
                  onChange={handleInputChange}
                  style={styles.input}
                >
                  <option value="United States">United States</option>
                  <option value="Canada">Canada</option>
                  <option value="Mexico">Mexico</option>
                </select>
              </div>

              {/* Shipping Method */}
              <div style={styles.section}>
                <h2 style={styles.sectionTitle}>Shipping Method</h2>
                <div style={styles.shippingOption}>
                  <label style={styles.radioLabel}>
                    <input type="radio" name="shipping" defaultChecked />
                    <span style={styles.radioText}>
                      Standard Shipping (5-7 business days) - $9.99
                    </span>
                  </label>
                </div>
              </div>

              {/* Payment */}
              <div style={styles.section}>
                <h2 style={styles.sectionTitle}>Payment</h2>
                <div style={styles.paymentMethods}>
                  <label style={styles.radioLabel}>
                    <input 
                      type="radio" 
                      name="paymentMethod" 
                      value="credit_card"
                      checked={formData.paymentMethod === 'credit_card'}
                      onChange={handleInputChange}
                    />
                    Credit Card
                  </label>
                </div>
                
                {formData.paymentMethod === 'credit_card' && (
                  <div style={styles.paymentForm}>
                    <input
                      type="text"
                      name="cardNumber"
                      placeholder="Card number"
                      value={formData.cardNumber}
                      onChange={handleInputChange}
                      style={styles.input}
                    />
                    <div style={styles.row}>
                      <input
                        type="text"
                        name="expiryDate"
                        placeholder="MM/YY"
                        value={formData.expiryDate}
                        onChange={handleInputChange}
                        style={styles.input}
                      />
                      <input
                        type="text"
                        name="cvv"
                        placeholder="CVV"
                        value={formData.cvv}
                        onChange={handleInputChange}
                        style={styles.input}
                      />
                    </div>
                    <input
                      type="text"
                      name="nameOnCard"
                      placeholder="Name on card"
                      value={formData.nameOnCard}
                      onChange={handleInputChange}
                      style={styles.input}
                    />
                  </div>
                )}
              </div>

              {/* Billing Address */}
              <div style={styles.section}>
                <label style={styles.checkbox}>
                  <input
                    type="checkbox"
                    name="billingDifferent"
                    checked={formData.billingDifferent}
                    onChange={handleInputChange}
                  />
                  Use a different billing address
                </label>
                
                {formData.billingDifferent && (
                  <div style={styles.billingForm}>
                    <h3 style={styles.billingTitle}>Billing Address</h3>
                    <div style={styles.row}>
                      <input
                        type="text"
                        name="billingFirstName"
                        placeholder="First name *"
                        value={formData.billingFirstName}
                        onChange={handleInputChange}
                        style={styles.input}
                        required={formData.billingDifferent}
                      />
                      <input
                        type="text"
                        name="billingLastName"
                        placeholder="Last name *"
                        value={formData.billingLastName}
                        onChange={handleInputChange}
                        style={styles.input}
                        required={formData.billingDifferent}
                      />
                    </div>
                    <input
                      type="text"
                      name="billingCompany"
                      placeholder="Company (optional)"
                      value={formData.billingCompany}
                      onChange={handleInputChange}
                      style={styles.input}
                    />
                    <input
                      type="text"
                      name="billingAddress1"
                      placeholder="Address *"
                      value={formData.billingAddress1}
                      onChange={handleInputChange}
                      style={styles.input}
                      required={formData.billingDifferent}
                    />
                    <input
                      type="text"
                      name="billingAddress2"
                      placeholder="Apartment, suite, etc. (optional)"
                      value={formData.billingAddress2}
                      onChange={handleInputChange}
                      style={styles.input}
                    />
                    <div style={styles.row}>
                      <input
                        type="text"
                        name="billingCity"
                        placeholder="City *"
                        value={formData.billingCity}
                        onChange={handleInputChange}
                        style={styles.input}
                        required={formData.billingDifferent}
                      />
                      <select
                        name="billingState"
                        value={formData.billingState}
                        onChange={handleInputChange}
                        style={styles.input}
                        required={formData.billingDifferent}
                      >
                        <option value="">State *</option>
                        <option value="CA">California</option>
                        <option value="NY">New York</option>
                        <option value="TX">Texas</option>
                        <option value="FL">Florida</option>
                        <option value="IL">Illinois</option>
                        <option value="PA">Pennsylvania</option>
                        <option value="OH">Ohio</option>
                        <option value="GA">Georgia</option>
                        <option value="NC">North Carolina</option>
                        <option value="MI">Michigan</option>
                        {/* Add more states as needed */}
                      </select>
                      <input
                        type="text"
                        name="billingZipCode"
                        placeholder="ZIP code *"
                        value={formData.billingZipCode}
                        onChange={handleInputChange}
                        style={styles.input}
                        required={formData.billingDifferent}
                      />
                    </div>
                    <select
                      name="billingCountry"
                      value={formData.billingCountry}
                      onChange={handleInputChange}
                      style={styles.input}
                    >
                      <option value="United States">United States</option>
                      <option value="Canada">Canada</option>
                      <option value="Mexico">Mexico</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Special Instructions */}
              <div style={styles.section}>
                <h2 style={styles.sectionTitle}>Special Instructions</h2>
                <textarea
                  name="specialInstructions"
                  placeholder="Special instructions for delivery (optional)"
                  value={formData.specialInstructions}
                  onChange={handleInputChange}
                  style={styles.textarea}
                  rows={3}
                />
              </div>

              {/* Submit Button */}
              <button 
                type="submit" 
                disabled={loading}
                style={styles.submitButton}
              >
                {loading ? 'Processing...' : `Complete Order - $${total.toFixed(2)}`}
              </button>
            </form>
          </div>

          {/* Order Summary */}
          <div style={styles.summarySection}>
            <div style={styles.orderSummary}>
              <h2 style={styles.summaryTitle}>Order Summary</h2>
              
              {/* Cart Items */}
              <div style={styles.cartItems}>
                {cart.items.map(item => (
                  <div key={item.id} style={styles.cartItem}>
                    <img 
                      src={item.product.image_url || '/placeholder/60/60'} 
                      alt={item.product.name}
                      style={styles.itemImage}
                    />
                    <div style={styles.itemDetails}>
                      <div style={styles.itemName}>{item.product.name}</div>
                      <div style={styles.itemQuantity}>Qty: {item.quantity}</div>
                    </div>
                    <div style={styles.itemPrice}>
                      ${(item.product.price * item.quantity).toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>

              {/* Order Totals */}
              <div style={styles.totals}>
                <div style={styles.totalRow}>
                  <span>Subtotal</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                <div style={styles.totalRow}>
                  <span>Shipping</span>
                  <span>${shipping.toFixed(2)}</span>
                </div>
                <div style={styles.totalRow}>
                  <span>Tax</span>
                  <span>${tax.toFixed(2)}</span>
                </div>
                <div style={styles.totalRowFinal}>
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>
            </div>
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
  },
  content: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '2rem 1rem',
  },
  header: {
    marginBottom: '2rem',
  },
  backButton: {
    backgroundColor: 'transparent',
    border: '1px solid #ddd',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
    marginBottom: '1rem',
    color: '#666',
  },
  title: {
    fontSize: '2rem',
    color: '#2c3e50',
    margin: 0,
  },
  mainContent: {
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '3rem',
  },
  formSection: {
    backgroundColor: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  section: {
    marginBottom: '2rem',
  },
  sectionTitle: {
    fontSize: '1.3rem',
    color: '#2c3e50',
    marginBottom: '1rem',
    borderBottom: '1px solid #eee',
    paddingBottom: '0.5rem',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '1rem',
    marginBottom: '1rem',
  },
  input: {
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    marginBottom: '1rem',
    width: '100%',
    boxSizing: 'border-box',
  },
  textarea: {
    padding: '0.75rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    marginBottom: '1rem',
    width: '100%',
    boxSizing: 'border-box',
    resize: 'vertical',
  },
  checkbox: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.9rem',
    color: '#666',
    cursor: 'pointer',
  },
  billingForm: {
    marginTop: '1.5rem',
    padding: '1.5rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    border: '1px solid #e9ecef',
  },
  billingTitle: {
    fontSize: '1.1rem',
    color: '#2c3e50',
    marginBottom: '1rem',
    fontWeight: 'bold',
  },
  radioLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    cursor: 'pointer',
    padding: '0.5rem 0',
  },
  radioText: {
    fontSize: '0.9rem',
  },
  shippingOption: {
    border: '1px solid #ddd',
    borderRadius: '4px',
    padding: '1rem',
  },
  paymentMethods: {
    marginBottom: '1rem',
  },
  paymentForm: {
    marginTop: '1rem',
  },
  error: {
    backgroundColor: '#fdf2f2',
    color: '#e74c3c',
    padding: '1rem',
    borderRadius: '4px',
    border: '1px solid #fecaca',
    marginBottom: '1rem',
  },
  submitButton: {
    backgroundColor: '#27ae60',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1.1rem',
    fontWeight: 'bold',
    width: '100%',
    marginTop: '1rem',
  },
  summarySection: {
    height: 'fit-content',
    position: 'sticky',
    top: '2rem',
  },
  orderSummary: {
    backgroundColor: 'white',
    padding: '1.5rem',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  summaryTitle: {
    fontSize: '1.3rem',
    color: '#2c3e50',
    marginBottom: '1rem',
    borderBottom: '1px solid #eee',
    paddingBottom: '0.5rem',
  },
  cartItems: {
    marginBottom: '1.5rem',
  },
  cartItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '0.75rem 0',
    borderBottom: '1px solid #f0f0f0',
  },
  itemImage: {
    width: '50px',
    height: '50px',
    objectFit: 'cover',
    borderRadius: '4px',
  },
  itemDetails: {
    flex: 1,
  },
  itemName: {
    fontSize: '0.9rem',
    fontWeight: '500',
    color: '#2c3e50',
    marginBottom: '0.25rem',
  },
  itemQuantity: {
    fontSize: '0.8rem',
    color: '#666',
  },
  itemPrice: {
    fontSize: '0.9rem',
    fontWeight: 'bold',
    color: '#e74c3c',
  },
  totals: {
    borderTop: '1px solid #eee',
    paddingTop: '1rem',
  },
  totalRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '0.5rem',
    fontSize: '0.9rem',
    color: '#666',
  },
  totalRowFinal: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '1.2rem',
    fontWeight: 'bold',
    color: '#2c3e50',
    borderTop: '1px solid #eee',
    paddingTop: '0.5rem',
    marginTop: '0.5rem',
  },
};

export default CheckoutPage;
