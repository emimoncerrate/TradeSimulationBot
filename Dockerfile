# =============================================================================
# Jain Global Slack Trading Bot - Multi-stage Docker Build
# =============================================================================
# This Dockerfile supports both local development and AWS Lambda deployment
# with optimized layers for caching and minimal final image size.

# =============================================================================
# BASE STAGE - Common dependencies and setup
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# =============================================================================
# DEPENDENCIES STAGE - Install Python dependencies
# =============================================================================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# =============================================================================
# DEVELOPMENT STAGE - For local development with hot reload
# =============================================================================
FROM dependencies as development

# Install development dependencies
RUN pip install \
    watchdog \
    pytest-watch \
    jupyter \
    ipython

# Copy application code
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for development server
EXPOSE 3000

# Health check for development
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000", "--reload"]

# =============================================================================
# PRODUCTION STAGE - Optimized for production deployment
# =============================================================================
FROM dependencies as production

# Copy only necessary application files
COPY app.py .
COPY listeners/ ./listeners/
COPY ui/ ./ui/
COPY services/ ./services/
COPY models/ ./models/
COPY utils/ ./utils/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p /app/logs

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port for production
EXPOSE 8080

# Health check for production
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Production command with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "30", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "app:app"]

# =============================================================================
# AWS LAMBDA STAGE - Optimized for AWS Lambda deployment
# =============================================================================
FROM public.ecr.aws/lambda/python:3.11 as lambda

# Copy Python dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages/ ${LAMBDA_RUNTIME_DIR}/

# Copy application code
COPY app.py ${LAMBDA_TASK_ROOT}/
COPY listeners/ ${LAMBDA_TASK_ROOT}/listeners/
COPY ui/ ${LAMBDA_TASK_ROOT}/ui/
COPY services/ ${LAMBDA_TASK_ROOT}/services/
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY utils/ ${LAMBDA_TASK_ROOT}/utils/
COPY config/ ${LAMBDA_TASK_ROOT}/config/

# Set the CMD to your handler
CMD ["app.lambda_handler"]

# =============================================================================
# TESTING STAGE - For running tests in CI/CD
# =============================================================================
FROM dependencies as testing

# Install additional testing dependencies
RUN pip install \
    pytest-xdist \
    pytest-benchmark \
    coverage[toml] \
    bandit \
    safety

# Copy all application code including tests
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run tests by default
CMD ["pytest", "-v", "--cov=.", "--cov-report=html", "--cov-report=term-missing"]