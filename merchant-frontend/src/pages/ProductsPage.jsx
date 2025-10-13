/* © 2025 Visa.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import React, { useState, useEffect } from 'react';
import ProductCard from '../components/ProductCard';
import SearchFilters from '../components/SearchFilters';
import { productsAPI } from '../services/api';

const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);
  const [currentFilters, setCurrentFilters] = useState({});

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async (filters = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await productsAPI.searchProducts(filters);
      setProducts(response.data.products);
      setTotal(response.data.total);
    } catch (err) {
      setError('Failed to load products. Please try again.');
      console.error('Error loading products:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query) => {
    const filters = { ...currentFilters, query };
    setCurrentFilters(filters);
    loadProducts(filters);
  };

  const handleFilter = (filterData) => {
    const filters = { ...currentFilters, ...filterData };
    setCurrentFilters(filters);
    loadProducts(filters);
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading products...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          {error}
          <button onClick={() => loadProducts()} style={styles.retryButton}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Products</h1>
      
      <SearchFilters onSearch={handleSearch} onFilter={handleFilter} />
      
      <div style={styles.resultsInfo}>
        Showing {products.length} of {total} products
      </div>

      {products.length === 0 ? (
        <div style={styles.noProducts}>
          No products found. Try adjusting your search or filters.
        </div>
      ) : (
        <div style={styles.productsGrid}>
          {products.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
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
    textAlign: 'center',
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
  },
  retryButton: {
    marginTop: '1rem',
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  resultsInfo: {
    marginBottom: '1rem',
    color: '#666',
    fontSize: '0.9rem',
  },
  noProducts: {
    textAlign: 'center',
    color: '#666',
    padding: '3rem',
    fontSize: '1.1rem',
  },
  productsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '2rem',
    marginTop: '2rem',
  },
};

export default ProductsPage;
