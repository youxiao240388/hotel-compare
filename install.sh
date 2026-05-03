#!/usr/bin/env bash
# 酒店比价工具 - 一键安装脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "🏨 酒店多平台比价工具 - 一键安装"
echo "===================================="

# 检测 Python
if command -v python3 &>/dev/null; then
    echo "✅ Python3: $(python3 --version)"
else
    echo "❌ 请先安装 Python 3.10+"
    exit 1
fi

# 检测 Chrome/Chromium
CHROME=""
for c in google-chrome google-chrome-stable chromium-browser chromium; do
    if command -v "$c" &>/dev/null; then
        CHROME="$c"
        echo "✅ Chrome: $($c --version 2>/dev/null || echo 'found')"
        break
    fi
done
if [ -z "$CHROME" ]; then
    echo "⚠️  未找到 Chrome，尝试安装 Chromium..."
    if command -v apt &>/dev/null; then
        sudo apt update && sudo apt install -y chromium-browser
    elif command -v brew &>/dev/null; then
        brew install chromium
    else
        echo "❌ 请手动安装 Chrome 或 Chromium"
        exit 1
    fi
fi

# 安装 Python 依赖
echo ""
echo "📦 安装 Python 依赖..."
cd "$SCRIPT_DIR"
pip install -r requirements.txt -q

# 创建数据目录
mkdir -p data/history data/embeddings
mkdir -p ~/.hotel-compare/chrome-profile

# 设置 DeepSeek API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo ""
    echo "🔑 请输入 DeepSeek API Key（在 https://platform.deepseek.com 获取）："
    read -r API_KEY
    if [ -n "$API_KEY" ]; then
        echo "export DEEPSEEK_API_KEY=$API_KEY" >> ~/.bashrc
        export DEEPSEEK_API_KEY="$API_KEY"
        echo "✅ API Key 已保存到 ~/.bashrc"
    fi
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "使用方法："
echo "  python main.py --hotel \"酒店名称\" --checkin 2024-06-01 --checkout 2024-06-02"
echo ""
echo "定时监控："
echo "  python main.py --hotel \"酒店名称\" --checkin 2024-06-01 --monitor --interval 6h"
