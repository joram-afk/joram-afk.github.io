# M-Pesa AI Agent Integration Guide

This documentation explains how to set up and use the M-Pesa payment integration with an AI Agent on this site.

## Overview

The integration enables:
- **AI Agent Services**: Pay-per-query AI assistant powered by Claude API
- **M-Pesa Payments**: Seamless payment processing using M-Pesa (Kenya's mobile money platform)
- **User Authentication**: Secure login via Google Sign-In
- **Transaction Tracking**: Complete history of all AI queries and payments

## Architecture

```
User → Login (Google) → API Key Manager → AI Agent Service
                            ↓
                         M-Pesa Payment
                            ↓
                    Claude AI Response
                            ↓
                    Transaction Log
```

## Setup Instructions

### Step 1: Get M-Pesa Daraja Credentials

1. Visit [Safaricom Daraja Portal](https://developer.safaricom.co.ke)
2. Register and create a new app
3. You'll receive:
   - **Consumer Key**
   - **Consumer Secret**
   - **Business Short Code**
   - **Lipa na M-Pesa Passkey**

### Step 2: Get AI Agent API Key

1. Visit [Anthropic Console](https://console.anthropic.com)
2. Create an API key for Claude
3. Copy your API key (starts with `sk-ant-`)

### Step 3: Configure on the Site

1. Log in with your Google account
2. Navigate to **API Key Manager** (`/api-key-manager.html`)
3. Fill in your M-Pesa credentials in the **M-Pesa Setup** tab
4. Fill in your AI Agent API Key in the **AI Agent Setup** tab
5. Click **Save** on both tabs

### Step 4: Test the Integration

1. In the API Key Manager, click **Test Connection** for both M-Pesa and AI Agent
2. Check the **Integration Status** tab to verify all connections

## File Structure

### Core Files

- **`mpesa-config.js`** - M-Pesa API configuration and authentication
- **`ai-agent.js`** - AI Agent service with payment handling
- **`api-key-manager.html`** - Configuration UI for credentials
- **`auth.js`** - User authentication helper
- **`assets/js/auth.js`** - Google Sign-In integration

### Key Functions

#### M-Pesa Functions (mpesa-config.js)

```javascript
// Get M-Pesa access token
await getMpesaAccessToken()

// Initiate payment
await initiateStkPush({
  phoneNumber: '254712345678',
  amount: 100,
  accountReference: 'AI_AGENT_PAYMENT',
  transactionDesc: 'AI Query Processing'
})

// Query transaction status
await queryTransactionStatus(checkoutRequestID)

// Save credentials
saveMpesaCredentials({
  consumerKey: '...',
  consumerSecret: '...',
  businessShortCode: '...',
  passkey: '...',
  environment: 'sandbox' // or 'production'
})
```

#### AI Agent Functions (ai-agent.js)

```javascript
// Process a query with payment
const result = await aiAgentService.processQuery(
  'Your question here',
  'basicQuery' // or 'advancedAnalysis', 'customReport', 'premiumSupport'
)

// Get transaction history
const history = await aiAgentService.getTransactionHistory()

// Calculate total spent
const total = await aiAgentService.getTotalSpent()
```

## Pricing

Service pricing (in KES):

| Service | Price | Token Limit |
|---------|-------|------------|
| Basic Query | 50 KES | 500 tokens |
| Advanced Analysis | 200 KES | 1000 tokens |
| Custom Report | 500 KES | 2000 tokens |
| Premium Support | 1000 KES | 4000 tokens |

## Usage Flow

### Basic Query Flow

1. User logs in with Google
2. User provides a query and selects service type
3. System initiates M-Pesa STK Push
4. User enters M-Pesa PIN
5. Payment confirmed (polling every 2 seconds)
6. AI Agent processes the query
7. Response displayed to user
8. Transaction logged to database

### Code Example

```html
<form id="query-form">
  <textarea id="query" placeholder="Enter your question" required></textarea>
  <select id="service-type">
    <option value="basicQuery">Basic Query (50 KES)</option>
    <option value="advancedAnalysis">Advanced Analysis (200 KES)</option>
  </select>
  <button type="submit">Send Query</button>
</form>

<script>
document.getElementById('query-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const query = document.getElementById('query').value;
  const serviceType = document.getElementById('service-type').value;
  
  try {
    const result = await aiAgentService.processQuery(query, serviceType);
    console.log('AI Response:', result.response);
    console.log('Cost:', result.cost, 'KES');
    console.log('Payment ID:', result.paymentId);
  } catch (error) {
    console.error('Error:', error.message);
  }
});
</script>
```

## Security Considerations

⚠️ **Important**: The current setup stores credentials in `localStorage`. For production:

1. **Never expose API keys in frontend code**
2. **Use a backend server** to handle:
   - API key storage (use environment variables)
   - M-Pesa authentication
   - Transaction verification
   - AI API calls

3. **Example Backend Endpoint** (Node.js/Express):

```javascript
// POST /api/ai-query
async function handleAIQuery(req, res) {
  const { query, serviceType, phoneNumber } = req.body;
  
  // Verify user
  const user = await verifyUser(req.headers.authorization);
  
  // Initiate M-Pesa payment (use server-side credentials)
  const payment = await initiateMpesaPayment({
    phoneNumber,
    amount: PRICING[serviceType]
  });
  
  // Wait for payment confirmation
  const confirmed = await waitForPayment(payment.checkoutRequestID);
  
  if (!confirmed) {
    return res.status(402).json({ error: 'Payment failed' });
  }
  
  // Call Claude API with server-side key
  const response = await callClaudeAPI(query, serviceType);
  
  // Log transaction
  await logTransaction({
    user: user.id,
    query,
    serviceType,
    cost: PRICING[serviceType],
    paymentId: payment.checkoutRequestID,
    response
  });
  
  res.json({ response, cost: PRICING[serviceType] });
}
```

## Testing

### Sandbox Testing (M-Pesa)

- Use test credentials from Safaricom Daraja
- Test phone numbers work without actual payment
- All transactions are simulated

### Development Environment

- Run locally: `python -m http.server 8000`
- Access: `http://localhost:8000/api-key-manager.html`

## Troubleshooting

### M-Pesa Connection Fails

```
Error: "Failed to get M-Pesa access token"
```

**Solutions:**
- Verify Consumer Key and Consumer Secret
- Check that you're using correct environment (sandbox vs production)
- Ensure API is enabled on Daraja portal
- Check CORS settings if using from different domain

### AI Agent Not Responding

```
Error: "AI Agent call failed"
```

**Solutions:**
- Verify API Key is correct (starts with `sk-ant-`)
- Check token balance in Anthropic console
- Verify model name is correct
- Check max tokens setting

### Payment Timeout

**Solutions:**
- Verify M-Pesa account has sufficient balance
- Check network connectivity
- Try with different phone number
- Contact M-Pesa support if issue persists

## Future Enhancements

- [ ] Implement webhook callbacks for M-Pesa
- [ ] Add payment history visualization
- [ ] Create admin dashboard for monitoring
- [ ] Implement subscription plans
- [ ] Add other payment methods (credit card, etc.)
- [ ] Multi-language support
- [ ] Rate limiting per user
- [ ] Referral program integration

## Support

For issues or questions:
1. Check Integration Status tab
2. Test connections individually
3. Review browser console for errors
4. Contact Safaricom Daraja support for M-Pesa issues
5. Contact Anthropic for Claude API issues

## Links

- [Safaricom Daraja Documentation](https://developer.safaricom.co.ke/docs)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference)
- [M-Pesa API Spec](https://developer.safaricom.co.ke/mpesa/apis)
