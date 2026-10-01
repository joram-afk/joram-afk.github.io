// M-Pesa Payment Agent Service
// Handles autonomous AI-driven payments

interface MpesaCredentials {
  consumerKey: string;
  consumerSecret: string;
  shortcode: string;
  passkey: string;
  environment: 'sandbox' | 'production';
}

interface PaymentRequest {
  userId: number;
  amount: number;
  phoneNumber: string;
  description: string;
  accountReference: string;
  maxAttempts: number;
}

interface PaymentResult {
  success: boolean;
  transactionId: string | null;
  message: string;
  timestamp: string;
}

interface AIAgentContext {
  userId: number;
  userEmail: string;
  userPhone: string;
  userBalance: number;
  requestedAction: string;
  approvalRequired: boolean;
}

class MpesaPaymentAgent {
  private credentials: MpesaCredentials;
  private baseUrl: string;
  private accessToken: string | null = null;
  private tokenExpiry: number = 0;

  constructor(credentials: MpesaCredentials) {
    this.credentials = credentials;
    this.baseUrl = credentials.environment === 'production'
      ? 'https://api.safaricom.co.ke'
      : 'https://sandbox.safaricom.co.ke';
  }

  private async authenticate(): Promise<boolean> {
    try {
      const auth = btoa(
        `${this.credentials.consumerKey}:${this.credentials.consumerSecret}`
      );
      const response = await fetch(
        `${this.baseUrl}/oauth/v1/generate?grant_type=client_credentials`,
        {
          method: 'GET',
          headers: {
            Authorization: `Basic ${auth}`,
          },
        }
      );

      if (!response.ok) throw new Error('Authentication failed');
      const data = await response.json();
      this.accessToken = data.access_token;
      this.tokenExpiry = Date.now() + 3599000; // 59m59s
      return true;
    } catch (error) {
      console.error('M-Pesa authentication failed:', error);
      return false;
    }
  }

  private async getToken(): Promise<string> {
    if (!this.accessToken || Date.now() > this.tokenExpiry) {
      await this.authenticate();
    }
    return this.accessToken || '';
  }

  async executePayment(request: PaymentRequest): Promise<PaymentResult> {
    const token = await this.getToken();
    if (!token) {
      return {
        success: false,
        transactionId: null,
        message: 'Failed to obtain access token',
        timestamp: new Date().toISOString(),
      };
    }

    const timestamp = new Date()
      .toISOString()
      .replace(/[^0-9]/g, '')
      .substring(0, 14);
    const password = btoa(
      `${this.credentials.shortcode}${this.credentials.passkey}${timestamp}`
    );

    const payload = {
      BusinessShortCode: this.credentials.shortcode,
      Password: password,
      Timestamp: timestamp,
      TransactionType: 'CustomerPayBillOnline',
      Amount: request.amount,
      PartyA: request.phoneNumber,
      PartyB: this.credentials.shortcode,
      PhoneNumber: request.phoneNumber,
      CallBackURL: 'https://your-backend.example.com/api/mpesa/callback',
      AccountReference: request.accountReference,
      TransactionDesc: request.description,
    };

    try {
      const response = await fetch(
        `${this.baseUrl}/mpesa/stkpush/v1/processrequest`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (response.ok && data.ResponseCode === '0') {
        return {
          success: true,
          transactionId: data.CheckoutRequestID,
          message: data.CustomerMessage,
          timestamp: new Date().toISOString(),
        };
      } else {
        return {
          success: false,
          transactionId: null,
          message: data.errorMessage || data.ResponseDescription,
          timestamp: new Date().toISOString(),
        };
      }
    } catch (error) {
      return {
        success: false,
        transactionId: null,
        message: `Payment execution failed: ${error}`,
        timestamp: new Date().toISOString(),
      };
    }
  }

  async checkPaymentStatus(checkoutRequestId: string): Promise<boolean> {
    const token = await this.getToken();
    if (!token) return false;

    const timestamp = new Date()
      .toISOString()
      .replace(/[^0-9]/g, '')
      .substring(0, 14);
    const password = btoa(
      `${this.credentials.shortcode}${this.credentials.passkey}${timestamp}`
    );

    const payload = {
      BusinessShortCode: this.credentials.shortcode,
      CheckoutRequestID: checkoutRequestId,
      Password: password,
      Timestamp: timestamp,
    };

    try {
      const response = await fetch(
        `${this.baseUrl}/mpesa/transactionstatus/v1/query`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();
      return data.ResultCode === '0';
    } catch (error) {
      console.error('Failed to check payment status:', error);
      return false;
    }
  }
}

export { MpesaPaymentAgent, MpesaCredentials, PaymentRequest, PaymentResult, AIAgentContext };
