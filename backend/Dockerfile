FROM python:3.11-slim AS backend

WORKDIR /app

# 复制后端代码
COPY backend/ ./backend/
COPY data/ ./data/     # ✅ 一定要加上这行！
COPY crawler/ ./crawler/
COPY deployment/ ./deployment/


# 安装依赖
RUN pip install --no-cache-dir -r backend/requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PORT=5000

EXPOSE 5000

CMD ["python", "backend/app.py"]
