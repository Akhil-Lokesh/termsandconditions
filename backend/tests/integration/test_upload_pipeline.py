"""
Integration test for document upload pipeline.

Tests the complete flow:
1. Upload PDF
2. Extract text
3. Parse structure
4. Generate embeddings
5. Store in Pinecone
6. Detect anomalies
"""

import pytest
import time
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.core.config import settings

# Mark as integration test
pytestmark = pytest.mark.integration


@pytest.fixture
def test_pdf_path():
    """Path to test PDF file."""
    return Path(__file__).parent.parent.parent / "data" / "test_samples" / "test_tos.pdf"


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers.

    Skips (rather than errors) when a token can't be established — these
    integration tests require a live, reachable backend + database, and the
    signup endpoint is rate-limited, so auth setup is an environmental
    precondition, not the behaviour under test.
    """
    # Create test user (tolerate "already registered" / rate-limit responses).
    client.post(
        "/api/v1/auth/signup",
        json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
        },
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpass123",
        },
    )

    body = response.json() if response.content else {}
    if "access_token" not in body:
        pytest.skip(
            f"auth unavailable (login {response.status_code}: "
            f"{body.get('detail', 'no token')})"
        )
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_upload_complete_pipeline(client, auth_headers, test_pdf_path):
    """
    Test complete document upload pipeline.
    """
    # Upload document
    with open(test_pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/documents/",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers=auth_headers,
        )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify response structure
    assert "id" in data
    assert data["filename"] == "test.pdf"
    assert data["processing_status"] in ["analyzing_anomalies", "completed"]
    assert data["clause_count"] > 0
    
    document_id = data["id"]
    
    # Wait for background processing (max 60 seconds)
    for _ in range(60):
        response = client.get(
            f"/api/v1/documents/{document_id}",
            headers=auth_headers,
        )
        doc_data = response.json()
        
        if doc_data["processing_status"] == "completed":
            break
        
        time.sleep(1)
    
    # Verify document processed
    assert doc_data["processing_status"] == "completed"
    assert doc_data["anomaly_count"] >= 0
    assert doc_data["risk_score"] is not None
    
    # Get anomaly report
    response = client.get(
        f"/api/v1/anomalies/{document_id}",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    anomaly_data = response.json()
    
    # Verify report structure
    assert "overall_risk" in anomaly_data
    assert "high_risk_anomalies" in anomaly_data
    assert "risk_score" in anomaly_data["overall_risk"]


@pytest.mark.asyncio
async def test_services_initialized():
    """Test that all services initialize correctly."""
    # Test Embedding Service
    embedding_service = EmbeddingService()
    embedding = await embedding_service.create_embedding("test")
    # Service produces 384-dim (all-MiniLM-L6-v2) padded to the Pinecone index
    # dimension; the returned vector is the padded one.
    assert len(embedding) == embedding_service.embedding_dim
    
    # Test Pinecone
    pinecone = PineconeService()
    await pinecone.initialize()
    assert pinecone.index is not None
    
    # Check baseline corpus
    stats = pinecone.index.describe_index_stats()
    baseline_count = stats['namespaces'].get(settings.PINECONE_BASELINE_NAMESPACE, {}).get('vector_count', 0)
    
    # Warn if baseline is small
    if baseline_count < 1000:
        pytest.skip(f"Baseline corpus too small ({baseline_count} vectors). Run index_baseline_corpus.py")


def test_query_endpoint(client, auth_headers, test_pdf_path):
    """Test Q&A query endpoint."""
    # First upload a document
    with open(test_pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/documents/",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers=auth_headers,
        )
    
    document_id = response.json()["id"]
    
    # Wait for processing
    time.sleep(10)
    
    # Query the document
    response = client.post(
        "/api/v1/query/",
        json={
            "document_id": document_id,
            "question": "What is the cancellation policy?",
        },
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "question" in data
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
