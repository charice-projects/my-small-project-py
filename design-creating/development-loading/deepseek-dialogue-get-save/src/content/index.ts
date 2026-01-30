import { DOMIntelligentAnalyzer } from './analyzer';
import { StandardizedFormatConverter } from './extractor/format-converter';
import { FloatingPanel } from './ui/floating-panel';

// 初始化扩展
class DeepSeekExtractor {
  private analyzer: DOMIntelligentAnalyzer;
  private converter: StandardizedFormatConverter;
  private floatingPanel: FloatingPanel;
  
  constructor() {
    console.log('🚀 DeepSeek对话提取器已加载');
    
    this.analyzer = new DOMIntelligentAnalyzer();
    this.converter = new StandardizedFormatConverter();
    this.floatingPanel = new FloatingPanel();
    
    this.init();
  }
  
  private init() {
    // 监听扩展消息
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sendResponse);
      return true; // 保持消息通道开放
    });
    
    // 初始化浮动面板
    this.floatingPanel.init();
    
    console.log('✅ DeepSeek提取器初始化完成');
  }
  
  private async handleMessage(request: any, sendResponse: (response: any) => void) {
    try {
      switch (request.action) {
        case 'extract':
          const result = await this.extractConversation();
          sendResponse({ success: true, data: result });
          break;
          
        case 'ping':
          sendResponse({ success: true, message: 'pong' });
          break;
          
        default:
          sendResponse({ success: false, error: '未知操作' });
      }
    } catch (error) {
      console.error('消息处理错误:', error);
      sendResponse({ success: false, error: error.message });
    }
  }
  
  private async extractConversation() {
    console.log('开始提取对话...');
    
    // 1. 使用智能分析器提取对话
    const extracted = await this.analyzer.analyze();
    
    // 2. 转换为标准格式
    const standardized = this.converter.convertToStandardFormat(extracted);
    
    console.log(`✅ 提取完成，共 ${extracted.conversation.length} 轮对话`);
    return standardized;
  }
}

// 启动扩展
new DeepSeekExtractor();