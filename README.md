# Zoom ETL Pipeline

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-3.1-017CEE?logo=apacheairflow&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-%E2%89%A5%201.6-844FBA?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900?logo=amazonwebservices&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

An end-to-end data pipeline that extracts metadata from the Zoom API (users, meetings, participants), transforms it, and stores it in an S3 data lake. Includes a separate event-driven system for processing Zoom meeting recordings via webhooks.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Zoom API   │────▶│  ETL (src/)  │────▶│  S3 (raw/   │────▶│ Glue Crawler │
│  (metadata) │     │  via Airflow │     │  parquet)   │     │  ─▶ Catalog  │
└─────────────┘     └──────────────┘     └─────────────┘     └──────┬───────┘
                                                                    │
                                                              ┌─────▼──────┐
                                                              │  Athena ─▶ │
                                                              │  Power BI  │
                                                              └────────────┘

┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│ Zoom Webhook│────▶│   Lambda     │────▶│    SQS      │────▶│  Recording   │
│  (events)   │     │ (catch/      │     │   Queue     │     │  Processor   │
└─────────────┘     │  validate)   │     └─────────────┘     │  (ECS)       │
                    └──────────────┘                          └──────┬───────┘
                                                                    │
                                                              ┌─────▼──────┐
                                                              │ S3 + Cloud │
                                                              │ Front URLs │
                                                              └────────────┘
```

The pipeline has two independent data flows:

**1. Metadata ETL (scheduled):** The `Zoom_ETL` Airflow DAG runs daily at 4 AM, calls the Zoom Server-to-Server OAuth API to extract user, meeting, and participant data, transforms it into parquet, and writes it to S3 through raw → silver → gold zones (see [`src/README.md`](src/README.md)). Glue Crawlers catalog the data, which is queried with Athena and visualized in Power BI through the Athena connector.

**2. Recording Processing (event-driven):** When a Zoom meeting recording completes, Zoom sends a webhook to a Lambda function. The Lambda validates the event and pushes it to SQS. An ECS Fargate service polls SQS, downloads the recording, stores it in S3, records the download in a DynamoDB tracking table, and generates CloudFront signed URLs for secure playback. A second Airflow DAG (`Zoom_Recording_Deletion`, daily at 6 AM) then deletes recordings from Zoom's cloud once they have been safely archived in S3 for at least 6 days.

## Project Structure

```
Zoom_ETL/
├── src/                          # Core ETL library (Zoom API client, services, transforms)
├── airflow/                      # Airflow DAGs and plugins
│   ├── dags/etl_process.py       # Main ETL DAG
│   ├── dags/delete_recording.py  # Recording deletion DAG
│   ├── entrypoint.sh             # Syncs DAGs from S3 at container start
│   └── plugins/hostname_helper.py# Fargate hostname resolution for worker logs
├── zoom_recording_processor/     # ECS service for downloading/processing recordings
├── zoom_webhook_catch/           # Lambda function for receiving Zoom webhooks
├── infra/                        # Terraform infrastructure (modules + environments)
├── Dockerfile                    # Airflow image (used by all ECS Airflow services)
├── docker-compose.yaml           # Local development environment
└── requirements.txt              # Python dependencies for the ETL library
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- AWS CLI v2, configured with SSO
- Terraform >= 1.6
- A Zoom Server-to-Server OAuth app (for metadata ETL) that includes Event Subscriptions feature.

## Zoom API Credentials

This project uses two types of Zoom authentication:

**Server-to-Server OAuth** (metadata ETL): Create a Server-to-Server OAuth app in the [Zoom App Marketplace](https://marketplace.zoom.us/). You need the Account ID, Client ID, and Client Secret. These are stored in AWS Secrets Manager and injected into the Airflow ECS tasks as the environment variables `Client_ID`, `Client_Secret`, and `account_ID` (these exact names — see `src/config/settings.py`).

**Webhook Verification Token** (recording processing): In Feature section, configure a general feature with the `recording.completed` event. The verification token is used by the Lambda to validate incoming requests. The webhook endpoint URL is the API Gateway or Function URL fronting the `zoom_webhook_catch` Lambda.

## Local Development

Start the full Airflow environment locally with docker-compose:

```bash
# Start all services (webserver, scheduler, triggerer, workers, PostgreSQL, Redis)
docker-compose up -d

# Access the Airflow UI
open http://localhost:8080

# View logs
docker-compose logs -f airflow-apiserver
```

The local environment uses CeleryExecutor with a local Redis broker and PostgreSQL metadata database, mirroring the production ECS Fargate setup. It requires a `.env` file at the repo root (gitignored):

```bash
# Airflow API server secrets — any random strings
AIRFLOW__API_AUTH__JWT_SECRET=<random-string>
AIRFLOW__API__SECRET_KEY=<random-string>

# Local Postgres container credentials — keep as airflow/airflow/airflow,
# the Airflow connection strings in docker-compose.yaml are hardcoded to match
MY_USER=airflow
PASSWORD=airflow
DATABASE=airflow

# Initial Airflow UI login, created by airflow-init
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow

# Linux only: your host UID, so files created in mounted volumes aren't root-owned
AIRFLOW_UID=50000
```

## Production Deployment (AWS ECS Fargate)

The production environment runs on ECS Fargate with the following architecture:

- **Airflow API Server** (webserver): Serves the Airflow UI behind an Application Load Balancer
- **Airflow Scheduler**: Parses DAGs and schedules task instances
- **Airflow Triggerer**: Handles deferrable/async operators
- **Celery Workers**: Execute DAG tasks, backed by ElastiCache Redis as the Celery broker
- **RDS PostgreSQL**: Airflow metadata database
- **ElastiCache Redis**: Celery broker and result backend

### Deploy Infrastructure

**Terraform state backend:** the `backend "s3"` blocks in `infra/envs/<env>/providers.tf` ship with placeholder names. Create your own state bucket (and, for the dev environment, a DynamoDB lock table), then either replace the placeholders or override them at init time with `terraform init -backend-config="bucket=<your-bucket>"`.

**AWS credentials:** the Terraform provider uses the `profile` variable (default `default`) — override it in `terraform.tfvars`. The AWS CLI Makefile targets (`redeploy`, `status`) use `SSO_PROFILE` (default `default`), e.g. `make redeploy SERVICE=scheduler SSO_PROFILE=<your-profile>`.

Before running Terraform, generate the CloudFront RSA key pair — both files are gitignored but required by the `cloudfront` and `secrets` modules (`file()` references resolve to the `infra/` directory):

```bash
openssl genrsa -out infra/cloudfront-private-key.pem 2048
openssl rsa -pubout -in infra/cloudfront-private-key.pem -out infra/cloudfront-public-key.pem
```

Also zip the webhook Lambda source, which the `lambda` module deploys:

```bash
cd infra/ && make zip-lambda
```

Then deploy (all targets accept `ENV=<dev|prod>`, default `prod`; a `terraform.tfvars` providing at least `personal_ip` is required in `infra/envs/<env>/`):

```bash
cd infra/

# Initialize Terraform
make init

# Review the plan
make plan

# Apply
make apply
```

After the first apply, set the real Zoom credentials in the Secrets Manager secret created by the `secrets` module (the Terraform version only writes placeholders).

### Build and Push the Airflow Image

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-west-1 | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-1.amazonaws.com

# Build and push (ECR repository is named <project>-<env>-airflow, e.g. zoom-etl-prod-airflow)
docker build -t airflow-custom .
docker tag airflow-custom:latest <account-id>.dkr.ecr.us-west-1.amazonaws.com/zoom-etl-prod-airflow:$(git rev-parse --short HEAD)
docker push <account-id>.dkr.ecr.us-west-1.amazonaws.com/zoom-etl-prod-airflow:$(git rev-parse --short HEAD)
```

DAGs are not baked into the image — they are synced from S3 by `airflow/entrypoint.sh` when a container starts. To ship DAG changes: `make dag-upload` followed by `make redeploy-all` (from `infra/`).

### Initialize Airflow (First Deploy Only)

After the infrastructure is up, run the database migration:

```bash
aws ecs run-task \
  --cluster zoom-etl-prod \
  --task-definition zoom-etl-prod-webserver \
  --launch-type FARGATE \
  --platform-version "1.4.0" \
  --network-configuration '{
    "awsvpcConfiguration": {
      "subnets": ["<subnet-1>", "<subnet-2>"],
      "securityGroups": ["<sg-id>"],
      "assignPublicIp": "DISABLED"
    }
  }' \
  --overrides '{
    "containerOverrides": [{
      "name": "webserver",
      "command": ["airflow", "db", "migrate"]
    }]
  }'
```

### Access the Airflow UI

The ALB only accepts traffic on port 8080 from the `personal_ip` CIDR set in `terraform.tfvars` (plus VPC-internal traffic). Alternatively, tunnel through AWS SSM without exposing anything:

```bash
cd infra/
make ssm-apiserver   # then open http://localhost:8080
```

### Force Service Redeployment

After pushing a new image, force all services to pick it up:

```bash
for svc in webserver scheduler triggerer worker; do
  aws ecs update-service \
    --cluster zoom-etl-prod \
    --service "zoom-etl-prod-${svc}" \
    --force-new-deployment
done
```

## Infrastructure Overview

All infrastructure is managed with Terraform, organized into reusable modules:

| Module | Purpose |
|--------|---------|
| `network` | VPC, subnets, NAT gateway, route tables |
| `ecs` | ECS cluster, Cloud Map service discovery |
| `airflow` | ECS task definitions and services for all Airflow components |
| `alb` | Application Load Balancer for the Airflow UI |
| `database` | RDS PostgreSQL for Airflow metadata |
| `redis` | ElastiCache Redis for Celery broker |
| `ecr` | Container registry for Docker images |
| `iam` | IAM roles (task execution role, task role) |
| `secrets` | Secrets Manager (DB password, Fernet key, API keys) |
| `lambda` | Lambda function for webhook processing |
| `sqs` | SQS queue for recording events |
| `downloader` | ECS service for the recording processor (with SQS-based auto-scaling) |
| `dynamodb` | DynamoDB table tracking downloaded recordings |
| `datalake` | S3 buckets, Glue Crawlers, Glue Catalog, Athena workgroup |
| `cloudfront` | CloudFront distribution with signed URL support |

Environments are separated under `infra/envs/` (dev, prod), each with their own state and variables.

## Key Configuration

### Airflow Environment Variables

These are set in the ECS task definitions:

| Variable | Description |
|----------|-------------|
| `AIRFLOW__CORE__EXECUTOR` | `CeleryExecutor` |
| `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` | RDS PostgreSQL connection string (from Secrets Manager) |
| `AIRFLOW__CELERY__BROKER_URL` | ElastiCache Redis endpoint |
| `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` | `http://webserver.airflow.local:8080/execution/` |
| `AIRFLOW__CORE__FERNET_KEY` | Encryption key for variables/connections (from Secrets Manager) |
| `AIRFLOW__CORE__HOSTNAME_CALLABLE` | `hostname_helper.get_hostname` (worker only, for log serving on Fargate) |

### Important Notes

- The Airflow image is shared across all services (webserver, scheduler, triggerer, worker). The ECS task definition `command` determines which component runs.
- The Fernet key must be consistent across all services and must never be rotated without re-encrypting existing variables and connections.
- Worker log serving uses Cloud Map service discovery (`worker.airflow.local:8793`) for the webserver to fetch task logs from workers.
- Passwords with special characters in connection strings must be URL-encoded.

## License

[MIT](LICENSE)