FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8088

CMD ["uvicorn", "src.collector.main:app", "--host", "0.0.0.0", "--port", "8088"]
