# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class KeyType(str, enum.Enum):
    """
    Discriminator for how the registry stores the public key for a row.

    - ``pem`` — legacy / default: row stores a literal PEM-encoded public
      key in ``public_key``. ``did_method`` and ``pq_public_key`` are NULL.
    - ``did`` — row stores a DID URI in ``key_id``; ``public_key`` is NULL
      and the registry resolves the DID Document via a registered
      ``DIDResolver`` at lookup time. ``did_method`` selects the resolver.

    The default is ``pem`` so all existing rows keep working unchanged
    after the column is added (``server_default='pem'`` in the migration).
    """

    PEM = "pem"
    DID = "did"

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
    key_id = Column(String(1024), nullable=False, index=True)  # widened from 100 to 1024 to fit DID URIs
    # ``public_key`` becomes nullable: when ``key_type == KeyType.DID`` the
    # registry resolves the public key from the DID Document at lookup time
    # and stores nothing locally. Existing rows are PEM-keyed and remain
    # required at the application layer (validators in schemas.py).
    public_key = Column(Text, nullable=True)  # PEM format public key (NULL for did rows)
    algorithm = Column(String(50), default="RSA-SHA256", nullable=False)  # Signature algorithm
    description = Column(Text)  # Optional key description
    is_active = Column(String(10), default="true", nullable=False)  # Key active status
    # --- Additive columns for DID + hybrid PQ keys ---
    # ``key_type`` discriminates PEM vs DID. ``server_default`` ensures all
    # existing rows materialize as ``pem`` after the ``ALTER TABLE ... ADD
    # COLUMN`` migration; no backfill is required.
    key_type = Column(
        SAEnum(KeyType, name="agent_key_type"),
        nullable=False,
        default=KeyType.PEM,
        server_default=KeyType.PEM.value,
    )
    # ``did_method`` selects the registered ``DIDResolver`` (e.g. "web",
    # "tenzro"). NULL for PEM rows.
    did_method = Column(String(64), nullable=True)
    # ``pq_public_key`` is the Base64-encoded raw ML-DSA-65 verifying key
    # (1952 bytes per FIPS 204 §4 Table 2) when the row registers a hybrid
    # ``ed25519-ml-dsa-65`` algorithm with a literal PEM. Hybrid keys
    # sourced from a DID Document are resolved at lookup time and do not
    # populate this column.
    pq_public_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with agent
    agent = relationship("Agent", back_populates="keys")
    
    def __repr__(self):
        return f"<AgentKey(id={self.id}, agent_id={self.agent_id}, key_id='{self.key_id}', active='{self.is_active}')>"
