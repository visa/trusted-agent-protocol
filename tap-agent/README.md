# TAP Agent

A sophisticated Streamlit web application for testing RFC 9421 HTTP Message Signatures with Trusted Agent Protocol (TAP) compliant merchants.

## Environment Configuration

The `generate_keys.sh` script will generate a set of keys for the agent.

## Features

- 🔐 **Dual Algorithm Support**: Ed25519 and RSA-PSS-SHA256 signatures
- 📋 **RFC 9421 Compliant**: Full HTTP Message Signatures implementation
- 🎯 **Action Selection**: Product details extraction or complete checkout process
- �️ **E-commerce Integration**: Automated cart management and order processing
- 🎭 **Playwright Automation**: Browser-based interaction with merchant sites
- 📊 **Dynamic Input Data**: Real-time signature parameter updates
- 🔄 **Session Management**: Persistent key storage and state management
- 🎨 **Modern UI**: Clean, intuitive Streamlit interface

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js (for merchant services)
- Playwright browsers (installed automatically)

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### Running the App

```bash
streamlit run agent_app.py
```

Open http://localhost:8501

## Sample Agent UI
![](../assets/tap-agent.png)

## Usage

### 1. Algorithm Selection
Choose between two signature algorithms:
- **Ed25519**: Modern, fast, and secure (recommended)
- **RSA-PSS-SHA256**: Traditional RSA with PSS padding

### 2. Configure Agent
- Set your **Agent ID** (default: "1")
- Set **Merchant URL** (default: http://localhost:3001/product/1)
- View auto-generated **Input Data** with signature parameters

### 3. Action Selection
Choose your interaction type:
- **📦 Product Details**: Extract product information from merchant site
- **🛒 Complete Checkout**: Perform full e-commerce checkout process

### 4. Execute Action
Click the action button to:
- Generate RFC 9421 compliant HTTP Message Signature
- Launch automated browser session with Playwright
- Interact with merchant using signed requests
- Display results in real-time

## Technology Stack

- **Python 3.8+**: Core runtime
- **Streamlit**: Modern web interface framework  
- **Cryptography**: Multi-algorithm signature support
- **Playwright**: Browser automation for e-commerce testing
- **Requests**: HTTP client for API interactions
- **Python-dotenv**: Environment variable management

## Cryptographic Implementation

### Ed25519 (Recommended)
- **Algorithm**: Ed25519 curve25519 signatures
- **Key Size**: 256-bit
- **Performance**: ~64x faster than RSA
- **Security**: Post-quantum resistant design
- **RFC Compliance**: RFC 9421 "ed25519" algorithm

### RSA-PSS-SHA256 (Traditional)
- **Algorithm**: RSA with PSS padding
- **Key Size**: 2048-bit minimum
- **Hash Function**: SHA-256
- **Padding**: PKCS#1 PSS
- **RFC Compliance**: RFC 9421 "rsa-pss-sha256" algorithm

## Dependencies

```
streamlit>=1.37.0
cryptography>=43.0.1
requests>=2.32.4
python-dotenv
playwright>=1.40.0
```

## Advanced Features

### HTTP Message Signatures (RFC 9421)
- **Signature Components**: `@authority`, `@path`, `created`, `expires`, `nonce`, `keyId`, `tag`
- **Multiple Algorithms**: Ed25519 and RSA-PSS-SHA256 support
- **Dynamic Tags**: `agent-browser-auth` for product details, `agent-payer-auth` for checkout
- **Base String Generation**: Compliant signature base string construction
- **Header Creation**: Proper `Signature-Input` and `Signature` header formatting

### E-commerce Automation
- **Product Extraction**: Automatic product title and price detection
- **Cart Management**: Add to cart, navigate to cart page
- **Checkout Flow**: Complete order submission with form filling
- **Order Tracking**: Extract order IDs using multiple strategies
- **Error Handling**: Comprehensive error reporting and debugging

### Browser Automation
- **Playwright Integration**: Headless Chrome automation
- **Dynamic Selectors**: Multiple selector strategies for robustness  
- **Page Interaction**: Click, type, navigate, wait for elements
- **Screenshot Capture**: Visual debugging capabilities
- **Session Management**: Persistent cookies and state

## Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Run with auto-reload
streamlit run agent_app.py --server.runOnSave true
```

### Environment Setup
```bash
# Generate RSA keys (optional - for RSA-PSS-SHA256)
openssl genrsa -out rsa_private_key.pem 2048
openssl rsa -in rsa_private_key.pem -pubout -out rsa_public_key.pem

# Generate Ed25519 keys (optional - for Ed25519)
openssl genpkey -algorithm Ed25519 -out ed25519_private.pem
openssl pkey -in ed25519_private.pem -pubout -out ed25519_public.pem
```

## Integration with TAP Ecosystem

### Required Services
1. **Agent Registry** (port 8080): Key management and agent registration
2. **Merchant Backend** (port 8000): Product and order APIs
3. **Merchant Frontend** (port 3001): E-commerce interface
4. **CDN Proxy** (port 3001): Signature verification service

### Service Communication
- **Signature Verification**: CDN Proxy validates signatures against Agent Registry
- **Product Data**: Retrieved from Merchant Backend via signed requests
- **Order Processing**: Complete checkout through Merchant Frontend
- **Key Management**: Public keys stored in Agent Registry for verification

## Deployment Options

### Streamlit Cloud
```bash
# Push to GitHub and deploy via Streamlit Cloud
git push origin main
# Configure secrets in Streamlit Cloud dashboard
```

### Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "agent_app.py", "--server.address", "0.0.0.0"]
```

### Local Production
```bash
# Install production dependencies
pip install -r requirements.txt
playwright install

# Run with production settings
streamlit run agent_app.py --server.port 8501 --server.address 0.0.0.0
```

## Troubleshooting

### Common Issues
- **Playwright browsers not installed**: Run `playwright install`
- **Environment variables missing**: Check `.env` file configuration
- **Port conflicts**: Ensure ports 8501, 8000, 3001, 3001, 8080 are available
- **Signature verification failures**: Verify key formats and Agent Registry connectivity

### Debug Mode
Set `DEBUG=true` in environment to enable verbose logging and detailed error messages.
