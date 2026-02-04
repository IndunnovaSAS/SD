# =============================================================================
# SD LMS - Dockerfile
# Multi-stage build for Django application
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base Python image
# -----------------------------------------------------------------------------
FROM python:3.12.1-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# -----------------------------------------------------------------------------
# Stage 2: Builder
# -----------------------------------------------------------------------------
FROM python-base as builder

# Install build dependencies (including WeasyPrint requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/production.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/production.txt

# -----------------------------------------------------------------------------
# Stage 3: Development
# -----------------------------------------------------------------------------
FROM python-base as development

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    postgresql-client \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install development dependencies
COPY requirements/local.txt requirements/local.txt
RUN pip install -r requirements/local.txt

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

WORKDIR /app

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# -----------------------------------------------------------------------------
# Stage 4: Production
# -----------------------------------------------------------------------------
FROM python-base as production

# Install runtime dependencies (including WeasyPrint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gettext \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Collect static files (using base settings to avoid external dependencies)
ENV SECRET_KEY="build-time-secret-key"
RUN python manage.py collectstatic --noinput --settings=config.settings.base

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "config.wsgi:application"]
