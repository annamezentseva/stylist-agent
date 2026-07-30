FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# По умолчанию поднимаем backend-API. Telegram-бот запускается отдельным сервисом
# (см. docker-compose.yml, команда переопределяется).
CMD ["uvicorn", "stylist.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
