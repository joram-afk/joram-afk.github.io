// ai-agent.js - AI Agent Service with M-Pesa Payment Integration
// Handles AI agent operations and payment processing

const AI_AGENT_CONFIG = {
  name: 'PaymentAgent',
  baseUrl: 'https://api.anthropic.com/v1', // Claude API (example)
  apiKey: localStorage.getItem('ai_agent_api_key') || 'YOUR_API_KEY',
  maxTokens: 1000,
  model: 'claude-3-sonnet-20240229',
  // Pricing for agent services (in KES)
  pricing: {
    basicQuery: 50,
    advancedAnalysis: 200,
    customReport: 500,
    premiumSupport: 1000
  }
};

// AI Agent Service Request Structure
class AIAgentService {
  constructor(config = AI_AGENT_CONFIG) {
    this.config = config;
    this.user = window.getLoggedInUser ? window.getLoggedInUser() : null;
  }

  // Process user query and generate response
  async processQuery(query, serviceType = 'basicQuery') {
    try {
      if (!this.user) {
        throw new Error('User must be logged in to use AI Agent');
      }

      const cost = this.config.pricing[serviceType];
      
      // Step 1: Initiate M-Pesa payment
      console.log(`Processing ${serviceType} - Amount: KES ${cost}`);
      const paymentResult = await this.initiatePayment({
        amount: cost,
        description: `AI Agent - ${serviceType}`,
        phoneNumber: this.user.phoneNumber || prompt('Enter your M-Pesa phone number (254xxxxxxxxx):')
      });

      if (!paymentResult.success) {
        throw new Error('Payment failed');
      }

      // Step 2: Wait for payment confirmation
      const paymentConfirmed = await this.waitForPaymentConfirmation(paymentResult.checkoutRequestID);
      
      if (!paymentConfirmed) {
        throw new Error('Payment timeout or cancelled');
      }

      // Step 3: Process the query with AI
      const aiResponse = await this.callAIAgent(query, serviceType);
      
      // Step 4: Log transaction
      await this.logTransaction({
        query: query,
        serviceType: serviceType,
        cost: cost,
        paymentId: paymentResult.checkoutRequestID,
        response: aiResponse,
        timestamp: new Date().toISOString()
      });

      return {
        success: true,
        response: aiResponse,
        cost: cost,
        paymentId: paymentResult.checkoutRequestID
      };
    } catch (error) {
      console.error('AI Agent query failed:', error);
      throw error;
    }
  }

  // Initiate M-Pesa payment
  async initiatePayment({ amount, description, phoneNumber }) {
    try {
      if (!window.initiateStkPush) {
        throw new Error('M-Pesa integration not loaded');
      }

      const result = await window.initiateStkPush({
        phoneNumber: phoneNumber,
        amount: amount,
        accountReference: `AI_AGENT_${Date.now()}`,
        transactionDesc: description
      });

      return {
        success: result.ResponseCode === '0',
        checkoutRequestID: result.CheckoutRequestID,
        message: result.ResponseDescription
      };
    } catch (error) {
      console.error('Payment initiation failed:', error);
      return { success: false, error: error.message };
    }
  }

  // Wait for M-Pesa payment confirmation (polling)
  async waitForPaymentConfirmation(checkoutRequestID, maxWaitTime = 30000) {
    const startTime = Date.now();
    const pollInterval = 2000; // Poll every 2 seconds

    while (Date.now() - startTime < maxWaitTime) {
      try {
        const status = await window.queryTransactionStatus(checkoutRequestID);
        
        if (status.ResultCode === '0') {
          console.log('Payment confirmed:', status);
          return true;
        }
        
        if (status.ResultCode !== '1032') { // 1032 = request pending
          console.log('Payment failed:', status);
          return false;
        }
      } catch (error) {
        console.error('Error checking payment status:', error);
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    console.log('Payment confirmation timeout');
    return false;
  }

  // Call AI Agent API (Claude example)
  async callAIAgent(query, serviceType) {
    try {
      // Example using Claude API (replace with your preferred AI service)
      const systemPrompt = this.getSystemPrompt(serviceType);
      
      // For client-side, this would typically go through a backend
      // For now, we'll return a mock response
      const response = await this.mockAIResponse(query, serviceType);
      
      return response;
    } catch (error) {
      console.error('AI Agent call failed:', error);
      throw error;
    }
  }

  // Get system prompt based on service type
  getSystemPrompt(serviceType) {
    const prompts = {
      basicQuery: 'You are a helpful assistant. Answer user queries concisely.',
      advancedAnalysis: 'You are an expert analyst. Provide detailed analysis and insights.',
      customReport: 'You are a professional report writer. Create comprehensive reports.',
      premiumSupport: 'You are a premium support specialist. Provide detailed solutions and recommendations.'
    };
    return prompts[serviceType] || prompts.basicQuery;
  }

  // Mock AI response (replace with actual API call)
  async mockAIResponse(query, serviceType) {
    // Simulate API latency
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
      query: query,
      response: `AI Response (${serviceType}): Analysis of your query "${query}" completed successfully.`,
      tokens: Math.floor(Math.random() * 500) + 100,
      timestamp: new Date().toISOString()
    };
  }

  // Log transaction to backend
  async logTransaction(transaction) {
    try {
      const userData = window.getCloud ? await window.getCloud() : {};
      userData.transactions = userData.transactions || [];
      userData.transactions.push(transaction);
      
      if (window.updateCloud) {
        await window.updateCloud(userData);
      }
      
      console.log('Transaction logged:', transaction);
    } catch (error) {
      console.error('Failed to log transaction:', error);
    }
  }

  // Get user transaction history
  async getTransactionHistory() {
    try {
      const userData = window.getCloud ? await window.getCloud() : {};
      return userData.transactions || [];
    } catch (error) {
      console.error('Failed to fetch transaction history:', error);
      return [];
    }
  }

  // Calculate total spent
  async getTotalSpent() {
    const transactions = await this.getTransactionHistory();
    return transactions.reduce((total, tx) => total + (tx.cost || 0), 0);
  }
}

// Initialize AI Agent Service
const aiAgentService = new AIAgentService();

// Expose to global scope
window.AIAgentService = AIAgentService;
window.aiAgentService = aiAgentService;
