# zoom_webhook_catch — Zoom Webhook Receiver (Lambda)

An AWS Lambda function that receives Zoom webhook events (`recording.completed`), validates them, and forwards recording-file events to an SQS queue for the `zoom_recording_processor` ECS service to download.

## How It Works

1. Zoom sends webhook requests to the endpoint fronting this Lambda.
2. **Endpoint validation:** Zoom's URL-verification challenge (`plainToken`) is answered with an HMAC-SHA256 `encryptedToken` computed from the webhook secret token.
3. **Signature verification:** every event's `x-zm-signature` header is verified (HMAC-SHA256 over `v0:{timestamp}:{body}`), and requests older than 5 minutes are rejected to prevent replay attacks.
4. **Recording selection:** from the event's `recording_files`, one preferred file per category is selected (e.g. the best available video view, the audio transcript, closed captions, summary files) so duplicate views of the same meeting aren't all downloaded.
5. Each selected file is pushed to SQS as an individual message with the meeting metadata, download URL, download token, and target S3 key partitions (`<env>/recording_file/year=.../month=.../day=.../` and `<env>/raw/recordings/...` for metadata).

## Module Structure

```
zoom_webhook_catch/
└── app/
    ├── lambda_function.py  # Handler: challenge response, signature checks, event routing
    ├── sqs_client.py       # Sends messages to SQS
    ├── secret_client.py    # Retrieves the webhook secret token from Secrets Manager
    └── exceptions.py       # Custom exception classes
```

## Configuration

Environment variables, set by Terraform in `infra/modules/lambda/main.tf`:

| Variable | Description |
|----------|-------------|
| `SECRET_NAME` | Secrets Manager secret containing `secret_token` (the Zoom webhook verification token) |
| `SQS_QUEUE_URL` | Queue receiving the recording-file messages |
| `BUCKET_NAME` | Data lake bucket (used to build target S3 keys) |
| `REGION` | AWS region |
| `ENVIRONMENT` | Environment name; used as the S3 key prefix |

## Deployment

The Lambda is deployed by Terraform (`infra/modules/lambda/`), which expects a zip of the `app/` directory:

```bash
cd infra/
make zip-lambda    # creates zoom_webhook_catch/zoom_webhook.zip
make plan && make apply
```
