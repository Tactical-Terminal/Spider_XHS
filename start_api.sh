#!/bin/bash
# 小红书API服务启动脚本 (Linux)

echo "==================================="
echo "   小红书API服务启动脚本"
echo "==================================="

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 检查.env文件
if [ ! -f .env ]; then
    echo "警告: 未找到.env配置文件"
    echo "正在从.env.example创建.env文件..."
    cp .env.example .env
    echo "请编辑 .env 文件并填入您的小红书Cookies"
    echo "然后重新运行此脚本"
    exit 1
fi

# 检查依赖是否安装
echo "检查依赖..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 启动服务器
echo ""
echo "正在启动API服务器..."
echo "按 Ctrl+C 停止服务器"
echo ""

python3 api_server.py
