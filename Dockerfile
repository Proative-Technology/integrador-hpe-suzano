FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs \
    && chmod 755 /app/logs

COPY . .

EXPOSE 8114

CMD ["gunicorn", "--bind", "0.0.0.0:8114", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--access-logfile", "-", "--error-logfile", "-", "app.main:app"]
