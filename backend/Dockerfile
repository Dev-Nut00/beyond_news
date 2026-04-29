FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend /app/backend

EXPOSE 8000

CMD ["python", "backend/web_preview.py"]
