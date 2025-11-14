FROM python:3.11-slim

WORKDIR /app

# Copy backend code
COPY backend/ /app/

# Copy data directory
COPY data/ /app/data/

# Install backend dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]

