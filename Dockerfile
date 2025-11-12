
# -------------------------
FROM node:18 AS frontend-build

WORKDIR /frontend
COPY frontend/ ./
RUN npm install && npm run build


# -------------------------
FROM python:3.11-slim AS backend

WORKDIR /app

COPY backend/ ./backend/
COPY data/ ./data/
COPY crawler/ ./crawler/
COPY deployment/ ./deployment/
COPY README.md ./
COPY --from=frontend-build /frontend/dist ./frontend/dist

RUN pip install --no-cache-dir -r backend/requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PORT=5000

EXPOSE 5000

CMD ["python", "backend/app.py"]
