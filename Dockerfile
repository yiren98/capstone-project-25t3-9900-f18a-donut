FROM python:3.11-slim

WORKDIR /app

# 复制 backend
COPY backend/ /app/backend/

# 复制 data
COPY data/ /app/data/

# 安装依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 设置工作目录为 backend
WORKDIR /app/backend

EXPOSE 5000

CMD ["python", "app.py"]

