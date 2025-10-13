# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import base64

# Configuration
API_BASE_URL = "http://localhost:9002"

# Page configuration
st.set_page_config(
    page_title="Agent Registry Management",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

def check_api_connection():
    """Check if the Agent Registry API is accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_all_agents():
    """Fetch all agents from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/agents", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch agents: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Error fetching agents: {str(e)}")
        return []

def get_agent_by_id(agent_id):
    """Fetch a specific agent by ID"""
    try:
        response = requests.get(f"{API_BASE_URL}/agents/{agent_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            st.error(f"Failed to fetch agent: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching agent: {str(e)}")
        return None

def get_agent_key(agent_id, key_id):
    """Fetch a specific key for an agent"""
    try:
        response = requests.get(f"{API_BASE_URL}/agents/{agent_id}/keys/{key_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            st.error(f"Failed to fetch key: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching key: {str(e)}")
        return None

def add_agent_key(agent_id, key_data):
    """Add a new key to an existing agent"""
    try:
        response = requests.post(f"{API_BASE_URL}/agents/{agent_id}/keys", json=key_data, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def register_agent(agent_data):
    """Register a new agent"""
    try:
        response = requests.post(f"{API_BASE_URL}/agents/register", json=agent_data, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def update_agent(agent_id, update_data):
    """Update an agent by ID"""
    try:
        response = requests.put(f"{API_BASE_URL}/agents/{agent_id}", json=update_data, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def deactivate_agent(agent_id):
    """Deactivate an agent by ID"""
    try:
        response = requests.delete(f"{API_BASE_URL}/agents/{agent_id}", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

def create_signature(private_key_pem: str, data: str) -> str:
    """Create a signature using the private key"""
    try:
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        signature = private_key.sign(
            data.encode('utf-8'),
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

def main():
    st.title("🔐 Agent Registry Management")
    st.markdown("---")
    
    # Check API connection
    if not check_api_connection():
        st.error("❌ Cannot connect to Agent Registry API")
        st.info(f"Make sure the Agent Registry Service is running on {API_BASE_URL}")
        st.stop()
    
    st.success("✅ Connected to Agent Registry API")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["📋 View Agents", "➕ Register Agent", "✏️ Update Agent", "🔍 Agent Lookup", "🧪 Test Signature"]
    )
    
    if page == "📋 View Agents":
        view_agents_page()
    elif page == "➕ Register Agent":
        register_agent_page()
    elif page == "✏️ Update Agent":
        update_agent_page()
    elif page == "🔍 Agent Lookup":
        agent_lookup_page()
    elif page == "🧪 Test Signature":
        test_signature_page()

def view_agents_page():
    st.header("📋 Registered Agents")
    
    # Refresh button
    if st.button("🔄 Refresh"):
        st.rerun()
    
    agents = get_all_agents()
    
    if not agents:
        st.info("No agents registered yet.")
        return
    
    # Display agents in a table
    df_data = []
    for agent in agents:
        key_count = len(agent.get('keys', []))
        df_data.append({
            "ID": agent["id"],
            "Name": agent["name"],
            "Domain": agent["domain"],
            "Keys": f"{key_count} key(s)",
            "Status": "🟢 Active" if agent.get("is_active", True) else "🔴 Inactive",
            "Description": agent.get("description", "")[:50] + "..." if agent.get("description") and len(agent.get("description", "")) > 50 else agent.get("description", ""),
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)
    
    # Detailed view
    st.subheader("Agent Details")
    agent_options = [f"{agent['id']} - {agent['name']}" for agent in agents]
    selected_option = st.selectbox("Select an agent to view details:", agent_options)
    
    if selected_option:
        agent_id = selected_option.split(' - ')[0]
        # Convert to int for comparison since API returns int IDs
        try:
            agent_id_int = int(agent_id)
            selected_agent = next((agent for agent in agents if agent["id"] == agent_id_int), None)
        except ValueError:
            selected_agent = None
            
        if selected_agent:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**ID:**", selected_agent["id"])
                st.write("**Name:**", selected_agent["name"])
                st.write("**Domain:**", selected_agent["domain"])
                st.write("**Status:**", "🟢 Active" if selected_agent.get("is_active", True) else "🔴 Inactive")
                st.write("**Description:**", selected_agent.get("description", "N/A"))
                st.write("**Contact Email:**", selected_agent.get("contact_email", "N/A"))
                st.write("**Created:**", selected_agent.get("created_at", "N/A"))
            
            with col2:
                st.write("**Associated Keys:**")
                if selected_agent.get('keys'):
                    for i, key in enumerate(selected_agent['keys'], 1):
                        key_name = key.get('key_id', 'Unnamed')  # API uses 'key_id' not 'key_name'
                        with st.expander(f"Key {i}: {key_name}"):
                            st.write(f"**Key ID:** {key.get('key_id', key.get('id', 'N/A'))}")
                            st.write(f"**Algorithm:** {key.get('algorithm', 'N/A')}")
                            st.write(f"**Description:** {key.get('description', 'N/A')}")
                            st.write(f"**Status:** {'🟢 Active' if key.get('is_active') == 'true' else '🔴 Inactive'}")
                            st.write(f"**Created:** {key.get('created_at', 'N/A')}")
                            if key.get('expires_at'):
                                st.write(f"**Expires:** {key['expires_at']}")
                            st.code(key['public_key'], language="text")
                else:
                    st.info("No keys registered for this agent.")
            
            # Add key button
            if st.button("➕ Add New Key", key=f"add_key_{agent_id}"):
                st.session_state[f'show_add_key_{agent_id}'] = True
            
            # Add key form
            if st.session_state.get(f'show_add_key_{agent_id}', False):
                st.subheader("Add New Key")
                with st.form(f"add_key_form_{agent_id}"):
                    key_name = st.text_input("Key Name", placeholder="e.g., Production Key 2024")
                    algorithm = st.selectbox("Algorithm", ["RS256", "RS384", "RS512"], index=0)
                    public_key = st.text_area("Public Key (PEM format)", 
                                            placeholder="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
                                            height=150)
                    expires_at = st.date_input("Expiration Date (optional)")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submit_key = st.form_submit_button("Add Key")
                    with col2:
                        cancel_key = st.form_submit_button("Cancel")
                    
                    if submit_key and public_key:
                        key_data = {
                            "key_name": key_name,
                            "algorithm": algorithm,
                            "public_key": public_key
                        }
                        if expires_at:
                            key_data["expires_at"] = expires_at.isoformat()
                        
                        success, result = add_agent_key(agent_id, key_data)
                        if success:
                            st.success("✅ Key added successfully!")
                            st.session_state[f'show_add_key_{agent_id}'] = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to add key: {result}")
                    
                    if cancel_key:
                        st.session_state[f'show_add_key_{agent_id}'] = False
                        st.rerun()

def register_agent_page():
    st.header("➕ Register New Agent")
    
    with st.form("register_agent_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Agent Name *", placeholder="e.g., Example Directory Service")
            domain = st.text_input("Domain *", placeholder="e.g., https://directory.example.com")
            contact_email = st.text_input("Contact Email", placeholder="directory-support@example.com")
        
        with col2:
            description = st.text_area("Description", placeholder="Example payment directory service")
        
        st.subheader("Initial Key")
        st.info("Add at least one key for the agent")
        
        col3, col4 = st.columns(2)
        with col3:
            key_name = st.text_input("Key Name *", placeholder="e.g., Production Key 2024")
            algorithm = st.selectbox("Algorithm *", ["RS256", "RS384", "RS512"], index=0)
        
        with col4:
            expires_at = st.date_input("Key Expiration Date (optional)")
        
        public_key = st.text_area(
            "Public Key (PEM format) *",
            placeholder="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
            height=200
        )
        
        submitted = st.form_submit_button("🚀 Register Agent")
        
        if submitted:
            if not name or not domain or not public_key or not key_name:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            # Prepare agent data with initial key
            agent_data = {
                "name": name,
                "domain": domain,
                "description": description,
                "contact_email": contact_email,
                "initial_key": {
                    "key_name": key_name,
                    "algorithm": algorithm,
                    "public_key": public_key
                }
            }
            
            if expires_at:
                agent_data["initial_key"]["expires_at"] = expires_at.isoformat()
            
            success, result = register_agent(agent_data)
            
            if success:
                st.success("✅ Agent registered successfully!")
                st.json(result)
                st.info(f"Agent ID: {result.get('id', 'N/A')} - Save this ID for future reference!")
            else:
                st.error(f"❌ Failed to register agent: {result}")

def update_agent_page():
    st.header("✏️ Update Agent")
    
    # First, select an agent to update
    agents = get_all_agents()
    if not agents:
        st.info("No agents available to update.")
        return
    
    agent_options = [f"{agent['id']} - {agent['name']}" for agent in agents]
    selected_option = st.selectbox("Select agent to update:", agent_options)
    
    if selected_option:
        agent_id = selected_option.split(' - ')[0]
        # Convert to int for comparison since API returns int IDs
        try:
            agent_id_int = int(agent_id)
            current_agent = next((agent for agent in agents if agent["id"] == agent_id_int), None)
        except ValueError:
            current_agent = None
        
        if current_agent:
            st.subheader(f"Updating: {current_agent['name']} (ID: {current_agent['id']})")
            
            with st.form("update_agent_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Agent Name", value=current_agent["name"])
                    contact_email = st.text_input("Contact Email", value=current_agent.get("contact_email", ""))
                
                with col2:
                    description = st.text_area("Description", value=current_agent.get("description", ""))
                    domain = st.text_input("Domain", value=current_agent["domain"])
                
                submitted = st.form_submit_button("💾 Update Agent")
                
                if submitted:
                    update_data = {}
                    
                    # Only include fields that have changed
                    if name != current_agent["name"]:
                        update_data["name"] = name
                    if description != current_agent.get("description", ""):
                        update_data["description"] = description
                    if contact_email != current_agent.get("contact_email", ""):
                        update_data["contact_email"] = contact_email
                    if domain != current_agent["domain"]:
                        update_data["domain"] = domain
                    
                    if not update_data:
                        st.info("No changes detected.")
                        return
                    
                    success, result = update_agent(agent_id, update_data)
                    
                    if success:
                        st.success("✅ Agent updated successfully!")
                        st.json(result)
                    else:
                        st.error(f"❌ Failed to update agent: {result}")

def agent_lookup_page():
    st.header("🔍 Agent Lookup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Lookup by Agent ID")
        agent_id = st.text_input("Enter Agent ID:", placeholder="e.g., 1")
        
        if st.button("🔍 Lookup by ID") and agent_id:
            agent = get_agent_by_id(agent_id)
            
            if agent:
                st.success("✅ Agent found!")
                display_agent_details(agent)
            else:
                st.error("❌ Agent not found for the specified ID.")
    
    with col2:
        st.subheader("Lookup by Domain")
        domain = st.text_input("Enter agent domain:", placeholder="https://directory.example.com")
        
        if st.button("🔍 Lookup by Domain") and domain:
            # Search through all agents for matching domain
            agents = get_all_agents()
            if agents:
                matching_agent = next((a for a in agents if a['domain'] == domain), None)
                if matching_agent:
                    st.success("✅ Agent found!")
                    display_agent_details(matching_agent)
                else:
                    st.error("❌ No agent found with the specified domain.")
            else:
                st.error("❌ Failed to fetch agents.")

def display_agent_details(agent):
    """Helper function to display agent details"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**ID:**", agent["id"])
        st.write("**Name:**", agent["name"])
        st.write("**Domain:**", agent["domain"])
        st.write("**Status:**", "🟢 Active" if agent.get("is_active", True) else "🔴 Inactive")
        st.write("**Description:**", agent.get("description", "N/A"))
        st.write("**Contact Email:**", agent.get("contact_email", "N/A"))
        st.write("**Created:**", agent.get("created_at", "N/A"))
    
    with col2:
        st.write("**Associated Keys:**")
        if agent.get('keys'):
            for i, key in enumerate(agent['keys'], 1):
                key_name = key.get('key_id', 'Unnamed')  # API uses 'key_id' not 'key_name'
                with st.expander(f"Key {i}: {key_name}"):
                    st.write(f"**Key ID:** {key.get('key_id', key.get('id', 'N/A'))}")
                    st.write(f"**Algorithm:** {key.get('algorithm', 'N/A')}")
                    st.write(f"**Description:** {key.get('description', 'N/A')}")
                    st.write(f"**Status:** {'🟢 Active' if key.get('is_active') == 'true' else '🔴 Inactive'}")
                    st.write(f"**Created:** {key.get('created_at', 'N/A')}")
                    if key.get('expires_at'):
                        st.write(f"**Expires:** {key['expires_at']}")
                    st.code(key['public_key'], language="text")
                    # Copy button for public key
                    if st.button(f"📋 Copy Key {i}", key=f"copy_key_{key.get('key_id', key.get('id', i))}"):
                        st.code(key['public_key'])
        else:
            st.info("No keys registered for this agent.")

def test_signature_page():
    st.header("🧪 Test Signature Generation")
    st.info("This page helps you test signature generation with private keys for registered agents.")
    
    # Select agent
    agents = get_all_agents()
    if not agents:
        st.info("No agents available for testing.")
        return
    
    agent_options = [f"{agent['id']} - {agent['name']}" for agent in agents]
    selected_option = st.selectbox("Select agent for testing:", agent_options)
    
    if not selected_option:
        return
    
    agent_id = selected_option.split(' - ')[0]
    # Convert to int for comparison since API returns int IDs
    try:
        agent_id_int = int(agent_id)
        selected_agent = next((agent for agent in agents if agent["id"] == agent_id_int), None)
    except ValueError:
        selected_agent = None
    
    if not selected_agent:
        st.error("Selected agent not found.")
        return
    
    st.subheader(f"Testing with: {selected_agent['name']}")
    
    # Select key from agent's keys
    if not selected_agent.get('keys'):
        st.warning("This agent has no keys registered. Please add a key first.")
        return
    
    key_options = [f"{key.get('key_id', key.get('id', 'unknown'))} - {key.get('key_id', 'Unnamed')} ({key.get('algorithm', 'Unknown')})" 
                   for key in selected_agent['keys']]
    selected_key_option = st.selectbox("Select key to test with:", key_options)
    
    if not selected_key_option:
        return
    
    key_id = selected_key_option.split(' - ')[0]
    selected_key = next((key for key in selected_agent['keys'] if key.get("key_id", key.get("id")) == key_id), None)
    
    if not selected_key:
        st.error("Selected key not found.")
        return
    
    st.write(f"**Selected Key:** {selected_key.get('key_id', 'Unnamed')}")
    st.write(f"**Algorithm:** {selected_key.get('algorithm', 'Unknown')}")
    st.write(f"**Description:** {selected_key.get('description', 'N/A')}")
    
    # Show public key
    with st.expander("View Public Key"):
        st.code(selected_key['public_key'], language="text")
    
    # Test data
    st.subheader("Test Data")
    test_data = st.text_area(
        "Data to sign (JSON format):",
        value='{"merchant_id": "test123", "timestamp": "' + datetime.now().isoformat() + '"}',
        height=100
    )
    
    # Convert to base64
    if test_data:
        try:
            test_data_base64 = base64.b64encode(test_data.encode('utf-8')).decode('utf-8')
            st.write("**Base64 encoded data:**")
            st.code(test_data_base64)
        except Exception as e:
            st.error(f"Error encoding data: {e}")
            return
    
    # Private key input
    private_key = st.text_area(
        "Private Key (PEM format) - For testing only:",
        placeholder="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        height=200,
        help="This should be the private key corresponding to the selected public key"
    )
    
    if st.button("🔐 Generate Signature") and private_key and test_data:
        try:
            signature = create_signature(private_key, test_data_base64)
            if signature:
                st.success("✅ Signature generated successfully!")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Signature (base64):**")
                    st.code(signature)
                
                with col2:
                    st.write("**Headers for CDN test:**")
                    headers = {
                        "signature-agent-id": agent_id,
                        "signature-key-id": key_id,
                        "signature-input": test_data_base64,
                        "signature": signature
                    }
                    st.code(json.dumps(headers, indent=2))
                
                # Test command
                st.write("**cURL command for testing:**")
                curl_cmd = f'''curl -X GET "http://localhost:3001/" \\
  -H "signature-agent-id: {agent_id}" \\
  -H "signature-key-id: {key_id}" \\
  -H "signature-input: {test_data_base64}" \\
  -H "signature: {signature}"'''
                st.code(curl_cmd, language="bash")
            
        except Exception as e:
            st.error(f"Error generating signature: {e}")

if __name__ == "__main__":
    main()
