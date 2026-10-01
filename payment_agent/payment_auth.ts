// AI Agent Payment Authorization
// Handles user approval for AI-driven transactions

import { AIAgentContext } from './mpesa_agent';

interface ApprovalPolicy {
  maxTransactionAmount: number;
  maxDailyAmount: number;
  requireApprovalAbove: number;
  allowedServices: string[];
  timeWindow: 'always' | 'business_hours' | 'custom';
  customHours?: { start: number; end: number }; // 0-23
}

interface UserApprovalLog {
  transactionId: string;
  userId: number;
  amount: number;
  description: string;
  approvedAt: string;
  expiresAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
}

class PaymentAuthorizer {
  private policy: ApprovalPolicy;
  private approvalLogs: Map<number, UserApprovalLog[]> = new Map();

  constructor(policy: ApprovalPolicy) {
    this.policy = policy;
  }

  canExecuteAutonomously(context: AIAgentContext): boolean {
    // Check if transaction amount is within autonomous limit
    if (context.requestedAction !== 'payment') return false;
    if (context.userBalance < 100) return false; // Minimum balance

    // Check time window
    if (!this.isWithinTimeWindow()) return false;

    return true;
  }

  private isWithinTimeWindow(): boolean {
    if (this.policy.timeWindow === 'always') return true;

    const now = new Date();
    const hour = now.getHours();

    if (this.policy.timeWindow === 'business_hours') {
      return hour >= 9 && hour <= 17; // 9 AM to 5 PM
    }

    if (this.policy.timeWindow === 'custom' && this.policy.customHours) {
      return hour >= this.policy.customHours.start && hour <= this.policy.customHours.end;
    }

    return false;
  }

  requiresApproval(amount: number): boolean {
    return amount > this.policy.requireApprovalAbove;
  }

  canProcessTransaction(userId: number, amount: number): boolean {
    if (amount > this.policy.maxTransactionAmount) return false;

    const userLogs = this.approvalLogs.get(userId) || [];
    const today = new Date().toISOString().split('T')[0];
    const dailySpent = userLogs
      .filter((log) => log.approvedAt.startsWith(today) && log.status === 'approved')
      .reduce((sum, log) => sum + log.amount, 0);

    return dailySpent + amount <= this.policy.maxDailyAmount;
  }

  recordApproval(log: UserApprovalLog): void {
    if (!this.approvalLogs.has(log.userId)) {
      this.approvalLogs.set(log.userId, []);
    }
    this.approvalLogs.get(log.userId)!.push(log);
  }
}

class AIPaymentAgent {
  private authorizer: PaymentAuthorizer;

  constructor(approvalPolicy: ApprovalPolicy) {
    this.authorizer = new PaymentAuthorizer(approvalPolicy);
  }

  async requestUserApproval(
    context: AIAgentContext,
    amount: number,
    reason: string
  ): Promise<boolean> {
    // In a real system, this would send a notification/push
    console.log(`
[APPROVAL REQUEST]
User: ${context.userEmail}
Amount: ${amount} KES
Reason: ${reason}
Phone: ${context.userPhone}
`);

    // Mock approval (replace with real notification system)
    return new Promise((resolve) => {
      // In production: send SMS/push, wait for response
      console.log('Awaiting user approval via SMS/Push...');
      setTimeout(() => resolve(true), 2000);
    });
  }

  async canExecutePayment(context: AIAgentContext, amount: number): Promise<boolean> {
    if (this.authorizer.canExecuteAutonomously(context)) {
      return this.authorizer.canProcessTransaction(context.userId, amount);
    }

    if (this.authorizer.requiresApproval(amount)) {
      return await this.requestUserApproval(context, amount, 'AI Agent Payment');
    }

    return false;
  }
}

export { PaymentAuthorizer, AIPaymentAgent, ApprovalPolicy, UserApprovalLog };
