FROM python:3.11-slim

# System dependencies: tesseract (+ rus/eng traineddata) for OCR, ghostscript for
# "strong" compression (called as a subprocess), qpdf as pikepdf's native backend.
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-rus \
      tesseract-ocr-eng \
      ghostscript \
      qpdf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# app/ sources are copied BEFORE `pip install .`: setuptools (packages.find = ["app*"])
# builds the wheel from the actual sources, so installing from pyproject.toml alone
# would produce an empty package. Accepted trade-off: any code change rebuilds this layer.
COPY pyproject.toml ./
COPY app/ app/
RUN pip install --no-cache-dir .

# Static frontend (vanilla JS, no build step), served by FastAPI at "/"
COPY web/ web/

# Run as non-root; /docs is the only writable location (documents + index.db).
RUN useradd -m pdfcabin \
    && mkdir /docs \
    && chown pdfcabin:pdfcabin /docs /app

USER pdfcabin

ENV PDFCABIN_DOCS_DIR=/docs \
    PDFCABIN_HOST=0.0.0.0 \
    PDFCABIN_PORT=8420 \
    PYTHONUTF8=1 \
    PYTHONUNBUFFERED=1

VOLUME /docs
EXPOSE 8420

# Healthcheck hits "/" (static UI, 200 without a token) instead of /api/health:
# that endpoint is deliberately token-protected, so probing it would report unhealthy.
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8420/')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8420"]
