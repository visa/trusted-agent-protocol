# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.models import (
    Cart as CartModel, 
    CartItem as CartItemModel, 
    Product as ProductModel,
    Order as OrderModel,
    OrderItem as OrderItemModel
)
from app.schemas import (
    CartCreate, Cart, CartItemCreate, CartItemUpdate,
    CartFinalizeRequest, CartFinalizeResponse, 
    CartFulfillRequest, CartFulfillResponse, Message
)
import uuid

router = APIRouter(prefix="/cart", tags=["cart"])

def generate_order_number():
    """Generate a unique order number"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:6].upper()
    return f"ORD-{timestamp}-{random_suffix}"

@router.post("/", response_model=Cart)
def create_cart(db: Session = Depends(get_db)):
    """Create a new cart with a unique session ID"""
    session_id = str(uuid.uuid4())
    db_cart = CartModel(session_id=session_id)
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    return db_cart

@router.get("/{session_id}", response_model=Cart)
def get_cart(session_id: str, db: Session = Depends(get_db)):
    """Get cart by session ID"""
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart

@router.post("/{session_id}/items", response_model=Cart)
def add_item_to_cart(
    session_id: str, 
    item: CartItemCreate, 
    db: Session = Depends(get_db)
):
    """Add an item to the cart"""
    # Get or create cart
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        cart = CartModel(session_id=session_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    # Check if product exists
    product = db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if item already exists in cart
    existing_item = db.query(CartItemModel).filter(
        CartItemModel.cart_id == cart.id,
        CartItemModel.product_id == item.product_id
    ).first()
    
    if existing_item:
        # Update quantity
        existing_item.quantity += item.quantity
    else:
        # Add new item
        cart_item = CartItemModel(
            cart_id=cart.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart)
    return cart

@router.put("/{session_id}/items/{product_id}", response_model=Cart)
def update_cart_item(
    session_id: str,
    product_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db)
):
    """Update the quantity of an item in the cart"""
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_item = db.query(CartItemModel).filter(
        CartItemModel.cart_id == cart.id,
        CartItemModel.product_id == product_id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    if item_update.quantity <= 0:
        # Remove item if quantity is 0 or negative
        db.delete(cart_item)
    else:
        cart_item.quantity = item_update.quantity
    
    db.commit()
    db.refresh(cart)
    return cart

@router.delete("/{session_id}/items/{product_id}", response_model=Message)
def remove_item_from_cart(
    session_id: str,
    product_id: int,
    db: Session = Depends(get_db)
):
    """Remove an item from the cart"""
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_item = db.query(CartItemModel).filter(
        CartItemModel.cart_id == cart.id,
        CartItemModel.product_id == product_id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    db.delete(cart_item)
    db.commit()
    
    return Message(message="Item removed from cart successfully")

@router.delete("/{session_id}", response_model=Message)
def clear_cart(session_id: str, db: Session = Depends(get_db)):
    """Clear all items from the cart"""
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Delete all cart items
    db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).delete()
    db.commit()
    
    return Message(message="Cart cleared successfully")

@router.post("/{session_id}/checkout")
def checkout_cart(
    session_id: str,
    checkout_data: dict,
    db: Session = Depends(get_db)
):
    """Checkout cart and create an order with payment processing"""
    from app.models.models import Order as OrderModel, OrderItem as OrderItemModel
    from datetime import datetime
    import uuid
    import re
    

    
    def generate_order_number():
        """Generate a unique order number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"ORD-{timestamp}-{unique_id}"
    
    def detect_card_brand(card_number):
        """Detect card brand from card number"""
        card_number = re.sub(r'\D', '', card_number)  # Remove non-digits
        
        if card_number.startswith('4'):
            return 'Visa'
        elif card_number.startswith(('51', '52', '53', '54', '55')) or card_number.startswith('2'):
            return 'Mastercard'
        elif card_number.startswith(('34', '37')):
            return 'American Express'
        elif card_number.startswith('6'):
            return 'Discover'
        else:
            return 'Unknown'
    
    def validate_card_number(card_number):
        """Basic Luhn algorithm validation"""
        card_number = re.sub(r'\D', '', card_number)
        if len(card_number) < 13 or len(card_number) > 19:
            return False
        
        # Luhn algorithm
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(card_number) == 0
    
    def validate_expiry(expiry_date):
        """Validate expiry date format MM/YY or MM/YYYY"""
        if not expiry_date:
            return False
        
        try:
            if '/' in expiry_date:
                month, year = expiry_date.split('/')
                month = int(month)
                year = int(year)
                
                # Convert 2-digit year to 4-digit
                if year < 100:
                    year += 2000
                
                # Basic validation
                if month < 1 or month > 12:
                    return False
                
                # Check if card is not expired
                from datetime import datetime
                current_date = datetime.now()
                if year < current_date.year or (year == current_date.year and month < current_date.month):
                    return False
                
                return True
        except (ValueError, IndexError):
            return False
        
        return False
    
    def process_payment(card_data, amount):
        """
        Mock payment processing function
        In production, this would integrate with a real payment processor like Stripe, Square, etc.
        """
        card_number = card_data.get('card_number', '')
        expiry_date = card_data.get('expiry_date', '')
        cvv = card_data.get('cvv', '')
        
        # Validate card number
        if not validate_card_number(card_number):
            return {"success": False, "error": "Invalid card number"}
        
        # Validate expiry date
        if not validate_expiry(expiry_date):
            return {"success": False, "error": "Invalid or expired card"}
        
        # Validate CVV
        if not cvv or len(cvv) < 3 or len(cvv) > 4:
            return {"success": False, "error": "Invalid CVV"}
        
        # Mock payment processing - always succeeds for demo
        # In production, make API call to payment processor here
        return {
            "success": True,
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "card_brand": detect_card_brand(card_number),
            "last_four": card_number[-4:]
        }
    
    # Get cart by session_id
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total amount
    total_amount = sum(item.product.price * item.quantity for item in cart.items)
    
    # Extract required fields from checkout_data
    customer_email = checkout_data.get('customer_email')
    customer_name = checkout_data.get('customer_name')
    
    if not customer_email or not customer_name:
        raise HTTPException(
            status_code=400, 
            detail="Customer email and name are required"
        )
    
    # Extract payment information - handle both frontend and MCP agent formats
    payment_data = {
        'card_number': checkout_data.get('card_number'),
        'expiry_date': checkout_data.get('expiry_date'), 
        'cvv': checkout_data.get('cvv'),
        'name_on_card': checkout_data.get('name_on_card') or checkout_data.get('cardholder_name')
    }
    
    # If no payment data provided (e.g., from MCP agent demo), use mock data
    if not any([payment_data['card_number'], payment_data['expiry_date'], payment_data['cvv']]):
        payment_data = {
            'card_number': '4111111111111111',  # Demo Visa card
            'expiry_date': '12/25',
            'cvv': '123',
            'name_on_card': checkout_data.get('customer_name', 'Demo Customer')
        }

    
    # Validate payment information is provided
    if not all([payment_data['card_number'], payment_data['expiry_date'], payment_data['cvv']]):
        raise HTTPException(
            status_code=400,
            detail="Complete payment information is required (card number, expiry date, CVV)"
        )
    
    # Process payment
    payment_result = process_payment(payment_data, total_amount)
    
    if not payment_result['success']:
        raise HTTPException(
            status_code=400,
            detail=f"Payment failed: {payment_result['error']}"
        )
    
    # Handle shipping address - handle both string and object formats
    shipping_address = checkout_data.get('shipping_address', {})
    if isinstance(shipping_address, str):
        shipping_address_str = shipping_address
    elif isinstance(shipping_address, dict):
        shipping_address_str = f"{shipping_address.get('street', '')}, {shipping_address.get('city', '')}, {shipping_address.get('state', '')} {shipping_address.get('zip', '')}, {shipping_address.get('country', '')}"
    else:
        shipping_address_str = "No shipping address provided"
    
    # Create order with all the form data
    order = OrderModel(
        order_number=generate_order_number(),
        customer_email=customer_email,
        customer_name=customer_name,
        total_amount=total_amount,
        status="confirmed",  # Set to confirmed since payment succeeded
        shipping_address=shipping_address_str,
        phone=checkout_data.get('customer_phone'),
        special_instructions=checkout_data.get('special_instructions'),
        billing_address=checkout_data.get('billing_address', shipping_address_str),
        payment_method=checkout_data.get('payment_method', {}).get('type', 'credit_card') if isinstance(checkout_data.get('payment_method'), dict) else checkout_data.get('payment_method', 'credit_card'),
        billing_different=checkout_data.get('billing_different', False),
        # Store payment information securely
        card_last_four=payment_result['last_four'],
        card_brand=payment_result['card_brand'],
        payment_status="processed"
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Create order items from cart items
    for cart_item in cart.items:
        order_item = OrderItemModel(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price=cart_item.product.price
        )
        db.add(order_item)
    
    # Clear cart after successful checkout
    from app.models.models import CartItem as CartItemModel
    db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).delete()
    
    db.commit()
    db.refresh(order)
    
    # Reload order with all relationships to ensure product data is available
    from sqlalchemy.orm import joinedload
    order = db.query(OrderModel).options(
        joinedload(OrderModel.items).joinedload(OrderItemModel.product)
    ).filter(OrderModel.id == order.id).first()
    

    
    # Build items with complete product information
    order_items = []
    for item in order.items:
        # If product relationship is None, fetch it explicitly
        if item.product is None:
            product = db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
        else:
            product = item.product
            
        # Build item with complete product data
        order_item = {
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product.name if product else f'Product {item.product_id}',
            "quantity": item.quantity,
            "price": float(item.price),  # Frontend expects 'price', not 'unit_price'
            "unit_price": float(item.price),
            "total_price": float(item.price * item.quantity),
            "product": {
                "id": product.id if product else item.product_id,
                "name": product.name if product else f'Product {item.product_id}',
                "price": float(product.price) if product else float(item.price),
                "image_url": (product.image_url if product and product.image_url else "/placeholder/150/150"),
                "description": (product.description if product and product.description else "")
            }
        }
        order_items.append(order_item)
    
    # Calculate order totals for response
    subtotal = sum(item.price * item.quantity for item in order.items)
    tax_amount = subtotal * 0.08  # 8% tax
    shipping_cost = 15.00 if subtotal < 50 else 0.00  # Free shipping over $50
    
    return {
        "message": "Order created and payment processed successfully",
        "data": {
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "total_amount": float(order.total_amount),
                "subtotal": float(subtotal),
                "tax_amount": float(tax_amount),
                "shipping_cost": float(shipping_cost),
                "status": order.status,
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat(),
                "items": order_items
            },
            "payment": {
                "method": checkout_data.get('payment_method', {}).get('type', 'credit_card') if isinstance(checkout_data.get('payment_method'), dict) else checkout_data.get('payment_method', 'credit_card'),
                "transaction_id": payment_result.get('transaction_id'),
                "amount_charged": float(order.total_amount),
                "status": "processed",
                "card_brand": order.card_brand,
                "last_four": order.card_last_four
            }
        },
        # Keep MCP-compatible fields for backward compatibility
        "status": "success",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "total_amount": float(order.total_amount),
            "subtotal": float(subtotal),
            "tax_amount": float(tax_amount),
            "shipping_cost": float(shipping_cost),
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "items": [{
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": float(item.price),
                "total_price": float(item.price * item.quantity)
            } for item in order.items]
        },
        "payment": {
            "method": checkout_data.get('payment_method', {}).get('type', 'credit_card') if isinstance(checkout_data.get('payment_method'), dict) else checkout_data.get('payment_method', 'credit_card'),
            "transaction_id": payment_result.get('transaction_id'),
            "amount_charged": float(order.total_amount),
            "status": "processed"
        },
        "fulfillment": {
            "tracking_number": f"TRK{uuid.uuid4().hex[:10].upper()}",
            "shipping_carrier": "Standard Shipping",
            "estimated_delivery": "5-7 business days",
            "status": "processing"
        }
    }

@router.post("/{session_id}/finalize", status_code=402, response_model=CartFinalizeResponse)
def finalize_cart(
    session_id: str,
    finalize_data: CartFinalizeRequest,
    db: Session = Depends(get_db)
):
    """
    Finalize cart with shipping, tax, coupons etc and return 402 Payment Required
    This endpoint implements the x402 protocol for payment processing
    """
    # Get cart by session_id
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Extract shipping and billing information
    shipping_address = finalize_data.shipping_address
    billing_address = finalize_data.billing_address or finalize_data.shipping_address
    customer_info = finalize_data.customer_info
    
    # Calculate base amount
    subtotal = sum(item.product.price * item.quantity for item in cart.items)
    
    # Calculate shipping (simplified logic - in production this would be more complex)
    shipping_cost = 0.0
    if shipping_address.country.upper() == 'US':
        if subtotal < 50:
            shipping_cost = 9.99
        else:
            shipping_cost = 0.0  # Free shipping over $50
    else:
        shipping_cost = 19.99  # International shipping
    
    # Calculate tax (simplified - 8% for US, 0% for international)
    tax_rate = 0.08 if shipping_address.country.upper() == 'US' else 0.0
    tax_amount = subtotal * tax_rate
    
    # Apply coupons/discounts (placeholder)
    discount_amount = 0.0
    coupon_code = finalize_data.coupon_code
    if coupon_code:
        # Simple coupon logic - in production, this would check a coupons table
        if coupon_code.upper() == 'SAVE10':
            discount_amount = subtotal * 0.10
        elif coupon_code.upper() == 'FREESHIP':
            shipping_cost = 0.0
    
    # Calculate final amount
    total_amount = subtotal + shipping_cost + tax_amount - discount_amount
    
    # Generate payment session ID
    import uuid
    payment_session_id = str(uuid.uuid4())
    
    # Store finalized cart details (in production, you might want to cache this)
    finalized_cart_data = {
        'session_id': session_id,
        'payment_session_id': payment_session_id,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax_amount': tax_amount,
        'discount_amount': discount_amount,
        'total_amount': total_amount,
        'shipping_address': shipping_address.dict(),
        'billing_address': billing_address.dict(),
        'customer_info': customer_info.dict(),
        'coupon_code': coupon_code,
        'items': [
            {
                'product_id': item.product_id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': item.product.price,
                'total_price': item.product.price * item.quantity
            } for item in cart.items
        ]
    }
    
    # In production, store this in Redis or database with expiration
    # For now, we'll use a simple in-memory store (not production ready)
    if not hasattr(finalize_cart, '_finalized_carts'):
        finalize_cart._finalized_carts = {}
    finalize_cart._finalized_carts[payment_session_id] = finalized_cart_data
    
    # Return 402 Payment Required with x402 protocol headers and payment details
    from fastapi import Response
    from fastapi.responses import JSONResponse
    
    response_data = {
        "error": "Payment Required",
        "message": "Cart finalized. Payment required to complete order.",
        "payment_session_id": payment_session_id,
        "amount": {
            "subtotal": round(subtotal, 2),
            "shipping": round(shipping_cost, 2),
            "tax": round(tax_amount, 2),
            "discount": round(discount_amount, 2),
            "total": round(total_amount, 2),
            "currency": "USD"
        },
        "payment_methods": [
            {
                "type": "credit_card",
                "provider": "merchant_payment_processor",
                "endpoint": f"http://localhost:8000/api/cart/{session_id}/fulfill",
                "method": "POST",
                "required_fields": [
                    "payment_session_id",
                    "card_number",
                    "expiry_date", 
                    "cvv",
                    "cardholder_name"
                ]
            }
        ],
        "expires_at": "2024-12-31T23:59:59Z",  # In production, set reasonable expiration
        "order_summary": {
            "items": finalized_cart_data['items'],
            "shipping_address": shipping_address.dict(),
            "customer": customer_info.dict()
        }
    }
    
    # Create response with 402 status and x402 headers
    response = JSONResponse(
        status_code=402,
        content=response_data
    )
    
    # Add x402 protocol headers
    response.headers["X-Payment-Required"] = "true"
    response.headers["X-Payment-Session-ID"] = payment_session_id
    response.headers["X-Payment-Amount"] = str(round(total_amount, 2))
    response.headers["X-Payment-Currency"] = "USD"
    response.headers["X-Payment-Provider"] = "merchant_payment_processor"
    
    return response

@router.post("/{session_id}/fulfill", response_model=CartFulfillResponse)
def fulfill_cart(
    session_id: str,
    payment_data: CartFulfillRequest,
    db: Session = Depends(get_db)
):
    """
    Fulfill cart after payment confirmation
    This endpoint completes the x402 protocol flow
    """
    from app.models.models import Order as OrderModel, OrderItem as OrderItemModel
    from datetime import datetime
    import uuid
    
    def generate_order_number():
        """Generate a unique order number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"ORD-{timestamp}-{unique_id}"
    
    # Get payment session ID from request
    payment_session_id = payment_data.payment_session_id
    
    # Retrieve finalized cart data
    if not hasattr(finalize_cart, '_finalized_carts') or payment_session_id not in finalize_cart._finalized_carts:
        raise HTTPException(status_code=404, detail="Payment session not found or expired")
    
    finalized_data = finalize_cart._finalized_carts[payment_session_id]
    
    # Verify cart still exists
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Extract payment information
    card_number = payment_data.card_number
    expiry_date = payment_data.expiry_date
    cvv = payment_data.cvv
    cardholder_name = payment_data.cardholder_name
    
    # Process payment (mock implementation)
    def process_payment_with_provider(payment_info, amount):
        """Mock payment processing - in production, integrate with Stripe, Square, etc."""
        import re
        
        # Basic validation
        card_clean = re.sub(r'\D', '', payment_info['card_number'])
        if len(card_clean) < 13 or len(card_clean) > 19:
            return {"success": False, "error": "Invalid card number"}
        
        # Mock successful payment
        return {
            "success": True,
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "provider_reference": f"ref_{uuid.uuid4().hex[:8]}",
            "last_four": card_clean[-4:],
            "card_brand": "Visa" if card_clean.startswith('4') else "Mastercard"
        }
    
    # Process payment
    payment_result = process_payment_with_provider({
        'card_number': card_number,
        'expiry_date': expiry_date,
        'cvv': cvv,
        'cardholder_name': cardholder_name
    }, finalized_data['total_amount'])
    
    if not payment_result['success']:
        raise HTTPException(status_code=400, detail=f"Payment failed: {payment_result['error']}")
    
    # Create order
    customer_info = finalized_data['customer_info']
    order = OrderModel(
        order_number=generate_order_number(),
        customer_email=customer_info.get('email'),
        customer_name=customer_info.get('name'),
        total_amount=finalized_data['total_amount'],
        status="confirmed",
        shipping_address=str(finalized_data['shipping_address']),
        billing_address=str(finalized_data['billing_address']),
        phone=customer_info.get('phone'),
        payment_method="credit_card",
        card_last_four=payment_result['last_four'],
        card_brand=payment_result['card_brand'],
        payment_status="processed"
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Create order items
    for item_data in finalized_data['items']:
        order_item = OrderItemModel(
            order_id=order.id,
            product_id=item_data['product_id'],
            quantity=item_data['quantity'],
            price=item_data['unit_price']
        )
        db.add(order_item)
    
    # Clear cart after successful fulfillment
    from app.models.models import CartItem as CartItemModel
    db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).delete()
    
    db.commit()
    
    # Clean up payment session data
    del finalize_cart._finalized_carts[payment_session_id]
    
    # Generate tracking number (mock)
    tracking_number = f"TRK{uuid.uuid4().hex[:10].upper()}"
    
    return {
        "status": "fulfilled",
        "message": "Order completed successfully",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at
        },
        "payment": {
            "transaction_id": payment_result['transaction_id'],
            "provider_reference": payment_result['provider_reference'],
            "status": "completed"
        },
        "fulfillment": {
            "tracking_number": tracking_number,
            "estimated_delivery": "5-7 business days",
            "shipping_carrier": "Standard Shipping"
        }
    }


@router.post("/{session_id}/x402/checkout")
async def x402_checkout(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Machine-to-machine x402 checkout endpoint.

    Two modes:
      A) No PAYMENT-SIGNATURE header → return HTTP 402 with payment requirements
      B) PAYMENT-SIGNATURE header present → verify, settle on-chain, create order
    """
    from app.x402_setup import (
        is_enabled,
        build_checkout_requirements,
        create_payment_required,
        settle,
    )
    from x402.http import (
        encode_payment_required_header,
        encode_payment_response_header,
        PAYMENT_SIGNATURE_HEADER,
        PAYMENT_REQUIRED_HEADER,
        PAYMENT_RESPONSE_HEADER,
    )

    if not is_enabled():
        raise HTTPException(
            status_code=503,
            detail="x402 payments are not enabled on this server"
        )

    # --- Load cart and calculate totals ---
    cart = db.query(CartModel).filter(CartModel.session_id == session_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    subtotal = sum(item.quantity * item.product.price for item in cart.items)
    tax_rate = 0.08  # 8% tax
    tax_amount = round(subtotal * tax_rate, 2)
    shipping_cost = 0.0
    total_amount = round(subtotal + tax_amount + shipping_cost, 2)

    # Build payment requirements for both Solana and Base USDC
    requirements = build_checkout_requirements(total_amount)
    if not requirements:
        raise HTTPException(
            status_code=503,
            detail="No x402 wallet addresses configured on merchant"
        )

    # Build the checkout URL for the payment required response
    checkout_url = str(request.url)

    # --- Check for payment header ---
    payment_header = request.headers.get(PAYMENT_SIGNATURE_HEADER)

    if not payment_header:
        # ======== Mode A: return 402 with payment options ========
        payment_required = create_payment_required(
            requirements,
            description=f"Payment of ${total_amount:.2f} required for checkout"
        )
        pr_header_value = encode_payment_required_header(payment_required)

        return JSONResponse(
            status_code=402,
            content={
                "status": "payment_required",
                "message": f"Payment of ${total_amount:.2f} USD required",
                "total": total_amount,
                "subtotal": subtotal,
                "tax": tax_amount,
                "shipping": shipping_cost,
                "currency": "USD",
                "checkout_url": checkout_url,
            },
            headers={PAYMENT_REQUIRED_HEADER: pr_header_value},
        )

    # ======== Mode B: verify + settle + create order ========
    try:
        success, settle_resp, error_msg = await settle(
            payment_header, requirements
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"x402 payment processing error: {str(e)}"
        )

    if not success:
        # Return 402 again so the client can retry
        payment_required = create_payment_required(requirements, description=error_msg)
        pr_header_value = encode_payment_required_header(payment_required)
        return JSONResponse(
            status_code=402,
            content={
                "status": "payment_failed",
                "error": error_msg,
                "checkout_url": checkout_url,
            },
            headers={PAYMENT_REQUIRED_HEADER: pr_header_value},
        )

    # Determine which network was used from settle response
    network = getattr(settle_resp, "network", "unknown")

    # Create order in DB
    order = OrderModel(
        order_number=generate_order_number(),
        customer_email="x402-agent@crypto.local",
        customer_name="x402 Agent",
        total_amount=total_amount,
        status="confirmed",
        payment_method="x402",
        payment_status="settled",
        card_last_four=None,
        card_brand=f"x402:{network}",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Create order items from cart
    for cart_item in cart.items:
        order_item = OrderItemModel(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price=cart_item.product.price,
        )
        db.add(order_item)

    # Clear cart
    from app.models.models import CartItem as CartItemModel
    db.query(CartItemModel).filter(CartItemModel.cart_id == cart.id).delete()
    db.commit()

    tracking_number = f"TRK{uuid.uuid4().hex[:10].upper()}"

    # Encode settle receipt into response header
    response_header_value = encode_payment_response_header(settle_resp)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "x402 checkout completed successfully",
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "total_amount": float(order.total_amount),
                "subtotal": float(subtotal),
                "tax_amount": float(tax_amount),
                "shipping_cost": float(shipping_cost),
                "status": order.status,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat(),
                "items": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product.name,
                        "quantity": item.quantity,
                        "unit_price": float(item.price),
                        "total_price": float(item.quantity * item.price),
                    }
                    for item in order.items
                ],
            },
            "payment": {
                "method": "x402",
                "network": network,
                "status": "settled",
            },
            "fulfillment": {
                "tracking_number": tracking_number,
                "estimated_delivery": "5-7 business days",
                "shipping_carrier": "Standard Shipping",
                "status": "processing",
            },
        },
        headers={PAYMENT_RESPONSE_HEADER: response_header_value},
    )
