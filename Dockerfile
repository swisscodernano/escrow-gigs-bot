FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app
CMD bash -lc "python -m app.wait_db python -m app.migrate && uvicorn app.app:apppython -m app.migrate && uvicorn app.app:app python -m app.migrate python -m app.migrate && uvicorn app.app:apppython -m app.migrate && uvicorn app.app:app uvicorn app.app:app --host 0.0.0.0 --port 8000"
