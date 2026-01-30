import { ExtractedConversation } from '../../../shared/types/conversation';

export abstract class BaseStrategy {
  public abstract readonly name: string;
  public abstract readonly priority: number;

  /**
   * 执行策略
   */
  public abstract execute(): Promise<ExtractedConversation>;

  /**
   * 通用方法：查找对话容器
   */
  protected findConversationContainer(): Element | null {
    // 尝试多种选择器
    const selectors = [
      '[class*="conversation"]',
      '[class*="chat"]',
      '[class*="message"]',
      'main',
      'article',
      '.container',
      '#root > div',
      'body > div'
    ];

    for (const selector of selectors) {
      const elements = document.querySelectorAll(selector);
      for (const element of elements) {
        if (this.isConversationContainer(element)) {
          return element;
        }
      }
    }

    return null;
  }

  /**
   * 判断元素是否为对话容器
   */
  protected isConversationContainer(element: Element): boolean {
    const text = element.textContent || '';
    const children = element.children.length;
    
    // 启发式规则
    const hasUserMessages = element.querySelectorAll('[class*="user"], [class*="question"]').length > 0;
    const hasAssistantMessages = element.querySelectorAll('[class*="assistant"], [class*="answer"], [class*="response"]').length > 0;
    const hasMultipleMessages = element.querySelectorAll('[class*="message"], [class*="bubble"]').length >= 2;
    
    return (hasUserMessages && hasAssistantMessages) || hasMultipleMessages;
  }

  /**
   * 提取消息元素
   */
  protected extractMessageElements(container: Element): Element[] {
    const candidates = Array.from(container.querySelectorAll('*')).filter(element => {
      // 排除小元素
      if (element.textContent && element.textContent.trim().length < 10) {
        return false;
      }

      // 检查是否可能是消息
      const html = element.outerHTML.toLowerCase();
      const hasMessageIndicators = 
        html.includes('message') ||
        html.includes('bubble') ||
        html.includes('chat') ||
        element.classList.toString().toLowerCase().includes('message');

      return hasMessageIndicators;
    });

    // 去重（移除嵌套在另一个候选元素中的元素）
    return candidates.filter((element, index) => {
      return !candidates.some((other, otherIndex) => 
        otherIndex !== index && other.contains(element)
      );
    });
  }

  /**
   * 分类消息类型
   */
  protected classifyMessage(element: Element): 'user' | 'assistant' {
    const html = element.outerHTML.toLowerCase();
    const className = element.className.toLowerCase();
    const text = element.textContent?.toLowerCase() || '';

    // 用户消息特征
    const userIndicators = [
      className.includes('user'),
      className.includes('human'),
      className.includes('question'),
      html.includes('user'),
      text.includes('用户') || text.includes('question'),
      element.querySelector('[class*="user"]') !== null
    ];

    // AI消息特征
    const aiIndicators = [
      className.includes('assistant'),
      className.includes('ai'),
      className.includes('bot'),
      className.includes('answer'),
      html.includes('assistant'),
      text.includes('assistant') || text.includes('回答'),
      element.querySelector('[class*="assistant"]') !== null
    ];

    const userScore = userIndicators.filter(Boolean).length;
    const aiScore = aiIndicators.filter(Boolean).length;

    return userScore >= aiScore ? 'user' : 'assistant';
  }
}