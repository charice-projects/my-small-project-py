export interface ConversationMessage {
  index: number;
  timestamp: Date;
  role: 'user' | 'assistant';
  html: string;
  text: string;
  metadata: {
    position?: {
      x: number;
      y: number;
    };
    elementInfo: {
      tagName: string;
      className: string;
      id?: string;
    };
  };
}

export interface AssistantMessage extends ConversationMessage {
  role: 'assistant';
  formatAnalysis: {
    hasCodeBlocks: boolean;
    codeLanguages: string[];
    hasHeadings: boolean;
    headingLevels: number[];
    hasLists: boolean;
    hasTables: boolean;
  };
}

export interface UserMessage extends ConversationMessage {
  role: 'user';
}

export interface ConversationRound {
  index: number;
  timestamp: Date;
  user: UserMessage;
  assistant: AssistantMessage;
  metadata: {
    extractionConfidence: number;
    elementCount: number;
  };
}

export interface ExtractedConversation {
  version: string;
  metadata: {
    sourceUrl: string;
    extractedAt: string;
    extractorVersion: string;
    strategyUsed: string;
    confidenceScore: number;
    pageInfo: {
      title: string;
      urlHash: string;
      userAgent: string;
    };
  };
  conversation: ConversationRound[];
  extractionStats: {
    totalRounds: number;
    successRate: number;
    processingTimeMs: number;
    domElementsAnalyzed: number;
  };
}