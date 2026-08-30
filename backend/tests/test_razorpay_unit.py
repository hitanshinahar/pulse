import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from razorpay.errors import BadRequestError, ServerError

from backend.main import app
from backend.integrations.razorpay.client import (
    get_razorpay_client, 
    verify_connection, 
    RazorpayIntegrationError,
    RazorpayUpstreamError
)
from backend.config import settings

client = TestClient(app)

def test_get_razorpay_client_missing_credentials():
    """Test that missing credentials raise an integration error."""
    with patch.object(settings, 'RAZORPAY_KEY_ID', ''), \
         patch.object(settings, 'RAZORPAY_KEY_SECRET', ''):
        with pytest.raises(RazorpayIntegrationError, match="Missing Razorpay credentials"):
            get_razorpay_client()

def test_verify_connection_success(mock_razorpay_client):
    """Test verify_connection when the Razorpay client succeeds."""
    with patch('backend.integrations.razorpay.client.get_razorpay_client', return_value=mock_razorpay_client()):
        # Mock fetch_all to succeed silently
        mock_razorpay_client().order.fetch_all.return_value = {"items": [], "count": 0}
        
        assert verify_connection() is True
        mock_razorpay_client().order.fetch_all.assert_called_once_with({"count": 1})

def test_verify_connection_auth_failure(mock_razorpay_client):
    """Test verify_connection when Razorpay throws an auth-related error."""
    with patch('backend.integrations.razorpay.client.get_razorpay_client', return_value=mock_razorpay_client()):
        # Mock fetch_all to raise a BadRequestError (common for invalid keys in sdk)
        mock_razorpay_client().order.fetch_all.side_effect = BadRequestError("Authentication failed")
        
        with pytest.raises(RazorpayIntegrationError, match="Razorpay authentication failed"):
            verify_connection()

def test_verify_connection_upstream_failure(mock_razorpay_client):
    """Test verify_connection when Razorpay services are down."""
    with patch('backend.integrations.razorpay.client.get_razorpay_client', return_value=mock_razorpay_client()):
        mock_razorpay_client().order.fetch_all.side_effect = ServerError("Service unavailable")
        
        with pytest.raises(RazorpayUpstreamError, match="Razorpay service is currently unavailable"):
            verify_connection()

def test_health_endpoint_success():
    """Test the health endpoint returns 200 when connectivity is verified."""
    with patch('backend.main.verify_connection', return_value=True):
        response = client.get("/api/v1/health/razorpay")
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Successfully authenticated with Razorpay Test Mode."}

def test_health_endpoint_missing_creds():
    """Test the health endpoint handles integration errors cleanly (401)."""
    with patch('backend.main.verify_connection', side_effect=RazorpayIntegrationError("Missing Razorpay credentials")):
        response = client.get("/api/v1/health/razorpay")
        assert response.status_code == 401
        assert "Missing Razorpay credentials" in response.json()["detail"]
