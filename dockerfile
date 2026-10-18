FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY sql/ sql/

# Show log output immediately instead of buffering it
ENV PYTHONUNBUFFERED=1

# Default command loads saved raw files; run extract with:
#   docker compose run --rm pipeline python src/extract.py 2026-10-01 2026-10-10
CMD ["python", "src/load.py"]