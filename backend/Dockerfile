FROM python:3.11-slim

WORKDIR /app

# 只复制 backend 内的代码
COPY . /app

# 复制整个 data 目录（从项目根目录）
COPY ../data /app/data

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
