export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  metadata?: {
    plan?: Record<string, unknown>;
    result?: Record<string, unknown>;
  };
}

export interface ChatPayload {
  question: string;
  pricingYamls: string[];
}
