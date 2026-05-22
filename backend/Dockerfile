FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PDF parsing / image handling if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    poppler-utils \
    tesseract-ocr \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement manifest from repo root
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN python -m spacy download en_core_web_md

# Copy source
COPY . /app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
