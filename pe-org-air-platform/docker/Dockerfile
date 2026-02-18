
# ----------------------------------------------------------------------
# UNIFIED DOCKERFILE FOR PE ORG-AIR PLATFORM (AIRFLOW + API)
# ----------------------------------------------------------------------
# Base Image: Official Apache Airflow (Python 3.11)
# We use this as base because Airflow has complex system dependencies
FROM apache/airflow:2.8.1-python3.11

USER root

# 1. Install System Dependencies
# Required for:
# - Playwright (browsers, networking deps)
# - Compilation (gcc)
# - PDF Generation (wkhtmltopdf)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    fonts-liberation \
    fonts-unifont \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# 2. Switch to Airflow User for Python Installs
USER airflow

# 3. Install Python Dependencies
# Copy requirements from project root (context is pe-org-air-platform)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# 4. Install Playwright Browsers
# Explicitly install chromium for the airflow user
RUN playwright install chromium

# 5. Copy Application Code
# We copy code into /opt/airflow/app for Airflow AND /app for API compatibility
COPY --chown=airflow:root app /opt/airflow/app
COPY --chown=airflow:root app /app

# Copy DAGs
COPY --chown=airflow:root dags /opt/airflow/dags

# Set PYTHONPATH so both Airflow and API can find 'app' module
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow:/app"
ENV PLAYWRIGHT_BROWSERS_PATH=/home/airflow/.cache/ms-playwright

# 6. Runtime Configuration
# - Airflow services use default entrypoint
# - API service overrides entrypoint in docker-compose
