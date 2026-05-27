#Setups the Trusted Agent Protocol application
#Works only on macOS

############################################################
# Global Variables / Utils
############################################################

PROJECT_DIR=$(pwd)
OPENED_WINDOWS=()

get_debug() {
    read -p "Debug mode? (y/n): " debug
    if [ "$debug" = "y" ]; then
        echo "DEBUG=true"
    else
        echo "DEBUG=false"
    fi
}

# Function to open a new terminal tab and run a command
run_in_tab() {
  local tab_name=$1
  local dir=$2
  local cmd=$3
  local full_cmd="cd \"$PROJECT_DIR/$dir\" && printf '\\033]0;%s\\007' \"$tab_name\" && $cmd"

  echo "Starting $tab_name..."
  
  local window_id
  window_id=$(osascript - "$full_cmd" <<'EOF'
    on run argv
    tell application "Terminal"
      activate
      tell application "System Events" to keystroke "t" using command down
      delay 0.5
      do script (item 1 of argv) in front window
      return id of front window
    end tell
    end run
EOF
  )

  if [ -n "$window_id" ]; then
    local found=0
    for wid in "${OPENED_WINDOWS[@]}"; do
      [ "$wid" = "$window_id" ] && found=1 && break
    done
    [ "$found" -eq 0 ] && OPENED_WINDOWS+=("$window_id")
  fi
}

cleanup() {
  echo ""
  echo "Shutting down all services..."
  for wid in "${OPENED_WINDOWS[@]}"; do
    osascript -e "tell application \"Terminal\"" -e "try" -e "close (every window whose id is $wid)" -e "end try" -e "end tell" 2>/dev/null || true
  done
  echo "All service windows closed."
}

trap cleanup EXIT INT TERM

start_app() {
  local tab_name=$1
  local dir=$2
  local cmd=$3

  if [ ! -d "$PROJECT_DIR/$dir" ]; then
    echo "Failed to start $tab_name: directory not found: $PROJECT_DIR/$dir"
    return 1
  fi

  if run_in_tab "$tab_name" "$dir" "$cmd"; then
    echo "Started $tab_name"
    return 0
  else
    echo "Failed to start $tab_name"
    return 1
  fi
}

############################################################
# Setup
############################################################

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found. Install it first, then rerun setup."
  exit 1
fi

if [ ! -d ".venv" ]; then
  uv venv .venv --python 3.12 || {
    echo "Failed to create Python 3.12 virtual environment with uv. Aborting setup."
    exit 1
  }
else
  echo "Using existing .venv"
fi

source .venv/bin/activate
uv pip install -r requirements.txt || {
  echo "Failed to install Python dependencies. Aborting setup."
  exit 1
}

#setup environment in agent-registry

cd agent-registry

get_debug

cat > .env << EOF
# Agent Registry Environment Variables

# Database Configuration
DATABASE_URL=sqlite:///./agent_registry.db

# Server Configuration
HOST=0.0.0.0
PORT=8001

# Debug Configuration
$(get_debug)
EOF 

../.venv/bin/python populate_sample_data.py

#setup environment in cdn-proxy

cd ../cdn-proxy

cat > .env << EOF
# CDN Proxy Environment Variables

# Server Configuration
PORT=3001

# Merchant API Configuration
MERCHANT_API_URL=http://localhost:8000

# Debug Configuration
$(get_debug)
EOF

#setup environment in merchant-backend

cd ../merchant-backend

get_debug

cat > .env << EOF
# Merchant Backend Environment Variables

# Server Configuration
PORT=8000

# Database Configuration
DATABASE_URL=sqlite:///./merchant_backend.db

# Debug Configuration
$(get_debug)
EOF

../.venv/bin/python create_sample_data.py

#setup environment in merchant-frontend

cd ../merchant-frontend

cat > .env << EOF
# React Frontend Environment Variables

# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_URL=/api

# CDN Configuration
VITE_CDN_PROXY_URL=http://localhost:3001

# Application Configuration
VITE_APP_NAME=Merchant Frontend
VITE_APP_VERSION=0.1.0

# Debug Configuration
VITE_DEBUG_MODE=$(get_debug)
EOF

#setup envioronment in tap-agent

cd ../tap-agent

#RSA Key Generation

openssl genrsa -out rsa_private_key.pem 2048
openssl rsa -in rsa_private_key.pem -pubout -out rsa_public_key.pem

RSA_PRIVATE_KEY=$(< rsa_private_key.pem)
RSA_PUBLIC_KEY=$(< rsa_public_key.pem)
RSA_PRIVATE_KEY_ENV=$(awk '{printf "%s\\n", $0}' rsa_private_key.pem)
RSA_PUBLIC_KEY_ENV=$(awk '{printf "%s\\n", $0}' rsa_public_key.pem)

echo "RSA Private Key: $RSA_PRIVATE_KEY"
echo "RSA Public Key: $RSA_PUBLIC_KEY"

#Ed25519 Key Generation

openssl genpkey -algorithm Ed25519 -out ed25519_private.pem
openssl pkey -in ed25519_private.pem -pubout -out ed25519_public.pem

ED25519_PRIVATE_KEY=$(base64 -b 0 -i ed25519_private.pem)
ED25519_PUBLIC_KEY=$(base64 -b 0 -i ed25519_public.pem)

echo "Ed25519 Private Key: $ED25519_PRIVATE_KEY"
echo "Ed25519 Public Key: $ED25519_PUBLIC_KEY"

cat > .env << EOF
# TAP Agent Environment Variables

# RSA Keys
RSA_PRIVATE_KEY="$RSA_PRIVATE_KEY_ENV"
RSA_PUBLIC_KEY="$RSA_PUBLIC_KEY_ENV"

# Ed25519 Keys
ED25519_PRIVATE_KEY="$ED25519_PRIVATE_KEY"
ED25519_PUBLIC_KEY="$ED25519_PUBLIC_KEY"

# Debug Configuration
$(get_debug)
EOF

rm rsa_private_key.pem rsa_public_key.pem ed25519_private.pem ed25519_public.pem

#starting the application

STARTUP_FAILED=0

start_app "agent-registry" "agent-registry" "source ../.venv/bin/activate && python3 main.py" || STARTUP_FAILED=1
start_app "cdn-proxy" "cdn-proxy" "npm install && npm start" || STARTUP_FAILED=1
start_app "merchant-backend" "merchant-backend" "source ../.venv/bin/activate && python3 -m uvicorn app.main:app --reload --port 8000" || STARTUP_FAILED=1
start_app "merchant-frontend" "merchant-frontend" "npm install && npm start" || STARTUP_FAILED=1
start_app "tap-agent" "tap-agent" "source ../.venv/bin/activate && playwright install && streamlit run agent_app.py --server.runOnSave true" || STARTUP_FAILED=1

if [ "$STARTUP_FAILED" -eq 0 ]; then
  echo "All applications started successfully!"
  echo "You can now access the applications at the following URLs:"
  echo "  - Agent Registry: http://localhost:8001"
  echo "  - CDN Proxy: http://localhost:3001"
  echo "  - Merchant Backend: http://localhost:8000"
  echo "  - Merchant Frontend: http://localhost:3000"
  echo "  - TAP Agent: http://localhost:8501"
  echo ""
  echo "Press Ctrl+C to stop all services and close terminal windows."
  while true; do sleep 1; done
else
  echo "One or more applications failed to start. Check the messages above."
  exit 1
fi
