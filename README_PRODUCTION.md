# M-Pesa AI Agent - Production Safe Implementation

A secure, multi-language command-line tool for AI-powered queries with M-Pesa payments.

## Architecture

```
User (CLI)
    ↓
Python AI Service (requests payment)
    ↓
User Approval (explicit yes/no)
    ↓
M-Pesa STK Push (user enters PIN)
    ↓
Payment Confirmation (callback/polling)
    ↓
Claude AI (processes query after payment confirmed)
    ↓
Result to user
```

## Key Security Features

✅ **No autonomous payments** - AI requests, user approves
✅ **User enters PIN** - Direct M-Pesa authentication
✅ **Transaction limits** - Maximum amount per transaction
✅ **Approval policies** - Configurable spending rules
✅ **Audit logging** - Every transaction tracked
✅ **No credential storage in CLI** - Credentials in .env only
✅ **Multi-language** - C++ (performance), TypeScript (validation), Kotlin (mobile), Python (core)

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your M-Pesa and Anthropic credentials
```

## Usage

### Register user
```bash
python -m cli auth register --email user@example.com --password pass123 --name "John Doe" --phone 254712345678
```

### Request AI query with payment approval
```bash
python -m cli ai request --user-id 1 --prompt "Analyze my data" --service advancedAnalysis
```

This will:
1. Show the cost (200 KES for advancedAnalysis)
2. Ask for explicit approval: `Approve payment? [y/N]:`
3. If approved, send STK Push to user's M-Pesa phone
4. User enters M-Pesa PIN on their device
5. Wait for payment confirmation
6. Call Claude API
7. Return result

### View transaction history
```bash
python -m cli transactions history --user-id 1
```

## Payment Approval Flow

```
┌─────────────────────────────────────┐
│ User enters: python -m cli ai request ...  │
└─────────────────────────────────────┘
                    ↓
        ┌───────────────────┐
        │  AI analyzes      │
        │  request          │
        └───────────────────┘
                    ↓
        ┌──���────────────────────────────┐
        │ PAYMENT APPROVAL SCREEN        │
        │                               │
        │ Service: Advanced Analysis    │
        │ Cost: 200 KES                 │
        │ Phone: 254712345678           │
        │                               │
        │ Approve payment? [y/N]:       │
        └───────────────────────────────┘
                    ↓
              User enters: y
                    ↓
        ┌───────────────────┐
        │ STK Push sent     │
        │ to M-Pesa         │
        └───────────────────┘
                    ↓
        ┌───────────────────────────────┐
        │ USER ON THEIR PHONE           │
        │ M-Pesa prompt appears         │
        │ User enters PIN               │
        │ Payment confirmed             │
        └───────────────────────────────┘
                    ↓
        ┌───────────────────┐
        │ Claude API call   │
        │ with user prompt  │
        └───────────────────┘
                    ↓
        ┌───────────────────┐
        │ Result returned   │
        │ to user CLI       │
        └───────────────────┘
```

## File Structure

```
.
├── cli.py                          # CLI entry point
├── config.py                       # Configuration from .env
├── database.py                     # SQLite initialization
├── models.py                       # Data models
├── auth.py                         # User auth (register/login)
├── payment.py                      # M-Pesa payment logic
├── payment_approval.py             # User approval workflow
├── ai.py                           # Claude AI invocation
├── ai_request_handler.py           # AI request processing with approval
│
├── mpesa_client_cpp/               # High-performance C++ M-Pesa client
│   ├── mpesa_client.hpp            # Authentication, STK push, balance check
│   └── README.md
│
├── payment_agent/                  # TypeScript validation layer
│   ├── mpesa_agent.ts              # M-Pesa transaction interface
│   ├── payment_auth.ts             # Approval policies and validation
│   └── README.md
│
├── mobile_payment/                 # Kotlin Android integration
│   └── android/
│       ├── MpesaCredentialManager.kt    # Secure credential storage
│       ├── MpesaPaymentService.kt       # Payment polling service
│       └── README.md
│
├── requirements.txt                # Python dependencies
├── .env.example                    # Configuration template
├── README.md                       # This file
└── data/
    └── app.db                      # SQLite database (auto-created)
```

## Approval Policies

Configure spending limits in code:

```python
APPROVAL_POLICY = {
    "maxTransactionAmount": 5000,        # Max per transaction in KES
    "maxDailyAmount": 20000,             # Max per day in KES
    "requireApprovalAbove": 100,         # Prompt user above this amount
    "allowedServices": [
        "basicQuery",
        "advancedAnalysis",
        "customReport",
        "premiumSupport"
    ]
}
```

## Pricing

| Service | Price |
|---------|-------|
| Basic Query | 50 KES |
| Advanced Analysis | 200 KES |
| Custom Report | 500 KES |
| Premium Support | 1000 KES |

## Environment Variables

```bash
# M-Pesa Daraja
MPESA_ENVIRONMENT=sandbox              # sandbox or production
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_passkey

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620

# Database
DATABASE_PATH=./data/app.db
```

## Database Schema

### users
- `id` - User ID
- `email` - Unique email
- `password_hash` - SHA256 hashed password
- `full_name` - User name
- `phone_number` - M-Pesa phone (254...)
- `created_at` - Registration timestamp

### payments
- `checkout_request_id` - M-Pesa transaction ID
- `user_id` - User who made payment
- `amount` - Payment amount in KES
- `phone_number` - M-Pesa phone
- `service_type` - Service purchased
- `status` - pending/paid/failed
- `receipt` - M-Pesa receipt number
- `created_at` - Payment initiated time

### transactions
- `id` - Transaction ID
- `user_id` - User
- `checkout_request_id` - Linked payment
- `service_type` - AI service used
- `prompt` - User's query
- `answer` - Claude's response
- `amount` - Cost in KES
- `created_at` - Execution time

## Troubleshooting

### "Payment timeout"
User didn't enter M-Pesa PIN within 30 seconds. Try again.

### "Insufficient balance"
User's M-Pesa account doesn't have enough KES. Top up and retry.

### "M-Pesa auth failed"
Check consumer key/secret in `.env`. Verify Daraja app is active.

### "Anthropic API error"
Verify API key is correct and has sufficient credits.

## Production Deployment

For production use:

1. **Never commit .env** - Use environment variables on server
2. **Use production M-Pesa credentials** - After testing in sandbox
3. **Add callback handler** - For asynchronous payment confirmation
4. **Use HTTPS** - All M-Pesa endpoints require TLS
5. **Monitor logs** - Track all payments and errors
6. **Regular backups** - Database contains transaction history

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review M-Pesa Daraja docs: https://developer.safaricom.co.ke/docs
3. Check Anthropic Claude docs: https://docs.anthropic.com/claude/reference
