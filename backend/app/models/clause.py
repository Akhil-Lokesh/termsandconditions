"""Clause model for storing individual clauses from T&C documents."""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base import Base


class Clause(Base):
    """Individual clause from a T&C document."""

    __tablename__ = "clauses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    section = Column(String, nullable=True)
    subsection = Column(String, nullable=True)
    clause_number = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    level = Column(
        Integer, nullable=True
    )  # Hierarchy level (0=section, 1=subsection, 2=clause)
    clause_metadata = Column(JSON, nullable=True)  # Additional metadata
    pinecone_id = Column(String, nullable=True)  # Reference to Pinecone vector ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="clauses")

    def __repr__(self) -> str:
        return f"<Clause(id={self.id}, section={self.section}, clause_number={self.clause_number})>"
