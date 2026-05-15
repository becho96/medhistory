FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Long-polling bot — no inbound ports needed.
CMD ["python", "main.py"]
