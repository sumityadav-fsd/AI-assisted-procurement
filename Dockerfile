# One container: React build -> served by FastAPI. Works on Render (Docker runtime) and Railway.
# Build:  docker build -t vinayak-procureai .
# Run:    docker run --rm -p 8000:8000 --env-file .env vinayak-procureai
# Optional OCR system packages (adds ~150 MB): docker build --build-arg INSTALL_OCR=true .

# ---- Stage 1: build the frontend ----
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.13-slim
ARG INSTALL_OCR=false
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend/dist \
    DATABASE_PATH=/app/backend/data/procureai.db \
    UPLOAD_DIR=/app/backend/data/uploads

# UNKNOWN: whether OCR will use Tesseract. Kept opt-in until Member 3 decides (see docs/mentor_questions.md).
RUN if [ "$INSTALL_OCR" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin tesseract-ocr-ben \
      && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /fe/dist frontend/dist

WORKDIR /app/backend
RUN mkdir -p data/uploads
EXPOSE 8000
# Render/Railway inject $PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
