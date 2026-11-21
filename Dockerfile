FROM python:3.13-slim
ARG INSTALL_OCR=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN if [ "$INSTALL_OCR" = "true" ]; then apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin tesseract-ocr-ben poppler-utils && rm -rf /var/lib/apt/lists/*; fi
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app /app/app
RUN mkdir -p /app/data/uploads
EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
