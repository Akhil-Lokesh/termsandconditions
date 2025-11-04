"""
Integration tests for full document processing pipeline.

Tests the complete flow from signup → login → upload → query → anomalies → delete.

Note: These tests require actual API keys for OpenAI and Pinecone.
      Set pytest markers to skip if keys not available.

Usage:
    # Run all integration tests
    pytest tests/integration/ -v

    # Run with coverage
    pytest tests/integration/ -v --cov=app

    # Skip slow tests
    pytest tests/integration/ -v -m "not slow"
"""

import pytest
from pathlib import Path
import time

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def test_user_email():
    """Generate unique test user email."""
    return f"test_{int(time.time())}@example.com"


@pytest.fixture
def test_pdf_path():
    """Path to test PDF file."""
    # Will be created by create_test_pdfs.py script
    pdf_path = Path(__file__).parent.parent.parent / "data" / "test_samples" / "simple_tos.pdf"

    if not pdf_path.exists():
        pytest.skip(f"Test PDF not found: {pdf_path}. Run scripts/create_test_pdfs.py first.")

    return pdf_path


class TestFullPipeline:
    """Test complete system functionality end-to-end."""

    def test_signup(self, client, test_user_email):
        """Test user signup."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user_email,
                "password": "testpassword123",
                "full_name": "Test User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_email
        assert data["is_active"] is True
        assert "id" in data

    def test_login(self, client, test_user_email):
        """Test user login."""
        # First signup
        client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user_email,
                "password": "testpassword123",
                "full_name": "Test User",
            },
        )

        # Then login
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_upload_document(self, auth_client, test_pdf_path):
        """Test document upload and processing."""
        with open(test_pdf_path, "rb") as f:
            response = auth_client.post(
                "/api/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
            )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["filename"] == "test.pdf"
        assert data["page_count"] > 0
        assert data["clause_count"] > 0
        assert data["processing_status"] in ["completed", "anomaly_detection_failed"]

        return data["id"]

    @pytest.mark.slow
    def test_full_workflow(self, client, test_user_email, test_pdf_path):
        """
        Test complete workflow: signup → login → upload → query → anomalies → delete.

        This is a comprehensive test that verifies all major features work together.
        Marked as slow because it does actual document processing.
        """
        # Step 1: Signup
        signup_response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user_email,
                "password": "testpassword123",
                "full_name": "Integration Test User",
            },
        )
        assert signup_response.status_code == 201

        # Step 2: Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_email,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create authenticated client
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Upload document
        with open(test_pdf_path, "rb") as f:
            upload_response = client.post(
                "/api/v1/documents",
                files={"file": ("test.pdf", f, "application/pdf")},
                headers=headers,
            )

        assert upload_response.status_code == 201
        doc_data = upload_response.json()
        document_id = doc_data["id"]

        # Verify upload response
        assert doc_data["filename"] == "test.pdf"
        assert doc_data["page_count"] > 0
        assert doc_data["clause_count"] > 0

        # Step 4: Query document
        query_response = client.post(
            "/api/v1/query",
            json={
                "document_id": document_id,
                "question": "What are the main terms?",
            },
            headers=headers,
        )

        assert query_response.status_code == 200
        query_data = query_response.json()

        # Verify query response
        assert "answer" in query_data
        assert "citations" in query_data
        assert len(query_data["citations"]) > 0
        assert query_data["confidence"] > 0

        # Step 5: Get anomalies
        anomalies_response = client.get(
            f"/api/v1/anomalies/{document_id}",
            headers=headers,
        )

        assert anomalies_response.status_code == 200
        anomalies_data = anomalies_response.json()

        # Verify anomalies response
        assert "anomalies" in anomalies_data
        assert "stats" in anomalies_data
        assert "total" in anomalies_data

        # Step 6: List documents
        list_response = client.get(
            "/api/v1/documents",
            headers=headers,
        )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data["documents"]) > 0
        assert list_data["total"] > 0

        # Step 7: Delete document
        delete_response = client.delete(
            f"/api/v1/documents/{document_id}",
            headers=headers,
        )

        assert delete_response.status_code == 204

        # Verify deletion
        get_response = client.get(
            f"/api/v1/documents/{document_id}",
            headers=headers,
        )
        assert get_response.status_code == 404


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_upload_invalid_file_type(self, auth_client):
        """Test uploading non-PDF file."""
        response = auth_client.post(
            "/api/v1/documents",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
        )

        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_query_nonexistent_document(self, auth_client):
        """Test querying document that doesn't exist."""
        response = auth_client.post(
            "/api/v1/query",
            json={
                "document_id": "nonexistent-id",
                "question": "Test question",
            },
        )

        assert response.status_code == 404

    def test_query_empty_question(self, auth_client):
        """Test query with empty question."""
        response = auth_client.post(
            "/api/v1/query",
            json={
                "document_id": "some-id",
                "question": "",
            },
        )

        assert response.status_code == 422

    def test_login_invalid_credentials(self, client):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    def test_signup_duplicate_email(self, client, test_user_email):
        """Test signup with email that already exists."""
        # First signup
        client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user_email,
                "password": "testpassword123",
                "full_name": "Test User",
            },
        )

        # Try to signup again with same email
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user_email,
                "password": "differentpassword",
                "full_name": "Another User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/api/v1/documents")

        assert response.status_code == 401


class TestDocumentOperations:
    """Test document-specific operations."""

    def test_list_empty_documents(self, auth_client):
        """Test listing documents when user has none."""
        response = auth_client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
        assert isinstance(data["documents"], list)

    def test_get_nonexistent_document(self, auth_client):
        """Test getting document that doesn't exist."""
        response = auth_client.get("/api/v1/documents/nonexistent-id")

        assert response.status_code == 404

    def test_anomalies_empty_document(self, auth_client):
        """Test getting anomalies for nonexistent document."""
        response = auth_client.get("/api/v1/anomalies/nonexistent-id")

        assert response.status_code == 404


# Pytest configuration and fixtures

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API keys)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (does actual processing)"
    )


@pytest.fixture
def client():
    """Create test client."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth_client(client, test_user_email):
    """Create authenticated test client."""
    # Signup
    client.post(
        "/api/v1/auth/signup",
        json={
            "email": test_user_email,
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_email,
            "password": "testpassword123",
        },
    )

    token = response.json()["access_token"]

    # Add authentication header to client
    client.headers.update({"Authorization": f"Bearer {token}"})

    return client


if __name__ == "__main__":
    print("Run with: pytest tests/integration/ -v")
