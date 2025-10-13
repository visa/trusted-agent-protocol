# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.security.signature_verification import signature_verifier
import base64
import json

router = APIRouter(prefix="/auth", tags=["authentication"])

class SignatureVerificationRequest(BaseModel):
    signature_agent: str
    signature_input: str
    signature: str
    authority: str
    path: str
    directory_agent: Optional[str] = None
    query_param: Optional[str] = None

class SignatureVerificationResponse(BaseModel):
    is_trusted: bool
    message: str
    agent_name: Optional[str] = None

@router.post("/verify-signature", response_model=SignatureVerificationResponse)
def verify_signature(verification_request: SignatureVerificationRequest):
    """Verify the signature from a trusted agent."""
    
    try:
        # Prepare request data for signature verification
        request_data = {
            "authority": verification_request.authority,
            "path": verification_request.path,
            "directory-agent": verification_request.directory_agent or "",
            "query-param": verification_request.query_param or ""
        }
        
        # Verify the signature
        is_trusted, message = signature_verifier.is_trusted_agent(
            verification_request.signature_agent,
            verification_request.signature_input,
            verification_request.signature,
            request_data
        )
        
        agent_name = None
        if is_trusted:
            # Extract agent name from the trusted agents
            for agent_url, agent_info in signature_verifier.trusted_agents.items():
                if agent_url in verification_request.signature_agent:
                    agent_name = agent_info["name"]
                    break
        
        return SignatureVerificationResponse(
            is_trusted=is_trusted,
            message=message,
            agent_name=agent_name
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")



@router.get("/check-verification")
def check_verification(request: Request):
    """Check if request was verified by CDN/Proxy"""
    
    print("🔍 /api/auth/check-verification endpoint called!")
    print(f"🔍 Request headers: {dict(request.headers)}")
    
    # Check headers set by CDN/Proxy
    agent_verified = request.headers.get("x-signature-verified") or request.headers.get("x-agent-verified")
    agent_name = request.headers.get("x-signature-key-id") or request.headers.get("x-agent-name") 
    verified_by = request.headers.get("x-verified-by")
    agent_data = request.headers.get("x-agent-data")

    decoded_agent_data = None
    if agent_data:
        try:
            decoded_agent_data = base64.b64decode(agent_data).decode("utf-8")
            print(f"Decoded agent data: {decoded_agent_data}")
        except Exception as e:
            print(f"Failed to decode agent data: {e}")

    access_allowed = True

    access_url = None
    if decoded_agent_data:
        try:
            data_json = json.loads(decoded_agent_data)
            access_url = data_json.get("accessUrl")
            if access_url and "admin" in access_url:
                access_allowed = False
            token = data_json.get("token")
            jwt_body = None
            if token:
                try:
                    # JWT format: header.payload.signature
                    parts = token.split(".")
                    if len(parts) == 3:
                        payload_b64 = parts[1]
                        # Add padding if necessary
                        padding = '=' * (-len(payload_b64) % 4)
                        payload_b64 += padding
                        payload_bytes = base64.urlsafe_b64decode(payload_b64)
                        jwt_body = json.loads(payload_bytes.decode("utf-8"))
                        print(f"JWT body: {jwt_body}")
                    else:
                        print("Invalid JWT format.")
                except Exception as e:
                    print(f"Failed to decode JWT body: {e}")
        except json.JSONDecodeError:
            print("Failed to parse decoded agent data as JSON.")

    print(f"Verification headers: verified={agent_verified}, name={agent_name}, by={verified_by}, data={decoded_agent_data}")

    if agent_verified == "true":
        if not access_allowed:
            return {
                "verified": False,
                "message": "Access Denied."
            }
        return {
            "verified": True,
            "agent_name": agent_name,
            "verified_by": verified_by or "CDN",
            "message": f"Request verified by {verified_by or 'CDN'}: {agent_name}"
        }
    else:
        return {
            "verified": False,
            "message": "Request not verified by CDN"
        }
