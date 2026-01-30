import { ExtractedConversation } from '../../shared/types/conversation';
import { BaseStrategy } from './strategies/base-strategy';
import { ReactStrategy } from './strategies/react-strategy';
import { StructureStrategy } from './strategies/structure-strategy';
import { VisualStrategy } from './strategies/visual-strategy';
import { MessageClassifier } from './classifier/message-classifier';
import { ConversationPairer } from './pairing/conversation-pairer';

export class DOMIntelligentAnalyzer {
  private strategies: BaseStrategy[];
  private classifier: MessageClassifier;
  private pairer: ConversationPairer;
  private startTime: number;

  constructor() {
    this.startTime = Date.now();
    this.classifier = new MessageClassifier();
    this.pairer = new ConversationPairer();
    
    // 初始化多策略提取器
    this.strategies = [
      new ReactStrategy(),
      new StructureStrategy(),
      new VisualStrategy()
    ];
  }

  /**
   * 主分析流程
   */
  public async analyze(): Promise<ExtractedConversation> {
    console.log('🔍 开始DOM智能分析...');

    let bestResult: ExtractedConversation | null = null;
    let bestScore = 0;

    // 尝试多种策略，选择最佳结果
    for (const strategy of this.strategies) {
      try {
        console.log(`尝试策略: ${strategy.name}`);
        const result = await strategy.execute();
        const score = this.evaluateExtraction(result);

        if (score > bestScore) {
          bestScore = score;
          bestResult = result;
          console.log(`✅ 策略 ${strategy.name} 得分: ${score}`);
        }
      } catch (error) {
        console.warn(`策略 ${strategy.name} 失败:`, error);
      }
    }

    if (!bestResult) {
      throw new Error('所有提取策略均失败');
    }

    // 应用质量验证
    bestResult = this.validateAndEnhance(bestResult);

    const processingTime = Date.now() - this.startTime;
    bestResult.extractionStats.processingTimeMs = processingTime;

    console.log(`✅ 分析完成，耗时: ${processingTime}ms`);
    return bestResult;
  }

  /**
   * 评估提取结果质量
   */
  private evaluateExtraction(result: ExtractedConversation): number {
    let score = 0;

    // 1. 对话轮次数量
    if (result.conversation.length > 0) {
      score += Math.min(result.conversation.length * 10, 30);
    }

    // 2. 提取置信度
    const avgConfidence = result.conversation.reduce(
      (sum, round) => sum + round.metadata.extractionConfidence, 0
    ) / result.conversation.length;
    score += avgConfidence * 40;

    // 3. 内容完整性
    const hasCodeBlocks = result.conversation.some(
      round => round.assistant.formatAnalysis.hasCodeBlocks
    );
    const hasHeadings = result.conversation.some(
      round => round.assistant.formatAnalysis.hasHeadings
    );

    if (hasCodeBlocks) score += 15;
    if (hasHeadings) score += 15;

    return score;
  }

  /**
   * 验证和增强提取结果
   */
  private validateAndEnhance(result: ExtractedConversation): ExtractedConversation {
    // 移除空对话轮次
    result.conversation = result.conversation.filter(
      round => round.user.text.trim().length > 0 && 
              round.assistant.text.trim().length > 0
    );

    // 更新统计信息
    result.extractionStats.totalRounds = result.conversation.length;
    result.extractionStats.successRate = result.conversation.length > 0 ? 100 : 0;
    result.extractionStats.domElementsAnalyzed = document.querySelectorAll('*').length;

    // 添加元数据
    result.metadata.extractedAt = new Date().toISOString();
    result.metadata.sourceUrl = window.location.href;
    result.metadata.pageInfo = {
      title: document.title,
      urlHash: window.location.hash,
      userAgent: navigator.userAgent
    };

    return result;
  }
}