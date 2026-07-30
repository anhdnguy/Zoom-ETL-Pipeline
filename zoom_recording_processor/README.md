# zoom_recording_processor — Recording Download Service

An ECS Fargate service that polls an SQS queue for Zoom recording completion events, downloads the recordings, stores them in S3, and generates CloudFront signed URLs for secure playback.

## Architecture

```
┌──────────────┐     ┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐     ┌─────────────┐
│  SQS Queue   │────▶│  SQS Handler│────▶│  Zoom Client         │────▶│  S3 Bucket  │────▶│  S3 Bucket  │
│  (recording  │     │  (polls and │     │  (downloads          │     │  (raw       │     │  (raw       │
│   events)    │     │   parses)   │     │   recording files)   │     │  recordings)│     │  payload)   │
└──────────────┘     └─────────────┘     └──────────────────────┘     └──────┬──────┘     └─────────────┘
                                                                             │
                                                                       ┌─────▼──────┐
                                                                       │ CloudFront │
                                                                       │ Signed URL │
                                                                       └────────────┘
```

## How It Works

1. The Zoom Webhook-Only app sends a `recording.completed` event to the `zoom_webhook_catch` Lambda.
2. The Lambda validates the webhook signature and pushes the event payload to an SQS queue.
3. This service continuously polls the SQS queue and processes messages concurrently (`CONCURRENT_WORKERS` threads). For each recording event it:
   1. Parses the message payload and extracts the download URLs.
   2. Checks whether the recording was already processed (idempotency), so redelivered SQS messages are skipped.
   3. Streams each recording file from Zoom directly to S3 (chunked download/upload, no local buffering of whole files).
   4. Generates CloudFront signed URLs for secure, time-limited access.
   5. Uploads the event payload/metadata to the S3 data lake raw zone.
   6. Writes a tracking record to DynamoDB (`recording_id`, S3 key, `delete_status: pending`, timestamps) — used later to delete the recording from Zoom after a successful download.

## Module Structure

```
zoom_recording_processor/
├── Dockerfile              # Container image for ECS Fargate
├── requirements.txt        # Python dependencies
├── app/
│   ├── main.py             # Entry point — starts the SQS polling loop
│   ├── sqs_handler.py      # SQS message polling, parsing, and deletion
│   ├── zoom_client.py      # Downloads recordings from Zoom download URLs
│   ├── s3_client.py        # Uploads recordings to S3
│   ├── cloudfront_client.py# Generates CloudFront signed URLs
│   ├── dynamodb_client.py  # Writes recording tracking records to DynamoDB
│   ├── secret_client.py    # Retrieves secrets from AWS Secrets Manager
│   ├── config.py           # Environment-based configuration
│   ├── exceptions.py       # Custom exception classes
│   └── logger.py           # Structured logging setup

```

## Configuration

All configuration is via environment variables (see `app/config.py`), set in the ECS task definition (`infra/modules/downloader/main.tf`). Required:

| Variable | Description |
|----------|-------------|
| `SQS_QUEUE_URL` | URL of the SQS queue to poll |
| `S3_BUCKET_NAME` | Target S3 bucket for recordings |
| `CLOUDFRONT_DOMAIN` | CloudFront distribution domain name |
| `CLOUDFRONT_KEY_PAIR_ID` | CloudFront key pair ID (injected from Secrets Manager as an ECS container secret) |
| `CLOUDFRONT_PRIVATE_KEY` | CloudFront RSA private key PEM (injected from Secrets Manager as an ECS container secret) |
| `DYNAMODB_TABLE_NAME` | DynamoDB table for recording tracking records |

Notable optional settings (see `app/config.py` for the full list and defaults): `AWS_REGION`, `CONCURRENT_WORKERS` (1–10), `MAX_RETRIES`, `CLOUDFRONT_URL_EXPIRATION`, `SQS_MAX_MESSAGES`, `SQS_WAIT_TIME_SECONDS`, `SQS_VISIBILITY_TIMEOUT`, `DOWNLOAD_CHUNK_SIZE`, `UPLOAD_CHUNK_SIZE`, `LOG_LEVEL`.

Note: the S3 key prefix is currently read from the `ENVIRONMENT` env var (default `zoom-recordings/`), not from the `S3_PREFIX` variable the task definition sets — see `Config.S3_PREFIX` in `app/config.py`.

## Building and Deploying

```bash
# Build the image
cd zoom_recording_processor
docker build -t zoom-recording-processor .

# Tag and push to ECR (repository is named <project>-<env>-downloader, e.g. zoom-etl-prod-downloader)
docker tag zoom-recording-processor:latest \
  <account-id>.dkr.ecr.us-west-1.amazonaws.com/zoom-etl-prod-downloader:latest
docker push <account-id>.dkr.ecr.us-west-1.amazonaws.com/zoom-etl-prod-downloader:latest
```

The ECS service is managed by Terraform in `infra/modules/downloader/`. It runs as a long-lived Fargate task that continuously polls SQS.

## Local Development

```bash
cd zoom_recording_processor
pip install -r requirements.txt

# Run locally (requires AWS credentials and a populated SQS queue)
python -m app.main
```

## CloudFront Signed URLs

Recordings are served through CloudFront with signed URLs for security. The signing uses an RSA key pair:

- The **public key** is registered with CloudFront by Terraform, read from `infra/cloudfront-public-key.pem` (gitignored — generate it before running Terraform; see the root README).
- The **private key** is stored in AWS Secrets Manager and injected into the container as the `CLOUDFRONT_PRIVATE_KEY` environment variable via the ECS task definition's `secrets` block.

Signed URLs have a configurable expiration time (`CLOUDFRONT_URL_EXPIRATION`, default 24 hours), after which the recording is no longer accessible via that URL.