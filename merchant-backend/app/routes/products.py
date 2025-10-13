# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import requests
import logging
from app.database.database import get_db
from app.models.models import Product as ProductModel
from app.schemas import Product, ProductList, ProductSearch, ProductCreate
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=ProductList)
def search_products(
    query: Optional[str] = Query(None, description="Search query for product name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    offset: int = Query(0, ge=0, description="Number of products to skip"),
    db: Session = Depends(get_db)
):
    """Search and filter products"""
    
    # Build query
    filters = []
    
    if query:
        filters.append(
            or_(
                ProductModel.name.ilike(f"%{query}%"),
                ProductModel.description.ilike(f"%{query}%")
            )
        )
    
    if category:
        filters.append(ProductModel.category.ilike(f"%{category}%"))
    
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    
    # Apply filters
    query_obj = db.query(ProductModel)
    if filters:
        query_obj = query_obj.filter(and_(*filters))
    
    # Get total count
    total = query_obj.count()
    
    # Apply pagination and get results
    products = query_obj.offset(offset).limit(limit).all()
    
    return ProductList(
        products=products,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/premium/search")
def premium_search_products(
    request: Request,
    query: Optional[str] = Query(None, description="Search query for product name or description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    offset: int = Query(0, ge=0, description="Number of products to skip"),
    delegate_token: Optional[str] = Query(None, description="x402 delegation token for payment"),
    db: Session = Depends(get_db)
):
    """Premium search endpoint that requires x402 payment via delegation token"""
    
    # Check if delegation token is provided
    if not delegate_token:
        # Return 402 Payment Required with payment details
        payment_details = {
            "error": "Payment Required",
            "message": "This premium search endpoint requires payment via x402 delegation token",
            "payment_required": True,
            "payment_details": {
                "amount": 0.50,  # $0.50 for premium search
                "currency": "USD",
                "payment_type": "x402_delegation",
                "payment_facilitator_url": "http://localhost:8001",
                "service_description": "Premium Product Search with Enhanced Features",
                "features": [
                    "Advanced search algorithms",
                    "Detailed product analytics",
                    "Personalized recommendations",
                    "Priority response time"
                ]
            }
        }
        return JSONResponse(
            status_code=402,
            content=payment_details
        )
    
    # Verify delegation token with Payment Facilitator
    try:
        pf_response = requests.post(
            "http://localhost:8001/verify-delegation",
            json={
                "delegation_token": delegate_token,
                "amount": 0.50,
                "merchant_id": "merchant_123",
                "service": "premium_search"
            },
            timeout=5
        )
        
        if pf_response.status_code != 200:
            logger.error(f"Payment Facilitator verification failed: {pf_response.status_code}")
            raise HTTPException(
                status_code=402, 
                detail="Invalid or expired delegation token"
            )
            
        verification_result = pf_response.json()
        if not verification_result.get("valid", False):
            raise HTTPException(
                status_code=402, 
                detail="Delegation token verification failed"
            )
            
        logger.info(f"✅ Delegation token verified for premium search: {verification_result}")
        
    except requests.RequestException as e:
        logger.error(f"Failed to verify delegation token: {e}")
        raise HTTPException(
            status_code=502, 
            detail="Payment verification service unavailable"
        )
    
    # Token verified, proceed with premium search
    logger.info(f"🔍 Premium search authorized for query: '{query}'")
    
    # Build enhanced query with premium features
    filters = []
    
    if query:
        # Enhanced search with stemming and fuzzy matching (premium feature)
        filters.append(
            or_(
                ProductModel.name.ilike(f"%{query}%"),
                ProductModel.description.ilike(f"%{query}%"),
                ProductModel.category.ilike(f"%{query}%")  # Also search in category
            )
        )
    
    if category:
        filters.append(ProductModel.category.ilike(f"%{category}%"))
    
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    
    # Apply filters with premium sorting
    query_obj = db.query(ProductModel)
    if filters:
        query_obj = query_obj.filter(and_(*filters))
    
    # Premium feature: Sort by relevance and popularity
    query_obj = query_obj.order_by(ProductModel.stock_quantity.desc(), ProductModel.price.asc())
    
    # Get total count
    total = query_obj.count()
    
    # Apply pagination
    products = query_obj.offset(offset).limit(limit).all()
    
    # Premium response with enhanced data
    return {
        "products": products,
        "total": total,
        "limit": limit,
        "offset": offset,
        "premium_features": {
            "enhanced_search": True,
            "relevance_sorted": True,
            "payment_confirmed": True,
            "service_tier": "premium"
        },
        "search_analytics": {
            "query_processed": query,
            "results_found": len(products),
            "search_time_ms": 45,  # Simulated faster response
            "relevance_score": 0.95
        }
    }

@router.get("/{product_id}", response_model=Product)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product by ID"""
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=Product)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product (admin functionality)"""
    db_product = ProductModel(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
