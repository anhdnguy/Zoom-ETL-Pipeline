# src/ — Zoom ETL Core Library

The core Python library that handles Zoom API communication, data transformation, and S3 storage. This code is called by the Airflow DAG (`airflow/dags/etl_process.py`) but is designed to be independently testable and reusable.

## Module Structure

```
src/
├── bootstrap.py            # Application initialization and dependency wiring
├── clients/                # Zoom API client layer
│   ├── zoom_client.py      # HTTP client for Zoom REST API
│   ├── zoom_token.py       # Server-to-Server OAuth token management
│   └── zoom_exceptions.py  # Custom exceptions for API errors
├── services/               # Business logic layer
│   ├── user_service.py     # Fetches and processes Zoom user data
│   ├── meeting_service.py  # Fetches and processes meeting data
│   ├── participant_service.py  # Fetches and processes participant data
│   └── retry.py            # Retry logic for transient API failures
├── transforms/             # Data transformation layer
│   ├── users.py            # User data normalization and cleaning
│   ├── meetings.py         # Meeting data normalization and cleaning
│   └── participants.py     # Participant data normalization and cleaning
├── storage/                # Data output layer
│   ├── s3_writer.py        # Writes transformed data to S3 as parquet
│   └── s3_exceptions.py    # Custom exceptions for S3 operations
├── config/
│   └── settings.py         # Configuration management (env vars, defaults)
└── utils/
    └── logger.py           # Structured logging configuration
```

## Data Flow

```
Zoom API  ──▶  zoom_client.py  ──▶  *_service.py  ──▶  transforms/*.py  ──▶  s3_writer.py  ──▶  S3
              (HTTP + auth)        (pagination,         (normalize,           (parquet)
                                    filtering)           clean, flatten)
```

1. **Client layer** (`clients/`): Handles HTTP communication with the Zoom API, including Server-to-Server OAuth token acquisition and refresh via `zoom_token.py`. The `zoom_client.py` provides methods for each API endpoint.

2. **Service layer** (`services/`): Contains the business logic for each data domain (users, meetings, participants). Services handle pagination, rate limiting, and call the transforms before passing data to storage. The `retry.py` module provides configurable retry logic for transient API failures (429, 5xx).

3. **Transform layer** (`transforms/`): Pure functions that normalize, clean, and flatten the raw JSON responses from Zoom into tabular structures suitable for analytics. Each transform module corresponds to a data domain.

4. **Storage layer** (`storage/`): Writes data to S3 in parquet format using `s3_writer.py`, following a medallion layout under `s3://<bucket>/<environment>/`:
   - `raw/<dataset>/year=YYYY/month=MM/day=DD/` — raw loads from the extract tasks (`_load_generic`)
   - `silver/<dataset>/...` — schema-enforced, cleaned data (`_transform_to_silver`)
   - `gold/<dataset>/...` — deduplicated, analytics-ready tables (`_build_gold_users`, `_build_gold_meetings`, `_build_gold_participants`)

## Authentication

The library uses Zoom Server-to-Server OAuth (client credentials flow). Required credentials:

| Credential | Env var (exact name) | Source in production |
|------------|----------------------|----------------------|
| Account ID | `account_ID` | Injected from Secrets Manager by the ECS task definition |
| Client ID | `Client_ID` | Injected from Secrets Manager by the ECS task definition |
| Client Secret | `Client_Secret` | Injected from Secrets Manager by the ECS task definition |

Token refresh is handled by `zoom_token.py`: the access token is cached in Redis (`RedisTokenStore`) and refreshed before expiry, with a Redis-based distributed lock (`RedisLock`) so concurrent Celery workers don't stampede the Zoom token endpoint. `bootstrap.build_zoom_client()` wires the Redis store, lock, token provider, and HTTP client together.

## Configuration

All configuration is managed through environment variables, loaded in `config/settings.py` (`AppConfig`). Note that `AppConfig.validate()` runs at import time, so importing the package fails immediately if required values are missing.

| Variable | Required | Description |
|----------|----------|-------------|
| `S3_BUCKET` | yes | Target S3 bucket for the data lake |
| `account_ID` | yes | Zoom Server-to-Server OAuth Account ID |
| `Client_ID` | yes | Zoom OAuth Client ID |
| `Client_Secret` | yes | Zoom OAuth Client Secret |
| `REDIS_HOST` / `REDIS_PORT` | yes | Redis used for OAuth token caching/locking |
| `AWS_REGION` | no (default `us-west-1`) | AWS region for S3 operations |
| `ENVIRONMENT` | no (default `dev`) | One of `dev`, `staging`, `prod`; used as the S3 key prefix |
| `MAX_RETRIES` | no (default `3`) | Retry attempts for failed API calls |
| `BATCH_SIZE` | no (default `100`) | Records per processing batch |
| `DEFAULT_PAGE_SIZE` | no (default `300`) | Records per page during Zoom API pagination |
| `ZOOM_API_TIMEOUT` | no (default `30`) | HTTP timeout in seconds |
| `LOG_LEVEL` | no (default `INFO`) | Logging level |

## Usage

The library is copied into the Airflow Docker image (`COPY ./src /opt/airflow/src` with `/opt/airflow` on `PYTHONPATH`) — there is no separate package install. The Airflow DAG (`airflow/dags/etl_process.py`) imports and calls the services directly:

```python
from datetime import datetime

from src.bootstrap import build_zoom_client
from src.services.user_service import UserService
from src.services.meeting_service import MeetingService
from src.services.participant_service import ParticipantService
from src.services.retry import RetryExecutor
from src.storage.s3_writer import S3Writer
from src.config import AppConfig

client = build_zoom_client()
retry = RetryExecutor(AppConfig.max_retries, logger)

# Extract
user_ids = UserService(client, retry).fetch_all_user_ids()          # chunked List[List[str]]
users = UserService(client, retry).fetch_user_details(user_ids[0])
meetings = MeetingService(client, retry).fetch_user_meetings_since(user_ids[0], last_run_dt)
details = MeetingService(client, retry).fetch_meeting_details(meetings)
participants = ParticipantService(client, retry).fetch_meeting_participants(meetings)

# Load (raw zone), then promote through the medallion zones
writer = S3Writer(AppConfig)
writer._load_generic(records=[users], dataset_name="users")
writer._transform_to_silver("users")
writer._build_gold_users()
```