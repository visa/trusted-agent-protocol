# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)  # Unique domain constraint
    description = Column(Text)  # Optional agent description
    contact_email = Column(String(255))  # Optional contact email
    is_active = Column(String(10), default="true", nullable=False)  # Active status
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with keys
    keys = relationship("AgentKey", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Agent(id={self.id}, domain='{self.domain}', name='{self.name}', active='{self.is_active}')>"

class AgentKey(Base):
    __tablename__ = "agent_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    key_id = Column(String(100), nullable=False, index=True)  # User-defined key identifier
    public_key = Column(Text, nullable=False)  # PEM format RSA public key
    algorithm = Column(String(50), default="RSA-SHA256", nullable=False)  # Signature algorithm
    description = Column(Text)  # Optional key description
    is_active = Column(String(10), default="true", nullable=False)  # Key active status
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with agent
    agent = relationship("Agent", back_populates="keys")
    
    def __repr__(self):
        return f"<AgentKey(id={self.id}, agent_id={self.agent_id}, key_id='{self.key_id}', active='{self.is_active}')>"
