# syntax=docker/dockerfile:1

# -------- Builder --------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for builds (keep minimal; psycopg[binary] ships wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Create virtualenv for deterministic runtime
ENV VENV_PATH=/opt/venv
RUN python -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:${PATH}"

WORKDIR /app/backend

# Install Python deps first to leverage layer caching
COPY app/backend/requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# -------- Runtime --------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# Copy venv from builder
COPY --from=builder ${VENV_PATH} ${VENV_PATH}

# Create non-root user
RUN useradd -ms /bin/bash appuser

# App files
WORKDIR /app/backend
COPY app/backend /app/backend

# Expose API port
EXPOSE 8000

# Drop privileges
USER appuser

# Run DB migrations then launch API
CMD sh -c "alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"


