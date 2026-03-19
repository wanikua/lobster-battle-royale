FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建目录
RUN mkdir -p /app/public /app/data /app/services

# 复制代码
COPY . .

# 暴露漏洞 web 服务端口
EXPOSE 5000

CMD ["python", "main.py"]
