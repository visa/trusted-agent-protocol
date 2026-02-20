# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from app.database.database import SessionLocal, create_tables
from app.models.models import Product

def create_sample_products():
    """Create sample products for testing"""
    db = SessionLocal()
    
    sample_products = [
        {
            "name": "Wireless Headphones",
            "description": "High-quality wireless headphones with noise cancellation",
            "price": 199.99,
            "category": "Electronics",
            "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
            "stock_quantity": 50
        },
        {
            "name": "Smartphone",
            "description": "Latest smartphone with advanced camera and long battery life",
            "price": 699.99,
            "category": "Electronics",
            "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9",
            "stock_quantity": 30
        },
        {
            "name": "Running Shoes",
            "description": "Comfortable running shoes for daily exercise",
            "price": 129.99,
            "category": "Sports",
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff",
            "stock_quantity": 75
        },
        {
            "name": "Coffee Maker",
            "description": "Automatic coffee maker with programmable timer",
            "price": 89.99,
            "category": "Kitchen",
            "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085",
            "stock_quantity": 25
        },
        {
            "name": "Laptop",
            "description": "High-performance laptop for work and gaming",
            "price": 1299.99,
            "category": "Electronics",
            "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853",
            "stock_quantity": 15
        },
        {
            "name": "Yoga Mat",
            "description": "Non-slip yoga mat for home workouts",
            "price": 29.99,
            "category": "Sports",
            "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b",
            "stock_quantity": 100
        },
        {
            "name": "Desk Lamp",
            "description": "LED desk lamp with adjustable brightness",
            "price": 49.99,
            "category": "Home",
            "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c",
            "stock_quantity": 40
        },
        {
            "name": "Bluetooth Speaker",
            "description": "Portable Bluetooth speaker with excellent sound quality",
            "price": 79.99,
            "category": "Electronics",
            "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1",
            "stock_quantity": 60
        },
        {
            "name": "Water Bottle",
            "description": "Insulated stainless steel water bottle",
            "price": 24.99,
            "category": "Sports",
            "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8",
            "stock_quantity": 80
        },
        {
            "name": "Book: Python Programming",
            "description": "Comprehensive guide to Python programming",
            "price": 39.99,
            "category": "Books",
            "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c",
            "stock_quantity": 35
        },
        {
            "name": "Gaming Headset",
            "description": "High-quality gaming headset with noise cancellation",
            "price": 89.99,
            "category": "Electronics",
            "image_url": "https://images.unsplash.com/photo-1599669454699-248893623440",
            "stock_quantity": 25
        },
        {
            "name": "Yoga Mat",
            "description": "Non-slip premium yoga mat for all exercises",
            "price": 29.99,
            "category": "Sports",
            "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b",
            "stock_quantity": 40
        },
        {
            "name": "Air Fryer",
            "description": "Digital air fryer for healthy cooking",
            "price": 119.99,
            "category": "Kitchen",
            "image_url": "https://images.unsplash.com/photo-1618336753974-aae8e04506aa",
            "stock_quantity": 15
        },
        {
            "name": "Desk Lamp",
            "description": "LED desk lamp with adjustable brightness",
            "price": 45.99,
            "category": "Home",
            "image_url": "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0",
            "stock_quantity": 30
        },
        {
            "name": "Cookbook: Healthy Meals",
            "description": "Collection of nutritious and delicious recipes",
            "price": 24.99,
            "category": "Books",
            "image_url": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570",
            "stock_quantity": 45
        },
        {
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse with long battery life",
            "price": 34.99,
            "category": "Electronics",
            "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46",
            "stock_quantity": 55
        },
        {
            "name": "Running Shoes",
            "description": "Lightweight running shoes with superior cushioning",
            "price": 129.99,
            "category": "Sports",
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff",
            "stock_quantity": 20
        },
        {
            "name": "Stand Mixer",
            "description": "Professional stand mixer for baking enthusiasts",
            "price": 299.99,
            "category": "Kitchen",
            "image_url": "https://images.unsplash.com/photo-1578662996442-48f60103fc96",
            "stock_quantity": 8
        },
        {
            "name": "Throw Pillows Set",
            "description": "Set of 4 decorative throw pillows",
            "price": 49.99,
            "category": "Home",
            "image_url": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7",
            "stock_quantity": 35
        },
        {
            "name": "Book: Web Development",
            "description": "Modern web development techniques and best practices",
            "price": 44.99,
            "category": "Books",
            "image_url": "https://images.unsplash.com/photo-1555066931-4365d14bab8c",
            "stock_quantity": 28
        },
        # Digital products suitable for x402 micropayments
        {
            "name": "API Call: Weather Data",
            "description": "Single weather API call with current conditions and forecast",
            "price": 0.01,
            "category": "Digital",
            "image_url": "https://images.unsplash.com/photo-1504608524841-42fe6f032b4b",
            "stock_quantity": 9999
        },
        {
            "name": "AI Image Generation",
            "description": "Generate one AI image from a text prompt",
            "price": 0.05,
            "category": "Digital",
            "image_url": "https://images.unsplash.com/photo-1547954575-855750c57bd3",
            "stock_quantity": 9999
        },
        {
            "name": "PDF Report: Market Summary",
            "description": "Daily market summary report with key insights",
            "price": 0.10,
            "category": "Digital",
            "image_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3",
            "stock_quantity": 9999
        },
        {
            "name": "Code Review: Single File",
            "description": "Automated code review and suggestions for one source file",
            "price": 0.25,
            "category": "Digital",
            "image_url": "https://images.unsplash.com/photo-1555066931-4365d14bab8c",
            "stock_quantity": 9999
        },
        {
            "name": "Translation: 1000 Words",
            "description": "Professional AI translation of up to 1000 words",
            "price": 0.50,
            "category": "Digital",
            "image_url": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8",
            "stock_quantity": 9999
        },
    ]
    
    # Check if products already exist
    existing_products = db.query(Product).count()
    if existing_products > 0:
        print(f"Database already has {existing_products} products. Skipping sample data creation.")
        db.close()
        return
    
    # Create products
    for product_data in sample_products:
        product = Product(**product_data)
        db.add(product)
    
    db.commit()
    print(f"Created {len(sample_products)} sample products")
    db.close()

if __name__ == "__main__":
    create_tables()
    create_sample_products()
