# Secure Python backend

This backend keeps M-Pesa and Anthropic credentials off GitHub Pages and out of browser storage.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
cp backend/.env.example .env
uvicorn backend.app:app --reload --port 8000
```

Set a public HTTPS `MPESA_CALLBACK_URL` before testing callbacks. Do not commit `.env`.

## API flow

1. `POST /api/payments/stk-push` starts an STK Push.
2. Safaricom calls `POST /api/mpesa/callback` after the customer responds.
3. `GET /api/payments/{checkout_request_id}` reads the payment status.
4. `POST /api/ai/query` accepts a paid checkout ID and calls Anthropic only after payment succeeds.

The browser should call this backend; it must never receive M-Pesa or Anthropic secrets. Add your production authentication provider before exposing these endpoints publicly.
