FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/parking.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data /app/instance

EXPOSE 8000

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 120"]
