# Recovery Firewall

Recovery Firewall is an AI decision layer for safe revenue recovery using the Razorpay API. 

## Phase 0.1: Razorpay Connectivity

This phase lays the foundation for communicating with the Razorpay Test Mode API securely.

### Setup Instructions

1. **Configure Environment Variables**
   Create a `.env` file in the root directory (where `backend/` is located) and add your Razorpay Test Mode credentials:
   ```env
   RAZORPAY_KEY_ID=your_test_key_id
   RAZORPAY_KEY_SECRET=your_test_key_secret
   ```
   *Note: Never commit `.env` to version control. It is already ignored in `.gitignore`.*

2. **Python Environment Setup**
   Ensure you have Python 3.9+ installed.
   ```bash
   # Create a virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r backend/requirements.txt
   ```

### Running the Application

To start the FastAPI backend server:
```bash
uvicorn backend.main:app --reload
```
The server will run on `http://127.0.0.1:8000`.

### Connectivity Check Endpoint

To verify that the application can securely authenticate with Razorpay Test Mode:
```bash
curl http://127.0.0.1:8000/api/v1/health/razorpay
```
- **Success**: Returns HTTP 200 if authentication is successful.
- **Failure**: Returns HTTP 401 or 502 if credentials are missing/invalid or the service is down.

### Running Tests

We have two types of tests: Unit Tests (mocked) and Live Integration Tests (real).

1. **Unit Tests** (Safe to run anywhere, does not use real credentials):
   ```bash
   pytest backend/tests/test_razorpay_unit.py
   ```

2. **Live Tests** (Requires real Test Mode credentials in `.env`):
   To prevent accidental execution in CI environments without credentials, live tests are skipped by default. To run them:
   
   **Windows (PowerShell):**
   ```powershell
   $env:RUN_LIVE_TESTS="1"; pytest backend/tests/test_razorpay_live.py
   ```
   
   **macOS/Linux:**
   ```bash
   RUN_LIVE_TESTS=1 pytest backend/tests/test_razorpay_live.py
   ```

## Phase 0.2: Real Razorpay Webhook Ingestion

This phase enables the application to receive, verify, and store real webhook events from the Razorpay Test Mode environment.

### Additional Configuration

1. **Database URL**
   Update your `.env` file with a PostgreSQL connection string (e.g., Supabase, local PostgreSQL):
   ```env
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/db
   ```

2. **Webhook Secret**
   Configure your webhook in the Razorpay Dashboard and add the generated secret to your `.env` file:
   ```env
   RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
   ```

### Webhook Setup & Testing

1. **Expose Local Server**
   To receive real webhooks locally, you must expose your server to the internet using a tool like `localtunnel` or `ngrok`:
   ```bash
   npx localtunnel --port 8000
   ```

2. **Configure Razorpay Dashboard**
   - Go to Razorpay Dashboard -> Webhooks -> Add New Webhook.
   - Set the URL to your public tunnel URL + `/api/v1/webhooks/razorpay` (e.g., `https://your-tunnel.loca.lt/api/v1/webhooks/razorpay`).
   - Enter your `RAZORPAY_WEBHOOK_SECRET`.
   - Select events: `payment.authorized`, `payment.captured`, `payment.failed`.

3. **Verify Functionality**
   - **Successful Payment**: Trigger a real test payment in Razorpay.
   - **Failed Payment**: Trigger a failed test payment in Razorpay.
   - **Invalid Signature**: Send a fake request using cURL to ensure it returns HTTP 400.
   - **Duplicate Handling**: Resend an event from the Razorpay Dashboard to ensure duplicate side effects do not occur.

### Inspection Endpoints (Dev Only)

To inspect the received and persisted events locally, you must run the server in development mode:
```bash
# Windows
$env:DEV_MODE="true"; uvicorn backend.main:app --reload
```

- List all events: `GET /api/v1/events/razorpay`
- Get a specific event: `GET /api/v1/events/razorpay/{event_id}`
