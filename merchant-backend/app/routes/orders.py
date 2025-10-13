# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.models import (
    Order as OrderModel, 
    OrderItem as OrderItemModel
)
from app.schemas import Order, OrderList, Message
import uuid
from datetime import datetime

router = APIRouter(prefix="/orders", tags=["orders"])

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"ORD-{timestamp}-{unique_id}"

# Checkout functionality moved to /cart/{session_id}/checkout

@router.get("/", response_model=OrderList)
def get_orders(
    customer_email: str = None,
    status: str = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get orders with optional filtering"""
    query = db.query(OrderModel)
    
    if customer_email:
        query = query.filter(OrderModel.customer_email == customer_email)
    
    if status:
        query = query.filter(OrderModel.status == status)
    
    total = query.count()
    orders = query.order_by(OrderModel.created_at.desc()).offset(offset).limit(limit).all()
    
    return OrderList(orders=orders, total=total)

@router.get("/{order_id}", response_model=Order)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a specific order by ID"""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.get("/number/{order_number}", response_model=Order)
def get_order_by_number(order_number: str, db: Session = Depends(get_db)):
    """Get a specific order by order number"""
    order = db.query(OrderModel).filter(OrderModel.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/{order_id}/status", response_model=Order)
def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """Update order status"""
    valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = status
    order.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    return order

@router.delete("/{order_id}", response_model=Message)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    """Cancel an order (only if status is pending or confirmed)"""
    order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400, 
            detail="Order cannot be cancelled. Only pending or confirmed orders can be cancelled."
        )
    
    order.status = "cancelled"
    order.updated_at = datetime.utcnow()
    
    db.commit()
    
    return Message(message=f"Order {order.order_number} has been cancelled successfully")
