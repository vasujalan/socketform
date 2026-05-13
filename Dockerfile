FROM python:3.11-slim

WORKDIR /app

COPY server.py .

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
