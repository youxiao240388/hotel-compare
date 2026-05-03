# 酒店比价工具 - Dockerfile
FROM python:3.11-slim

LABEL description="酒店多平台比价工具 - DrissionPage + DeepSeek LLM"

# 安装 Chrome 和依赖
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    curl \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# Chrome 环境变量
ENV CHROME_PATH=/usr/bin/chromium
ENV CHROME_BIN=/usr/bin/chromium

# 工作目录
WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目
COPY . .

# 创建 Chrome 用户数据目录
RUN mkdir -p /root/.hotel-compare/chrome-profile

# 入口
ENTRYPOINT ["python3", "main.py"]
CMD ["--help"]
