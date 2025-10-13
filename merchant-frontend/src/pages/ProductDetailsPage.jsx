/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useToast } from '../context/ToastContext';
import { getProduct } from '../services/api';

const ProductDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const { showToast } = useToast();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quantity, setQuantity] = useState(1);
  const [selectedSize, setSelectedSize] = useState('');
  const [selectedColor, setSelectedColor] = useState('');
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);



  // Mock variations for demonstration - in a real app, these would come from the API
  const getProductVariations = (product) => {
    if (!product) return { sizes: [], colors: [] };
    
    const variations = {
      sizes: [],
      colors: []
    };

    // Add sizes based on product category
    if (product.category === 'Sports') {
      variations.sizes = ['S', 'M', 'L', 'XL'];
      variations.colors = ['Black', 'Blue', 'Red', 'White'];
    } else if (product.category === 'Electronics') {
      variations.colors = ['Black', 'Silver', 'White'];
    } else if (product.category === 'Kitchen') {
      variations.colors = ['Stainless Steel', 'Black', 'White'];
    } else if (product.category === 'Home') {
      variations.sizes = ['Small', 'Medium', 'Large'];
      variations.colors = ['Beige', 'Gray', 'Navy', 'Cream'];
    }

    return variations;
  };

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        console.log('🔍 Fetching product with ID:', id);
        setLoading(true);
        const data = await getProduct(id);
        console.log('✅ Product data received:', data);
        setProduct(data);
        
        // Set default selections
        const variations = getProductVariations(data);
        if (variations.sizes.length > 0) {
          setSelectedSize(variations.sizes[0]);
        }
        if (variations.colors.length > 0) {
          setSelectedColor(variations.colors[0]);
        }
      } catch (error) {
        console.error('❌ Error fetching product:', error);
        showToast('Error loading product details', 'error');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchProduct();
    }
  }, [id, showToast]);

  const handleAddToCart = () => {
    if (product) {
      addToCart(product.id, quantity);
      showToast(`Added ${quantity} ${product.name} to cart`, 'success');
      navigate('/');
    }
  };



  const handleQuantityChange = (e) => {
    const value = parseInt(e.target.value);
    if (value >= 1 && value <= product.stock_quantity) {
      setQuantity(value);
    }
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading product details...</div>
      </div>
    );
  }

  if (!product) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>Product not found</div>
        <button style={styles.backButton} onClick={() => navigate('/')}>
          Back to Products
        </button>
      </div>
    );
  }

  const variations = getProductVariations(product);

  return (
    <div style={styles.container}>
      <button style={styles.backButton} onClick={() => navigate('/')}>
        ← Back to Products
      </button>
      
      <div style={{
        ...styles.productDetails,
        ...(isMobile ? styles.productDetailsMobile : {})
      }}>
        <div style={styles.imageSection}>
          <img 
            src={product.image_url} 
            alt={product.name}
            style={styles.mainImage}
            onError={(e) => {
              if (!imageError) {
                setImageError(true);
                e.target.src = 'https://via.placeholder.com/500x400/cccccc/666666?text=Product+Image';
              }
            }}
          />
        </div>
        
        <div style={styles.infoSection}>
          <div style={styles.breadcrumb}>
            <span style={styles.category}>{product.category}</span>
          </div>
          
          <h1 style={styles.title}>{product.name}</h1>
          
          <div style={styles.price}>${product.price.toFixed(2)}</div>
          
          <div style={styles.description}>
            <h3>Description</h3>
            <p>{product.description}</p>
          </div>

          <div style={styles.stock}>
            <span style={product.stock_quantity > 0 ? styles.inStock : styles.outOfStock}>
              {product.stock_quantity > 0 
                ? `${product.stock_quantity} in stock` 
                : 'Out of stock'
              }
            </span>
          </div>

          {/* Variations */}
          {variations.sizes.length > 0 && (
            <div style={styles.variation}>
              <label style={styles.variationLabel}>Size:</label>
              <select 
                style={styles.select}
                value={selectedSize}
                onChange={(e) => setSelectedSize(e.target.value)}
              >
                {variations.sizes.map(size => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </div>
          )}

          {variations.colors.length > 0 && (
            <div style={styles.variation}>
              <label style={styles.variationLabel}>Color:</label>
              <select 
                style={styles.select}
                value={selectedColor}
                onChange={(e) => setSelectedColor(e.target.value)}
              >
                {variations.colors.map(color => (
                  <option key={color} value={color}>{color}</option>
                ))}
              </select>
            </div>
          )}

          {/* Quantity */}
          <div style={styles.variation}>
            <label style={styles.variationLabel}>Quantity:</label>
            <input 
              type="number"
              min="1"
              max={product.stock_quantity}
              value={quantity}
              onChange={handleQuantityChange}
              style={styles.quantityInput}
            />
          </div>

          {/* Add to Cart Button */}
          <button 
            style={product.stock_quantity > 0 ? styles.addToCartButton : styles.disabledButton}
            onClick={handleAddToCart}
            disabled={product.stock_quantity === 0}
          >
            {product.stock_quantity === 0 ? 'Out of Stock' : 'Add to Cart'}
          </button>

          {/* Product Features */}
          <div style={styles.features}>
            <h3>Features</h3>
            <ul>
              <li>High quality materials</li>
              <li>Fast shipping available</li>
              <li>30-day return policy</li>
              <li>1-year warranty</li>
            </ul>
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
    padding: '2rem',
  },
  loading: {
    textAlign: 'center',
    padding: '2rem',
    fontSize: '1.2rem',
  },
  error: {
    textAlign: 'center',
    padding: '2rem',
    fontSize: '1.2rem',
    color: '#e74c3c',
  },
  backButton: {
    backgroundColor: '#95a5a6',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
    marginBottom: '2rem',
    fontSize: '0.9rem',
  },
  productDetails: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '3rem',
  },
  productDetailsMobile: {
    gridTemplateColumns: '1fr',
    gap: '2rem',
  },
  imageSection: {
    display: 'flex',
    flexDirection: 'column',
  },
  mainImage: {
    width: '100%',
    height: '400px',
    objectFit: 'cover',
    borderRadius: '8px',
    border: '1px solid #ddd',
  },
  infoSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  breadcrumb: {
    fontSize: '0.9rem',
    color: '#666',
  },
  category: {
    backgroundColor: '#ecf0f1',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    color: '#2c3e50',
  },
  title: {
    fontSize: '2rem',
    fontWeight: 'bold',
    color: '#2c3e50',
    margin: '0',
  },
  price: {
    fontSize: '2rem',
    fontWeight: 'bold',
    color: '#e74c3c',
  },
  description: {
    lineHeight: '1.6',
  },
  stock: {
    fontSize: '0.9rem',
  },
  inStock: {
    color: '#27ae60',
    fontWeight: 'bold',
  },
  outOfStock: {
    color: '#e74c3c',
    fontWeight: 'bold',
  },
  variation: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  variationLabel: {
    fontWeight: 'bold',
    minWidth: '80px',
  },
  select: {
    padding: '0.5rem',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '1rem',
    minWidth: '150px',
  },
  quantityInput: {
    padding: '0.5rem',
    borderRadius: '4px',
    border: '1px solid #ddd',
    fontSize: '1rem',
    width: '80px',
  },
  addToCartButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1.1rem',
    fontWeight: 'bold',
    marginTop: '1rem',
    transition: 'background-color 0.2s',
  },
  disabledButton: {
    backgroundColor: '#bdc3c7',
    color: 'white',
    border: 'none',
    padding: '1rem 2rem',
    borderRadius: '4px',
    cursor: 'not-allowed',
    fontSize: '1.1rem',
    fontWeight: 'bold',
    marginTop: '1rem',
  },
  features: {
    marginTop: '2rem',
    padding: '1rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
  },
};

export default ProductDetailsPage;
