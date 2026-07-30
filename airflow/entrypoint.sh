#!/bin/bash
set -e

echo "Syncing DAGs from S3..."
aws s3 sync "${AIRFLOW_S3_DAGS_URI}" /opt/airflow/dags/ --delete --exact-timestamps
echo "DAG sync complete. Found $(ls /opt/airflow/dags/*.py 2>/dev/null | wc -l) DAG files."

echo "Reserializing DAGs..."
airflow dags reserialize
echo "Reserialization complete."

exec "$@"