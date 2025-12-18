import streamlit as st
import uuid
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from our new modules
from crypto import (
    get_ed25519_keys, 
    get_rsa_keys, 
    create_http_message_signature, 
    create_ed25519_signature, 
    parse_url_components
)
from agent import (
    launch_with_playwright, 
    complete_checkout_with_playwright, 
    get_product_extraction_results
)

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
    if 'rsa_private_key' not in st.session_state:
        st.session_state.rsa_private_key = ""
    if 'rsa_public_key' not in st.session_state:
        st.session_state.rsa_public_key = ""
    if 'ed25519_private_key' not in st.session_state:
        st.session_state.ed25519_private_key = ""
    if 'ed25519_public_key' not in st.session_state:
        st.session_state.ed25519_public_key = ""
    if 'product_details' not in st.session_state:
        st.session_state.product_details = None
    if 'input_data' not in st.session_state:
        # Generate default values only once - use Ed25519 as default
        nonce = str(uuid.uuid4())
        created = int(time.time())
        expires = created + 8 * 60  # 8 minutes from now
        keyId = "primary-ed25519"
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
    if not st.session_state.rsa_private_key or not st.session_state.rsa_public_key:
        try:
            private_key, public_key = get_rsa_keys()
            st.session_state.rsa_private_key = private_key
            st.session_state.rsa_public_key = public_key
        except Exception as e:
            st.warning(f"Could not load RSA keys: {e}")
    
    # Load Ed25519 keys if not already loaded
    if not st.session_state.ed25519_private_key or not st.session_state.ed25519_public_key:
        try:
            ed25519_private_key, ed25519_public_key = get_ed25519_keys()
            st.session_state.ed25519_private_key = ed25519_private_key
            st.session_state.ed25519_public_key = ed25519_public_key
        except Exception:
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
            nonce = str(uuid.uuid4())
            created = int(time.time())
            expires = created + 8 * 60
            
            if signature_algorithm == "ed25519":
                keyId = "primary-ed25519"
            else:
                keyId = "primary"
                
            tag = "agent-browser-auth"
            authority, path = parse_url_components(reference_url)

            default_input = {
                "nonce": nonce, "created": created, "expires": expires,
                "keyId": keyId, "tag": tag, "authority": authority, "path": path
            }
            st.session_state.input_data = json.dumps(default_input, indent=2)
            st.rerun()
    
    # Action Selection
    st.subheader("🎯 Action Selection")
    action_choice = st.radio(
        "Choose an action:",
        options=["Product Details", "Checkout"],
        index=0,
        help="Select whether to fetch product details or complete a checkout process.",
        horizontal=True
    )
    
    # Update input data function
    def update_input_data_with_action():
        if signature_algorithm == "ed25519": keyId = "primary-ed25519"
        else: keyId = "primary"
        
        tag = "agent-browser-auth" if action_choice == "Product Details" else "agent-payer-auth"
        authority, path = parse_url_components(reference_url)
        
        try:
            current_data = json.loads(st.session_state.input_data)
            nonce = current_data.get('nonce', str(uuid.uuid4()))
            created = current_data.get('created', int(time.time()))
            expires = current_data.get('expires', created + 8 * 60)
        except:
            nonce = str(uuid.uuid4())
            created = int(time.time())
            expires = created + 8 * 60
        
        updated_input = {
            "nonce": nonce, "created": created, "expires": expires,
            "keyId": keyId, "tag": tag, "authority": authority, "path": path
        }
        return json.dumps(updated_input, indent=2)
    
    expected_input_data = update_input_data_with_action()
    if st.session_state.input_data != expected_input_data:
        try:
            current_parsed = json.loads(st.session_state.input_data)
            expected_parsed = json.loads(expected_input_data)
            if (current_parsed.get('keyId') != expected_parsed.get('keyId') or 
                current_parsed.get('authority') != expected_parsed.get('authority') or
                current_parsed.get('path') != expected_parsed.get('path') or
                current_parsed.get('tag') != expected_parsed.get('tag')):
                st.session_state.input_data = expected_input_data
                st.rerun()
        except:
            st.session_state.input_data = expected_input_data
            st.rerun()
    
    # Launch Section
    st.header("🚀 Launch")
    
    launch_disabled = False
    if signature_algorithm == "ed25519":
        if not st.session_state.ed25519_private_key:
            st.warning("Please configure Ed25519 keys in your environment first")
            launch_disabled = True
    else:
        if not st.session_state.rsa_private_key:
            st.warning("Please configure RSA keys in your environment first")
            launch_disabled = True
    
    button_text = "📦 Fetch Product Details" if action_choice == "Product Details" else "🛒 Complete Checkout"
    tag_value = "agent-browser-auth" if action_choice == "Product Details" else "agent-payer-auth"
    
    if st.button(button_text, type="primary", disabled=launch_disabled):
        with st.spinner(f"Processing {action_choice}..."):
            try:
                parsed_json = json.loads(st.session_state.input_data)
                nonce = parsed_json.get('nonce', str(uuid.uuid4()))
                created = parsed_json.get('created', int(time.time()))
                expires = parsed_json.get('expires', created + 8 * 60)
                tag = parsed_json.get('tag', tag_value)
            except:
                nonce, created, expires, tag = str(uuid.uuid4()), int(time.time()), int(time.time()) + 480, tag_value
            
            authority, path = parse_url_components(reference_url)
            
            if authority and path:
                if signature_algorithm == "ed25519":
                    sig_in, sig = create_ed25519_signature(
                        st.session_state.ed25519_private_key, authority, path, "primary-ed25519", nonce, created, expires, tag
                    )
                else:
                    sig_in, sig = create_http_message_signature(
                        st.session_state.rsa_private_key, authority, path, "primary", nonce, created, expires, tag
                    )

                if sig_in and sig:
                    headers = {'Signature-Input': sig_in, 'Signature': sig}
                    
                    if action_choice == "Product Details":
                        if launch_with_playwright(reference_url, headers):
                            st.success("✅ Product extraction started!")
                            # Polling for results
                            for _ in range(10):
                                time.sleep(1)
                                results = get_product_extraction_results()
                                if results:
                                    st.session_state.product_details = results
                                    st.rerun()
                        else:
                            st.error("❌ Failed to launch browser")
                    else:  # Checkout
                        parsed = parse_url_components(reference_url)
                        # We need base URL for cart/checkout
                        from urllib.parse import urlparse
                        p = urlparse(reference_url)
                        base = f"{p.scheme}://{p.netloc}"
                        success, order_info = complete_checkout_with_playwright(reference_url, f"{base}/cart", f"{base}/checkout", headers)
                        
                        if success:
                            st.success("🎉 Checkout completed!")
                            if order_info.get('order_id'):
                                st.metric("Order ID", order_info['order_id'])
                                with st.expander("🔍 Details"): st.json(order_info)
                        else:
                            st.error(f"❌ Checkout failed: {order_info.get('error', 'Unknown error')}")
                else:
                    st.error("❌ Failed to create signature")
            else:
                st.error("❌ Failed to parse URL")
    
    # Product Details Section
    if st.session_state.product_details:
        st.header("📦 Product Details")
        if st.button("🗑️ Clear Details"):
            st.session_state.product_details = None
            st.rerun()
        
        c1, c2 = st.columns(2)
        with c1: st.subheader("Title"); st.write(st.session_state.product_details.get('title', 'Not found'))
        with c2: st.subheader("Price"); st.write(st.session_state.product_details.get('price', 'Not found'))
        with st.expander("🔍 Log"): st.text(st.session_state.product_details.get('extraction_log', ''))

if __name__ == "__main__":
    main()
