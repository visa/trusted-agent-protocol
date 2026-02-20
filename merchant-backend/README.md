# Merchant Backend

Sample e-commerce backend service demonstrating TAP (Trusted Agent Protocol) integration with FastAPI.

## Installation

```bash
# Install dependencies (from root directory)
pip install -r requirements.txt

# Start server (database is auto-created and seeded on startup)
cd merchant-backend
python -m uvicorn app.main:app --reload --port 8000
```

Access the API at http://localhost:8000 (docs at /docs)

## Key Features

- **Product Management** - CRUD operations for products
- **Shopping Cart** - Session-based cart with persistence  
- **Order Processing** - Order creation and tracking
- **TAP Integration** - RFC 9421 signature verification support

## Sample API Endpoints

- `GET /products` - List all products
- `POST /cart/add` - Add item to cart
- `POST /orders` - Create order from cart
- `GET /orders` - View order history

## Architecture

This sample demonstrates:
- FastAPI async patterns
- SQLAlchemy ORM with SQLite
- Integration with signature verification
- RESTful API design principles
- RESTful API design principles

## Data Management

### Initialize Sample Data
The database and sample products are automatically created when the server starts. No manual setup is needed.

To re-seed manually (e.g., after deleting the database):
```bash
python create_sample_data.py
```

### Update Database Schema
```bash
# Run database migrations
python update_database.py
```

### Database Operations
```python
# Direct database access (in Python shell)
from app.database.database import get_db
from app.models.models import Product

# Example: Get all products
db = next(get_db())
products = db.query(Product).all()
```

## Authentication & Security

### JWT Authentication
- Bearer token authentication
- Configurable token expiration
- Automatic token refresh mechanism

### Password Security
- Bcrypt password hashing
- Strong password requirements
- Secure session management

### CORS Configuration
- Configurable allowed origins
- Development and production settings
- Secure headers and credentials handling

## TAP Integration

### Signature Verification
- RFC 9421 HTTP Message Signatures support
- Integration with CDN Proxy for signature validation
- Agent Registry integration for public key retrieval
- Ed25519 and RSA-PSS-SHA256 algorithm support

### Request Flow
1. Client makes request (through CDN Proxy)
2. CDN validates signature headers
3. Verified requests reach merchant backend
4. Backend processes business logic
5. Response returned through proxy chain

## Development

### Development Server
```bash
# Start with auto-reload
uvicorn app.main:app --reload --port 8000

# Start with specific host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Database Management
```bash
# Reset database (will be re-created and seeded on next server start)
rm merchant.db

# Update schema
python update_database.py

# Backup database
cp merchant.db merchant_backup.db
```

### Logging
```bash
# View logs in development
tail -f logs/merchant-backend.log

# Set log level in .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## Testing

### Manual Testing
- **API Docs**: Visit http://localhost:8000/docs for interactive testing
- **ReDoc**: Visit http://localhost:8000/redoc for detailed documentation
- **Health Check**: GET http://localhost:8000/

### Sample API Calls
```bash
# Get all products
curl http://localhost:8000/products

# Get specific product
curl http://localhost:8000/products/1

# Add item to cart
curl -X POST http://localhost:8000/cart/add \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 2}'

# Create order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "John Doe", "customer_email": "john@example.com"}'
```

## Production Deployment

### Environment Setup
```bash
# Production environment variables
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=postgresql://user:pass@localhost/merchant_db
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Process Management
```bash
# Using systemd (Linux)
sudo systemctl start merchant-backend
sudo systemctl enable merchant-backend

# Using PM2 (Node.js process manager)
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name merchant-backend
```

## Integration with TAP Ecosystem

### Required Services
1. **CDN Proxy** (port 3001): Request routing and signature verification
2. **Agent Registry** (port 8080): Agent public key management
3. **Merchant Frontend** (port 3001): User interface

### Service Dependencies
- Database (SQLite/PostgreSQL)
- Agent Registry for signature verification
- CDN Proxy for secure request routing

## Performance Considerations

- **Database Connection Pooling**: Efficient database connections
- **Async Operations**: Non-blocking I/O for better concurrency
- **Response Caching**: Cache frequently accessed data
- **Request Logging**: Structured logging for monitoring
- **Error Handling**: Comprehensive error responses

## Troubleshooting

### Common Issues
- **Database connection errors**: Check DATABASE_URL and file permissions
- **Port conflicts**: Ensure port 8000 is available
- **CORS issues**: Verify ALLOWED_ORIGINS configuration
- **Authentication failures**: Check SECRET_KEY and token configuration

### Debug Mode
Set `DEBUG=true` and `LOG_LEVEL=DEBUG` for detailed logging and error traces.
