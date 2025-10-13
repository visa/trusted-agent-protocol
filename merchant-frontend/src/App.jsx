/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ToastProvider } from './context/ToastContext';
import { CartProvider } from './context/CartContext';
import Header from './components/Header';
import ProductsPage from './pages/ProductsPage';
import ProductDetailsPage from './pages/ProductDetailsPage';
import CartPage from './pages/CartPage';
import CheckoutPage from './pages/CheckoutPage';
import OrderSuccessPage from './pages/OrderSuccessPage';
import OrdersPage, { OrderDetailPage } from './pages/OrdersPage';


function App() {
  return (
    <ToastProvider>
      <CartProvider>
        <Router>
          <div style={styles.app}>
            <Header />
            <main style={styles.main}>
              <Routes>
                <Route path="/" element={<ProductsPage />} />
                <Route path="/product/:id" element={<ProductDetailsPage />} />
                <Route path="/cart" element={<CartPage />} />
                <Route path="/checkout" element={<CheckoutPage />} />
                <Route path="/order-success" element={<OrderSuccessPage />} />
                <Route path="/orders" element={<OrdersPage />} />
                <Route path="/order/:orderNumber" element={<OrderDetailPage />} />

              </Routes>
            </main>
            <footer style={styles.footer}>
              <div style={styles.footerContent}>
                <p>&copy; 2025 TAP Sample Merchant. All rights reserved.</p>
              </div>
            </footer>
          </div>
        </Router>
      </CartProvider>
    </ToastProvider>
  );
}

const styles = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#f8f9fa',
    display: 'flex',
    flexDirection: 'column',
  },
  main: {
    flex: 1,
  },
  footer: {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '2rem 0',
    marginTop: '4rem',
  },
  footerContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 1rem',
    textAlign: 'center',
  },
};

export default App;
