set -e

# 0) sei nella cartella che contiene docker-compose.yml?
test -f docker-compose.yml || { echo "Esegui qui dove c'è docker-compose.yml"; exit 1; }
test -d backend || { echo "Manca la cartella backend/ (sei nella cartella sbagliata?)"; exit 1; }

# 1) crea src/ e sposta codice
mkdir -p src/app
[ -d backend/ai ] && mkdir -p src/app/ai && rsync -a backend/ai/ src/app/ai/
[ -d backend/payment ] && mkdir -p src/app/payment && rsync -a backend/payment/ src/app/payment/
rsync -a --include="*.py" --exclude="*" backend/ src/app/
[ -f src/app/__init__.py ] || touch src/app/__init__.py

# 2) porta i file di build in root
[ -f backend/requirements.txt ] && mv backend/requirements.txt requirements.txt

# Dockerfile pulito in root
cat > Dockerfile << 'DOCKER'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app
CMD bash -lc "python -m app.migrate && uvicorn app.app:app --host 0.0.0.0 --port 8000"
DOCKER

# 3) docker-compose semplificato
cp docker-compose.yml docker-compose.yml.bak || true
cat > docker-compose.yml << 'YAML'
services:
  app:
    build:
      context: .
      dockerfile: ./Dockerfile
    env_file:
      - .env
    depends_on:
      - db
    ports:
      - "8000:8000"
    restart: unless-stopped
    command: bash -lc "python -m app.migrate && uvicorn app.app:app --host 0.0.0.0 --port 8000"

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  pgdata:
YAML

# 4) rimuovi backend (ora tutto è sotto src/)
rm -rf backend

echo "✅ Refactor completato."
