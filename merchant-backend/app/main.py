# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import time
import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Request, Response

# Load environment variables
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import create_tables
from app.routes import products, cart, orders, auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Reference Merchant API",
    description="A reference implementation of an e-commerce backend API",
    version="1.0.0"
)

# Add simple request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request without consuming body
    logger.info(f"🔵 REQUEST: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"🟢 RESPONSE: {response.status_code} - {process_time:.3f}s")
    
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3001,http://localhost:3003").split(","),  # React app URL + Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(auth.router, prefix="/api")

@app.on_event("startup")
def startup_event():
    """Create database tables and seed sample data on startup"""
    logger.info("🚀 Starting Reference Merchant API...")
    create_tables()
    logger.info("✅ Database tables created/verified")
    from create_sample_data import create_sample_products
    create_sample_products()
    logger.info("✅ Sample products seeded")
    # Initialize x402 payments if enabled
    from app.x402_setup import initialize_x402, is_enabled
    initialize_x402()
    if is_enabled():
        logger.info("💰 x402 payments enabled")
    else:
        logger.info("ℹ️ x402 payments disabled")

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "Welcome to Reference Merchant API"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # Run development server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )
