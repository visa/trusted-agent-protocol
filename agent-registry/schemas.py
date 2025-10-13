# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

# Agent Key schemas
class AgentKeyBase(BaseModel):
    """Base agent key schema"""
    key_id: str = Field(..., min_length=1, max_length=100, description="Key identifier (e.g., 'primary', 'backup-2024')")
    public_key: str = Field(..., min_length=20, description="Public key in PEM format (RSA) or base64 format (Ed25519)")
    algorithm: str = Field("RSA-SHA256", description="Signature algorithm")
    description: Optional[str] = Field(None, max_length=1000, description="Optional key description")
    is_active: str = Field("true", description="Key active status")
    
    @validator('public_key', always=True)
    def validate_public_key(cls, v, values):
        """Validate public key format based on algorithm"""
        # Get algorithm from values dict, fallback to RSA-SHA256
        algorithm = values.get('algorithm', 'RSA-SHA256')
        if algorithm:
            algorithm = algorithm.lower()
        
        # Auto-detect Ed25519 based on key format if algorithm detection fails
        is_ed25519 = ('ed25519' in algorithm) or (len(v.strip()) < 100 and not v.strip().startswith('-----'))
        
        if is_ed25519:
            # Ed25519 keys are base64 encoded, typically 44 characters
            import base64
            try:
                decoded = base64.b64decode(v.strip())
                if len(decoded) != 32:  # Ed25519 public keys are exactly 32 bytes
                    raise ValueError('Ed25519 public key must be exactly 32 bytes when base64 decoded')
            except Exception:
                raise ValueError('Ed25519 public key must be valid base64 encoding')
        else:
            # RSA keys must be in PEM format
            if not v.strip().startswith('-----BEGIN PUBLIC KEY-----'):
                raise ValueError('RSA public key must be in PEM format starting with -----BEGIN PUBLIC KEY-----')
            if not v.strip().endswith('-----END PUBLIC KEY-----'):
                raise ValueError('RSA public key must be in PEM format ending with -----END PUBLIC KEY-----')
        
        return v.strip()
    
    @validator('is_active')
    def validate_is_active(cls, v):
        """Validate active status"""
        if v not in ['true', 'false']:
            raise ValueError('is_active must be "true" or "false"')
        return v

class AgentKeyCreate(AgentKeyBase):
    """Schema for creating a new agent key"""
    pass

class AgentKeyUpdate(BaseModel):
    """Schema for updating an existing agent key"""
    key_id: Optional[str] = Field(None, min_length=1, max_length=100)
    public_key: Optional[str] = Field(None, min_length=20)
    algorithm: Optional[str] = Field(None)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[str] = Field(None)
    
    @validator('public_key', always=True)
    def validate_public_key(cls, v, values):
        """Validate public key format if provided"""
        if v is not None:
            # Get algorithm from values dict, fallback to RSA-SHA256
            algorithm = values.get('algorithm', 'RSA-SHA256')
            if algorithm:
                algorithm = algorithm.lower()
            
            # Auto-detect Ed25519 based on key format if algorithm detection fails
            is_ed25519 = ('ed25519' in algorithm) or (len(v.strip()) < 100 and not v.strip().startswith('-----'))
            
            if is_ed25519:
                # Ed25519 keys are base64 encoded, typically 44 characters
                import base64
                try:
                    decoded = base64.b64decode(v.strip())
                    if len(decoded) != 32:  # Ed25519 public keys are exactly 32 bytes
                        raise ValueError('Ed25519 public key must be exactly 32 bytes when base64 decoded')
                except Exception:
                    raise ValueError('Ed25519 public key must be valid base64 encoding')
            else:
                # RSA keys must be in PEM format
                if not v.strip().startswith('-----BEGIN PUBLIC KEY-----'):
                    raise ValueError('RSA public key must be in PEM format starting with -----BEGIN PUBLIC KEY-----')
                if not v.strip().endswith('-----END PUBLIC KEY-----'):
                    raise ValueError('RSA public key must be in PEM format ending with -----END PUBLIC KEY-----')
            
            return v.strip()
        return v
    
    @validator('is_active')
    def validate_is_active(cls, v):
        """Validate active status if provided"""
        if v is not None and v not in ['true', 'false']:
            raise ValueError('is_active must be "true" or "false"')
        return v

class AgentKeyFull(AgentKeyBase):
    """Full agent key information including metadata"""
    id: int
    agent_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Agent schemas
class AgentBase(BaseModel):
    """Base agent schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    domain: str = Field(..., min_length=1, max_length=255, description="Agent domain (e.g., https://directory.example.com)")
    description: Optional[str] = Field(None, max_length=1000, description="Optional agent description")
    contact_email: Optional[str] = Field(None, max_length=255, description="Optional contact email")
    is_active: str = Field("true", description="Agent active status")
    
    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Domain must start with http:// or https://')
        return v
    
    @validator('is_active')
    def validate_is_active(cls, v):
        """Validate active status"""
        if v not in ['true', 'false']:
            raise ValueError('is_active must be "true" or "false"')
        return v

class AgentCreate(AgentBase):
    """Schema for creating a new agent"""
    keys: List[AgentKeyCreate] = Field(default=[], description="Initial keys for the agent")

class AgentUpdate(BaseModel):
    """Schema for updating an existing agent"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    contact_email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[str] = Field(None)
    
    @validator('is_active')
    def validate_is_active(cls, v):
        """Validate active status if provided"""
        if v is not None and v not in ['true', 'false']:
            raise ValueError('is_active must be "true" or "false"')
        return v

class AgentPublicInfo(BaseModel):
    """Public information returned for agent lookups"""
    id: int
    name: str
    domain: str
    description: Optional[str] = None
    is_active: str
    keys: List[AgentKeyFull] = []
    
    class Config:
        from_attributes = True

class AgentFull(AgentBase):
    """Full agent information including metadata"""
    id: int
    created_at: datetime
    updated_at: datetime
    keys: List[AgentKeyFull] = []
    
    class Config:
        from_attributes = True

class AgentResponse(BaseModel):
    """Response schema for agent operations"""
    success: bool
    message: str
    agent: AgentFull

class AgentKeyResponse(BaseModel):
    """Response schema for agent key operations"""
    success: bool
    message: str
    key: AgentKeyFull

class Message(BaseModel):
    """Simple message response"""
    message: str
