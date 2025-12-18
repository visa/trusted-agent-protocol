import time
import threading
import datetime
import re
import streamlit as st
from typing import Tuple, Dict, Any, Optional

# Global variables to store results across threads
_product_extraction_results = None
_order_completion_results = None

def get_product_extraction_results():
    global _product_extraction_results
    return _product_extraction_results

def get_order_completion_results():
    global _order_completion_results
    return _order_completion_results

def set_product_extraction_results(results):
    global _product_extraction_results
    _product_extraction_results = results

def set_order_completion_results(results):
    global _order_completion_results
    _order_completion_results = results

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
                    if 'api' in request.url.lower() or request.method == 'OPTIONS':
                        print(f"API Request: {request.method} {request.url}")
                
                def handle_response(response):
                    if response.status >= 400:
                        print(f"Failed Request: {response.status} {response.request.method} {response.url}")
                
                page.on('request', handle_request)
                page.on('response', handle_response)
                
                def handle_console(msg):
                    if msg.type == 'error':
                        print(f"Console Error: {msg.text}")
                
                page.on('console', handle_console)
                
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to: {url}")
                    time.sleep(3)
                    
                    product_info = {}
                    
                    # Common selectors
                    title_selectors = ['h1', '[data-testid="product-title"]', '.product-title', '.product-name', '[class*="title"]', '[class*="product"]', 'title']
                    price_selectors = ['[data-testid="price"]', '.price', '.product-price', '[class*="price"]', '[class*="cost"]', '[class*="amount"]', 'span:has-text("$")', 'span:has-text("€")', 'span:has-text("£")']
                    
                    for selector in title_selectors:
                        try:
                            title_element = page.query_selector(selector)
                            if title_element:
                                title_text = title_element.inner_text().strip()
                                if title_text and len(title_text) > 3:
                                    product_info['title'] = title_text
                                    break
                        except: continue
                    
                    for selector in price_selectors:
                        try:
                            price_element = page.query_selector(selector)
                            if price_element:
                                price_text = price_element.inner_text().strip()
                                if price_text and (any(char in price_text for char in ['$', '€', '£', '¥']) or any(char.isdigit() for char in price_text)):
                                    product_info['price'] = price_text
                                    break
                        except: continue
                    
                    if not product_info.get('title'):
                        try: product_info['title'] = page.title()
                        except: pass
                    
                    if not product_info.get('price'):
                        try:
                            all_text = page.content()
                            price_pattern = r'[\$€£¥]\s*\d+(?:[.,]\d{2})?|\d+(?:[.,]\d{2})?\s*[\$€£¥]'
                            prices = re.findall(price_pattern, all_text)
                            if prices: product_info['price'] = prices[0]
                        except: pass
                    
                    extraction_log = ["🛍️  PRODUCT EXTRACTION RESULTS", "="*50]
                    extraction_log.append(f"📦 Title: {product_info.get('title', 'Not found')}")
                    extraction_log.append(f"💰 Price: {product_info.get('price', 'Not found')}")
                    extraction_log.append("="*50)
                    
                    set_product_extraction_results({
                        'title': product_info.get('title'),
                        'price': product_info.get('price'),
                        'url': url,
                        'extraction_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'extraction_log': '\n'.join(extraction_log)
                    })
                    
                    print("\n" + '\n'.join(extraction_log))
                    time.sleep(3)
                except Exception as e:
                    print(f"❌ Navigation or extraction error: {e}")
                finally:
                    try: browser.close()
                    except: pass
        
        browser_thread = threading.Thread(target=run_browser, daemon=True)
        browser_thread.start()
        time.sleep(2)
        st.success("✅ Browser launched with headers!")
        return True
    except Exception as e:
        st.error(f"Error launching browser: {str(e)}")
        return False

def complete_checkout_with_playwright(product_url: str, cart_url: str, checkout_url: str, headers: dict = None) -> Tuple[bool, dict]:
    """Complete full checkout process"""
    try:
        from playwright.sync_api import sync_playwright
        import threading
        import time
        import re
        
        set_order_completion_results(None)
        if headers is None: headers = {}
        
        def run_full_checkout():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False, args=['--disable-web-security', '--disable-features=VizDisplayCompositor', '--ignore-certificate-errors', '--ignore-ssl-errors'])
                context = browser.new_context(extra_http_headers=headers, ignore_https_errors=True, viewport={'width': 1280, 'height': 720})
                page = context.new_page()
                
                try:
                    # STEP 1: Product Page
                    print(f"🛍️  STEP 1: {product_url}")
                    page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
                    time.sleep(3)
                    
                    # STEP 2: Add to Cart
                    print(f"🛒 STEP 2: Add to Cart")
                    add_to_cart_selectors = ['button:has-text("Add to Cart")', 'button:has-text("Add To Cart")', '[data-testid="add-to-cart"]', '.add-cart', '#addToCart']
                    cart_added = False
                    for selector in add_to_cart_selectors:
                        try:
                            btn = page.query_selector(selector)
                            if btn and btn.is_visible():
                                btn.click()
                                cart_added = True
                                break
                        except: continue
                    
                    if not cart_added:
                        try:
                            btns = page.query_selector_all('button')
                            for btn in btns[:10]:
                                if any(phrase in btn.inner_text().lower() for phrase in ['add', 'cart', 'buy']):
                                    btn.click()
                                    cart_added = True
                                    break
                        except: pass
                    
                    time.sleep(2)
                    
                    # STEP 3: Cart Page
                    print(f"🛒 STEP 3: {cart_url}")
                    page.goto(cart_url, wait_until='domcontentloaded', timeout=30000)
                    time.sleep(3)
                    
                    # STEP 4: Proceed to Checkout
                    print(f"➡️ STEP 4: Proceed to Checkout")
                    proceed_selectors = ['button:has-text("Proceed to Checkout")', 'button:has-text("Checkout")', 'a:has-text("Checkout")', '[data-testid="checkout"]', '#checkout']
                    proceeded = False
                    for selector in proceed_selectors:
                        try:
                            btn = page.query_selector(selector)
                            if btn and btn.is_visible():
                                btn.click()
                                proceeded = True
                                break
                        except: continue
                    
                    if not proceeded:
                        page.goto(checkout_url, wait_until='domcontentloaded', timeout=30000)
                    
                    time.sleep(3)
                    
                    # STEP 5: Form
                    print(f"📝 STEP 5: Fill Form")
                    checkout_info = {
                        'email': 'john.doe@example.com', 'phone': '+1-555-0123', 'firstName': 'John', 'lastName': 'Doe',
                        'company': 'Example Company', 'address1': '123 Main St', 'city': 'New York', 'state': 'NY', 'zipCode': '10001',
                        'cardNumber': '4111111111111111', 'expiryDate': '12/25', 'cvv': '123', 'nameOnCard': 'John Doe'
                    }
                    
                    for field, value in checkout_info.items():
                        try:
                            elem = page.query_selector(f'[name="{field}"], #{field}, [placeholder*="{field}"]')
                            if elem and elem.is_visible(): elem.fill(value)
                        except: continue
                    
                    time.sleep(2)
                    
                    # Submit
                    submit_selectors = ['button[type="submit"]', 'button:has-text("Complete Order")', 'button:has-text("Place Order")']
                    submitted = False
                    for selector in submit_selectors:
                        try:
                            btn = page.query_selector(selector)
                            if btn and btn.is_visible():
                                btn.click()
                                submitted = True
                                break
                        except: continue
                    
                    if submitted:
                        print("✅ Submitted")
                        success_reached = False
                        for _ in range(15):
                            if any(p in page.url.lower() for p in ['success', 'confirmation', 'thank-you']):
                                success_reached = True; break
                            time.sleep(1)
                        
                        order_id = None
                        if success_reached:
                            time.sleep(2)
                            match = re.search(r'Order\s*#\s*([A-Z0-9-]+)', page.content(), re.IGNORECASE)
                            if match: order_id = match.group(1)
                        
                        set_order_completion_results({
                            'order_id': order_id,
                            'success_page_url': page.url,
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    time.sleep(3)
                except Exception as e:
                    print(f"❌ Checkout error: {e}")
                finally:
                    browser.close()
        
        t = threading.Thread(target=run_full_checkout, daemon=True)
        t.start()
        t.join(timeout=120)
        
        res = get_order_completion_results()
        if res: return True, res
        return False, {'error': 'Timed out'}
    except Exception as e:
        return False, {'error': str(e)}
