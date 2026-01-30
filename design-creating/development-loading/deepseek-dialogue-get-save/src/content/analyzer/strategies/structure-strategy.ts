import { BaseStrategy } from './base-strategy';
import { ExtractedConversation, ConversationRound } from '../../../shared/types/conversation';
import DOMPurify from 'dompurify';

export class StructureStrategy extends BaseStrategy {
  public readonly name = 'DOM结构分析策略';
  public readonly priority = 80;

  public async execute(): Promise<ExtractedConversation> {
    console.log('🏗️ 使用DOM结构分析策略...');

    const container = this.findConversationContainer();
    if (!container) {
      throw new Error('未找到对话容器');
    }

    // 分析页面整体结构
    const pageStructure = this.analyzePageStructure();
    const conversation = this.extractUsingStructureAnalysis(container, pageStructure);

    return this.createExtractedConversation(conversation);
  }

  /**
   * 分析页面整体结构
   */
  private analyzePageStructure() {
    const structure = {
      totalElements: document.querySelectorAll('*').length,
      depth: this.calculateMaxDepth(document.body),
      semanticElements: {
        main: document.querySelectorAll('main').length,
        article: document.querySelectorAll('article').length,
        section: document.querySelectorAll('section').length,
        header: document.querySelectorAll('header').length,
        footer: document.querySelectorAll('footer').length,
        nav: document.querySelectorAll('nav').length
      },
      layoutPatterns: this.detectLayoutPatterns()
    };

    console.log('页面结构分析:', structure);
    return structure;
  }

  /**
   * 计算DOM最大深度
   */
  private calculateMaxDepth(element: Element, depth = 0): number {
    const children = element.children;
    if (children.length === 0) return depth;
    
    let maxChildDepth = depth;
    for (const child of children) {
      const childDepth = this.calculateMaxDepth(child, depth + 1);
      if (childDepth > maxChildDepth) {
        maxChildDepth = childDepth;
      }
    }
    
    return maxChildDepth;
  }

  /**
   * 检测布局模式
   */
  private detectLayoutPatterns() {
    const patterns = [];
    
    // 检测是否使用常见布局类
    const commonLayoutClasses = [
      'container', 'wrapper', 'content', 'sidebar',
      'layout', 'grid', 'flex', 'chat-container',
      'message-list', 'conversation-panel'
    ];
    
    const classPatterns = commonLayoutClasses.filter(cls => 
      document.querySelector(`[class*="${cls}"]`) !== null
    );
    
    if (classPatterns.length > 0) {
      patterns.push(`使用常见布局类: ${classPatterns.join(', ')}`);
    }
    
    // 检测Flexbox布局
    const flexElements = Array.from(document.querySelectorAll('*')).filter(el => {
      const style = window.getComputedStyle(el);
      return style.display === 'flex';
    });
    
    if (flexElements.length > 10) {
      patterns.push('使用Flexbox布局');
    }
    
    // 检测网格布局
    const gridElements = Array.from(document.querySelectorAll('*')).filter(el => {
      const style = window.getComputedStyle(el);
      return style.display === 'grid';
    });
    
    if (gridElements.length > 5) {
      patterns.push('使用Grid布局');
    }
    
    return patterns;
  }

  /**
   * 使用结构分析提取对话
   */
  private extractUsingStructureAnalysis(container: Element, pageStructure: any): ConversationRound[] {
    const conversation: ConversationRound[] = [];
    
    // 使用树形结构分析
    const messageClusters = this.findMessageClusters(container);
    console.log(`找到 ${messageClusters.length} 个消息簇`);
    
    // 处理每个消息簇
    for (const cluster of messageClusters) {
      const round = this.processMessageCluster(cluster);
      if (round) {
        conversation.push(round);
      }
    }
    
    // 如果聚类失败，使用回退策略
    if (conversation.length === 0) {
      console.log('聚类失败，使用顺序配对策略...');
      return this.fallbackToSequentialPairing(container);
    }
    
    return conversation;
  }

  /**
   * 查找消息簇（根据结构相似性聚类）
   */
  private findMessageClusters(container: Element): Element[][] {
    const allElements = Array.from(container.querySelectorAll('*'));
    
    // 过滤可能的消息元素
    const candidateElements = allElements.filter(element => {
      const text = element.textContent?.trim() || '';
      const html = element.outerHTML;
      
      // 排除小元素
      if (text.length < 20 && !this.containsCode(element)) {
        return false;
      }
      
      // 检查结构特征
      const children = element.children.length;
      const depth = this.calculateMaxDepth(element);
      const hasComplexContent = children > 0 || depth > 2;
      
      return hasComplexContent && text.length > 10;
    });
    
    console.log(`候选元素: ${candidateElements.length}`);
    
    // 根据结构相似性聚类
    const clusters: Element[][] = [];
    const processed = new Set<Element>();
    
    for (const element of candidateElements) {
      if (processed.has(element)) continue;
      
      const cluster = [element];
      processed.add(element);
      
      // 查找相似结构的相邻元素
      const elementSignature = this.calculateElementSignature(element);
      
      // 检查前后兄弟元素
      let prevSibling = element.previousElementSibling;
      let nextSibling = element.nextElementSibling;
      
      // 向前查找
      while (prevSibling && candidateElements.includes(prevSibling) && !processed.has(prevSibling)) {
        const prevSignature = this.calculateElementSignature(prevSibling);
        if (this.isSimilarSignature(elementSignature, prevSignature)) {
          cluster.unshift(prevSibling);
          processed.add(prevSibling);
        }
        prevSibling = prevSibling.previousElementSibling;
      }
      
      // 向后查找
      while (nextSibling && candidateElements.includes(nextSibling) && !processed.has(nextSibling)) {
        const nextSignature = this.calculateElementSignature(nextSibling);
        if (this.isSimilarSignature(elementSignature, nextSignature)) {
          cluster.push(nextSibling);
          processed.add(nextSibling);
        }
        nextSibling = nextSibling.nextElementSibling;
      }
      
      if (cluster.length >= 2) {
        clusters.push(cluster);
      }
    }
    
    // 按大小排序
    clusters.sort((a, b) => b.length - a.length);
    
    return clusters;
  }

  /**
   * 计算元素特征签名
   */
  private calculateElementSignature(element: Element): string {
    const features: string[] = [];
    
    // 标签名
    features.push(`tag:${element.tagName.toLowerCase()}`);
    
    // 类名（取前3个）
    const classes = element.className.split(/\s+/).filter(Boolean);
    classes.slice(0, 3).forEach(cls => {
      features.push(`cls:${cls}`);
    });
    
    // 子元素数量
    features.push(`children:${element.children.length}`);
    
    // 文本长度范围
    const textLength = element.textContent?.length || 0;
    if (textLength < 100) features.push('text:short');
    else if (textLength < 500) features.push('text:medium');
    else features.push('text:long');
    
    // 是否包含代码
    if (this.containsCode(element)) {
      features.push('has:code');
    }
    
    // 是否包含列表
    if (element.querySelector('ul, ol, li')) {
      features.push('has:list');
    }
    
    // 是否包含图片
    if (element.querySelector('img')) {
      features.push('has:img');
    }
    
    return features.join('|');
  }

  /**
   * 判断特征是否相似
   */
  private isSimilarSignature(sig1: string, sig2: string): boolean {
    const features1 = new Set(sig1.split('|'));
    const features2 = new Set(sig2.split('|'));
    
    // 计算Jaccard相似度
    const intersection = new Set([...features1].filter(x => features2.has(x)));
    const union = new Set([...features1, ...features2]);
    
    const similarity = intersection.size / union.size;
    return similarity > 0.6; // 相似度阈值
  }

  /**
   * 处理消息簇
   */
  private processMessageCluster(cluster: Element[]): ConversationRound | null {
    if (cluster.length < 2) return null;
    
    // 尝试将簇中的元素配对为用户和AI消息
    let userElement: Element | null = null;
    let assistantElement: Element | null = null;
    
    for (const element of cluster) {
      const role = this.classifyMessage(element);
      
      if (role === 'user' && !userElement) {
        userElement = element;
      } else if (role === 'assistant' && !assistantElement) {
        assistantElement = element;
      }
      
      if (userElement && assistantElement) {
        break;
      }
    }
    
    if (userElement && assistantElement) {
      return this.createConversationRound(
        cluster.indexOf(userElement) + cluster.indexOf(assistantElement),
        userElement,
        assistantElement
      );
    }
    
    return null;
  }

  /**
   * 回退策略：顺序配对
   */
  private fallbackToSequentialPairing(container: Element): ConversationRound[] {
    const elements = this.extractMessageElements(container);
    const conversation: ConversationRound[] = [];
    let userElement: Element | null = null;
    
    // 按顺序处理元素
    for (let i = 0; i < elements.length; i++) {
      const element = elements[i];
      const role = this.classifyMessage(element);
      
      if (role === 'user') {
        userElement = element;
      } else if (role === 'assistant' && userElement) {
        // 检查用户和AI消息是否在合理距离内
        const userIndex = elements.indexOf(userElement);
        if (i - userIndex <= 3) { // 最多间隔2个其他元素
          const round = this.createConversationRound(
            conversation.length + 1,
            userElement,
            element
          );
          conversation.push(round);
          userElement = null;
        }
      }
    }
    
    return conversation;
  }

  /**
   * 创建对话轮次
   */
  private createConversationRound(
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
        html: DOMPurify.sanitize(userElement.outerHTML),
        text: this.extractText(userElement),
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
        html: DOMPurify.sanitize(assistantElement.outerHTML),
        text: this.extractText(assistantElement),
        formatAnalysis: this.analyzeFormat(assistantElement),
        metadata: {
          elementInfo: {
            tagName: assistantElement.tagName,
            className: assistantElement.className
          }
        }
      },
      metadata: {
        extractionConfidence: this.calculateStructureConfidence(userElement, assistantElement),
        elementCount: 2
      }
    };
  }

  /**
   * 创建提取结果
   */
  private createExtractedConversation(conversation: ConversationRound[]): ExtractedConversation {
    const confidenceScore = conversation.length > 0 
      ? conversation.reduce((sum, round) => sum + round.metadata.extractionConfidence, 0) / conversation.length
      : 0;
    
    return {
      version: '1.0',
      metadata: {
        sourceUrl: window.location.href,
        extractedAt: new Date().toISOString(),
        extractorVersion: '1.0.0',
        strategyUsed: 'structure-analysis',
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
  private containsCode(element: Element): boolean {
    return element.querySelector('pre, code') !== null || 
           element.textContent?.includes('```') ||
           /<pre>|<code>|```/.test(element.outerHTML);
  }

  private extractText(element: Element): string {
    return element.textContent?.trim() || '';
  }

  private analyzeFormat(element: Element) {
    const html = element.outerHTML;
    const hasCodeBlocks = this.containsCode(element);
    const hasHeadings = /<h[1-6]/.test(html);
    const hasLists = element.querySelector('ul, ol, li') !== null;
    const hasTables = element.querySelector('table') !== null;
    
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

  private calculateStructureConfidence(userElement: Element, assistantElement: Element): number {
    let confidence = 0.6; // 基础置信度
    
    // 1. 检查DOM层次关系
    const userPath = this.getElementPath(userElement);
    const assistantPath = this.getElementPath(assistantElement);
    
    // 检查路径相似度
    const pathSimilarity = this.calculatePathSimilarity(userPath, assistantPath);
    confidence += pathSimilarity * 0.2;
    
    // 2. 检查位置关系
    const userRect = userElement.getBoundingClientRect();
    const assistantRect = assistantElement.getBoundingClientRect();
    
    if (assistantRect.top > userRect.bottom && 
        assistantRect.top - userRect.bottom < 500) {
      confidence += 0.15; // 合理的位置关系
    }
    
    // 3. 检查样式相似性
    const styleSimilarity = this.calculateStyleSimilarity(userElement, assistantElement);
    confidence += styleSimilarity * 0.15;
    
    return Math.min(confidence, 0.95);
  }

  private getElementPath(element: Element): string {
    const path: string[] = [];
    let current: Element | null = element;
    
    for (let i = 0; i < 5 && current; i++) {
      const tag = current.tagName.toLowerCase();
      const id = current.id ? `#${current.id}` : '';
      const classes = current.className ? `.${current.className.split(' ').join('.')}` : '';
      path.unshift(tag + id + classes);
      current = current.parentElement;
    }
    
    return path.join(' > ');
  }

  private calculatePathSimilarity(path1: string, path2: string): number {
    const parts1 = path1.split(' > ');
    const parts2 = path2.split(' > ');
    
    let matches = 0;
    const minLength = Math.min(parts1.length, parts2.length);
    
    for (let i = 0; i < minLength; i++) {
      if (parts1[i] === parts2[i]) {
        matches++;
      }
    }
    
    return matches / Math.max(parts1.length, parts2.length);
  }

  private calculateStyleSimilarity(element1: Element, element2: Element): number {
    const style1 = window.getComputedStyle(element1);
    const style2 = window.getComputedStyle(element2);
    
    const properties = [
      'display', 'position', 'float', 'clear',
      'width', 'height', 'margin', 'padding',
      'border', 'background', 'color', 'font',
      'textAlign', 'lineHeight'
    ];
    
    let matches = 0;
    properties.forEach(prop => {
      if (style1[prop as any] === style2[prop as any]) {
        matches++;
      }
    });
    
    return matches / properties.length;
  }
}