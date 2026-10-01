# M-Pesa AI Agent CLI

A command-line tool for processing AI queries with M-Pesa payment integration.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the root directory:

```
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_passkey
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620
DATABASE_PATH=./data/app.db
```

## Usage

### Register a new user

```bash
python -m cli auth register --email user@example.com --password password123 --name "John Doe" --phone 254712345678
```

### Login

```bash
python -m cli auth login --email user@example.com --password password123
```

### Start a payment

```bash
python -m cli payment start --phone 254712345678 --service basicQuery
```

### Check payment status

```bash
python -m cli payment status --checkout-id CHECKOUT_ID
```

### Send an AI query

```bash
python -m cli ai query --checkout-id CHECKOUT_ID --prompt "What is machine learning?" --service basicQuery
```

### View transaction history

```bash
python -m cli transactions history --email user@example.com
```

## Pricing

- Basic Query: 50 KES
- Advanced Analysis: 200 KES
- Custom Report: 500 KES
- Premium Support: 1000 KES
