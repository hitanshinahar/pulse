import logging
import razorpay
from razorpay.errors import BadRequestError, ServerError
from backend.config import settings

logger = logging.getLogger(__name__)

class RazorpayIntegrationError(Exception):
    """Raised when there is an authentication or configuration issue with Razorpay."""
    pass

class RazorpayUpstreamError(Exception):
    """Raised when Razorpay services are unavailable."""
    pass

def get_razorpay_client() -> razorpay.Client:
    """Instantiate a Razorpay client securely from configuration."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay credentials are missing from configuration.")
        raise RazorpayIntegrationError("Missing Razorpay credentials. Check .env configuration.")
    
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def verify_connection() -> bool:
    """
    Verifies that the backend can successfully authenticate against Razorpay Test Mode.
    Makes a real API request to fetch a single order.
    """
    try:
        client = get_razorpay_client()
        # Make a low-impact read request to verify authentication
        client.order.fetch_all({"count": 1})
        return True
    except BadRequestError as e:
        # BadRequestError often occurs for invalid credentials in Razorpay Python SDK
        logger.error(f"Razorpay authentication failed: {str(e)}")
        raise RazorpayIntegrationError("Razorpay authentication failed. Check credentials validity.") from e
    except ServerError as e:
        logger.error(f"Razorpay upstream service error: {str(e)}")
        raise RazorpayUpstreamError("Razorpay service is currently unavailable.") from e
    except RazorpayIntegrationError:
        raise
    except Exception as e:
        # Check if the error message implies authentication failure
        if "Authentication failed" in str(e) or "unauthorized" in str(e).lower() or getattr(e, 'status_code', 0) == 401:
            logger.error("Razorpay authentication failed due to unauthorized access.")
            raise RazorpayIntegrationError("Razorpay authentication failed. Invalid API keys.") from e
        
        logger.error(f"Unexpected error communicating with Razorpay: {str(e)}")
        raise RazorpayUpstreamError("Unexpected error communicating with Razorpay.") from e
