FROM python:3.11-slim

WORKDIR /app

# 复制 backend
COPY backend/ /app/backend/

# 复制 data
COPY data/ /app/data/

# 安装依赖
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 切换到 backend 目录（这里有 app.py）
WORKDIR /app/backend

EXPOSE 5000

# 启动 Flask 后端
CMD ["python", "app.py"]
