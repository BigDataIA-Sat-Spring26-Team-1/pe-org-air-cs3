
FROM apache/airflow:2.8.1-python3.11

USER root
# Install system dependencies if needed (e.g. for pdfkit)
RUN apt-get update && \
    apt-get install -y wkhtmltopdf && \
    apt-get clean

USER airflow

# Copy requirements and install
COPY pe-org-air-platform/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Set PYTHONPATH to include the app code
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/app_code"
