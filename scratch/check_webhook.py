import requests

url = "https://pulse-1j48.onrender.com/api/v1/webhooks/razorpay"

try:
    print(f"Checking {url} with 60s timeout...")
    response = requests.get(url, timeout=60)
    print(f"GET Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
