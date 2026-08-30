import pytest
import os
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.integrations.razorpay.client import verify_connection

client = TestClient(app)

# This test should only run if explicitly requested, to prevent CI failures when creds are missing
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="Live tests require RUN_LIVE_TESTS=1 and real Razorpay credentials"
)

def test_live_razorpay_connectivity():
    """
    Verifies actual connectivity to Razorpay Test Mode using real credentials.
    Do NOT mock the client here.
    """
    # Ensure credentials exist before running the test
    assert settings.RAZORPAY_KEY_ID != "", "RAZORPAY_KEY_ID must be set for live tests"
    assert settings.RAZORPAY_KEY_SECRET != "", "RAZORPAY_KEY_SECRET must be set for live tests"
    
    # Run the underlying connection verification
    is_connected = verify_connection()
    assert is_connected is True

def test_live_health_endpoint():
    """
    Verifies the /api/v1/health/razorpay endpoint returns 200 with real credentials.
    """
    response = client.get("/api/v1/health/razorpay")
    
    # Assuming valid test mode credentials, this should succeed.
    # We do NOT assert the exact full json in case the message changes, but status must be 200.
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
