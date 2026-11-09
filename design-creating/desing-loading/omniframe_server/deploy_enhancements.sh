# [file name]: deploy_enhancements.sh
#!/bin/bash

echo "开始部署Omniframe AI文件管理系统增强功能..."

# 1. 备份现有文件
echo "1. 备份现有文件..."
BACKUP_DIR="./backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r core/*.py $BACKUP_DIR/ 2>/dev/null || true
cp -r services/*.py $BACKUP_DIR/ 2>/dev/null || true
echo "备份完成到: $BACKUP_DIR"

# 2. 创建新目录
echo "2. 创建新目录..."
mkdir -p core/interactive
mkdir -p config

# 3. 复制新文件
echo "3. 复制新文件..."

# 复制核心模块
cp interactive_service.py core/interactive/
cp enhanced_context_manager.py core/
cp enhanced_task_dispatcher.py core/

# 复制配置文件
cp interactive_settings.yaml config/

# 复制测试文件
cp enhanced_test_commands.py test_enhanced.py

echo "4. 更新requirements.txt..."
echo "websocket-client==1.7.0" >> requirements.txt
echo "pytest-asyncio==0.23.5" >> requirements.txt

echo "5. 创建符号链接（可选）..."
ln -sf core/enhanced_task_dispatcher.py core/task_dispatcher.py 2>/dev/null || true
ln -sf core/enhanced_context_manager.py core/context_manager.py 2>/dev/null || true

echo "6. 安装新依赖..."
pip install -r requirements.txt --upgrade

echo "7. 重启服务..."
pkill -f "uvicorn" || true
sleep 2

# 启动服务（根据实际情况调整）
cd omniframe_server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload &
cd ..

echo "8. 等待服务启动..."
sleep 5

echo "9. 运行测试..."
python test_enhanced.py

echo "部署完成！"
echo "新的API端点:"
echo "  POST /api/commands/execute - 执行命令（支持会话）"
echo "  WS   /api/commands/ws     - WebSocket实时交互"
echo ""
echo "测试命令: python test_enhanced.py"