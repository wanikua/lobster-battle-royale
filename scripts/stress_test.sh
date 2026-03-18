#!/bin/bash
# 🦞 API 限流压力测试

echo "🔧 API 限流压力测试"
echo "==================="

API_KEY="${DASHSCOPE_API_KEY:-请设置环境变量}"
ENDPOINT="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

echo "📡 测试 API Key 连通性..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "说你好"}],
        "max_tokens": 10
    }')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ API Key 有效！"
else
    echo "❌ API 返回 $HTTP_CODE"
    echo "$BODY"
    exit 1
fi

echo ""
echo "🔨 开始压力测试（模拟 10 只龙虾同时调用）..."
echo "发送 30 个并发请求..."

START=$(date +%s)
SUCCESS=0
FAILED=0

for i in $(seq 1 30); do
    curl -s -o /dev/null -w "%{http_code}" -X POST "$ENDPOINT" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"qwen-plus\",
            \"messages\": [{\"role\": \"user\", \"content\": \"测试 $i\"}],
            \"max_tokens\": 5
        }" &
done

wait

END=$(date +%s)
DURATION=$((END - START))

echo ""
echo "📊 测试结果："
echo "  总请求: 30"
echo "  耗时: ${DURATION}s"
echo "  注意: 检查上面的 HTTP 状态码，200=成功，429=限流"
echo ""
echo "💡 建议："
echo "  如果出现 429，考虑："
echo "  1. 降低每只龙虾的调用频率"
echo "  2. 使用多个 API Key"
echo "  3. 减少龙虾数量"
