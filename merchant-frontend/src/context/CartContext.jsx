/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { cartAPI } from '../services/api';
import { useToast } from './ToastContext';

const CartContext = createContext();

const initialState = {
  cart: null,
  sessionId: null,
  loading: false,
  error: null,
};

function cartReducer(state, action) {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_CART':
      return { ...state, cart: action.payload, loading: false, error: null };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'CLEAR_CART':
      return { ...state, cart: null };
    default:
      return state;
  }
}

export function CartProvider({ children }) {
  const [state, dispatch] = useReducer(cartReducer, initialState);
  const { showSuccess, showError } = useToast();

  // Initialize cart session
  useEffect(() => {
    const initializeCart = async () => {
      let sessionId = localStorage.getItem('cartSessionId');
      
      if (!sessionId) {
        try {
          const response = await cartAPI.createCart();
          sessionId = response.data.session_id;
          localStorage.setItem('cartSessionId', sessionId);
        } catch (error) {
          console.error('Failed to create cart:', error);
          dispatch({ type: 'SET_ERROR', payload: 'Failed to initialize cart' });
          return;
        }
      }
      
      dispatch({ type: 'SET_SESSION_ID', payload: sessionId });
      await loadCart(sessionId);
    };

    initializeCart();
  }, []);

  const loadCart = async (sessionId) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await cartAPI.getCart(sessionId);
      dispatch({ type: 'SET_CART', payload: response.data });
    } catch (error) {
      console.error('Failed to load cart:', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load cart' });
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    if (!state.sessionId) {
      showError('Cart session not initialized');
      return;
    }
    
    dispatch({ type: 'SET_LOADING', payload: true });
    
    // Add timeout to prevent hanging
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Request timeout')), 15000)
    );
    
    try {
      console.log('🛒 Adding to cart:', { sessionId: state.sessionId, productId, quantity });
      
      const response = await Promise.race([
        cartAPI.addItemToCart(state.sessionId, {
          product_id: productId,
          quantity: quantity,
        }),
        timeoutPromise
      ]);
      
      console.log('🛒 Cart response:', response.data);
      dispatch({ type: 'SET_CART', payload: response.data });
      
      // Show success toast
      const productName = response.data.items.find(item => item.product.id === productId)?.product.name || 'Product';
      showSuccess(`${productName} added to cart!`);
    } catch (error) {
      console.error('🔴 Failed to add item to cart:', error);
      
      let errorMessage = 'Failed to add item to cart';
      if (error.message === 'Request timeout') {
        errorMessage = 'Request timed out. Please try again.';
      } else if (error.response?.status === 404) {
        errorMessage = 'Product not found';
      } else if (error.response?.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      }
      
      dispatch({ type: 'SET_ERROR', payload: errorMessage });
      showError(errorMessage);
    }
  };

  const updateCartItem = async (productId, quantity) => {
    if (!state.sessionId) return;
    
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await cartAPI.updateCartItem(state.sessionId, productId, quantity);
      dispatch({ type: 'SET_CART', payload: response.data });
      showSuccess('Cart updated');
    } catch (error) {
      console.error('Failed to update cart item:', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to update cart item' });
      showError('Failed to update cart item');
    }
  };

  const removeFromCart = async (productId) => {
    if (!state.sessionId) return;
    
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      await cartAPI.removeItemFromCart(state.sessionId, productId);
      await loadCart(state.sessionId);
      showSuccess('Item removed from cart');
    } catch (error) {
      console.error('Failed to remove item from cart:', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to remove item from cart' });
      showError('Failed to remove item from cart');
    }
  };

  const clearCart = async () => {
    if (!state.sessionId) return;
    
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      await cartAPI.clearCart(state.sessionId);
      dispatch({ type: 'CLEAR_CART' });
      showSuccess('Cart cleared');
    } catch (error) {
      console.error('Failed to clear cart:', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to clear cart' });
      showError('Failed to clear cart');
    }
  };

  const getCartTotal = () => {
    if (!state.cart || !state.cart.items) return 0;
    return state.cart.items.reduce((total, item) => {
      return total + (item.product.price * item.quantity);
    }, 0);
  };

  const getCartItemCount = () => {
    if (!state.cart || !state.cart.items) return 0;
    return state.cart.items.reduce((total, item) => total + item.quantity, 0);
  };

  const value = {
    ...state,
    addToCart,
    updateCartItem,
    removeFromCart,
    clearCart,
    getCartTotal,
    getCartItemCount,
  };

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}
