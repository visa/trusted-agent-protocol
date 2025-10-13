# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# Product schemas
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    image_url: Optional[str] = None
    stock_quantity: int = 0

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Cart schemas
class CartItemBase(BaseModel):
    product_id: int
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int

class CartItem(CartItemBase):
    id: int
    product: Product
    
    class Config:
        from_attributes = True

class CartBase(BaseModel):
    session_id: str

class CartCreate(CartBase):
    pass

class Cart(CartBase):
    id: int
    items: List[CartItem] = []
    
    class Config:
        from_attributes = True

# x402 Protocol Schemas
class CustomerInfo(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class Address(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str

class CartFinalizeRequest(BaseModel):
    customer_info: CustomerInfo
    shipping_address: Address
    billing_address: Optional[Address] = None
    coupon_code: Optional[str] = None

class PaymentAmount(BaseModel):
    subtotal: float
    shipping: float
    tax: float
    discount: float
    total: float
    currency: str = "USD"

class PaymentMethod(BaseModel):
    type: str
    provider: str
    endpoint: str
    method: str
    required_fields: List[str]

class OrderSummaryItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class OrderSummary(BaseModel):
    items: List[OrderSummaryItem]
    shipping_address: Address
    customer: CustomerInfo

class CartFinalizeResponse(BaseModel):
    error: str
    message: str
    payment_session_id: str
    amount: PaymentAmount
    payment_methods: List[PaymentMethod]
    expires_at: str
    order_summary: OrderSummary

class CartFulfillRequest(BaseModel):
    payment_session_id: str
    card_number: str
    expiry_date: str
    cvv: str
    cardholder_name: str

class OrderInfo(BaseModel):
    id: int
    order_number: str
    status: str
    total_amount: float
    created_at: datetime

class PaymentInfo(BaseModel):
    transaction_id: str
    provider_reference: str
    status: str

class FulfillmentInfo(BaseModel):
    tracking_number: str
    estimated_delivery: str
    shipping_carrier: str

class CartFulfillResponse(BaseModel):
    status: str
    message: str
    order: OrderInfo
    payment: PaymentInfo
    fulfillment: FulfillmentInfo

# Order schemas
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderItem(OrderItemBase):
    id: int
    product: Product
    
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    customer_email: EmailStr
    customer_name: str

class OrderCreate(OrderBase):
    cart_id: int
    # Optional shipping information
    shipping_address: Optional[str] = None
    phone: Optional[str] = None
    special_instructions: Optional[str] = None

class Order(OrderBase):
    id: int
    order_number: str
    total_amount: float
    status: str
    items: List[OrderItem] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Search and filter schemas
class ProductSearch(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = 20
    offset: int = 0

# Response schemas
class ProductList(BaseModel):
    products: List[Product]
    total: int
    limit: int
    offset: int

class OrderList(BaseModel):
    orders: List[Order]
    total: int

# Message schemas
class Message(BaseModel):
    message: str
