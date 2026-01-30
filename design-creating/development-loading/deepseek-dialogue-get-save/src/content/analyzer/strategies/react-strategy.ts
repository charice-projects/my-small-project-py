import { BaseStrategy } from './base-strategy';
import { ExtractedConversation, ConversationRound } from '../../../shared/types/conversation';
import DOMPurify from 'dompurify';

export class ReactStrategy extends BaseStrategy {
  public readonly name = 'React组件分析策略';
  public readonly priority = 100; // 最高优先级

  public async execute(): Promise<ExtractedConversation> {
    console.log('🔬 使用React策略分析页面...');

    const container = this.findConversationContainer();
    if (!container) {
      throw new Error('未找到对话容器');
    }

    // 尝试通过React DevTools Bridge获取组件数据
    const reactData = await this.tryGetReactData(container);
    
    if (reactData && reactData.messages) {
      return this.extractFromReactData(reactData);
    }

    // 回退到DOM分析
    return this.extractFromDOM(container);
  }

  /**
   * 尝试通过React DevTools获取数据
   */
  private async tryGetReactData(container: Element): Promise<any> {
    try {
      // 检查React DevTools是否可用
      if ((window as any).__REACT_DEVTOOLS_GLOBAL_HOOK__) {
        console.log('✅ React DevTools可用');
        
        // 尝试查找React Fiber节点
        const reactRoot = this.findReactRoot(container);
        if (reactRoot) {
          return this.extractReactFiberData(reactRoot);
        }
      }
    } catch (error) {
      console.warn('React数据提取失败:', error);
    }
    
    return null;
  }

  /**
   * 查找React根节点
   */
  private findReactRoot(element: Element): any {
    let current = element;
    
    for (let i = 0; i < 10 && current; i++) {
      const keys = Object.keys(current);
      const reactKey = keys.find(key => 
        key.startsWith('__reactFiber$') || 
        key.startsWith('__reactProps$')
      );
      
      if (reactKey) {
        return (current as any)[reactKey];
      }
      
      current = current.parentElement as Element;
    }
    
    return null;
  }

  /**
   * 从React Fiber数据提取
   */
  private extractReactFiberData(fiber: any): any {
    const messages: any[] = [];
    
    // 遍历Fiber树
    const traverse = (node: any, depth = 0) => {
      if (!node) return;
      
      // 检查节点类型
      const type = node.type;
      const props = node.memoizedProps || {};
      
      // 检查是否可能是消息组件
      if (props && this.isMessageComponent(type, props)) {
        messages.push({
          role: this.detectRoleFromComponent(type, props),
          content: props.children || props.content,
          props
        });
      }
      
      // 遍历子节点和兄弟节点
      if (node.child) traverse(node.child, depth + 1);
      if (node.sibling) traverse(node.sibling, depth);
    };
    
    traverse(fiber);
    return { messages };
  }

  /**
   * 判断是否为消息组件
   */
  private isMessageComponent(type: any, props: any): boolean {
    if (!type) return false;
    
    const typeName = typeof type === 'string' 
      ? type 
      : (type.displayName || type.name || '');
    
    const propKeys = Object.keys(props);
    
    const indicators = [
      typeName.toLowerCase().includes('message'),
      typeName.toLowerCase().includes('chat'),
      typeName.toLowerCase().includes('bubble'),
      propKeys.some(key => key.toLowerCase().includes('message')),
      propKeys.some(key => key.toLowerCase().includes('role')),
      props.role === 'user' || props.role === 'assistant'
    ];
    
    return indicators.some(Boolean);
  }

  /**
   * 从组件检测角色
   */
  private detectRoleFromComponent(type: any, props: any): 'user' | 'assistant' {
    if (props.role) {
      return props.role === 'user' ? 'user' : 'assistant';
    }
    
    const typeName = typeof type === 'string' 
      ? type 
      : (type.displayName || type.name || '').toLowerCase();
    
    if (typeName.includes('user') || typeName.includes('human')) {
      return 'user';
    }
    
    return 'assistant';
  }

  /**
   * 从React数据提取对话
   */
  private extractFromReactData(reactData: any): ExtractedConversation {
    const conversation: ConversationRound[] = [];
    let userMessage: any = null;
    
    // 配对用户和AI消息
    reactData.messages.forEach((message: any, index: number) => {
      if (message.role === 'user') {
        userMessage = message;
      } else if (message.role === 'assistant' && userMessage) {
        const round = this.createConversationRound(
          conversation.length + 1,
          userMessage,
          message
        );
        conversation.push(round);
        userMessage = null;
      }
    });
    
    return this.createExtractedConversation(conversation, 'react-strategy');
  }

  /**
   * 从DOM提取（回退策略）
   */
  private extractFromDOM(container: Element): ExtractedConversation {
    const elements = this.extractMessageElements(container);
    const conversation: ConversationRound[] = [];
    let userMessage: Element | null = null;
    
    elements.forEach((element, index) => {
      const role = this.classifyMessage(element);
      
      if (role === 'user') {
        userMessage = element;
      } else if (role === 'assistant' && userMessage) {
        const round = this.createConversationRoundFromElements(
          conversation.length + 1,
          userMessage,
          element
        );
        conversation.push(round);
        userMessage = null;
      }
    });
    
    return this.createExtractedConversation(conversation, 'dom-fallback');
  }

  /**
   * 创建对话轮次（从React数据）
   */
  private createConversationRound(
    index: number,
    userMessage: any,
    assistantMessage: any
  ): ConversationRound {
    const now = new Date();
    
    return {
      index,
      timestamp: now,
      user: {
        index,
        timestamp: now,
        role: 'user' as const,
        html: this.sanitizeHTML(userMessage.content || ''),
        text: this.extractText(userMessage.content || ''),
        metadata: {
          elementInfo: {
            tagName: 'div',
            className: 'react-user-message'
          }
        }
      },
      assistant: {
        index,
        timestamp: now,
        role: 'assistant' as const,
        html: this.sanitizeHTML(assistantMessage.content || ''),
        text: this.extractText(assistantMessage.content || ''),
        formatAnalysis: this.analyzeFormat(assistantMessage.content || ''),
        metadata: {
          elementInfo: {
            tagName: 'div',
            className: 'react-assistant-message'
          }
        }
      },
      metadata: {
        extractionConfidence: 0.9,
        elementCount: 2
      }
    };
  }

  /**
   * 创建对话轮次（从DOM元素）
   */
  private createConversationRoundFromElements(
    index: number,
    userElement: Element,
    assistantElement: Element
  ): ConversationRound {
    const now = new Date();
    
    return {
      index,
      timestamp: now,
      user: {
        index,
        timestamp: now,
        role: 'user' as const,
        html: this.sanitizeHTML(userElement.outerHTML),
        text: this.extractText(userElement.textContent || ''),
        metadata: {
          elementInfo: {
            tagName: userElement.tagName,
            className: userElement.className
          }
        }
      },
      assistant: {
        index,
        timestamp: now,
        role: 'assistant' as const,
        html: this.sanitizeHTML(assistantElement.outerHTML),
        text: this.extractText(assistantElement.textContent || ''),
        formatAnalysis: this.analyzeFormat(assistantElement.outerHTML),
        metadata: {
          elementInfo: {
            tagName: assistantElement.tagName,
            className: assistantElement.className
          }
        }
      },
      metadata: {
        extractionConfidence: this.calculateConfidence(userElement, assistantElement),
        elementCount: 2
      }
    };
  }

  /**
   * 创建提取结果
   */
  private createExtractedConversation(
    conversation: ConversationRound[],
    strategyUsed: string
  ): ExtractedConversation {
    const confidenceScore = conversation.length > 0 
      ? conversation.reduce((sum, round) => sum + round.metadata.extractionConfidence, 0) / conversation.length
      : 0;
    
    return {
      version: '1.0',
      metadata: {
        sourceUrl: window.location.href,
        extractedAt: new Date().toISOString(),
        extractorVersion: '1.0.0',
        strategyUsed,
        confidenceScore,
        pageInfo: {
          title: document.title,
          urlHash: window.location.hash,
          userAgent: navigator.userAgent
        }
      },
      conversation,
      extractionStats: {
        totalRounds: conversation.length,
        successRate: conversation.length > 0 ? 100 : 0,
        processingTimeMs: 0,
        domElementsAnalyzed: document.querySelectorAll('*').length
      }
    };
  }

  /**
   * 工具方法
   */
  private sanitizeHTML(html: string): string {
    return DOMPurify.sanitize(html);
  }

  private extractText(html: string): string {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    return temp.textContent?.trim() || '';
  }

  private analyzeFormat(html: string) {
    const hasCodeBlocks = /<pre>|<code>|```/.test(html);
    const hasHeadings = /<h[1-6]/.test(html);
    const hasLists = /<ul>|<ol>|<li>/.test(html);
    const hasTables = /<table>/.test(html);
    
    // 提取标题层级
    const headingLevels: number[] = [];
    const headingMatches = html.match(/<h([1-6])/g) || [];
    headingMatches.forEach(match => {
      const level = parseInt(match.charAt(2));
      if (!headingLevels.includes(level)) {
        headingLevels.push(level);
      }
    });
    
    // 检测代码语言
    const codeLanguages: string[] = [];
    const codeMatches = html.match(/```(\w+)/g) || [];
    codeMatches.forEach(match => {
      const lang = match.slice(3);
      if (!codeLanguages.includes(lang)) {
        codeLanguages.push(lang);
      }
    });
    
    return {
      hasCodeBlocks,
      codeLanguages,
      hasHeadings,
      headingLevels,
      hasLists,
      hasTables
    };
  }

  private calculateConfidence(userElement: Element, assistantElement: Element): number {
    let confidence = 0.7; // 基础置信度
    
    // 基于位置关系
    const userRect = userElement.getBoundingClientRect();
    const assistantRect = assistantElement.getBoundingClientRect();
    
    if (assistantRect.top > userRect.bottom) {
      confidence += 0.2; // AI消息在用户消息下方
    }
    
    // 基于样式相似性
    const userClasses = userElement.className;
    const assistantClasses = assistantElement.className;
    
    if (userClasses && assistantClasses) {
      const commonWords = this.findCommonWords(userClasses, assistantClasses);
      if (commonWords.length > 0) {
        confidence += 0.1;
      }
    }
    
    return Math.min(confidence, 0.95);
  }

  private findCommonWords(str1: string, str2: string): string[] {
    const words1 = str1.toLowerCase().split(/[^a-z]/).filter(Boolean);
    const words2 = str2.toLowerCase().split(/[^a-z]/).filter(Boolean);
    
    return words1.filter(word => words2.includes(word));
  }
}