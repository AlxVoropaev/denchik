FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so source-only edits don't bust this layer.
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

EXPOSE 8000

# NB: stays as root in dev because docker-compose bind-mounts ./data:/app/data
# from the host, and a fixed-UID non-root user cannot write to a host-owned
# directory without UID-mapping plumbing that's out of scope for this dev
# image. Production deployment should rebuild with a non-root user and a
# named volume (or a UID-aligned bind mount).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
