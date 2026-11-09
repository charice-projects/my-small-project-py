# [file name]: rollback_deployment.sh
#!/bin/bash

echo "开始回滚部署..."

# 1. 停止服务
echo "1. 停止服务..."
pkill -f "uvicorn" || true
sleep 2

# 2. 恢复备份
echo "2. 恢复备份..."
if [ -z "$1" ]; then
    echo "请指定备份目录: ./rollback_deployment.sh <备份目录>"
    exit 1
fi

BACKUP_DIR=$1

if [ ! -d "$BACKUP_DIR" ]; then
    echo "备份目录不存在: $BACKUP_DIR"
    exit 1
fi

# 恢复核心文件
cp $BACKUP_DIR/*.py core/ 2>/dev/null || true

# 3. 启动服务
echo "3. 启动服务..."
cd omniframe_server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload &
cd ..

echo "4. 等待服务启动..."
sleep 5

echo "5. 运行原始测试..."
python test_commands.py

echo "回滚完成！"