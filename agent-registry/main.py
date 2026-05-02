# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends

# Load environment variables
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import uvicorn

from database import get_db, init_db
from models import Agent, AgentKey
from schemas import (AgentCreate, AgentUpdate, AgentResponse, AgentPublicInfo,
                     AgentKeyCreate, AgentKeyUpdate, AgentKeyResponse, Message)
from did_resolver import (
    DIDResolutionError,
    DIDResolverNotRegistered,
    DIDResolverRegistry,
    TenzroDIDResolver,
    WebDIDResolver,
)

app = FastAPI(
    title="Agent Registry Service",
    description="Registration and lookup service for payment directory agents",
    version="1.0.0"
)

# Enable CORS for all origins (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# DID resolver registry (additive — only used when key_type == 'did')
# ---------------------------------------------------------------------------

#: Process-wide resolver registry. Operators register DID methods explicitly
#: at startup; there is no implicit method list. ``did:web:`` is always
#: registered (W3C standard, no third-party trust assumption beyond HTTPS).
#: ``did:tenzro:`` is opt-in via env var ``TAP_ENABLE_DID_TENZRO=1``.
did_resolvers: DIDResolverRegistry = DIDResolverRegistry()


def _resolve_did_key(key: "AgentKey") -> dict:
    """
    Resolve a DID-keyed AgentKey row into the same response shape this
    file already returns for PEM rows. Pure projection — caller decides
    error mapping.
    """
    try:
        resolved = did_resolvers.resolve(key.key_id, method_hint=key.did_method)
    except DIDResolverNotRegistered as exc:
        # No resolver for this method on this deployment — operator config
        # gap, not a client error.
        raise HTTPException(status_code=501, detail=str(exc))
    except DIDResolutionError as exc:
        # Document missing or malformed — surface as 404 so clients can
        # distinguish from a registry-level outage.
        raise HTTPException(status_code=404, detail=f"DID resolution failed: {exc}")

    out = {
        "key_id": key.key_id,
        "is_active": key.is_active,
        "public_key": resolved.classical_pem,
        "algorithm": resolved.algorithm,
        "description": key.description,
        "key_type": "did",
        "did_method": key.did_method,
    }
    if resolved.pq_public_key_bytes is not None:
        import base64 as _b64
        out["pq_public_key"] = _b64.b64encode(resolved.pq_public_key_bytes).decode("ascii")
    return out


@app.on_event("startup")
async def startup_event():
    """Initialize database and DID resolvers on startup."""
    init_db()
    # did:web is registered unconditionally — pure W3C standard, no
    # third-party trust assumption beyond HTTPS.
    did_resolvers.register(WebDIDResolver())
    if os.getenv("TAP_ENABLE_DID_TENZRO", "0") in ("1", "true", "True"):
        rpc_url = os.getenv("TAP_TENZRO_RPC_URL", TenzroDIDResolver.DEFAULT_RPC_URL)
        did_resolvers.register(TenzroDIDResolver(rpc_url=rpc_url))
        print(f"🔗 did:tenzro: resolver enabled (rpc={rpc_url})")
    print("🏁 Agent Registry Service started successfully")

@app.get("/", response_model=Message)
async def root():
    """Health check endpoint"""
    return {"message": "Agent Registry Service is running"}

@app.post("/agents/register", response_model=AgentResponse)
async def register_agent(agent: AgentCreate, db: Session = Depends(get_db)):
    """
    Register a new agent or update existing agent for the domain
    """
    try:
        # Check if agent with domain already exists
        existing_agent = db.query(Agent).filter(Agent.domain == agent.domain).first()
        
        if existing_agent:
            # Update existing agent
            for field, value in agent.dict(exclude={'keys'}).items():
                if hasattr(existing_agent, field):
                    setattr(existing_agent, field, value)
            
            # Handle keys separately
            if agent.keys:
                for key_data in agent.keys:
                    # Check if key_id already exists for this agent
                    existing_key = db.query(AgentKey).filter(
                        AgentKey.agent_id == existing_agent.id,
                        AgentKey.key_id == key_data.key_id
                    ).first()
                    
                    if existing_key:
                        # Update existing key
                        for field, value in key_data.dict().items():
                            setattr(existing_key, field, value)
                    else:
                        # Create new key
                        new_key = AgentKey(agent_id=existing_agent.id, **key_data.dict())
                        db.add(new_key)
            
            db.commit()
            db.refresh(existing_agent)
            
            print(f"✅ Updated agent registration for domain: {agent.domain}")
            return {
                "success": True,
                "message": f"Agent registration updated for domain: {agent.domain}",
                "agent": existing_agent
            }
        else:
            # Create new agent
            agent_dict = agent.dict(exclude={'keys'})
            new_agent = Agent(**agent_dict)
            db.add(new_agent)
            db.flush()  # Get the agent ID
            
            # Add keys
            if agent.keys:
                for key_data in agent.keys:
                    new_key = AgentKey(agent_id=new_agent.id, **key_data.dict())
                    db.add(new_key)
            
            db.commit()
            db.refresh(new_agent)
            
            print(f"✅ New agent registered for domain: {agent.domain}, ID: {new_agent.id}")
            return {
                "success": True,
                "message": f"Agent successfully registered for domain: {agent.domain}, ID: {new_agent.id}",
                "agent": new_agent
            }
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error registering agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to register agent: {str(e)}")

@app.get("/agents/{agent_id}", response_model=AgentPublicInfo)
async def get_agent_by_id(agent_id: int, db: Session = Depends(get_db)):
    """
    Get agent information by agent ID
    """
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            print(f"❌ Agent not found for ID: {agent_id}")
            raise HTTPException(status_code=404, detail=f"Agent not found for ID: {agent_id}")
        
        if agent.is_active != "true":
            print(f"❌ Agent inactive for ID: {agent_id}")
            raise HTTPException(status_code=404, detail=f"Agent is inactive for ID: {agent_id}")
        
        print(f"✅ Retrieved agent info for ID: {agent_id}")
        return AgentPublicInfo.model_validate(agent)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve agent: {str(e)}")

@app.get("/agents/{agent_id}/keys/{key_id}")
async def get_agent_key(agent_id: int, key_id: str, db: Session = Depends(get_db)):
    """
    Get specific key for an agent by agent ID and key ID
    """
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found for ID: {agent_id}")
        
        if agent.is_active != "true":
            raise HTTPException(status_code=404, detail=f"Agent is inactive for ID: {agent_id}")
        
        key = db.query(AgentKey).filter(
            AgentKey.agent_id == agent_id,
            AgentKey.key_id == key_id
        ).first()
        
        if not key:
            raise HTTPException(status_code=404, detail=f"Key '{key_id}' not found for agent {agent_id}")
        
        if key.is_active != "true":
            raise HTTPException(status_code=404, detail=f"Key '{key_id}' is inactive for agent {agent_id}")

        # DID-keyed rows: resolve the DID Document into the same response
        # shape the PEM path returns. PEM rows are handled by the original
        # branch below — unchanged.
        if getattr(key, "key_type", "pem") == "did" or (
            hasattr(key, "key_type") and getattr(key.key_type, "value", None) == "did"
        ):
            resolved = _resolve_did_key(key)
            print(f"✅ Resolved DID key '{key_id}' for agent ID: {agent_id}")
            return {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "agent_domain": agent.domain,
                **resolved,
            }

        print(f"✅ Retrieved key '{key_id}' for agent ID: {agent_id}")
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "agent_domain": agent.domain,
            "key_id": key_id,
            "is_active": key.is_active,
            "public_key": key.public_key,
            "algorithm": key.algorithm,
            "description": key.description,
            "key_type": "pem",
            "pq_public_key": getattr(key, "pq_public_key", None),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving agent key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve agent key: {str(e)}")

@app.post("/agents/{agent_id}/keys", response_model=AgentKeyResponse)
async def add_agent_key(agent_id: int, key: AgentKeyCreate, db: Session = Depends(get_db)):
    """
    Add a new key to an existing agent
    """
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found for ID: {agent_id}")
        
        # Check if key_id already exists for this agent
        existing_key = db.query(AgentKey).filter(
            AgentKey.agent_id == agent_id,
            AgentKey.key_id == key.key_id
        ).first()
        
        if existing_key:
            raise HTTPException(status_code=400, detail=f"Key '{key.key_id}' already exists for agent {agent_id}")
        
        # Create new key
        new_key = AgentKey(agent_id=agent_id, **key.dict())
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        print(f"✅ Added key '{key.key_id}' to agent ID: {agent_id}")
        return {
            "success": True,
            "message": f"Key '{key.key_id}' added to agent {agent_id}",
            "key": new_key
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error adding agent key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add agent key: {str(e)}")

@app.get("/keys/{key_id}")
async def get_key_by_id(key_id: str, db: Session = Depends(get_db)):
    """
    Get key information by key ID only (without requiring agent ID)
    """
    try:
        # Find the key directly by key_id
        key = db.query(AgentKey).filter(AgentKey.key_id == key_id).first()
        
        if not key:
            print(f"❌ Key not found for ID: {key_id}")
            raise HTTPException(status_code=404, detail=f"Key not found for ID: {key_id}")
        
        # Check if key is active
        if key.is_active != "true":
            print(f"❌ Key inactive for ID: {key_id}")
            raise HTTPException(status_code=404, detail=f"Key is inactive for ID: {key_id}")
        
        # Get associated agent info (optional - for context)
        agent = db.query(Agent).filter(Agent.id == key.agent_id).first()

        # DID-keyed rows: resolve the DID Document into the same response
        # shape the PEM path returns.
        if getattr(key, "key_type", "pem") == "did" or (
            hasattr(key, "key_type") and getattr(key.key_type, "value", None) == "did"
        ):
            resolved = _resolve_did_key(key)
            print(f"✅ Resolved DID key '{key_id}' (agent: {agent.name if agent else 'unknown'})")
            return {
                **resolved,
                "agent_id": key.agent_id,
                "agent_name": agent.name if agent else None,
                "agent_domain": agent.domain if agent else None,
            }

        print(f"✅ Retrieved key '{key_id}' (agent: {agent.name if agent else 'unknown'})")
        return {
            "key_id": key_id,
            "is_active": key.is_active,
            "public_key": key.public_key,
            "algorithm": key.algorithm,
            "description": key.description,
            "agent_id": key.agent_id,
            "agent_name": agent.name if agent else None,
            "agent_domain": agent.domain if agent else None,
            "key_type": "pem",
            "pq_public_key": getattr(key, "pq_public_key", None),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve key: {str(e)}")

@app.get("/agents", response_model=list[AgentPublicInfo])
async def list_agents(active_only: bool = True, db: Session = Depends(get_db)):
    """
    List all registered agents (optionally active only)
    """
    try:
        query = db.query(Agent)
        if active_only:
            query = query.filter(Agent.is_active == "true")
        
        agents = query.all()
        print(f"✅ Retrieved {len(agents)} agents")
        return [AgentPublicInfo.model_validate(agent) for agent in agents]
        
    except Exception as e:
        print(f"❌ Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@app.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, agent_update: AgentUpdate, db: Session = Depends(get_db)):
    """
    Update specific fields of an existing agent
    """
    try:
        existing_agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not existing_agent:
            print(f"❌ Agent not found for ID: {agent_id}")
            raise HTTPException(status_code=404, detail=f"Agent not found for ID: {agent_id}")
        
        # Update only provided fields
        update_data = agent_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_agent, field, value)
        
        db.commit()
        db.refresh(existing_agent)
        
        print(f"✅ Updated agent for ID: {agent_id}")
        return {
            "success": True,
            "message": f"Agent updated for ID: {agent_id}",
            "agent": existing_agent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")

@app.delete("/agents/{agent_id}", response_model=Message)
async def deactivate_agent(agent_id: int, db: Session = Depends(get_db)):
    """
    Deactivate an agent (soft delete)
    """
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            print(f"❌ Agent not found for ID: {agent_id}")
            raise HTTPException(status_code=404, detail=f"Agent not found for ID: {agent_id}")
        
        agent.is_active = "false"
        db.commit()
        
        print(f"✅ Deactivated agent for ID: {agent_id}")
        return {"message": f"Agent deactivated for ID: {agent_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error deactivating agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to deactivate agent: {str(e)}")

# Legacy endpoint for domain-based lookup (for backward compatibility)
@app.get("/agents/domain/{domain}", response_model=AgentPublicInfo)
async def get_agent_by_domain(domain: str, db: Session = Depends(get_db)):
    """
    Get agent information by domain (legacy endpoint)
    """
    try:
        agent = db.query(Agent).filter(Agent.domain == domain).first()
        
        if not agent:
            print(f"❌ Agent not found for domain: {domain}")
            raise HTTPException(status_code=404, detail=f"Agent not found for domain: {domain}")
        
        if agent.is_active != "true":
            print(f"❌ Agent inactive for domain: {domain}")
            raise HTTPException(status_code=404, detail=f"Agent is inactive for domain: {domain}")
        
        print(f"✅ Retrieved agent info for domain: {domain}")
        return AgentPublicInfo.model_validate(agent)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve agent: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9002)
