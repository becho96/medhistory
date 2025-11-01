FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода экспортера
COPY custom_exporter.py .

# Переменные окружения по умолчанию
ENV BACKEND_URL=http://backend:8000
ENV SCRAPE_INTERVAL=30
ENV EXPORTER_PORT=9100

# Открыть порт для Prometheus
EXPOSE 9100

# Запуск экспортера
CMD ["python", "custom_exporter.py"]

