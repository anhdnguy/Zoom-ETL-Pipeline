FROM apache/airflow:3.1.7

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    awscli \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# Python Dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# COPY --chown=airflow:root ./airflow/dags /opt/airflow/dags
COPY --chown=airflow:root ./src /opt/airflow/src
COPY --chown=airflow:root ./airflow/plugins/hostname_helper.py /opt/airflow/hostname_helper.py

COPY --chown=airflow:root ./airflow/entrypoint.sh /opt/airflow/entrypoint.sh
RUN chmod +x /opt/airflow/entrypoint.sh

ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow"