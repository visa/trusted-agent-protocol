# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import uuid
import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import base64
import json
import time
import webbrowser
import requests
import threading
import datetime
import re
from urllib.parse import urlencode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

# Get RSA keys from environment variables
def get_static_keys_from_env():
    """Get RSA keys from environment variables"""
    private_key = os.getenv('RSA_PRIVATE_KEY')
    public_key = os.getenv('RSA_PUBLIC_KEY')
    
    if not private_key or not public_key:
        raise ValueError("RSA_PRIVATE_KEY and RSA_PUBLIC_KEY must be set in environment variables")
    
    return private_key, public_key

def get_ed25519_keys_from_env():
    """Get Ed25519 keys from environment variables"""
    private_key = os.getenv('ED25519_PRIVATE_KEY')
    public_key = os.getenv('ED25519_PUBLIC_KEY')
    
    if not private_key or not public_key:
        raise ValueError("ED25519_PRIVATE_KEY and ED25519_PUBLIC_KEY must be set in environment variables")
    
    return private_key, public_key

# Global variable to store product extraction results across threads
_product_extraction_results = None

# Global variable to store order completion results across threads
_order_completion_results = None

def get_static_keys():
    """Return the static private and public keys from environment variables"""
    return get_static_keys_from_env()

def create_http_message_signature(private_key_pem: str, authority: str, path: str, keyid: str, nonce: str, created: int, expires: int, tag: str) -> tuple[str, str]:
    """Create HTTP Message Signature following RFC 9421 syntax"""
    try:
        # Create signature parameters string
        signature_params = f'("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="rsa-pss-sha256"; nonce="{nonce}"; tag="{tag}"'
        
        # Create the signature base string following RFC 9421 format
        signature_base_lines = [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {signature_params}'
        ]
        signature_base = '\n'.join(signature_base_lines)
        
        print(f"🔐 RFC 9421 Signature Base String:\n{signature_base}")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        print(f"📋 Signature Params: {signature_params}")
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        # Sign the signature base string using RSA-PSS (matching the algorithm declared)
        signature = private_key.sign(
            signature_base.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Format the signature-input header (RFC 9421 format)
        signature_input_header = f'sig2=("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="rsa-pss-sha256"; nonce="{nonce}"; tag="{tag}"'
        
        # Format the signature header (RFC 9421 format)
        signature_header = f'sig2=:{signature_b64}:'
        
        print(f"✅ Created RFC 9421 compliant signature")
        print(f"📤 Signature-Input: {signature_input_header}")
        print(f"🔒 Signature: {signature_header}")
        
        return signature_input_header, signature_header
        
    except Exception as e:
        print(f"❌ Error creating HTTP message signature: {str(e)}")
        return "", ""

def parse_url_components(url: str) -> tuple[str, str]:
    """Parse URL to extract authority and path components for RFC 9421"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Authority is the host (and port if not default)
        authority = parsed.netloc
        
        # Path includes the path and query parameters
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        
        print(f"🔍 Parsed URL: {url}")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        
        return authority, path
    except Exception as e:
        print(f"❌ Error parsing URL: {str(e)}")
        return "", ""

def launch_with_playwright(url: str, headers: dict) -> bool:
    """Launch browser with headers using Playwright"""
    try:
        # Check if playwright is installed
        from playwright.sync_api import sync_playwright
        import threading
        import time
        
        def run_browser():
            """Run browser in a separate thread to keep it alive"""
            with sync_playwright() as p:
                # Launch browser with additional options to handle network issues
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors',
                        '--ignore-certificate-errors-spki-list'
                    ]
                )
                
                # Create context with signature headers applied to all requests
                context = browser.new_context(
                    extra_http_headers=headers,
                    ignore_https_errors=True,
                    viewport={'width': 1280, 'height': 720}
                )
                
                page = context.new_page()
                
                print(f"🔧 Browser context created with signature headers")
                print("📨 Signature Headers:")
                for key, value in headers.items():
                    if key == 'signature':
                        print(f"   {key}: {value[:20]}..." if len(value) > 20 else f"   {key}: {value}")
                    else:
                        print(f"   {key}: {value}")
                
                # Add request/response interceptors to handle failed API calls
                def handle_request(request):
                    # Log API calls
                    if 'api' in request.url.lower() or request.method == 'OPTIONS':
                        print(f"API Request: {request.method} {request.url}")
                
                def handle_response(response):
                    # Handle failed OPTIONS and API requests
                    if response.status >= 400:
                        print(f"Failed Request: {response.status} {response.request.method} {response.url}")
                        # Don't let failed API calls crash the browser
                        return
                
                # Set up request/response listeners
                page.on('request', handle_request)
                page.on('response', handle_response)
                
                # Handle console errors from the website
                def handle_console(msg):
                    if msg.type == 'error':
                        print(f"Console Error: {msg.text}")
                
                page.on('console', handle_console)
                
                # Navigate to the URL with error handling
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to: {url}")
                    
                    # Wait a bit for the page to fully load
                    time.sleep(3)
                    
                    # Try to extract product information
                    product_info = {}
                    
                    # Common selectors for product title
                    title_selectors = [
                        'h1',
                        '[data-testid="product-title"]',
                        '.product-title',
                        '.product-name',
                        '[class*="title"]',
                        '[class*="product"]',
                        'title'
                    ]
                    
                    # Common selectors for product price
                    price_selectors = [
                        '[data-testid="price"]',
                        '.price',
                        '.product-price',
                        '[class*="price"]',
                        '[class*="cost"]',
                        '[class*="amount"]',
                        'span:has-text("$")',
                        'span:has-text("€")',
                        'span:has-text("£")'
                    ]
                    
                    # Extract product title
                    for selector in title_selectors:
                        try:
                            title_element = page.query_selector(selector)
                            if title_element:
                                title_text = title_element.inner_text().strip()
                                if title_text and len(title_text) > 3:  # Valid title
                                    product_info['title'] = title_text
                                    print(f"📦 Product Title: {title_text}")
                                    break
                        except:
                            continue
                    
                    # Extract product price
                    for selector in price_selectors:
                        try:
                            price_element = page.query_selector(selector)
                            if price_element:
                                price_text = price_element.inner_text().strip()
                                # Check if it looks like a price (contains currency symbols or numbers)
                                if price_text and any(char in price_text for char in ['$', '€', '£', '¥']) or any(char.isdigit() for char in price_text):
                                    product_info['price'] = price_text
                                    print(f"💰 Product Price: {price_text}")
                                    break
                        except:
                            continue
                    
                    # If we couldn't find specific elements, try generic extraction
                    if not product_info.get('title'):
                        try:
                            page_title = page.title()
                            if page_title:
                                product_info['title'] = page_title
                                print(f"📦 Page Title: {page_title}")
                        except:
                            pass
                    
                    if not product_info.get('price'):
                        try:
                            # Look for any text that contains currency symbols
                            all_text = page.content()
                            import re
                            price_pattern = r'[\$€£¥]\s*\d+(?:[.,]\d{2})?|\d+(?:[.,]\d{2})?\s*[\$€£¥]'
                            prices = re.findall(price_pattern, all_text)
                            if prices:
                                product_info['price'] = prices[0]
                                print(f"💰 Found Price: {prices[0]}")
                        except:
                            pass
                    
                    # Log the results and store globally
                    global _product_extraction_results
                    import datetime
                    
                    extraction_log = []
                    extraction_log.append("🛍️  PRODUCT EXTRACTION RESULTS")
                    extraction_log.append("="*50)
                    
                    if product_info.get('title'):
                        extraction_log.append(f"📦 Title: {product_info['title']}")
                        print(f"📦 Title: {product_info['title']}")
                    else:
                        extraction_log.append("❌ Title: Not found")
                        print("❌ Title: Not found")
                    
                    if product_info.get('price'):
                        extraction_log.append(f"💰 Price: {product_info['price']}")
                        print(f"💰 Price: {product_info['price']}")
                    else:
                        extraction_log.append("❌ Price: Not found")
                        print("❌ Price: Not found")
                    
                    extraction_log.append("="*50)
                    
                    # Store results globally
                    _product_extraction_results = {
                        'title': product_info.get('title'),
                        'price': product_info.get('price'),
                        'url': url,
                        'extraction_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'extraction_log': '\n'.join(extraction_log)
                    }
                    
                    print("\n" + '\n'.join(extraction_log))
                    
                    # Wait a moment before closing
                    print("⏳ Closing browser in 3 seconds...")
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"❌ Navigation or extraction error: {e}")
                
                # Close the browser automatically
                try:
                    print("🔒 Closing browser...")
                    browser.close()
                except Exception as e:
                    print(f"Error closing browser: {e}")
        
        # Start browser in a separate thread so it doesn't block Streamlit
        browser_thread = threading.Thread(target=run_browser, daemon=True)
        browser_thread.start()
        
        # Give it a moment to start
        time.sleep(2)
        
        st.success("✅ Browser launched with headers!")
        st.info("🤖 Browser will automatically extract product info and close.")
        st.warning("� Check the terminal/console for extraction results.")
        return True
            
    except ImportError:
        return False
    except Exception as e:
        st.error(f"Error launching browser: {str(e)}")
        return False

def complete_checkout_with_playwright(product_url: str, cart_url: str, checkout_url: str, headers: dict = None) -> tuple[bool, dict]:
    """Complete full checkout process: product page → add to cart → cart page → proceed to checkout → complete order"""
    try:
        # Check if playwright is installed
        from playwright.sync_api import sync_playwright
        import threading
        import time
        import re
        
        # Reset order completion results
        global _order_completion_results
        _order_completion_results = None
        
        # Ensure headers are provided
        if headers is None:
            headers = {}
        
        def run_full_checkout():
            """Run complete checkout process in a separate thread"""
            with sync_playwright() as p:
                # Launch browser with additional options
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors'
                    ]
                )
                
                # Create context with signature headers applied to all requests
                print(f"🔧 Setting up browser context with signature headers")
                context = browser.new_context(
                    extra_http_headers=headers,
                    ignore_https_errors=True,
                    viewport={'width': 1280, 'height': 720}
                )
                
                page = context.new_page()
                
                # Log headers being sent
                print("🛒 STARTING COMPLETE CHECKOUT PROCESS")
                print("="*50)
                print(f"📦 Product URL: {product_url}")
                print(f"🛒 Cart URL: {cart_url}")
                print(f"💳 Checkout URL: {checkout_url}")
                print("📨 Signature Headers:")
                for key, value in headers.items():
                    if key == 'signature':
                        print(f"   {key}: {value[:20]}..." if len(value) > 20 else f"   {key}: {value}")
                    else:
                        print(f"   {key}: {value}")
                print("="*50)
                
                try:
                    # STEP 1: Navigate to product page
                    print(f"🛍️ STEP 1: Navigating to product page: {product_url}")
                    page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to product page")
                    
                    # Wait for page to load
                    time.sleep(3)
                    
                    # STEP 2: Find and click "Add to Cart" button
                    print(f"🛒 STEP 2: Looking for 'Add to Cart' button...")
                    
                    # Common selectors for "Add to Cart" buttons
                    add_to_cart_selectors = [
                        'button:has-text("Add to Cart")',
                        'button:has-text("Add To Cart")',
                        'button:has-text("ADD TO CART")',
                        '[data-testid="add-to-cart"]',
                        '[id*="add-to-cart"]',
                        '[class*="add-to-cart"]',
                        '.add-cart',
                        '.addToCart',
                        '#addToCart',
                        'input[value*="Add to Cart"]',
                        'button[title*="Add to Cart"]',
                        '.btn-add-cart',
                        '.cart-add'
                    ]
                    
                    cart_added = False
                    for selector in add_to_cart_selectors:
                        try:
                            add_button = page.query_selector(selector)
                            if add_button and add_button.is_visible():
                                print(f"🎯 Found 'Add to Cart' button: {selector}")
                                add_button.click()
                                print(f"✅ Successfully clicked 'Add to Cart'")
                                cart_added = True
                                break
                        except Exception as e:
                            continue
                    
                    if not cart_added:
                        print("❌ Could not find 'Add to Cart' button")
                        # Try to find any button that might be add to cart
                        try:
                            all_buttons = page.query_selector_all('button')
                            for button in all_buttons[:10]:  # Check first 10 buttons
                                text = button.inner_text().lower()
                                if any(phrase in text for phrase in ['add', 'cart', 'buy', 'purchase']):
                                    print(f"🔄 Trying button with text: {text}")
                                    button.click()
                                    cart_added = True
                                    break
                        except:
                            pass
                    
                    if cart_added:
                        # Wait a moment for cart update
                        time.sleep(2)
                        print("✅ Product added to cart successfully")
                    else:
                        print("⚠️ Could not add product to cart, proceeding anyway")
                    
                    # STEP 3: Navigate to cart page
                    print(f"🛒 STEP 3: Navigating to cart page: {cart_url}")
                    page.goto(cart_url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to cart page")
                    
                    # Wait for cart page to load
                    time.sleep(3)
                    
                    # STEP 4: Find and click "Proceed to Checkout" button
                    print(f"➡️ STEP 4: Looking for 'Proceed to Checkout' button...")
                    
                    # Common selectors for "Proceed to Checkout" buttons
                    proceed_checkout_selectors = [
                        'button:has-text("Proceed to Checkout")',
                        'button:has-text("Proceed To Checkout")',
                        'button:has-text("PROCEED TO CHECKOUT")',
                        'button:has-text("Checkout")',
                        'button:has-text("CHECKOUT")',
                        'a:has-text("Proceed to Checkout")',
                        'a:has-text("Checkout")',
                        '[data-testid="proceed-to-checkout"]',
                        '[data-testid="checkout"]',
                        '[id*="proceed-checkout"]',
                        '[id*="checkout"]',
                        '[class*="proceed-checkout"]',
                        '[class*="checkout-btn"]',
                        '.proceed-checkout',
                        '.checkout-proceed',
                        '#proceedToCheckout',
                        '#checkout',
                        '.btn-checkout',
                        'input[value*="Checkout"]',
                        'button[title*="Checkout"]'
                    ]
                    
                    checkout_proceeded = False
                    for selector in proceed_checkout_selectors:
                        try:
                            proceed_button = page.query_selector(selector)
                            if proceed_button and proceed_button.is_visible():
                                print(f"🎯 Found 'Proceed to Checkout' button: {selector}")
                                proceed_button.click()
                                print(f"✅ Successfully clicked 'Proceed to Checkout'")
                                checkout_proceeded = True
                                break
                        except Exception as e:
                            continue
                    
                    if not checkout_proceeded:
                        print("❌ Could not find 'Proceed to Checkout' button")
                        # Try to find any button that might be proceed to checkout
                        try:
                            all_buttons = page.query_selector_all('button, a')
                            for button in all_buttons[:15]:  # Check first 15 buttons/links
                                text = button.inner_text().lower()
                                if any(phrase in text for phrase in ['proceed', 'checkout', 'continue', 'next']):
                                    print(f"🔄 Trying button with text: {text}")
                                    button.click()
                                    checkout_proceeded = True
                                    break
                        except:
                            pass
                    
                    if checkout_proceeded:
                        # Wait for navigation to checkout page
                        time.sleep(3)
                        print("✅ Successfully proceeded to checkout")
                    else:
                        print("⚠️ Could not proceed to checkout, trying direct navigation")
                        # Fallback: navigate directly to checkout page
                        print(f"🛒 STEP 4b: Direct navigation to checkout: {checkout_url}")
                        page.goto(checkout_url, wait_until='domcontentloaded', timeout=30000)
                    
                    # STEP 5: We should now be on the checkout page
                    print(f"✅ Now on checkout page (current URL: {page.url})")
                    
                    # Wait for checkout page to load
                    time.sleep(3)
                    
                    # STEP 5: Fill out checkout form
                    print(f"📝 STEP 5: Filling out comprehensive checkout form...")
                    
                    # First, let's scan the page to see what form elements are available
                    print("🔍 Scanning page for form elements...")
                    try:
                        all_inputs = page.query_selector_all('input, select, textarea')
                        print(f"📋 Found {len(all_inputs)} form elements on the page:")
                        
                        for i, input_elem in enumerate(all_inputs[:20]):  # Show first 20 elements
                            try:
                                try:
                                    tag = input_elem.evaluate('el => el.tagName') or 'unknown'
                                except:
                                    tag = input_elem.get_attribute('tagName') or 'unknown'
                                    
                                input_type = input_elem.get_attribute('type') or 'text'
                                name = input_elem.get_attribute('name') or 'no-name'
                                input_id = input_elem.get_attribute('id') or 'no-id'
                                placeholder = input_elem.get_attribute('placeholder') or 'no-placeholder'
                                visible = input_elem.is_visible()
                                enabled = input_elem.is_enabled()
                                
                                print(f"   {i+1}. {tag.lower()}[{input_type}] name='{name}' id='{input_id}' placeholder='{placeholder}' visible={visible} enabled={enabled}")
                            except:
                                print(f"   {i+1}. <error reading element>")
                                
                        if len(all_inputs) > 20:
                            print(f"   ... and {len(all_inputs) - 20} more elements")
                            
                    except Exception as e:
                        print(f"⚠️ Error scanning form elements: {e}")
                    
                    print("="*50)
                    
                    # Comprehensive checkout form data matching the React form structure
                    checkout_info = {
                        # Contact Information
                        'email': 'john.doe@example.com',
                        'phone': '+1-555-0123',
                        
                        # Shipping Address
                        'firstName': 'John',
                        'lastName': 'Doe',
                        'company': 'Example Company Inc.',
                        'address1': '123 Main Street',
                        'address2': 'Suite 456',
                        'city': 'New York',
                        'state': 'NY',
                        'zipCode': '10001',
                        'country': 'United States',
                        
                        # Billing Address (initially same as shipping)
                        'billingFirstName': 'John',
                        'billingLastName': 'Doe', 
                        'billingCompany': 'Example Company Inc.',
                        'billingAddress1': '123 Main Street',
                        'billingAddress2': 'Suite 456',
                        'billingCity': 'New York',
                        'billingState': 'NY',
                        'billingZipCode': '10001',
                        'billingCountry': 'United States',
                        
                        # Payment Information
                        'cardNumber': '4111111111111111',
                        'expiryDate': '12/25',
                        'cvv': '123',
                        'nameOnCard': 'John Doe',
                        
                        # Additional Options
                        'specialInstructions': 'Please handle with care - signature authentication sample order'
                    }
                    
                    # Comprehensive form field selectors matching React form structure
                    form_selectors = {
                        # Contact Information
                        'email': ['#email', '[name="email"]', '[type="email"]', '[placeholder*="email"]', '[data-testid="email"]'],
                        'phone': ['#phone', '[name="phone"]', '[type="tel"]', '[placeholder*="phone"]', '[data-testid="phone"]'],
                        
                        # Shipping Address
                        'firstName': ['#firstName', '[name="firstName"]', '[placeholder*="first"]', '[data-testid="firstName"]', '[id*="first"]'],
                        'lastName': ['#lastName', '[name="lastName"]', '[placeholder*="last"]', '[data-testid="lastName"]', '[id*="last"]'],
                        'company': ['#company', '[name="company"]', '[placeholder*="company"]', '[data-testid="company"]'],
                        'address1': ['#address1', '[name="address1"]', '[placeholder*="address"]', '[data-testid="address1"]', '#address'],
                        'address2': ['#address2', '[name="address2"]', '[placeholder*="address2"]', '[data-testid="address2"]', '[placeholder*="apt"]'],
                        'city': ['#city', '[name="city"]', '[placeholder*="city"]', '[data-testid="city"]'],
                        'state': ['#state', '[name="state"]', '[placeholder*="state"]', '[data-testid="state"]'],
                        'zipCode': ['#zipCode', '#zip', '[name="zip"]', '[name="zipCode"]', '[placeholder*="zip"]', '[data-testid="zipCode"]'],
                        'country': ['#country', '[name="country"]', '[data-testid="country"]'],
                        
                        # Billing Address
                        'billingFirstName': ['#billingFirstName', '[name="billingFirstName"]', '[data-testid="billingFirstName"]'],
                        'billingLastName': ['#billingLastName', '[name="billingLastName"]', '[data-testid="billingLastName"]'],
                        'billingCompany': ['#billingCompany', '[name="billingCompany"]', '[data-testid="billingCompany"]'],
                        'billingAddress1': ['#billingAddress1', '[name="billingAddress1"]', '[data-testid="billingAddress1"]'],
                        'billingAddress2': ['#billingAddress2', '[name="billingAddress2"]', '[data-testid="billingAddress2"]'],
                        'billingCity': ['#billingCity', '[name="billingCity"]', '[data-testid="billingCity"]'],
                        'billingState': ['#billingState', '[name="billingState"]', '[data-testid="billingState"]'],
                        'billingZipCode': ['#billingZipCode', '[name="billingZipCode"]', '[data-testid="billingZipCode"]'],
                        'billingCountry': ['#billingCountry', '[name="billingCountry"]', '[data-testid="billingCountry"]'],
                        
                        # Payment Information
                        'cardNumber': ['#cardNumber', '[name="cardNumber"]', '[placeholder*="card"]', '[data-testid="cardNumber"]', '[id*="card"]'],
                        'expiryDate': ['#expiryDate', '[name="expiryDate"]', '[placeholder*="expiry"]', '[data-testid="expiryDate"]', '[placeholder*="mm/yy"]'],
                        'cvv': ['#cvv', '[name="cvv"]', '[placeholder*="cvv"]', '[data-testid="cvv"]', '[placeholder*="security"]'],
                        'nameOnCard': ['#nameOnCard', '[name="nameOnCard"]', '[placeholder*="name on card"]', '[data-testid="nameOnCard"]'],
                        
                        # Additional Options
                        'specialInstructions': ['#specialInstructions', '[name="specialInstructions"]', '[placeholder*="instructions"]', '[data-testid="specialInstructions"]', 'textarea[name*="instructions"]']
                    }
                    
                    # Fill form fields with enhanced logic and better error handling
                    fields_filled = 0
                    for field, value in checkout_info.items():
                        field_filled = False
                        print(f"🔍 Attempting to fill field: {field}")
                        
                        for selector in form_selectors.get(field, []):
                            try:
                                element = page.query_selector(selector)
                                if element:
                                    # Check if element is visible and enabled
                                    is_visible = element.is_visible()
                                    is_enabled = element.is_enabled()
                                    
                                    print(f"   🎯 Found element with selector: {selector}")
                                    print(f"      Visible: {is_visible}, Enabled: {is_enabled}")
                                    
                                    if is_visible and is_enabled:
                                        # Get element tag and type safely
                                        try:
                                            tag_name = element.evaluate('el => el.tagName')
                                        except:
                                            tag_name = element.get_attribute('tagName')
                                        
                                        element_type = element.get_attribute('type')
                                        
                                        print(f"      Tag: {tag_name}, Type: {element_type}")
                                        
                                        # Check if it's a select dropdown
                                        if tag_name and tag_name.lower() == 'select':
                                            element.select_option(value)
                                            print(f"✅ Selected {field}: {value}")
                                            field_filled = True
                                            fields_filled += 1
                                            break
                                        # Check if it's a checkbox
                                        elif element_type and element_type.lower() == 'checkbox':
                                            # For now, we'll leave checkboxes unchecked (billingDifferent=false, newsletter=false)
                                            print(f"📋 Skipped checkbox {field} (keeping default state)")
                                            field_filled = True
                                            break
                                        # Check if it's a radio button
                                        elif element_type and element_type.lower() == 'radio':
                                            element.check()
                                            print(f"✅ Selected radio {field}: {value}")
                                            field_filled = True
                                            fields_filled += 1
                                            break
                                        # Regular input field (text, email, tel, etc.)
                                        else:
                                            # Fill the field (this automatically clears and replaces content)
                                            element.fill(value)
                                            
                                            # Verify the value was set
                                            try:
                                                filled_value = element.input_value()
                                                if filled_value == value:
                                                    print(f"✅ Filled {field}: {value}")
                                                    field_filled = True
                                                    fields_filled += 1
                                                    break
                                                else:
                                                    print(f"⚠️ Value mismatch for {field}. Expected: {value}, Got: {filled_value}")
                                            except:
                                                # Some elements don't support input_value(), just assume it worked
                                                print(f"✅ Filled {field}: {value} (verification skipped)")
                                                field_filled = True
                                                fields_filled += 1
                                                break
                                    else:
                                        print(f"      Element not visible or enabled, skipping")
                                else:
                                    print(f"   ❌ Element not found for selector: {selector}")
                                    
                            except Exception as e:
                                print(f"   ⚠️ Error with selector {selector}: {str(e)}")
                                continue
                        
                        if not field_filled:
                            print(f"⚠️ Could not fill {field}: {value}")
                            # Try a more generic approach for this field
                            try:
                                # Look for any input with name, id, or placeholder containing the field name
                                generic_selectors = [
                                    f'[name*="{field.lower()}"]',
                                    f'[id*="{field.lower()}"]',
                                    f'[placeholder*="{field.lower()}"]',
                                    f'input[name*="{field.lower()}"]',
                                    f'input[id*="{field.lower()}"]'
                                ]
                                
                                for generic_selector in generic_selectors:
                                    try:
                                        generic_element = page.query_selector(generic_selector)
                                        if generic_element and generic_element.is_visible() and generic_element.is_enabled():
                                            generic_element.fill(value)
                                            print(f"✅ Filled {field} using generic selector: {generic_selector}")
                                            field_filled = True
                                            fields_filled += 1
                                            break
                                    except:
                                        continue
                                        
                            except Exception as e:
                                print(f"   ⚠️ Generic selector approach failed: {str(e)}")
                    
                    print(f"📊 Successfully filled {fields_filled} out of {len(checkout_info)} fields")
                    
                    # Handle special cases: Payment method selection
                    try:
                        # Try to select credit card as payment method
                        payment_selectors = [
                            'input[value="credit_card"]',
                            'input[name="paymentMethod"][value="credit_card"]',
                            '[data-testid="credit-card-option"]',
                            'input[type="radio"][value*="credit"]'
                        ]
                        
                        for selector in payment_selectors:
                            try:
                                payment_element = page.query_selector(selector)
                                if payment_element:
                                    payment_element.check()
                                    print("✅ Selected credit card payment method")
                                    break
                            except:
                                continue
                    except:
                        print("⚠️ Could not select payment method")
                    
                    # Wait for form validation
                    time.sleep(3)
                    

                    
                    # Look for and click submit/complete order button with comprehensive selectors
                    print(f"🔄 Looking for submit/complete order button...")
                    
                    submit_selectors = [
                        # Primary submit buttons
                        'button[type="submit"]',
                        'input[type="submit"]',
                        
                        # Text-based button selectors
                        'button:has-text("Complete Order")',
                        'button:has-text("Place Order")',
                        'button:has-text("Submit Order")',
                        'button:has-text("Complete")',
                        'button:has-text("Submit")',
                        'button:has-text("Order")',
                        'button:has-text("Purchase")',
                        'button:has-text("Checkout")',
                        'button:has-text("Buy Now")',
                        'button:has-text("Confirm")',
                        
                        # Case-insensitive variations
                        'button:has-text("COMPLETE ORDER")',
                        'button:has-text("PLACE ORDER")',
                        'button:has-text("SUBMIT ORDER")',
                        
                        # Data attributes and IDs
                        '[data-testid="submit-order"]',
                        '[data-testid="complete-order"]',
                        '[data-testid="place-order"]',
                        '[data-testid="checkout-submit"]',
                        
                        # Class-based selectors
                        '.submit-btn',
                        '.complete-order',
                        '.place-order',
                        '.checkout-submit',
                        '.order-submit',
                        
                        # ID selectors
                        '#submit',
                        '#complete-order',
                        '#place-order',
                        '#checkout-submit',
                        '#order-submit'
                    ]
                    
                    submit_clicked = False
                    for selector in submit_selectors:
                        try:
                            button = page.query_selector(selector)
                            if button and button.is_visible() and button.is_enabled():
                                print(f"🎯 Found submit button: {selector}")
                                button.click()
                                print(f"✅ Successfully clicked submit button")
                                submit_clicked = True
                                break
                        except Exception as e:
                            continue
                    
                    if not submit_clicked:
                        print("❌ Could not find submit button, trying fallback approach...")
                        # Fallback: look for any button that might be a submit button
                        try:
                            all_buttons = page.query_selector_all('button, input[type="button"], input[type="submit"]')
                            for button in all_buttons:
                                try:
                                    text = button.inner_text().lower() if button.inner_text() else ''
                                    value = button.get_attribute('value') or ''
                                    if any(phrase in text or phrase in value.lower() for phrase in ['submit', 'complete', 'order', 'place', 'confirm', 'buy']):
                                        print(f"🔄 Trying fallback button: {text or value}")
                                        button.click()
                                        submit_clicked = True
                                        break
                                except:
                                    continue
                        except:
                            pass
                    
                    if submit_clicked:
                        print("✅ Order submission initiated")
                        
                        # STEP 6: Wait for redirect to order success page
                        print(f"⏳ Waiting for redirect to order success page...")
                        
                        success_page_reached = False
                        current_url = page.url
                        print(f"📍 Starting URL: {current_url}")
                        
                        # Strategy 1: Wait for navigation event (works for full page redirects)
                        try:
                            print("🔄 Attempting to wait for navigation event...")
                            page.wait_for_navigation(timeout=15000)  # 15 seconds
                            new_url = page.url
                            print(f"✅ Navigation detected! New URL: {new_url}")
                            
                            # Check if the new URL is a success page
                            success_patterns = ['/order-success', '/success', '/confirmation', '/thank-you', '/order-complete', '/order-confirmed']
                            if any(pattern in new_url.lower() for pattern in success_patterns):
                                success_page_reached = True
                                print(f"✅ Successfully redirected to order success page via navigation: {new_url}")
                            
                        except Exception as e:
                            print(f"⚠️ No navigation event detected: {e}")
                        
                        # Strategy 2: Wait for URL pattern match (works for client-side routing)
                        if not success_page_reached:
                            print("🔄 Attempting to wait for URL pattern match...")
                            success_patterns = ['**/order-success*', '**/success*', '**/confirmation*', '**/thank-you*']
                            
                            for pattern in success_patterns:
                                try:
                                    print(f"   Trying pattern: {pattern}")
                                    page.wait_for_url(pattern, timeout=10000)  # 10 seconds per pattern
                                    new_url = page.url
                                    print(f"✅ URL pattern matched! New URL: {new_url}")
                                    success_page_reached = True
                                    break
                                except Exception as e:
                                    print(f"   Pattern {pattern} not matched: {e}")
                                    continue
                        
                        # Strategy 3: Manual polling with DOM change detection
                        if not success_page_reached:
                            print("🔄 Falling back to manual URL polling with DOM monitoring...")
                            max_wait_time = 20
                            wait_interval = 1
                            waited_time = 0
                            last_url = page.url
                            
                            while waited_time < max_wait_time and not success_page_reached:
                                try:
                                    current_url = page.url
                                    
                                    # Check if URL changed
                                    if current_url != last_url:
                                        print(f"🔍 URL changed from {last_url} to {current_url}")
                                        last_url = current_url
                                    
                                    # Check for success page patterns
                                    success_patterns = ['/order-success', '/success', '/confirmation', '/thank-you', '/order-complete', '/order-confirmed']
                                    if any(pattern in current_url.lower() for pattern in success_patterns):
                                        success_page_reached = True
                                        print(f"✅ Success page detected via polling: {current_url}")
                                        break
                                    
                                    # Also check DOM content for success indicators
                                    try:
                                        # Look for success-related text in the page
                                        success_text_indicators = [
                                            'text="Order placed successfully"',
                                            'text="Thank you for your order"',
                                            'text="Order confirmation"',
                                            'text="Your order has been placed"',
                                            ':has-text("Order #")',
                                            ':has-text("Order Number")'
                                        ]
                                        
                                        for indicator in success_text_indicators:
                                            try:
                                                element = page.query_selector(indicator)
                                                if element and element.is_visible():
                                                    print(f"✅ Success page detected via DOM content: found '{indicator}'")
                                                    success_page_reached = True
                                                    break
                                            except:
                                                continue
                                        
                                        if success_page_reached:
                                            break
                                            
                                    except:
                                        pass
                                    
                                    print(f"🔍 Current URL (polling {waited_time}s): {current_url}")
                                    time.sleep(wait_interval)
                                    waited_time += wait_interval
                                    
                                except Exception as e:
                                    print(f"⚠️ Error during polling: {e}")
                                    time.sleep(wait_interval)
                                    waited_time += wait_interval
                        
                        if not success_page_reached:
                            print(f"⚠️ Could not detect order success page after all strategies")
                            print(f"📍 Final URL: {page.url}")
                            
                            # Still try to extract order info from current page in case it's there
                            print("🔄 Attempting order extraction from current page anyway...")
                        else:
                            print(f"✅ Order success page reached: {page.url}")
                        
                        # STEP 7: Extract order number from success page
                        print(f"🔍 Extracting order number from success page...")
                        
                        # Wait for success page to fully load
                        time.sleep(3)
                        
                        order_id = None
                        order_info = {}
                        
                        # Comprehensive order number extraction strategies
                        order_extraction_strategies = [
                            # Strategy 1: Look for "Order #" or "Order Number" text patterns
                            {
                                'name': 'Order # Text Pattern',
                                'selectors': [
                                    'span:has-text("Order #")',
                                    'div:has-text("Order #")',
                                    'p:has-text("Order #")',
                                    'span:has-text("Order Number")',
                                    'div:has-text("Order Number")',
                                    'p:has-text("Order Number")',
                                    'h1:has-text("Order")',
                                    'h2:has-text("Order")',
                                    'h3:has-text("Order")'
                                ],
                                'regex': r'Order\s*#\s*([A-Z0-9][A-Za-z0-9-]{5,})'
                            },
                            
                            # Strategy 2: Look for data attributes and IDs
                            {
                                'name': 'Data Attributes',
                                'selectors': [
                                    '[data-testid*="order"]',
                                    '[data-testid*="orderNumber"]',
                                    '[data-testid*="order-id"]',
                                    '[id*="order-number"]',
                                    '[id*="orderNumber"]',
                                    '[id*="order-id"]',
                                    '[class*="order-number"]',
                                    '[class*="orderNumber"]',
                                    '[class*="order-id"]'
                                ],
                                'regex': r'([A-Za-z0-9-]+)'
                            },
                            
                            # Strategy 3: Look for confirmation/success specific elements
                            {
                                'name': 'Confirmation Elements',
                                'selectors': [
                                    '.confirmation .order-number',
                                    '.success .order-number',
                                    '.order-confirmation',
                                    '.order-summary',
                                    '.thank-you .order-number'
                                ],
                                'regex': r'([A-Za-z0-9-]+)'
                            }
                        ]
                        
                        # Try each extraction strategy
                        for strategy in order_extraction_strategies:
                            if order_id:
                                break
                                
                            print(f"🎯 Trying strategy: {strategy['name']}")
                            
                            for selector in strategy['selectors']:
                                try:
                                    element = page.query_selector(selector)
                                    if element and element.is_visible():
                                        text = element.inner_text().strip()
                                        print(f"🔍 Found element with text: {text}")
                                        
                                        # Extract order ID using strategy's regex
                                        order_match = re.search(strategy['regex'], text, re.IGNORECASE)
                                        if order_match:
                                            order_id = order_match.group(1)
                                            print(f"✅ Extracted order ID: {order_id} (using {strategy['name']})")
                                            
                                            # Store additional order info
                                            order_info = {
                                                'order_id': order_id,
                                                'extraction_method': strategy['name'],
                                                'selector_used': selector,
                                                'full_text': text,
                                                'success_page_url': page.url,
                                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                                            }
                                            break
                                except Exception as e:
                                    continue
                        
                        # Fallback: Extract from URL if still not found
                        if not order_id:
                            print("🔄 Trying URL extraction as fallback...")
                            try:
                                current_url = page.url
                                url_patterns = [
                                    r'order-success/([A-Za-z0-9-]+)',
                                    r'order/([A-Za-z0-9-]+)',
                                    r'success/([A-Za-z0-9-]+)',
                                    r'confirmation/([A-Za-z0-9-]+)',
                                    r'[?&]order[=:]([A-Za-z0-9-]+)',
                                    r'[?&]id[=:]([A-Za-z0-9-]+)',
                                    r'[?&]order_id[=:]([A-Za-z0-9-]+)'
                                ]
                                
                                for pattern in url_patterns:
                                    url_match = re.search(pattern, current_url, re.IGNORECASE)
                                    if url_match:
                                        order_id = url_match.group(1)
                                        order_info = {
                                            'order_id': order_id,
                                            'extraction_method': 'URL Pattern',
                                            'pattern_used': pattern,
                                            'success_page_url': current_url,
                                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                                        }
                                        print(f"✅ Extracted order ID from URL: {order_id}")
                                        break
                            except Exception as e:
                                print(f"⚠️ URL extraction error: {e}")
                        
                        # Final fallback: Get any text that looks like an order ID
                        if not order_id:
                            print("🔄 Final fallback: scanning entire page content...")
                            try:
                                page_content = page.content()
                                # Look for patterns like "ORD-20251013090947-B12E70F6", "12345", etc.
                                fallback_patterns = [
                                    r'Order\s*#\s*([A-Z0-9][A-Za-z0-9-]{5,})',
                                    r'\b(ORD-[A-Z0-9-]+)\b',
                                    r'\b([A-Z]{3}-[0-9]{14}-[A-Z0-9]{8})\b',
                                    r'order[#\s:]*([A-Z0-9-]{6,})',
                                    r'confirmation[#\s:]*([A-Z0-9-]{6,})',
                                    r'\b([A-Z]{2,}[0-9]{4,})\b',
                                    r'\b([0-9]{6,})\b'
                                ]
                                
                                for pattern in fallback_patterns:
                                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                                    if matches:
                                        order_id = matches[0]
                                        order_info = {
                                            'order_id': order_id,
                                            'extraction_method': 'Page Content Scan',
                                            'pattern_used': pattern,
                                            'success_page_url': page.url,
                                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                                        }
                                        print(f"✅ Extracted order ID from page content: {order_id}")
                                        break
                            except Exception as e:
                                print(f"⚠️ Page content scan error: {e}")
                        
                    else:
                        print("❌ Could not submit order - no submit button found")
                        order_info = {
                            'error': 'Could not submit order - no submit button found',
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                    
                    # Log comprehensive results
                    print("\n" + "="*60)
                    print("🛒 CHECKOUT COMPLETION RESULTS")
                    print("="*60)
                    
                    if order_id:
                        print(f"✅ ORDER SUCCESSFULLY PLACED!")
                        print(f"📋 Order ID: {order_id}")
                        print(f"🔍 Extraction Method: {order_info.get('extraction_method', 'Unknown')}")
                        print(f"🌐 Success Page URL: {order_info.get('success_page_url', page.url)}")
                        print(f"🕒 Completed At: {order_info.get('timestamp', 'Unknown')}")
                        
                        if order_info.get('full_text'):
                            print(f"📝 Full Text Found: {order_info['full_text']}")
                        
                        # Store order info globally for UI display
                        global _order_completion_results
                        _order_completion_results = order_info
                        
                    else:
                        print("❌ Order ID: Not found")
                        print("🔍 Attempted all extraction strategies without success")
                        
                        # Try to get page content for debugging
                        try:
                            print("📄 Success page content (first 1000 chars):")
                            page_content = page.content()
                            print(page_content[:1000] + "..." if len(page_content) > 1000 else page_content)
                        except Exception as e:
                            print(f"⚠️ Could not retrieve page content: {e}")
                        
                        # Store error info
                        _order_completion_results = {
                            'error': 'Order ID not found after successful form submission',
                            'final_url': page.url,
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                    
                    print("="*60)
                    
                    # Wait before closing to allow user to see results
                    print("⏳ Closing browser in 3 seconds...")
                    time.sleep(3)
                    
                    return order_id is not None, order_info
                    
                except Exception as e:
                    print(f"❌ Checkout error: {e}")
                
                # Close the browser
                try:
                    print("🔒 Closing browser...")
                    browser.close()
                except Exception as e:
                    print(f"Error closing browser: {e}")
        
        # Start checkout in a separate thread
        checkout_thread = threading.Thread(target=run_full_checkout, daemon=True)
        checkout_thread.start()
        
        # Wait for the thread to complete (with timeout)
        checkout_thread.join(timeout=120)  # 2 minute timeout
        
        # Check if thread is still alive (timed out)
        if checkout_thread.is_alive():
            print("⚠️ Checkout process timed out after 2 minutes")
            return False, {'error': 'Checkout process timed out after 2 minutes', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}
        
        # Return results
        if _order_completion_results:
            if 'error' in _order_completion_results:
                return False, _order_completion_results
            else:
                return True, _order_completion_results
        else:
            return False, {'error': 'Checkout process completed but no results found', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}
            
    except ImportError:
        return False, {'error': 'Playwright not installed', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}
    except Exception as e:
        return False, {'error': f'Checkout error: {str(e)}', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}

def create_signature(private_key_pem: str, json_data: str) -> str:
    """Create a signature using the private key with JSON data and base64 encoding"""
    try:
        # Parse JSON to validate it
        try:
            parsed_json = json.loads(json_data)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {str(e)}")
            return ""
        
        # Convert JSON to string (compact format)
        json_string = json.dumps(parsed_json, separators=(',', ':'), sort_keys=True)
        
        # Base64 encode the JSON string
        base64_data = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        print(f"Base64 Encoded Data: {base64_data}")    
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        # Sign the base64 encoded data
        signature = private_key.sign(
            base64_data.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        st.error(f"Error creating signature: {str(e)}")
        return ""

def create_http_message_signature(private_key_pem: str, authority: str, path: str, keyid: str, nonce: str, created: int, expires: int, tag: str) -> tuple[str, str]:
    """Create HTTP Message Signature following RFC 9421 syntax"""
    try:
        # Create signature parameters string
        signature_params = f'("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="rsa-pss-sha256"; nonce="{nonce}"; tag="{tag}"'
        
        # Create the signature base string following RFC 9421 format
        signature_base_lines = [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {signature_params}'
        ]
        signature_base = '\n'.join(signature_base_lines)
        
        print(f"Signature Base String:\n{signature_base}")
        print(f"Authority: {authority}")
        print(f"Path: {path}")
        print(f"Signature Params: {signature_params}")
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        # Sign the signature base string using RSA-PSS (matching the algorithm declared)
        signature = private_key.sign(
            signature_base.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Format the signature-input header (RFC 9421 format)
        signature_input_header = f'sig2=("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="rsa-pss-sha256"; nonce="{nonce}"; tag="{tag}"'
        
        # Format the signature header (RFC 9421 format)
        signature_header = f'sig2=:{signature_b64}:'
        
        return signature_input_header, signature_header
        
    except Exception as e:
        st.error(f"Error creating HTTP message signature: {str(e)}")
        return "", ""

def create_ed25519_signature(private_key_pem: str, authority: str, path: str, keyid: str, nonce: str, created: int, expires: int, tag: str) -> tuple[str, str]:
    """Create HTTP Message Signature using Ed25519 following RFC 9421"""
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        
        print(f"🔐 Creating Ed25519 signature...")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        
        # Create signature parameters string
        signature_params = f'("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
        
        # Create the signature base string
        signature_base_lines = [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {signature_params}'
        ]
        signature_base = '\n'.join(signature_base_lines)
        
        print(f"🔐 Ed25519 Signature Base String:\n{signature_base}")
        
        # Load Ed25519 keys from environment variables
        try:
            ed25519_private_b64, ed25519_public_b64 = get_ed25519_keys_from_env()
            print(f"🔑 Using Ed25519 keys from environment variables")
        except ValueError as e:
            print(f"❌ Ed25519 keys not found in environment: {e}")
            st.error(f"Ed25519 keys not configured. Please add ED25519_PRIVATE_KEY and ED25519_PUBLIC_KEY to your .env file.")
            return "", ""
        
        # Load private key from base64
        private_bytes = base64.b64decode(ed25519_private_b64)
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        
        print(f"🔑 Using Ed25519 Private Key: {ed25519_private_b64[:20]}...")
        print(f"🔑 Using Ed25519 Public Key: {ed25519_public_b64[:20]}...")
        
        # Sign with Ed25519 (no padding needed)
        signature = private_key.sign(signature_base.encode('utf-8'))
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        # Format headers
        signature_input_header = f'sig2=("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
        signature_header = f'sig2=:{signature_b64}:'
        
        print(f"✅ Created Ed25519 signature")
        print(f"📤 Signature-Input: {signature_input_header}")
        print(f"🔒 Signature: {signature_header}")
        
        return signature_input_header, signature_header
        
    except Exception as e:
        print(f"❌ Error creating Ed25519 signature: {str(e)}")
        st.error(f"Error creating Ed25519 signature: {str(e)}")
        return "", ""

def parse_url_components(url: str) -> tuple[str, str]:
    """Parse URL to extract authority and path components"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Authority is the host (and port if not default)
        authority = parsed.netloc
        
        # Path includes the path and query parameters
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        
        return authority, path
    except Exception as e:
        st.error(f"Error parsing URL: {str(e)}")
        return "", ""

def perform_x402_checkout(merchant_api_url: str, product_id: int, quantity: int = 1) -> dict:
    """
    Perform an x402 checkout against the merchant backend API.

    Flow:
      1. Create cart
      2. Add items
      3. POST x402/checkout (no payment header) → get 402 + requirements
      4. Sign payment with x402 client
      5. POST x402/checkout (with payment header) → get 200 + order
    """
    import httpx
    from x402.client import x402ClientSync
    from x402.http import (
        decode_payment_required_header,
        encode_payment_signature_header,
        PAYMENT_SIGNATURE_HEADER,
        PAYMENT_REQUIRED_HEADER,
        PAYMENT_RESPONSE_HEADER,
    )

    # --- Build x402 client with wallet signers ---
    client = x402ClientSync()

    evm_key = os.getenv("EVM_PRIVATE_KEY", "")
    svm_key = os.getenv("SVM_PRIVATE_KEY", "")

    if evm_key:
        from eth_account import Account
        from x402.mechanisms.evm.signers import EthAccountSigner
        from x402.mechanisms.evm.exact import register_exact_evm_client
        account = Account.from_key(evm_key)
        evm_signer = EthAccountSigner(account)
        register_exact_evm_client(client, evm_signer)

    if svm_key:
        from x402.mechanisms.svm.signers import KeypairSigner
        from x402.mechanisms.svm.exact import register_exact_svm_client
        svm_signer = KeypairSigner.from_base58(svm_key)
        register_exact_svm_client(client, svm_signer)

    base = merchant_api_url.rstrip("/")
    http = httpx.Client(timeout=30)

    # 1. Create cart
    resp = http.post(f"{base}/api/cart/")
    resp.raise_for_status()
    session_id = resp.json()["session_id"]

    # 2. Add item
    resp = http.post(
        f"{base}/api/cart/{session_id}/items",
        json={"product_id": product_id, "quantity": quantity},
    )
    resp.raise_for_status()

    # 3. Initial checkout request (no payment) → 402
    checkout_url = f"{base}/api/cart/{session_id}/x402/checkout"
    resp = http.post(checkout_url)
    if resp.status_code != 402:
        return {"success": False, "error": f"Expected 402, got {resp.status_code}: {resp.text}"}

    # 4. Decode payment requirements from header
    pr_header = resp.headers.get(PAYMENT_REQUIRED_HEADER, "")
    if not pr_header:
        return {"success": False, "error": "No PAYMENT-REQUIRED header in 402 response"}

    payment_required = decode_payment_required_header(pr_header)

    # 5. Sign payment
    payload = client.create_payment_payload(payment_required)
    payment_sig_value = encode_payment_signature_header(payload)

    # 6. Retry with signed payment header
    resp = http.post(
        checkout_url,
        headers={PAYMENT_SIGNATURE_HEADER: payment_sig_value},
    )

    if resp.status_code == 200:
        payment_response_header = resp.headers.get(PAYMENT_RESPONSE_HEADER, "")
        return {"success": True, "payment_response_header": payment_response_header, **resp.json()}
    else:
        return {"success": False, "error": f"Checkout failed ({resp.status_code}): {resp.text}"}


def main():
    st.set_page_config(
        page_title="TAP Agent",
        page_icon="🔐",
        layout="wide"
    )
    
    st.title("🔐 TAP Agent")
    st.markdown("Generate signatures and launch sample merchant product details")
    
    # Configuration Section
    st.header("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        agent_name = st.text_input(
            "Agent Id",
            value="1",
            help="Id of this TAP agent"
        )
        
        reference_url = st.text_input(
            "Merchant URL",
            value="http://localhost:3001/product/1",
            help="URL of the sample merchant product details page"
        )
    
    # Initialize session state with static keys
    if 'private_key' not in st.session_state:
        st.session_state.private_key = ""
    if 'public_key' not in st.session_state:
        st.session_state.public_key = ""
    if 'ed25519_private_key' not in st.session_state:
        st.session_state.ed25519_private_key = ""
    if 'ed25519_public_key' not in st.session_state:
        st.session_state.ed25519_public_key = ""
    if 'product_details' not in st.session_state:
        st.session_state.product_details = None
    if 'input_data' not in st.session_state:
        # Generate default values only once - use Ed25519 as default
        import time
        nonce = str(uuid.uuid4())
        created = int(time.time())
        expires = created + 8 * 60  # 8 minutes from now
        keyId = "primary-ed25519"  # Default to Ed25519 since it's the default algorithm
        tag = "agent-browser-auth"
        
        # Parse URL into authority and path components
        authority, path = parse_url_components(reference_url)
        
        default_input = {
            "nonce": nonce,
            "created": created,
            "expires": expires,
            "keyId": keyId,
            "tag": tag,
            "authority": authority,
            "path": path
        }
        st.session_state.input_data = json.dumps(default_input, indent=2)
    
    # Load static keys if not already loaded
    if not st.session_state.private_key or not st.session_state.public_key:
        private_key, public_key = get_static_keys()
        st.session_state.private_key = private_key
        st.session_state.public_key = public_key
    
    # Load Ed25519 keys if not already loaded
    if not st.session_state.ed25519_private_key or not st.session_state.ed25519_public_key:
        try:
            ed25519_private_key, ed25519_public_key = get_ed25519_keys_from_env()
            st.session_state.ed25519_private_key = ed25519_private_key
            st.session_state.ed25519_public_key = ed25519_public_key
        except ValueError:
            # Ed25519 keys not configured - will show error when trying to use them
            pass
    
    # Algorithm Selection
    st.header("🔐 Signature Algorithm")
    signature_algorithm = st.radio(
        "Select signature algorithm:",
        options=["ed25519", "rsa-pss-sha256"],
        index=0,  # Default to ed25519
        help="Choose the cryptographic algorithm for signature creation. Ed25519 is faster and more secure.",
        horizontal=True
    )
    
    # Show algorithm info
    if signature_algorithm == "ed25519":
        st.info("🚀 **Ed25519** - Fast, secure, and modern signature algorithm. Uses keys from environment variables.")
    else:
        st.info("🔒 **RSA-PSS-SHA256** - Traditional RSA signature with PSS padding. Uses keys from environment variables.")
    
    with col2:
        st.subheader("Input Data")
        st.caption("Input data that will be signed before sending to the sample merchant")
        st.code(st.session_state.input_data, language="json", line_numbers=False)
        
        # Reset button
        if st.button("🔄 Reset to Default JSON"):
            import time
            nonce = str(uuid.uuid4())
            created = int(time.time())
            expires = created + 8 * 60  # 8 minutes from now
            
            # Use algorithm-appropriate keyId
            if signature_algorithm == "ed25519":
                keyId = "primary-ed25519"
            else:
                keyId = "primary"
                
            tag = "agent-browser-auth"
            
            # Parse URL into authority and path components
            authority, path = parse_url_components(reference_url)

            default_input = {
                "nonce": nonce,
                "created": created,
                "expires": expires,
                "keyId": keyId,
                "tag": tag,
                "authority": authority,
                "path": path
            }
            st.session_state.input_data = json.dumps(default_input, indent=2)
            st.rerun()
    

    
    # Action Selection
    st.subheader("🎯 Action Selection")
    action_choice = st.radio(
        "Choose an action:",
        options=["Product Details", "Checkout", "x402 Checkout"],
        index=0,  # Default to Product Details
        help="Select whether to fetch product details, complete a browser checkout, or pay with x402.",
        horizontal=True
    )
    
    # Update input data function that considers action choice
    def update_input_data_with_action():
        """Update input data when signature algorithm, merchant URL, or action changes"""
        import time
        
        # Determine keyId based on signature algorithm
        if signature_algorithm == "ed25519":
            keyId = "primary-ed25519"
        else:
            keyId = "primary"
        
        # Determine tag based on action choice
        if action_choice == "Product Details":
            tag = "agent-browser-auth"
        else:  # Checkout
            tag = "agent-payer-auth"
        
        # Parse URL into authority and path components
        authority, path = parse_url_components(reference_url)
        
        # Parse current input data to preserve nonce, created, expires if they exist
        try:
            current_data = json.loads(st.session_state.input_data)
            nonce = current_data.get('nonce', str(uuid.uuid4()))
            created = current_data.get('created', int(time.time()))
            expires = current_data.get('expires', created + 8 * 60)
        except (json.JSONDecodeError, KeyError):
            # If parsing fails, use defaults
            nonce = str(uuid.uuid4())
            created = int(time.time())
            expires = created + 8 * 60
        
        # Create updated input data
        updated_input = {
            "nonce": nonce,
            "created": created,
            "expires": expires,
            "keyId": keyId,
            "tag": tag,
            "authority": authority,
            "path": path
        }
        
        return json.dumps(updated_input, indent=2)
    
    # Check if we need to update input data
    expected_input_data = update_input_data_with_action()
    if st.session_state.input_data != expected_input_data:
        # Parse both to compare just the structure, ignoring whitespace differences
        try:
            current_parsed = json.loads(st.session_state.input_data)
            expected_parsed = json.loads(expected_input_data)
            
            # Update if keyId, authority, path, or tag have changed
            if (current_parsed.get('keyId') != expected_parsed.get('keyId') or 
                current_parsed.get('authority') != expected_parsed.get('authority') or
                current_parsed.get('path') != expected_parsed.get('path') or
                current_parsed.get('tag') != expected_parsed.get('tag')):
                st.session_state.input_data = expected_input_data
                st.rerun()
        except json.JSONDecodeError:
            # If parsing fails, update with the expected data
            st.session_state.input_data = expected_input_data
            st.rerun()
    
    # Launch Section
    st.header("🚀 Launch")
    
    # Check if the required keys are available for the selected algorithm
    if signature_algorithm == "ed25519":
        if not st.session_state.ed25519_private_key:
            st.warning("Please configure Ed25519 keys in your .env file first")
            launch_disabled = True
        else:
            launch_disabled = False
    else:  # rsa-pss-sha256
        if not st.session_state.private_key:
            st.warning("Please configure RSA keys in your .env file first")
            launch_disabled = True
        else:
            launch_disabled = False
    
    # Dynamic button based on selection
    if action_choice == "Product Details":
        button_text = "📦 Fetch Product Details"
        button_help = "Create RFC 9421 signature and fetch product details from the merchant"
        tag_value = "agent-browser-auth"
    elif action_choice == "Checkout":
        button_text = "🛒 Complete Checkout"
        button_help = "Create RFC 9421 signature and complete the checkout process"
        tag_value = "agent-payer-auth"
    else:  # x402 Checkout
        button_text = "💰 Pay with USDC (x402)"
        button_help = "Pay with x402 (USDC on Solana or Base)"
        tag_value = "agent-payer-auth"

    # x402 Checkout has its own UI section
    if action_choice == "x402 Checkout":
        st.subheader("💰 x402 Checkout")
        x402_col1, x402_col2 = st.columns(2)
        with x402_col1:
            x402_product_id = st.number_input("Product ID", min_value=1, value=1, step=1)
        with x402_col2:
            x402_quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

        x402_api_url = os.getenv("CDN_PROXY_URL", "http://localhost:3001")
        st.caption(f"CDN Proxy: {x402_api_url}")

        if st.button(button_text, type="primary", help=button_help):
            with st.spinner("Processing x402 payment..."):
                try:
                    result = perform_x402_checkout(x402_api_url, x402_product_id, x402_quantity)
                    if result.get("success"):
                        st.success("🎉 x402 Checkout completed successfully!")
                        order_data = result.get("order", {})
                        if order_data:
                            st.markdown("### 📋 Order Confirmation")
                            oc1, oc2 = st.columns(2)
                            with oc1:
                                st.metric("Order Number", order_data.get("order_number", "N/A"))
                                st.metric("Total", f"${order_data.get('total_amount', 0):.2f}")
                            with oc2:
                                st.metric("Payment", result.get("payment", {}).get("method", "x402"))
                                st.metric("Network", result.get("payment", {}).get("network", "unknown"))
                        pr_header = result.get("payment_response_header", "")
                        if pr_header:
                            st.markdown("### 🧾 Payment Response Header")
                            import base64, json as _json
                            try:
                                decoded = _json.loads(base64.b64decode(pr_header))
                                st.json(decoded)
                            except Exception:
                                st.code(pr_header, language="text")
                        with st.expander("🔍 Full Response"):
                            st.json(result)
                    else:
                        st.error(f"❌ x402 Checkout failed: {result.get('error', 'Unknown error')}")
                        with st.expander("Error Details"):
                            st.json(result)
                except Exception as e:
                    st.error(f"❌ x402 Checkout error: {str(e)}")

    # Single launch button that adapts to the selected action (Product Details / Checkout)
    elif st.button(button_text, type="primary", disabled=launch_disabled, help=button_help):
        if st.session_state.private_key:
            import time
            spinner_text = f"Creating RFC 9421 signature and {'fetching product details' if action_choice == 'Product Details' else 'completing checkout'}..."
            
            with st.spinner(spinner_text):
                    # Parse current input data to get signature parameters
                # Parse current input data to get signature parameters
                try:
                    parsed_json = json.loads(st.session_state.input_data)
                    nonce = parsed_json.get('nonce', str(uuid.uuid4()))
                    created = parsed_json.get('created', int(time.time()))
                    expires = parsed_json.get('expires', created + 8 * 60)
                    tag = parsed_json.get('tag', tag_value)
                except json.JSONDecodeError:
                    st.error("Invalid JSON format in input data")
                    nonce = str(uuid.uuid4())
                    created = int(time.time())
                    expires = created + 8 * 60
                    tag = tag_value
                # Parse URL components for RFC 9421
                print(f"🔍 Attempting to parse URL: '{reference_url}'")
                authority, path = parse_url_components(reference_url)
                print(f"🔍 Parse result - Authority: '{authority}', Path: '{path}'")
                
                if authority and path:
                        # Create RFC 9421 compliant signature using selected algorithm
                        if signature_algorithm == "ed25519":
                            signature_input_header, signature_header = create_ed25519_signature(
                                private_key_pem="",  # Ed25519 function will load from environment
                                authority=authority,
                                path=path,
                                keyid="primary-ed25519",
                                nonce=nonce,
                                created=created,
                                expires=expires,
                                tag=tag
                            )
                        else:  # rsa-pss-sha256
                            signature_input_header, signature_header = create_http_message_signature(
                                private_key_pem=st.session_state.private_key,
                                authority=authority,
                                path=path,
                                keyid="primary",
                                nonce=nonce,
                                created=created,
                                expires=expires,
                                tag=tag
                            )

                        print(f"Signature Algorithm: {signature_algorithm}")
                        print(f"Signature input String:\n{signature_input_header}")
                        print(f"Signature String:\n{signature_header}")

                        if signature_input_header and signature_header:
                            # Create headers for the request
                            headers = {
                                'Signature-Input': signature_input_header,
                                'Signature': signature_header
                            }
                            
                            if action_choice == "Product Details":
                                # Fetch product details
                                if launch_with_playwright(reference_url, headers):
                                    st.success("✅ Product extraction started!")
                                    st.info("🔄 Please wait a few seconds for extraction to complete, then check the Product Details section below.")
                                    
                                    # Start checking for results
                                    import time
                                    max_wait_time = 10  # seconds
                                    check_interval = 1  # second
                                    waited = 0
                                    
                                    while waited < max_wait_time:
                                        time.sleep(check_interval)
                                        waited += check_interval
                                        
                                        global _product_extraction_results
                                        if _product_extraction_results:
                                            st.session_state.product_details = _product_extraction_results
                                            st.rerun()
                                            break
                                    
                                    # If we get here, extraction didn't complete in time
                                    if not _product_extraction_results:
                                        st.warning("⏳ Product extraction is taking longer than expected. Check the console for updates.")
                                else:
                                    st.error("❌ Failed to launch browser for product extraction")
                            else:  # Checkout
                                # Complete checkout process
                                product_url = reference_url  # Use the same reference URL for the product
                                
                                # Construct cart and checkout URLs based on merchant URL
                                from urllib.parse import urlparse
                                parsed = urlparse(reference_url)
                                base_url = f"{parsed.scheme}://{parsed.netloc}"
                                cart_url = f"{base_url}/cart"
                                checkout_url = f"{base_url}/checkout"
                                
                                print(f"🛒 Attempting checkout with RFC 9421 signature...")
                                print(f"📄 Product URL: {product_url}")
                                print(f"🛒 Cart URL: {cart_url}")
                                print(f"💳 Checkout URL: {checkout_url}")
                                
                                checkout_result = complete_checkout_with_playwright(product_url, cart_url, checkout_url, headers)
                                success, order_info = checkout_result
                                
                                if success and order_info:
                                    st.success("🎉 Checkout completed successfully!")
                                    
                                    if order_info.get('order_id'):
                                        st.markdown("### 📋 Order Confirmation")
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric("Order ID", order_info['order_id'])
                                            st.write(f"**Completed At:** {order_info.get('timestamp', 'Unknown')}")
                                        
                                        with col2:
                                            st.write(f"**Extraction Method:** {order_info.get('extraction_method', 'Unknown')}")
                                        st.write(f"**Success Page:** [View]({order_info.get('success_page_url', '#')})")
                                    
                                        # Show full order details in expander
                                        with st.expander("🔍 Full Order Details"):
                                            st.json(order_info)
                                    
                                    else:
                                        st.warning("Order was placed but order ID could not be extracted.")
                                        if order_info:
                                            with st.expander("Debug Information"):
                                                st.json(order_info)
                                else:
                                    st.error("❌ Checkout failed.")
                                    if order_info and 'error' in order_info:
                                        st.error(f"Error: {order_info['error']}")
                                        with st.expander("Error Details"):
                                            st.json(order_info)
                                    elif not success:
                                        st.error("Checkout process failed to complete successfully.")
                        else:
                            st.error("❌ Failed to create RFC 9421 signature")
                else:
                    st.error("❌ Failed to parse URL components for signature")
    
    
    # Product Details Section
    if st.session_state.product_details:
        st.header("📦 Product Details")
        
        # Clear button
        if st.button("🗑️ Clear Product Details"):
            st.session_state.product_details = None
            st.rerun()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.product_details.get('title'):
                st.subheader("📦 Product Title")
                st.write(st.session_state.product_details['title'])
            else:
                st.subheader("📦 Product Title")
                st.write("❌ Not found")
        
        with col2:
            if st.session_state.product_details.get('price'):
                st.subheader("💰 Product Price")
                st.write(st.session_state.product_details['price'])
            else:
                st.subheader("💰 Product Price")
                st.write("❌ Not found")
        
        # Additional extraction details
        with st.expander("🔍 Extraction Details"):
            extraction_time = st.session_state.product_details.get('extraction_time', 'Unknown')
            st.write(f"**Extraction Time:** {extraction_time}")
            st.write(f"**URL:** {st.session_state.product_details.get('url', 'Unknown')}")
            if st.session_state.product_details.get('extraction_log'):
                st.text_area("Extraction Log", value=st.session_state.product_details['extraction_log'], height=150)

if __name__ == "__main__":
    main()
