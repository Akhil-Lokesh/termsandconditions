"""Document schemas for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DocumentBase(BaseModel):
    """Base document schema."""

    filename: str


class DocumentCreate(DocumentBase):
    """Schema for document creation."""

    pass


class DocumentMetadata(BaseModel):
    """Schema for document metadata."""

    company: Optional[str] = None
    jurisdiction: Optional[str] = None
    effective_date: Optional[str] = None
    version: Optional[str] = None
    document_type: Optional[str] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: str
    filename: str
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Document metadata (company, jurisdiction, etc.)"
    )
    page_count: Optional[int] = Field(
        default=None, description="Number of pages in document"
    )
    clause_count: Optional[int] = Field(
        default=None, description="Number of clauses found"
    )
    anomaly_count: Optional[int] = Field(
        default=0, description="Number of anomalies detected"
    )
    processing_status: str = Field(
        description="Processing status: pending, completed, failed, etc."
    )
    created_at: datetime = Field(description="Document upload timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "terms_of_service.pdf",
                "metadata": {
                    "company": "Example Corp",
                    "jurisdiction": "California, USA",
                    "effective_date": "2024-01-01",
                },
                "page_count": 15,
                "clause_count": 42,
                "anomaly_count": 3,
                "processing_status": "completed",
                "created_at": "2024-10-24T10:30:00Z",
            }
        },
    }


class DocumentListResponse(BaseModel):
    """Schema for list of documents with pagination."""

    documents: List[DocumentResponse]
    total: int = Field(description="Total number of documents")
    skip: int = Field(default=0, description="Number of documents skipped")
    limit: int = Field(default=100, description="Maximum number of documents returned")


class DocumentWithAnomalies(DocumentResponse):
    """Schema for document with anomaly preview."""

    anomaly_count: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0


class ComparisonRequest(BaseModel):
    """Request schema for comparing documents."""

    document_ids: List[str] = Field(..., min_length=2, max_length=5, description="List of document IDs to compare (2-5 documents)")


class ComparisonResponse(BaseModel):
    """Response schema for document comparison."""

    documents: List[Dict[str, Any]] = Field(..., description="Summary of each document")
    differences: List[Dict[str, Any]] = Field(..., description="Key differences between documents")
    recommendations: str = Field(..., description="Recommendation on which document is best/worst")
