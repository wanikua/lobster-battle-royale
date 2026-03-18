#!/bin/bash
# 🦞 龙虾大乱斗 - 一键启动

set -e

echo "🦞 龙虾大乱斗 - 启动实验"
echo "========================="

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在！"
    echo "请先复制 .env.example 并填入 API Key："
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "📦 构建镜像..."
docker compose build

echo "🚀 启动所有服务..."
docker compose up -d

echo ""
echo "✅ 启动完成！"
echo ""
echo "📊 Dashboard: http://localhost:${DASHBOARD_PORT:-8080}"
echo "🔧 裁判 API:  http://localhost:${REFEREE_PORT:-8000}"
echo ""
echo "📋 常用命令："
echo "  查看日志:    docker compose logs -f"
echo "  查看状态:    docker compose ps"
echo "  开始游戏:    curl -X POST http://localhost:${REFEREE_PORT:-8000}/admin/start"
echo "  暂停游戏:    curl -X POST http://localhost:${REFEREE_PORT:-8000}/admin/pause"
echo "  触发事件:    curl -X POST http://localhost:${REFEREE_PORT:-8000}/admin/random-event"
echo "  停止实验:    ./scripts/stop.sh"
echo ""
echo "🦞 等待龙虾们就位后，运行以下命令开始战斗："
echo "  curl -X POST http://localhost:${REFEREE_PORT:-8000}/admin/start"
