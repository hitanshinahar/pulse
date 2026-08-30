import pytest
import os
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_razorpay_client():
    with patch('backend.integrations.razorpay.client.razorpay.Client') as MockClient:
        yield MockClient
