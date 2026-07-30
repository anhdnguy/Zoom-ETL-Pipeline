import boto3
from botocore.exceptions import ClientError
import pandas as pd
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

from src.config import AppConfig
from src.storage.s3_exceptions import (
    S3UploadError,
    S3BucketNotFoundError
)

class S3Writer:
    """
    Loads Zoom datasets (users, meetings, participants, recordings, etc.)
    into S3 as partitioned Parquet files:
    
    s3://bucket/<environment>/raw/<dataset_name>/year=YYYY/month=MM/day=DD/<dataset>.parquet
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.bucket = config.s3_bucket
        self.base_prefix = config.environment
        self.s3 = boto3.client("s3", region_name=config.aws_region)
    
    def _upload_parquet(self, df: pd.DataFrame, key: str):
        """Convert DF to Parquet and upload to S3."""
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)

        try:
            self.s3.upload_fileobj(buffer, self.bucket, key)
            logger.info(f"Uploaded Parquet file: s3://{self.bucket}/{key}")
        
        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NoSuchBucket':
                raise S3BucketNotFoundError(f"Bucket not found: {self.bucket_name}")
            else:
                raise S3UploadError(f"S3 upload failed: {str(e)}")
        
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")


    def _load_generic(
        self,
        records: List[List[Dict[str, Any]]],
        dataset_name: str
    ):
        """
        Generic loader for any dataset type.
        Records: list of dicts from the extract steps.
        dataset_name: "users", "meetings", "participants", etc.
        timestamp_field: determines partition date (default: current UTC)
        """
        logger.info(f"Processing {dataset_name} dataset, {len(records)} chunks.")

        if not records:
            logger.warning(f"No {dataset_name} records to load.")
            return
        
        for count, record in enumerate(records):
            logger.info(f"Processing chunk {count}.")
            # Convert to DataFrame
            df = pd.DataFrame(record)

            # Build S3 key
            partition_time = datetime.now(timezone.utc)
            partition = f"year={partition_time.year}/month={partition_time.month:02d}/day={partition_time.day:02d}"
            key = f"{self.base_prefix}/raw/{dataset_name}/{partition}/{dataset_name}_{count}.parquet"

            self._upload_parquet(df, key)
            logger.info(f"Successfully processed chunk {count}.")
        
        logger.info(f"Successfully processed {dataset_name} dataset.")

    def _transform_to_silver(self, dataset_name: str):
        """
        Generic task to read from bronze, enforce schema, write to silver.
        dataset_name: the name of the dataset (users, meetings, participants)
        """
        logger.info(f"Reading {dataset_name} dataset")

        # Define expected schema per dataset
        SCHEMAS = {
            "users": {
                "id": "str",
                "jid": "str",
                "pmi": "int64",
                "dept": "str",
                "type": "int64",
                "email": "str",
                "status": "str",
                "cluster": "str",
                "pic_url": "str",
                "role_id": "str",
                "use_pmi": "bool",
                "language": "str",
                "location": "str",
                "timezone": "str",
                "verified": "int64",
                "group_ids": "str",       # array<string> → serialize as JSON string
                "job_title": "str",
                "last_name": "str",
                "role_name": "str",
                "account_id": "str",
                "created_at": "str",
                "first_name": "str",
                "cms_user_id": "str",
                "cost_center": "str",
                "login_types": "str",     # array<bigint> → serialize as JSON string
                "display_name": "str",
                "im_group_ids": "str",    # array<int> → serialize as JSON string
                "phone_number": "str",
                "phone_country": "str",
                "account_number": "int64",
                "last_login_time": "str",
                "user_created_at": "str",
                "last_client_version": "str",
                "personal_meeting_url": "str",
                "company": "str",
                "phone_numbers": "str",   # array<struct> → serialize as JSON string
                "vanity_url": "str",
                "manager": "str",
            },
            "meetings": {
                "id": "int64",
                "dept": "str",
                "type": "int64",
                "uuid": "str",
                "topic": "str",
                "source": "str",
                "host_id": "str",
                "duration": "int64",
                "end_time": "str",
                "user_name": "str",
                "start_time": "str",
                "user_email": "str",
                "total_minutes": "float64",
                "participants_count": "int64",
                "has_meeting_summary": "bool",
            },
            "participants": {
                "id": "str",
                "name": "str",
                "status": "str",
                "groupid": "str",
                "user_id": "str",
                "duration": "int64",
                "failover": "bool",
                "join_time": "str",
                "leave_time": "str",
                "user_email": "str",
                "meeting_uuid": "str",
                "internal_user": "bool",
                "registrant_id": "str",
            },
        }

        schema = SCHEMAS.get(dataset_name, {})

        partition_time = datetime.now(timezone.utc)
        partition = f"year={partition_time.year}/month={partition_time.month:02d}/day={partition_time.day:02d}"
        prefix = f"{self.base_prefix}/raw/{dataset_name}/{partition}/"

        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        if "Contents" not in response:
            logger.warning(f"No bronze files found for {dataset_name} at {prefix}")
            return
        
        # Read all parquet files for today
        logger.info(f"Reading all parquet files for {partition_time} for {dataset_name} dataset.")
        dfs = []
        for obj in response["Contents"]:
            if obj["Key"].endswith(".parquet"):
                buffer = BytesIO()
                self.s3.download_fileobj(self.bucket, obj["Key"], buffer)
                buffer.seek(0)
                dfs.append(pd.read_parquet(buffer))

        if not dfs:
            return
        
        df = pd.concat(dfs, ignore_index=True)

        # Enforce schema
        logger.info(f"Emforcing schema for {dataset_name} dataset.")
        for col, dtype in schema.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except (ValueError, TypeError):
                    logger.warning(f"Could not cast {col} to {dtype}, coercing")
                    df[col] = pd.to_numeric(df[col], errors="coerce") if dtype in ("int64", "float64") else df[col].astype("str")

        # Drop coulmns not in schema
        df = df[[c for c in schema.keys() if c in df.columns]]

        # Write to silver zone
        silver_key = f"{self.base_prefix}/silver/{dataset_name}/{partition}/{dataset_name}.parquet"
        self._upload_parquet(df, silver_key)

    def _build_gold_users(self):
        """Read all silver user partitions, keep latest record per user."""
        prefix = f"{self.base_prefix}/silver/users/"
        paginator = self.s3.get_paginator("list_objects_v2")

        dfs = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".parquet"):
                    buffer = BytesIO()
                    self.s3.download_fileobj(self.bucket, obj["Key"], buffer)
                    buffer.seek(0)
                    # Add partition date from the key for sorting
                    # Key format: env/silver/users/year=2026/month=03/day=20/users.parquet
                    parts = {p.split("=")[0]: p.split("=")[1]
                             for p in obj["Key"].split("/") if "=" in p}
                    df = pd.read_parquet(buffer)
                    df["_partition_date"] = f"{parts.get('year','')}-{parts.get('month','')}-{parts.get('day','')}"
                    dfs.append(df)
        
        if not dfs:
            logger.warning("No silver user data found")
            return
        
        df = pd.concat(dfs, ignore_index=True)

        # Sort by partition date descending, keep the latest record per user
        df = df.sort_values("_partition_date", ascending=False)
        df = df.drop_duplicates(subset=["id"], keep="first")
        df = df.drop(columns=["_partition_date"])

        # Write single file to gold — partition by year, just one file
        partition_time = datetime.now(timezone.utc)
        partition_year = partition_time.year
        gold_key = f"{self.base_prefix}/gold/users/{partition_year}/users.parquet"
        self._upload_parquet(df, gold_key)

    def _build_gold_meetings(self):
        """Deduplicate meetings by uuid, keep latest record."""
        prefix = f"{self.base_prefix}/silver/meetings/"
        paginator = self.s3.get_paginator("list_objects_v2")

        dfs = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".parquet"):
                    buffer = BytesIO()
                    self.s3.download_fileobj(self.bucket, obj["Key"], buffer)
                    buffer.seek(0)
                    # Add partition date from the key for sorting
                    # Key format: env/silver/users/year=2026/month=03/day=20/users.parquet
                    parts = {p.split("=")[0]: p.split("=")[1]
                             for p in obj["Key"].split("/") if "=" in p}
                    df = pd.read_parquet(buffer)
                    df["_partition_date"] = f"{parts.get('year','')}-{parts.get('month','')}-{parts.get('day','')}"
                    dfs.append(df)
        
        if not dfs:
            logger.warning("No silver user data found")
            return
        
        df = pd.concat(dfs, ignore_index=True)
        # Sort by partition date descending, keep the latest record per meeting
        df = df.sort_values("_partition_date", ascending=False)
        df = df.drop_duplicates(subset=["uuid"], keep="first")
        df = df.drop(columns=["_partition_date"])

        # Write single file to gold — partition by year, just one file
        partition_time = datetime.now(timezone.utc)
        partition_year = partition_time.year
        gold_key = f"{self.base_prefix}/gold/meetings/{partition_year}/meetings.parquet"
        self._upload_parquet(df, gold_key)

    def _build_gold_participants(self):
        """Deduplicate participants, preserving re-entries."""
        prefix = f"{self.base_prefix}/silver/participants/"
        paginator = self.s3.get_paginator("list_objects_v2")

        dfs = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                if obj["Key"].endswith(".parquet"):
                    buffer = BytesIO()
                    self.s3.download_fileobj(self.bucket, obj["Key"], buffer)
                    buffer.seek(0)
                    # Add partition date from the key for sorting
                    # Key format: env/silver/users/year=2026/month=03/day=20/users.parquet
                    parts = {p.split("=")[0]: p.split("=")[1]
                             for p in obj["Key"].split("/") if "=" in p}
                    df = pd.read_parquet(buffer)
                    df["_partition_date"] = f"{parts.get('year','')}-{parts.get('month','')}-{parts.get('day','')}"
                    dfs.append(df)
        
        if not dfs:
            logger.warning("No silver user data found")
            return
        
        df = pd.concat(dfs, ignore_index=True)

        # Deduplicate: same person + same meeting + same join time = duplicate pull
        # Different join time = re-entry (kept)
        dedup_cols = ["meeting_uuid", "user_email", "join_time"]

        # Handle nulls in user_email — fall back to name
        null_email_count = df["user_email"].isnull().sum()
        if null_email_count > 0:
            logger.warning(f"{null_email_count} rows with null user_email, using name as fallback")
            df["_dedup_key"] = df["user_email"].fillna(df["name"])
            dedup_cols = ["meeting_uuid", "_dedup_key", "join_time"]

        before = len(df)
        df = df.drop_duplicates(subset=dedup_cols, keep="last")
        if "_dedup_key" in df.columns:
            df = df.drop(columns=["_dedup_key"])
        
        # Write single file to gold — partition by year, just one file
        partition_time = datetime.now(timezone.utc)
        partition_year = partition_time.year
        gold_key = f"{self.base_prefix}/gold/participants/{partition_year}/participants.parquet"
        self._upload_parquet(df, gold_key)
        logger.info(f"Gold participants: {before} → {len(df)} (removed {before - len(df)} duplicates)")