# web-app/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# simple Flask app stub
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
