FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Use shell form (not JSON array) so ${PORT:-8000} variable expansion works.
# Azure App Service injects the PORT environment variable at runtime.
# --workers 1 is required because APScheduler runs in-process and must not
# be duplicated across multiple worker processes.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
