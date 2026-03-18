#!/bin/bash
# 🦞 龙虾大乱斗 - 停止实验

echo "🛑 停止龙虾大乱斗..."
docker compose down

echo "✅ 所有服务已停止"
echo ""
echo "💾 数据保留在 Docker volume 中"
echo "  清除数据: docker compose down -v"
