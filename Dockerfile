FROM python:3.11-slim

WORKDIR /app

# copy backend
COPY backend/ /app/backend/

# copy data
COPY data/ /app/data/


COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt


WORKDIR /app/backend

EXPOSE 5000


CMD ["python", "app.py"]