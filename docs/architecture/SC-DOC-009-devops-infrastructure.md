# STEM COGENT — DOCUMENT 9: DEVOPS & INFRASTRUCTURE SPECIFICATION

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** DevOps / Platform Engineering
**Document ID:** SC-DOC-009
**Cloud Provider:** AWS (eu-west-1 primary)
**Depends On:** SC-DOC-002, SC-DOC-003, SC-DOC-006, SC-DOC-008
**Referenced By:** SC-DOC-010 (Sprint & Delivery Plan)
**Last Updated:** 2026

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-009 |
| Document Type | DevOps & Infrastructure Specification |
| Approvers | DevOps Lead, Principal Architect, Security Lead |

---

## GOVERNING PRINCIPLE — RIGHT-SIZED INFRASTRUCTURE

This document deliberately avoids over-engineering. Stem Cogent is a startup building toward product-market fit. The infrastructure defined here is sufficient to handle launch-scale load reliably, deployable by a small team, and designed to grow incrementally as signal volume and customer count increase.

**What this means in practice:**
- ECS Fargate over EKS at launch — less operational overhead, same container isolation
- Redis Streams over Kafka at launch — simpler ops, sufficient throughput for <100K signals/day
- Single-region at launch (eu-west-1) with DR capability — multi-region after revenue
- CloudWatch as primary observability — sufficient at launch before Datadog/Grafana complexity is justified

---

## TABLE OF CONTENTS

1. Infrastructure Overview
2. AWS Account & Environment Architecture
3. Terraform IaC Structure
4. CI/CD Pipeline
   - 4.1 Repository Structure
   - 4.2 Branch Strategy
   - 4.3 Backend CI Pipeline
   - 4.4 Frontend CI Pipeline
   - 4.5 Infrastructure CD Pipeline
   - 4.6 Application CD Pipeline
5. Container Orchestration (ECS Fargate)
   - 5.1 Service Definitions
   - 5.2 Compute Sizing Matrix
   - 5.3 Autoscaling Configuration
   - 5.4 Deployment Strategy
   - 5.5 Worker Service Configuration
6. Data Infrastructure
   - 6.1 RDS PostgreSQL
   - 6.2 ElastiCache Redis
   - 6.3 S3 Buckets
   - 6.4 SQS Queues
   - 6.5 ClickHouse
7. Observability Stack
   - 7.1 Metrics (CloudWatch)
   - 7.2 Structured Logging
   - 7.3 Distributed Tracing (AWS X-Ray)
   - 7.4 Dashboards
   - 7.5 Alerting
8. Database Operations
   - 8.1 Migration Management
   - 8.2 Backup & Recovery
   - 8.3 Reprocessing Utility
9. Environment Configuration
10. On-Call & Operational Runbooks

---

---

# SECTION 1 — INFRASTRUCTURE OVERVIEW

---

## 1.1 What Gets Built

```
COMPUTE
  ECS Fargate — API service, all pipeline workers, MLflow
  No EC2 to manage. No Kubernetes cluster to operate.

DATA STORES
  RDS PostgreSQL 16 (Multi-AZ) — primary operational database
  ElastiCache Redis 7 (cluster mode disabled at launch) — cache + broker
  S3 — raw signals, uploads, artefacts, digests, backups
  SQS — all inter-service queues (14 queues + DLQs)
  ClickHouse — analytics (single node at launch, EBS-backed)

NETWORKING
  Single VPC, 3-tier subnet layout (public / private-app / private-data)
  NAT Gateway per AZ for outbound internet (LLM API calls)
  VPC Endpoints for all AWS service access

DELIVERY
  CloudFront — frontend CDN + API edge caching
  ALB — API load balancer

SECURITY
  AWS KMS — encryption keys
  AWS Secrets Manager — all secrets
  AWS WAF — attached to CloudFront
  AWS GuardDuty — threat detection

OBSERVABILITY
  CloudWatch Logs — all structured logs
  CloudWatch Metrics — all custom pipeline metrics
  CloudWatch Alarms — all operational alerts
  AWS X-Ray — distributed tracing
  AWS CloudTrail — audit trail for all AWS API calls
```

## 1.2 What Is NOT Built at Launch

```
NOT at launch:
  - EKS (Kubernetes) — ECS Fargate is simpler, sufficient
  - Multi-region active-active — eu-west-1 primary + DR config only
  - Kafka / MSK — Redis Streams handles <100K signals/day
  - Dedicated monitoring platform (Datadog/Grafana/Prometheus) — CloudWatch sufficient
  - Service mesh (Istio/Linkerd) — VPC security groups + TLS sufficient
  - Pinecone / Weaviate — pgvector handles embedding retrieval at launch
  - Neo4j cloud — self-hosted on single EC2 instance at launch
  - SageMaker real-time endpoints — ECS CPU inference sufficient at launch
```

---

---

# SECTION 2 — AWS ACCOUNT & ENVIRONMENT ARCHITECTURE

---

## 2.1 Account Structure

Three AWS accounts using AWS Organizations:

```
AWS Organization
├── Management Account (billing only — no workloads)
├── Production Account    (sc-prod)
└── Non-Production Account (sc-nonprod — runs both staging and dev)
```

**Why not separate staging/dev accounts:** A startup with a small team does not need three workload accounts. Non-prod isolation is handled at the resource-naming and VPC level.

## 2.2 Environments

| Environment | Account | Region | Purpose |
|---|---|---|---|
| `dev` | sc-nonprod | eu-west-1 | Local development support; integration testing |
| `staging` | sc-nonprod | eu-west-1 | Pre-production validation; load testing; QA |
| `prod` | sc-prod | eu-west-1 | Live production; customer-facing |

Environment differences are managed exclusively through Terraform variable files and GitHub Actions environment secrets — the infrastructure code is identical across environments.

## 2.3 Resource Naming Convention

```
{service}-{component}-{env}

Examples:
  sc-api-service-prod
  sc-rds-postgres-prod
  sc-pipeline-raw-signals-prod  (SQS queue)
  sc-raw-signals-prod           (S3 bucket)
  sc-classification-service-staging
```

---

---

# SECTION 3 — TERRAFORM IAC STRUCTURE

---

## 3.1 Repository Layout

```
infrastructure/
├── terraform/
│   ├── modules/
│   │   ├── vpc/              # VPC, subnets, NAT gateways, VPC endpoints
│   │   ├── ecs/              # ECS cluster, task definitions, services
│   │   ├── rds/              # PostgreSQL RDS instance + parameter group
│   │   ├── elasticache/      # Redis ElastiCache cluster
│   │   ├── s3/               # All S3 buckets with lifecycle policies
│   │   ├── sqs/              # All SQS queues + DLQs
│   │   ├── cloudfront/       # CloudFront distribution + WAF
│   │   ├── alb/              # Application Load Balancer + target groups
│   │   ├── iam/              # All IAM roles and policies
│   │   ├── kms/              # KMS keys per data classification
│   │   ├── secrets/          # Secrets Manager secret definitions (not values)
│   │   └── observability/    # CloudWatch dashboards, alarms, log groups
│   │
│   ├── environments/
│   │   ├── prod/
│   │   │   ├── main.tf       # Wires modules together for prod
│   │   │   ├── variables.tf
│   │   │   └── prod.tfvars   # Prod-specific sizes, counts, settings
│   │   └── staging/
│   │       ├── main.tf
│   │       └── staging.tfvars  # Smaller instances, single-AZ where appropriate
│   │
│   └── backend.tf            # S3 remote state + DynamoDB lock table
```

## 3.2 Remote State Configuration

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "sc-terraform-state-prod"
    key            = "stem-cogent/{env}/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:eu-west-1:ACCOUNT:key/sc-terraform-state-key"
    dynamodb_table = "sc-terraform-locks"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

---

---

# SECTION 4 — CI/CD PIPELINE

---

## 4.1 Repository Structure

```
stem-cogent-platform/         (monorepo)
├── backend/
├── frontend/
├── infrastructure/
└── .github/
    └── workflows/
        ├── backend-ci.yml
        ├── frontend-ci.yml
        ├── infrastructure-cd.yml
        └── application-cd.yml
```

## 4.2 Branch Strategy

```
main          — production-deployable code; protected; requires PR + 1 approval
staging       — staging environment; auto-deploys on merge
feature/*     — developer feature branches; CI runs on PR open
hotfix/*      — emergency fixes; fast-track to main with expedited review
```

**Branch protection rules on `main`:**
- Require PR with minimum 1 approving review
- Require all CI checks to pass
- No direct push permitted (including repository admins)
- Require linear history (no merge commits — squash or rebase only)

## 4.3 Backend CI Pipeline

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI

on:
  pull_request:
    paths:
      - 'backend/**'
      - 'infrastructure/docker/backend.Dockerfile'
      - '.github/workflows/backend-ci.yml'

permissions:
  contents: read

jobs:
  test-and-scan:
    runs-on: ubuntu-latest
    env:
      IMAGE_REF: sc-api-service:${{ github.sha }}
    services:
      # Spin up local Postgres + Redis for integration tests
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: sc_test
          POSTGRES_USER: sc_test
          POSTGRES_PASSWORD: sc_test
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"

    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt

      # ── Code quality ──────────────────────────────────────────────
      - name: Lint (ruff)
        run: ruff check backend/

      - name: Type check (mypy)
        run: mypy backend/app --ignore-missing-imports

      # ── Security ──────────────────────────────────────────────────
      - name: SAST — Bandit
        run: bandit -r backend/app -ll -f json -o bandit-report.json
        continue-on-error: false   # HIGH findings fail the build

      - name: Secrets scan — TruffleHog
        run: trufflehog filesystem --directory=backend/ --fail

      - name: Dependency CVE scan — Safety
        run: safety check -r backend/requirements.txt --full-report

      # ── Tests ─────────────────────────────────────────────────────
      - name: Run unit tests
        run: |
          pytest backend/tests/unit/ -v \
            --cov=backend/app \
            --cov-report=xml \
            --cov-fail-under=75
        env:
          DATABASE_URL: postgresql://sc_test:sc_test@localhost/sc_test
          REDIS_URL: redis://localhost:6379

      - name: Run integration tests
        run: |
          pytest backend/tests/integration/ -v \
            --timeout=30
        env:
          DATABASE_URL: postgresql://sc_test:sc_test@localhost/sc_test
          REDIS_URL: redis://localhost:6379
          ENVIRONMENT: test

      # ── Build Docker image ─────────────────────────────────────────
      - name: Build Docker image (verify it builds)
        run: |
          docker build --pull -f infrastructure/docker/backend.Dockerfile \
            -t "$IMAGE_REF" \
            backend/

      - name: Verify container base OS
        run: |
          container_os="$(docker run --rm --entrypoint sh "$IMAGE_REF" \
            -c '. /etc/os-release; printf "%s" "$ID"')"
          echo "Container base OS: $container_os"
          test "$container_os" = "alpine"

      - name: Container image scan — Trivy
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: ${{ env.IMAGE_REF }}
          scan-type: image
          format: table
          vuln-type: os,library
          scanners: vuln,secret
          ignore-unfixed: false
          severity: CRITICAL,HIGH
          exit-code: '1'    # Fail on HIGH or CRITICAL CVEs in image
```

## 4.4 Frontend CI Pipeline

```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI

on:
  pull_request:
    paths: ['frontend/**']

jobs:
  test-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend/

      - name: Type check
        run: npm run type-check
        working-directory: frontend/

      - name: Lint (ESLint)
        run: npm run lint
        working-directory: frontend/

      - name: Unit tests (Vitest)
        run: npm run test:unit -- --coverage
        working-directory: frontend/

      - name: Build (verify production build succeeds)
        run: npm run build
        working-directory: frontend/
        env:
          NEXT_PUBLIC_API_URL: https://api.staging.stemcogent.com
          NEXT_PUBLIC_WS_URL: wss://api.staging.stemcogent.com

      - name: Bundle size check
        run: |
          # Fail if initial JS bundle exceeds 200KB gzipped
          node scripts/check-bundle-size.js --max-kb=200
        working-directory: frontend/
```

## 4.5 Infrastructure CD Pipeline

```yaml
# .github/workflows/infrastructure-cd.yml
name: Infrastructure CD

on:
  push:
    branches: [main, staging]
    paths: ['infrastructure/terraform/**']

jobs:
  terraform:
    runs-on: ubuntu-latest
    environment: ${{ github.ref_name == 'main' && 'production' || 'staging' }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT:role/sc-github-actions-terraform-role
          aws-region: eu-west-1

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.7.x'

      - name: Terraform Init
        run: terraform init
        working-directory: infrastructure/terraform/environments/${{ env.TF_ENV }}

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        id: plan
        run: terraform plan -out=tfplan -var-file="${{ env.TF_ENV }}.tfvars"
        working-directory: infrastructure/terraform/environments/${{ env.TF_ENV }}

      - name: Post plan summary to PR
        uses: actions/github-script@v7
        # Posts Terraform plan output as a PR comment for review

      # Production requires manual approval before apply
      - name: Manual approval gate (production only)
        if: github.ref_name == 'main'
        uses: trstringer/manual-approval@v1
        with:
          approvers: devops-lead,principal-architect
          minimum-approvals: 1

      - name: Terraform Apply
        run: terraform apply tfplan
        working-directory: infrastructure/terraform/environments/${{ env.TF_ENV }}
```

## 4.6 Application CD Pipeline

```yaml
# .github/workflows/application-cd.yml
name: Application CD

on:
  push:
    branches: [main, staging]

env:
  ECR_REGISTRY: ACCOUNT.dkr.ecr.eu-west-1.amazonaws.com
  AWS_REGION: eu-west-1

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.ref_name == 'main' && 'production' || 'staging' }}

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT:role/sc-github-actions-deploy-role
          aws-region: eu-west-1

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2

      # Build and push all service images in parallel
      - name: Build & push API service image
        run: |
          IMAGE_TAG=${{ github.sha }}
          docker build -f infrastructure/docker/backend.Dockerfile \
            -t $ECR_REGISTRY/sc-api-service-$ENV:$IMAGE_TAG \
            -t $ECR_REGISTRY/sc-api-service-$ENV:latest \
            backend/
          docker push $ECR_REGISTRY/sc-api-service-$ENV:$IMAGE_TAG
          docker push $ECR_REGISTRY/sc-api-service-$ENV:latest

      - name: Build & push worker image
        run: |
          IMAGE_TAG=${{ github.sha }}
          docker build -f infrastructure/docker/worker.Dockerfile \
            -t $ECR_REGISTRY/sc-worker-$ENV:$IMAGE_TAG \
            backend/
          docker push $ECR_REGISTRY/sc-worker-$ENV:$IMAGE_TAG

      - name: Build & push frontend image
        run: |
          docker build -f infrastructure/docker/frontend.Dockerfile \
            -t $ECR_REGISTRY/sc-frontend-$ENV:$IMAGE_TAG \
            frontend/

      # Run DB migrations before deploying new app version
      - name: Run database migrations
        run: |
          aws ecs run-task \
            --cluster sc-cluster-$ENV \
            --task-definition sc-migration-task-$ENV \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$PRIVATE_SUBNET_IDS],securityGroups=[$MIGRATION_SG_ID],assignPublicIp=DISABLED}" \
            --overrides '{"containerOverrides":[{"name":"migration","command":["alembic","upgrade","head"]}]}'

      # Deploy services with rolling update
      - name: Deploy API service
        run: |
          aws ecs update-service \
            --cluster sc-cluster-$ENV \
            --service sc-api-service-$ENV \
            --force-new-deployment

      - name: Deploy worker services
        run: |
          for service in rss-collector api-collector normalization classification enrichment synthesis delivery alert; do
            aws ecs update-service \
              --cluster sc-cluster-$ENV \
              --service sc-${service}-worker-$ENV \
              --force-new-deployment
          done

      - name: Wait for deployment stability
        run: |
          aws ecs wait services-stable \
            --cluster sc-cluster-$ENV \
            --services sc-api-service-$ENV

      # Smoke test after deployment
      - name: Smoke test
        run: |
          # Health check
          curl -f https://api.$DOMAIN/health/ready || exit 1
          # Auth check
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            https://api.$DOMAIN/api/v1/signals)
          [ "$STATUS" = "401" ] || exit 1  # Unauthenticated should return 401

      # Rollback on smoke test failure
      - name: Rollback on failure
        if: failure()
        run: |
          echo "Deployment failed — rolling back to previous task definition"
          PREV_TASK_DEF=$(aws ecs describe-services \
            --cluster sc-cluster-$ENV \
            --services sc-api-service-$ENV \
            --query 'services[0].deployments[1].taskDefinition' \
            --output text)
          aws ecs update-service \
            --cluster sc-cluster-$ENV \
            --service sc-api-service-$ENV \
            --task-definition $PREV_TASK_DEF
```

---

---

# SECTION 5 — CONTAINER ORCHESTRATION (ECS FARGATE)

---

## 5.1 Service Definitions

All compute runs on **AWS ECS Fargate** — serverless containers with no EC2 instance management.

```
ECS Cluster: sc-cluster-{env}

Services:
  API Layer:
    sc-api-service              ← FastAPI app (public-facing via ALB)

  Pipeline Workers:
    sc-rss-collector-worker     ← RSS/Atom feed collection
    sc-api-collector-worker     ← REST API source collection
    sc-scraper-worker           ← Playwright web scraping
    sc-pdf-collector-worker     ← PDF download + extraction
    sc-upload-collector-worker  ← Enterprise document processing
    sc-validation-worker        ← Source validation + deduplication
    sc-normalization-worker     ← Parsing + NER + language detection
    sc-classification-worker    ← DistilBERT + rule-based classification
    sc-enrichment-worker        ← Confidence scoring + entity resolution
    sc-clustering-worker        ← Signal clustering + trend detection
    sc-synthesis-worker         ← Context assembly + LLM synthesis
    sc-alert-worker             ← Alert threshold evaluation + dispatch
    sc-delivery-worker          ← Email + push + WebSocket delivery
    sc-digest-worker            ← Scheduled digest generation

  Internal Services:
    sc-mlflow-server            ← MLflow tracking server (internal only)
```

## 5.2 Compute Sizing Matrix

Sizing is deliberately conservative at launch. Scale up when CloudWatch metrics show CPU > 70% sustained.

| Service | CPU (vCPU) | Memory (MB) | Min Tasks | Max Tasks | Notes |
|---|---|---|---|---|---|
| `sc-api-service` | 1.0 | 2048 | 2 | 10 | 2 for HA; scales with request rate |
| `sc-rss-collector-worker` | 0.5 | 512 | 1 | 20 | Scales with queue depth |
| `sc-api-collector-worker` | 0.5 | 512 | 1 | 30 | Higher max — API sources dominant |
| `sc-scraper-worker` | 1.0 | 2048 | 1 | 8 | Playwright is memory-heavy |
| `sc-pdf-collector-worker` | 0.5 | 1024 | 1 | 10 | PDF parsing is CPU-light |
| `sc-upload-collector-worker` | 0.5 | 512 | 1 | 10 | Triggered by upload events |
| `sc-validation-worker` | 0.5 | 512 | 1 | 15 | Fast; parallel with storage |
| `sc-normalization-worker` | 1.0 | 2048 | 1 | 15 | LLM translation calls add latency |
| `sc-classification-worker` | 2.0 | 4096 | 2 | 20 | DistilBERT in-process; 2 min for HA |
| `sc-enrichment-worker` | 1.0 | 2048 | 1 | 15 | Parallel substages |
| `sc-clustering-worker` | 1.0 | 2048 | 1 | 10 | pgvector queries dominate |
| `sc-synthesis-worker` | 0.5 | 2048 | 1 | 15 | Waits on LLM API; low CPU |
| `sc-alert-worker` | 0.5 | 512 | 1 | 10 | Fast; mostly Redis + DB writes |
| `sc-delivery-worker` | 0.5 | 512 | 1 | 10 | Waits on email/push APIs |
| `sc-digest-worker` | 1.0 | 2048 | 1 | 5 | Scheduled; low volume |
| `sc-mlflow-server` | 0.5 | 1024 | 1 | 1 | Single instance; internal only |

## 5.3 Autoscaling Configuration

All pipeline worker services scale on **SQS queue depth** via Application Auto Scaling. The API service scales on **ALB request count**.

```python
AUTOSCALING_CONFIG = {
    # Pattern applied to all pipeline worker services
    "worker_scaling": {
        "metric":           "SQS ApproximateNumberOfMessagesVisible",
        "scale_out": {
            "threshold":    100,   # messages per running task
            "cooldown_seconds": 60
        },
        "scale_in": {
            "threshold":    10,    # messages per running task
            "cooldown_seconds": 300   # longer cooldown prevents thrashing
        },
        "evaluation_periods": 2,   # 2 consecutive periods before scaling
        "period_seconds":     60
    },

    # API service scales on request count
    "api_scaling": {
        "metric":           "ALBRequestCountPerTarget",
        "target_value":     1000,  # requests per minute per task
        "scale_out_cooldown": 60,
        "scale_in_cooldown":  300
    }
}
```

**Terraform autoscaling resource (example — classification worker):**

```hcl
resource "aws_appautoscaling_policy" "classification_worker_scale_out" {
  name               = "sc-classification-worker-scale-out-${var.env}"
  resource_id        = "service/sc-cluster-${var.env}/sc-classification-worker-${var.env}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  policy_type        = "StepScaling"

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_lower_bound = 0
      metric_interval_upper_bound = 200
      scaling_adjustment          = 1   # Add 1 task
    }
    step_adjustment {
      metric_interval_lower_bound = 200
      scaling_adjustment          = 3   # Add 3 tasks for large backlogs
    }
  }
}
```

## 5.4 Deployment Strategy

**Strategy:** Rolling update with minimum healthy percent = 50%, maximum percent = 200%.

```
ROLLING DEPLOYMENT SEQUENCE:
  1. ECS launches new task (new version)
  2. ALB health check passes on new task
  3. ECS drains connections from one old task
  4. Old task stopped
  5. Repeat until all tasks running new version

ZERO-DOWNTIME GUARANTEES:
  - API service: min 2 tasks always running; new tasks added before old removed
  - Pipeline workers: SQS message visibility timeout ensures in-flight messages
    complete before worker task is drained
  - DB migrations run BEFORE app deployment (backward-compatible migrations only)
```

**Backward-compatible migration rule:** Every migration must work with both the current AND next version of the application code. No migration can drop a column or table that the previous version of the app still reads.

## 5.5 Dockerfiles

```dockerfile
# infrastructure/docker/backend.Dockerfile
FROM python:3.12.13-alpine3.23 AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12.13-alpine3.23 AS runtime

# Security: non-root user
RUN addgroup -g 1000 -S appuser \
    && adduser -u 1000 -S -D -H -G appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app/ ./app/

# Security: read-only filesystem + non-root
USER 1000
RUN chmod -R 444 /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=5).close()"

CMD ["gunicorn", "app.main:app",
     "--worker-class", "uvicorn.workers.UvicornWorker",
     "--workers", "2",
     "--bind", "0.0.0.0:8000",
     "--access-logfile", "-",
     "--error-logfile", "-",
     "--log-level", "info"]
```

```dockerfile
# infrastructure/docker/worker.Dockerfile
FROM python:3.12.13-alpine3.23 AS runtime

RUN addgroup -g 1000 -S workeruser \
    && adduser -u 1000 -S -D -H -G workeruser workeruser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

USER 1000

# CMD overridden per ECS task definition to specify which worker type
# e.g., celery -A app.workers.celery_app worker --queues=ingestion-priority
CMD ["celery", "-A", "app.workers.celery_app", "worker",
     "--loglevel=info", "--concurrency=4"]
```

---

---

# SECTION 6 — DATA INFRASTRUCTURE

---

## 6.1 RDS PostgreSQL

```hcl
# Production configuration
resource "aws_db_instance" "sc_postgres_prod" {
  identifier        = "sc-postgres-prod"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t4g.large"   # 2 vCPU, 8 GB RAM — sufficient at launch
  allocated_storage = 100              # GB
  max_allocated_storage = 500          # Auto-scales up to 500GB

  db_name  = "stemcogent"
  username = "sc_admin"
  password = data.aws_secretsmanager_secret_version.rds_password.secret_string

  multi_az               = true      # Automatic failover to standby
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.sc_rds.arn

  backup_retention_period = 7         # 7 days automated backups
  backup_window           = "02:00-03:00"  # 02:00-03:00 UTC (low traffic window)
  maintenance_window      = "sun:03:00-sun:04:00"

  deletion_protection     = true      # Cannot be deleted via console
  skip_final_snapshot     = false
  final_snapshot_identifier = "sc-postgres-prod-final-${formatdate("YYYYMMDD", timestamp())}"

  performance_insights_enabled = true
  monitoring_interval          = 60   # Enhanced monitoring every 60s
  monitoring_role_arn          = aws_iam_role.rds_monitoring.arn

  parameter_group_name = aws_db_parameter_group.sc_postgres16.name

  vpc_security_group_ids = [aws_security_group.data_layer.id]
  db_subnet_group_name   = aws_db_subnet_group.private_data.name
}

# Read replica for API read queries and ClickHouse CDC
resource "aws_db_instance" "sc_postgres_prod_replica" {
  identifier          = "sc-postgres-prod-replica"
  replicate_source_db = aws_db_instance.sc_postgres_prod.identifier
  instance_class      = "db.t4g.medium"   # Smaller — reads only
  publicly_accessible = false
  skip_final_snapshot = true
}

# PostgreSQL parameter tuning
resource "aws_db_parameter_group" "sc_postgres16" {
  family = "postgres16"
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgvector"
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"   # Log queries taking > 1 second
  }
  parameter {
    name  = "max_connections"
    value = "200"
  }
}
```

**Instance sizing upgrade path:**
- Launch: `db.t4g.large` (2 vCPU, 8GB)
- Phase 2 (>50K signals/day or >10 customers): `db.t4g.xlarge` (4 vCPU, 16GB)
- Phase 3 (>200K signals/day): `db.r7g.xlarge` (4 vCPU, 32GB — memory-optimized)

## 6.2 ElastiCache Redis

```hcl
resource "aws_elasticache_replication_group" "sc_redis_prod" {
  replication_group_id = "sc-redis-prod"
  description          = "Stem Cogent Redis — cache, broker, rate limiting"

  node_type            = "cache.t4g.medium"   # 2 vCPU, 3.1 GB RAM
  num_cache_clusters   = 1    # Single node at launch (no cluster mode)
                               # Add replica for HA when budget allows

  engine_version       = "7.1"
  port                 = 6379

  at_rest_encryption_enabled  = false  # Redis in-memory data is not encrypted at rest
                                        # (data also persists in DB — Redis is cache)
  transit_encryption_enabled  = true   # TLS in-transit
  auth_token                  = data.aws_secretsmanager_secret_version.redis_auth.secret_string

  automatic_failover_enabled  = false  # Requires multiple nodes
  multi_az_enabled            = false  # Single node at launch

  snapshot_retention_limit    = 3      # 3 daily RDB snapshots
  snapshot_window             = "03:00-04:00"

  subnet_group_name           = aws_elasticache_subnet_group.private_data.name
  security_group_ids          = [aws_security_group.data_layer.id]
}
```

## 6.3 SQS Queues

All pipeline queues defined in Terraform. DLQ paired with every queue.

```hcl
locals {
  pipeline_queues = [
    "ingestion-priority",
    "ingestion-standard",
    "pipeline-raw-signals",
    "pipeline-validated",
    "pipeline-normalized",
    "pipeline-classified",
    "pipeline-enriched",
    "pipeline-scored",
    "pipeline-clustered",
    "pipeline-synthesized",
    "pipeline-recommended",
    "pipeline-alerts",
    "pipeline-suspicious",
    "classification-review",
    "entity-review",
    "feedback-events",
    "graph-updates"
  ]
}

resource "aws_sqs_queue" "pipeline_queues" {
  for_each = toset(local.pipeline_queues)

  name                       = "sc-${each.key}-${var.env}"
  visibility_timeout_seconds = lookup(var.queue_visibility_timeouts, each.key, 300)
  message_retention_seconds  = 259200   # 72 hours
  receive_wait_time_seconds  = 20       # Long polling
  sqs_managed_sse_enabled    = true     # SSE encryption

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlqs[each.key].arn
    maxReceiveCount     = lookup(var.queue_max_receive_counts, each.key, 3)
  })
}

resource "aws_sqs_queue" "dlqs" {
  for_each = toset(local.pipeline_queues)

  name                      = "sc-${each.key}-dlq-${var.env}"
  message_retention_seconds = 1209600  # 14 days in DLQ
  sqs_managed_sse_enabled   = true
}
```

## 6.4 ClickHouse

At launch, ClickHouse runs as a **single EC2 instance** (not RDS — no managed ClickHouse in AWS). This is intentional simplicity.

```hcl
resource "aws_instance" "clickhouse" {
  ami           = data.aws_ami.ubuntu_22.id
  instance_type = "t3.large"   # 2 vCPU, 8GB RAM — sufficient at launch analytics volume
  subnet_id     = aws_subnet.private_data_a.id

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 200      # GB
    encrypted             = true
    kms_key_id            = aws_kms_key.sc_analytics.arn
    delete_on_termination = false    # Preserve data on instance replacement
  }

  vpc_security_group_ids = [aws_security_group.clickhouse.id]
  iam_instance_profile   = aws_iam_instance_profile.clickhouse.name

  user_data = base64encode(templatefile("scripts/install-clickhouse.sh", {
    clickhouse_version = "24.3"
    admin_password_arn = aws_secretsmanager_secret.clickhouse_admin.arn
  }))

  tags = { Name = "sc-clickhouse-${var.env}" }
}
```

**ClickHouse upgrade path:** Replace with `t3.xlarge` when analytics query latency p95 exceeds 2 seconds. Move to ClickHouse Cloud when team capacity allows managed service overhead reduction.

---

---

# SECTION 7 — OBSERVABILITY STACK

---

## 7.1 Metrics (CloudWatch)

### Custom Metrics Architecture

All services publish custom metrics to CloudWatch via `boto3.put_metric_data()`. A shared metrics utility standardizes metric publishing:

```python
# app/utils/metrics.py

import boto3
from functools import lru_cache

@lru_cache(maxsize=1)
def get_cloudwatch_client():
    return boto3.client("cloudwatch", region_name="eu-west-1")

class PipelineMetrics:
    NAMESPACE = "StemCogent/Pipeline"

    @staticmethod
    def increment(metric_name: str, tags: dict = None, value: float = 1.0):
        dimensions = [
            {"Name": k, "Value": str(v)}
            for k, v in (tags or {}).items()
        ]
        get_cloudwatch_client().put_metric_data(
            Namespace=PipelineMetrics.NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": "Count",
                "Dimensions": dimensions
            }]
        )

    @staticmethod
    def histogram(metric_name: str, value: float,
                  unit: str = "Milliseconds", tags: dict = None):
        dimensions = [
            {"Name": k, "Value": str(v)}
            for k, v in (tags or {}).items()
        ]
        get_cloudwatch_client().put_metric_data(
            Namespace=PipelineMetrics.NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": dimensions
            }]
        )

# Usage in pipeline workers:
PipelineMetrics.increment("SignalsProcessed",
                           tags={"Stage": "classification", "Domain": "REGULATORY"})
PipelineMetrics.histogram("ProcessingLatencyMs",
                           value=elapsed_ms,
                           tags={"Stage": "synthesis"})
```

### Complete Metric Inventory

```python
PIPELINE_METRICS = {
    # Throughput
    "SignalsProcessed":         "Counter — signals completed per stage",
    "SignalsFailed":            "Counter — failures per stage and failure type",
    "SignalsDeduplicated":      "Counter — dedup type (EXACT/SEMANTIC/NEAR)",
    "AlertsDispatched":         "Counter — per alert type and channel",

    # Quality
    "ClassificationConfidence": "Histogram — P50/P95/P99 per domain",
    "ConfidenceScore":          "Histogram — P50/P95 of confidence scores",
    "UrgencyScore":             "Histogram — urgency score distribution",
    "CitationHallucinations":   "Counter — uncited claims stripped from LLM output",

    # Latency
    "ProcessingLatencyMs":      "Histogram — end-to-end and per stage",
    "LLMRequestDurationMs":     "Histogram — per provider and operation",
    "EmbeddingRequestDurationMs": "Histogram — embedding API latency",

    # Queue health
    "QueueDepth":               "Gauge — per queue (polled from SQS every 60s)",
    "DLQMessageCount":          "Gauge — per DLQ (critical alert trigger)",

    # Source health
    "CollectorSuccessTotal":    "Counter — per source_id",
    "CollectorFailureTotal":    "Counter — per source_id and failure reason",
    "SourceHealthStatus":       "Gauge — 1=ACTIVE, 0.5=DEGRADED, 0=FAILED",

    # CIL
    "CILQueryTotal":            "Counter — per intent type",
    "CILResponseLatencyMs":     "Histogram — P50/P95/P99",
    "CILOutOfScopeRate":        "Gauge — % of queries rejected as out-of-scope",

    # Cost
    "LLMTokensUsed":            "Counter — per provider and operation type",
    "EstimatedLLMCostUSD":      "Gauge — rolling daily estimate"
}
```

### SQS Queue Depth Poller

Queue depth is not emitted automatically by SQS into custom CloudWatch metrics — it needs to be polled:

```python
# app/workers/tasks/monitoring.py
# Celery Beat task — runs every 60 seconds

@celery_app.task(name="poll_queue_depths")
def poll_queue_depths():
    sqs = boto3.client("sqs", region_name="eu-west-1")
    cw  = get_cloudwatch_client()

    queues = {
        "ingestion-priority":   settings.SQS_INGESTION_PRIORITY_URL,
        "pipeline-classified":  settings.SQS_PIPELINE_CLASSIFIED_URL,
        "pipeline-synthesized": settings.SQS_PIPELINE_SYNTHESIZED_URL,
        # ... all queues
    }

    metric_data = []
    for queue_name, queue_url in queues.items():
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages",
                             "ApproximateNumberOfMessagesNotVisible"]
        )["Attributes"]

        visible = int(attrs["ApproximateNumberOfMessages"])
        in_flight = int(attrs["ApproximateNumberOfMessagesNotVisible"])

        metric_data.extend([
            {"MetricName": "QueueDepth",
             "Value": visible,
             "Unit": "Count",
             "Dimensions": [{"Name": "QueueName", "Value": queue_name}]},
            {"MetricName": "QueueMessagesInFlight",
             "Value": in_flight,
             "Unit": "Count",
             "Dimensions": [{"Name": "QueueName", "Value": queue_name}]}
        ])

    cw.put_metric_data(Namespace="StemCogent/Pipeline", MetricData=metric_data)
```

---

## 7.2 Structured Logging

All services emit structured JSON logs to CloudWatch Logs. Logs are queryable via CloudWatch Log Insights.

```python
# app/core/logging.py

import logging
import json
from contextvars import ContextVar

# Context variables propagated through request/worker lifecycle
request_id_var:     ContextVar[str | None] = ContextVar("request_id",     default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
tenant_id_var:      ContextVar[str | None] = ContextVar("tenant_id",      default=None)
signal_id_var:      ContextVar[str | None] = ContextVar("signal_id",      default=None)

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp":      self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level":          record.levelname,
            "service":        record.__dict__.get("service", "unknown"),
            "environment":    settings.ENVIRONMENT,
            "message":        record.getMessage(),
            "logger":         record.name,
            "request_id":     request_id_var.get(),
            "correlation_id": correlation_id_var.get(),
            "tenant_id":      tenant_id_var.get(),
            "signal_id":      signal_id_var.get(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms
        if hasattr(record, "error_code"):
            log_record["error_code"] = record.error_code

        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()   # CloudWatch captures stdout
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

### CloudWatch Log Groups

```python
LOG_GROUPS = {
    "/sc/api-service/{env}":            "API request/response logs; 90 day retention",
    "/sc/pipeline/ingestion/{env}":     "Collector worker logs; 30 day retention",
    "/sc/pipeline/processing/{env}":    "Normalization, classification, enrichment; 30 day",
    "/sc/pipeline/synthesis/{env}":     "Synthesis worker logs; 30 day retention",
    "/sc/pipeline/delivery/{env}":      "Delivery worker logs; 30 day retention",
    "/sc/pipeline/dlq/{env}":           "DLQ processor logs; 90 day retention",
    "/sc/infrastructure/{env}":         "ECS task lifecycle events; 14 day retention",
}
```

### CloudWatch Log Insights Queries

Key operational queries pre-built for daily use:

```sql
-- Pipeline error rate by stage (last 1 hour)
fields @timestamp, service, error_code, signal_id
| filter level = "ERROR"
| stats count(*) as error_count by service, error_code
| sort error_count desc

-- Average synthesis latency by hour
fields @timestamp, duration_ms
| filter service = "synthesis-worker" and @message like "SIGNAL_SYNTHESIZED"
| stats avg(duration_ms) as avg_ms, pct(duration_ms, 95) as p95_ms by bin(1h)

-- DLQ arrivals in last 24 hours
fields @timestamp, service, correlation_id, error_code
| filter @logStream like "dlq"
| sort @timestamp desc

-- LLM fallback rate (last 24 hours)
fields @timestamp, llm_synthesis_failed
| filter llm_synthesis_failed = true
| stats count(*) as fallback_count by bin(1h)
```

---

## 7.3 Distributed Tracing (AWS X-Ray)

X-Ray traces the full request lifecycle from API entry to delivery, using `correlation_id` (the pipeline's own ID) as the trace annotation. This links X-Ray traces to CloudWatch logs and the pipeline audit records.

```python
# app/core/tracing.py

from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

# Patch common libraries for automatic trace propagation
patch_all()  # Patches: boto3, requests, httpx, psycopg2, redis

def configure_tracing(app):
    xray_recorder.configure(
        service="sc-api-service",
        sampling=True,
        sampling_rules={
            "default": {
                "fixed_target": 2,   # 2 requests/second sampled always
                "rate": 0.05         # 5% of remaining requests sampled
            },
            "rules": [
                {
                    "description": "Health checks — do not sample",
                    "url_path": "/health/*",
                    "fixed_target": 0,
                    "rate": 0
                },
                {
                    "description": "CIL queries — sample 100% for latency analysis",
                    "url_path": "/api/v1/cil/*",
                    "fixed_target": 0,
                    "rate": 1.0
                }
            ]
        }
    )
    app.add_middleware(XRayMiddleware, recorder=xray_recorder)
```

**Worker tracing:** Pipeline workers create X-Ray subsegments for each processing stage, annotated with `correlation_id` and `signal_id`:

```python
async def process(self, event: EventEnvelope):
    with xray_recorder.in_subsegment(f"classification-worker") as subsegment:
        subsegment.put_annotation("correlation_id", event.correlation_id)
        subsegment.put_annotation("signal_id", event.payload.get("signal_id"))
        subsegment.put_annotation("source_tier", event.payload.get("source_tier"))

        # ... processing logic

        subsegment.put_metadata("classification_result", {
            "primary_domain": result.primary_domain,
            "confidence": result.confidence,
            "method": result.method
        })
```

---

## 7.4 Dashboards

Three CloudWatch dashboards — kept deliberately minimal, one per operational concern:

### Dashboard 1: Pipeline Health

```
PIPELINE HEALTH — Updated every 60 seconds

Row 1: STATUS INDICATORS (single-value widgets)
  [Ingestion queue depth] [Classification queue depth] [Synthesis queue depth]
  [DLQ total messages]   [Active alerts today]         [Pipeline uptime %]

Row 2: THROUGHPUT (line graphs, last 24 hours)
  [Signals processed/hour by stage]  [Signal classification domain breakdown]

Row 3: LATENCY (line graphs, last 6 hours)
  [P95 E2E pipeline latency]  [P95 classification latency]  [P95 LLM synthesis latency]

Row 4: ERRORS (bar charts)
  [Errors by stage (last 1 hour)]  [Collector failure rate by source tier]
```

### Dashboard 2: Intelligence Quality

```
INTELLIGENCE QUALITY — Updated every 5 minutes

Row 1: CONFIDENCE DISTRIBUTION (histogram)
  [Confidence score percentile distribution today]
  [% HIGH_CONFIDENCE vs MODERATE vs LOW]

Row 2: CLASSIFICATION
  [Domain distribution of signals today]
  [Classification method breakdown (HYBRID vs RULE_ONLY vs ML_ONLY)]
  [Review flag rate]

Row 3: LLM QUALITY
  [Citation hallucination rate]  [LLM fallback rate]  [Template synthesis rate]
```

### Dashboard 3: Cost & Capacity

```
COST & CAPACITY — Updated every hour

Row 1: ESTIMATED COSTS
  [Estimated daily LLM spend ($)]  [LLM tokens used today (by provider)]
  [ECS Fargate task hours today]   [S3 storage growth (GB/day)]

Row 2: CAPACITY
  [ECS task counts by service]  [RDS connections used / max]
  [Redis memory used %]          [SQS queue ages (oldest message age)]
```

---

## 7.5 Alerting

All alerts route to SNS topics → PagerDuty (P1/P2) or Slack (P2/P3).

```python
CLOUDWATCH_ALARMS = [

    # ── P1 ALARMS (PagerDuty — 24/7 immediate response) ──────────────────

    {
        "name": "sc-dlq-critical-depth",
        "metric": "DLQMessageCount",
        "dimensions": {"QueueName": "ingestion-priority-dlq"},
        "threshold": 1,            # Any message in CRITICAL source DLQ = P1
        "comparison": "GreaterThanOrEqualToThreshold",
        "evaluation_periods": 1,
        "severity": "P1"
    },
    {
        "name": "sc-pipeline-e2e-latency-critical",
        "metric": "ProcessingLatencyMs",
        "dimensions": {"Stage": "e2e"},
        "threshold": 600000,       # 10 minutes in milliseconds
        "statistic": "p95",
        "evaluation_periods": 2,
        "severity": "P1"
    },
    {
        "name": "sc-rds-connection-saturation",
        "metric": "DatabaseConnections",
        "namespace": "AWS/RDS",
        "threshold": 180,          # 90% of max_connections=200
        "evaluation_periods": 3,
        "severity": "P1"
    },

    # ── P2 ALARMS (PagerDuty + Slack — respond within 30 min) ────────────

    {
        "name": "sc-llm-error-rate-high",
        "metric": "LLMRequestError",
        "threshold": 0.10,         # 10% error rate
        "statistic": "Average",
        "period_seconds": 900,     # 15-minute window
        "evaluation_periods": 2,
        "severity": "P2"
    },
    {
        "name": "sc-synthesis-queue-backed-up",
        "metric": "QueueDepth",
        "dimensions": {"QueueName": "pipeline-synthesized"},
        "threshold": 5000,         # > 5000 messages backed up
        "evaluation_periods": 2,
        "severity": "P2"
    },
    {
        "name": "sc-api-error-rate",
        "metric": "5XXError",
        "namespace": "AWS/ApplicationELB",
        "threshold": 0.05,         # > 5% 5xx error rate
        "evaluation_periods": 3,
        "severity": "P2"
    },
    {
        "name": "sc-rds-cpu-high",
        "metric": "CPUUtilization",
        "namespace": "AWS/RDS",
        "threshold": 85,           # > 85% CPU for 5 minutes
        "evaluation_periods": 5,
        "severity": "P2"
    },
    {
        "name": "sc-redis-memory-high",
        "metric": "DatabaseMemoryUsagePercentage",
        "namespace": "AWS/ElastiCache",
        "threshold": 80,
        "evaluation_periods": 3,
        "severity": "P2"
    },
    {
        "name": "sc-collector-failure-spike",
        "metric": "CollectorFailureTotal",
        "threshold": 50,           # > 50 collector failures in 30 minutes
        "period_seconds": 1800,
        "evaluation_periods": 1,
        "severity": "P2"
    },
    {
        "name": "sc-llm-daily-cost-warning",
        "metric": "EstimatedLLMCostUSD",
        "threshold": 150,          # > $150 estimated daily LLM spend
        "evaluation_periods": 1,
        "severity": "P2"
    },

    # ── P3 ALARMS (Slack only — respond next business day) ────────────────

    {
        "name": "sc-classification-review-queue-growing",
        "metric": "QueueDepth",
        "dimensions": {"QueueName": "classification-review"},
        "threshold": 500,
        "evaluation_periods": 5,
        "severity": "P3"
    },
    {
        "name": "sc-entity-review-queue-growing",
        "metric": "QueueDepth",
        "dimensions": {"QueueName": "entity-review"},
        "threshold": 200,
        "evaluation_periods": 5,
        "severity": "P3"
    },
    {
        "name": "sc-llm-fallback-rate-high",
        "metric": "LLMFallbackActivations",
        "threshold": 50,           # > 50 template fallbacks/hour
        "period_seconds": 3600,
        "evaluation_periods": 1,
        "severity": "P3"
    }
]
```

---

---

# SECTION 8 — DATABASE OPERATIONS

---

## 8.1 Migration Management

**Tool:** Alembic (SQLAlchemy migration framework)

```python
# Migration rules (enforced by PR review checklist):
MIGRATION_RULES = [
    "Every schema change requires an Alembic migration script",
    "No ad hoc DDL in production — ever",
    "Migrations must be backward-compatible with previous app version",
    "Non-destructive changes (ADD COLUMN, CREATE INDEX CONCURRENTLY) are safe to apply with zero downtime",
    "Destructive changes (DROP COLUMN) require 3-step: deprecate → deploy → apply DDL",
    "CREATE INDEX must use CONCURRENTLY to avoid table locks",
    "Migration history committed to repository — never modified after merge"
]

# Migration naming convention
# {revision_id}_{YYYY_MM_DD}_{short_description}.py
# Example: 0043_2025_06_15_add_novelty_score_to_signals.py
```

**Alembic migration CI check:**

```yaml
# In backend-ci.yml
- name: Verify migration consistency
  run: |
    alembic check   # Fails if pending migrations exist that haven't been applied to schema
    alembic history --verbose   # Output for review
```

**Production migration execution (in CD pipeline before app deploy):**

```bash
# Runs as a one-shot ECS task before new app version deploys
aws ecs run-task \
  --cluster sc-cluster-prod \
  --task-definition sc-migration-task-prod \
  --overrides '{"containerOverrides":[{"name":"migration",
    "command":["alembic","upgrade","head"],
    "environment":[{"name":"DATABASE_URL","value":"'"$DB_URL"'"}]}]}'

# Wait for task completion
aws ecs wait tasks-stopped --cluster sc-cluster-prod --tasks $TASK_ARN

# Verify exit code
EXIT_CODE=$(aws ecs describe-tasks --cluster sc-cluster-prod --tasks $TASK_ARN \
  --query 'tasks[0].containers[0].exitCode' --output text)
[ "$EXIT_CODE" = "0" ] || { echo "Migration failed"; exit 1; }
```

## 8.2 Backup & Recovery

```python
BACKUP_CONFIGURATION = {
    "rds_automated": {
        "retention_days": 7,
        "window": "02:00-03:00 UTC",
        "type": "Automated snapshots + continuous WAL archival (PITR)"
    },
    "rds_manual": {
        "frequency": "Weekly (Sunday 03:00 UTC)",
        "retention": "30 days",
        "trigger": "GitHub Actions scheduled workflow"
    },
    "s3_replication": {
        "raw_signals_bucket": "Cross-region replication to eu-west-2 (DR)",
        "enterprise_uploads_bucket": "Cross-region replication to eu-west-2"
    },
    "clickhouse": {
        "method": "EBS snapshot via AWS Data Lifecycle Manager",
        "frequency": "Daily",
        "retention": "7 snapshots"
    },
    "rto_target": "2 hours (full RDS restore from snapshot + WAL replay)",
    "rpo_target": "5 minutes (PITR capability)"
}
```

**Monthly restore test (automated):**

```bash
# .github/workflows/restore-test.yml — runs first Sunday of each month
# 1. Create RDS snapshot from production
# 2. Restore to temporary isolated test instance
# 3. Run smoke queries against restored instance
# 4. Verify data consistency: row counts, recent signal timestamps
# 5. Destroy test instance
# 6. Write test result to compliance evidence S3 bucket
```

## 8.3 Signal Reprocessing Utility

Allows reprocessing any signal from its raw S3 snapshot — used after pipeline bugs, classifier retraining, or taxonomy updates:

```python
# infrastructure/scripts/reprocess.py

"""
Reprocess signals from raw S3 snapshots.

Usage:
  # Reprocess a single signal from a specific pipeline stage
  python reprocess.py --signal-id {uuid} --from-stage normalized

  # Reprocess all signals from a date range (after classifier retrain)
  python reprocess.py --from-date 2025-06-01 --to-date 2025-06-07 \
                      --from-stage classified --domain REGULATORY

  # Reprocess all DLQ messages for a specific stage
  python reprocess.py --from-dlq pipeline-normalized-dlq
"""

async def reprocess_signal(signal_id: str, from_stage: str):
    # 1. Fetch current signal record from DB
    signal = await db.fetch_one(
        "SELECT * FROM pipeline.signals WHERE id = $1", signal_id
    )

    # 2. Build event envelope from raw storage path
    raw_path = signal["raw_storage_path"]
    collection_job_id = signal["collection_job_id"]

    # 3. Construct and publish event to appropriate queue
    stage_queue_map = {
        "raw":          settings.SQS_PIPELINE_RAW_SIGNALS,
        "validated":    settings.SQS_PIPELINE_VALIDATED,
        "normalized":   settings.SQS_PIPELINE_NORMALIZED,
        "classified":   settings.SQS_PIPELINE_CLASSIFIED,
    }

    queue_url = stage_queue_map[from_stage]
    event = build_reprocessing_event(signal, from_stage, raw_path)
    sqs.send_message(QueueUrl=queue_url, MessageBody=event.model_dump_json())

    print(f"Signal {signal_id} queued for reprocessing from {from_stage}")
```

---

---

# SECTION 9 — ENVIRONMENT CONFIGURATION

---

## 9.1 Environment Variables

No secrets in environment variables. All secret values referenced via Secrets Manager ARN or SSM Parameter Store path. Non-secret configuration is set as environment variables in ECS task definitions via Terraform.

```python
# app/core/config.py — Pydantic settings model

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Service identity (non-secret — set in ECS task definition)
    ENVIRONMENT:           str = "development"
    SERVICE_NAME:          str = "sc-api-service"
    AWS_REGION:            str = "eu-west-1"
    LOG_LEVEL:             str = "INFO"

    # Database (non-secret endpoint config — password fetched from Secrets Manager)
    DATABASE_HOST:         str
    DATABASE_PORT:         int = 5432
    DATABASE_NAME:         str = "stemcogent"
    DATABASE_REPLICA_HOST: str | None = None
    DATABASE_URL:          str | None = None  # Local development and CI only

    # Redis (non-secret endpoint — auth token fetched from Secrets Manager)
    REDIS_HOST:            str
    REDIS_PORT:            int = 6379
    REDIS_URL:             str | None = None  # Local development and CI only

    # SQS Queue URLs (non-secret)
    SQS_INGESTION_PRIORITY_URL:   str
    SQS_PIPELINE_RAW_SIGNALS_URL: str
    SQS_PIPELINE_VALIDATED_URL:   str
    # ... all queue URLs

    # S3 Buckets (non-secret)
    S3_RAW_SIGNALS_BUCKET:        str
    S3_ENTERPRISE_UPLOADS_BUCKET: str
    S3_ML_ARTEFACTS_BUCKET:       str

    # Secrets Manager ARNs (these reference secrets — not the secrets themselves)
    DATABASE_CREDENTIALS_ARN:     str
    REDIS_AUTH_TOKEN_ARN:         str
    JWT_SIGNING_SECRET_ARN:       str
    OPENAI_API_KEY_ARN:           str
    ANTHROPIC_API_KEY_ARN:        str

    # Feature flags (non-secret)
    SYNTHESIS_ENABLED:            bool = True
    CIL_ENABLED:                  bool = True
    CLICKHOUSE_ENABLED:           bool = True

```

---

---

# SECTION 10 — ON-CALL & OPERATIONAL RUNBOOKS

---

## 10.1 On-Call Rotation

```
ROTATION: Weekly, Mon–Mon 09:00 WAT
TEAM: 2 engineers minimum in rotation pool
ESCALATION:
  P1 immediate: On-call engineer
  P1 unacknowledged >15 min: Escalate to Engineering Lead
  P1 unresolved >1 hour: Escalate to CTO
```

## 10.2 Common Runbooks

### Runbook: DLQ Message Arrived (Critical Source)

```
SYMPTOM: CloudWatch alarm sc-dlq-critical-depth fires

STEP 1 — IDENTIFY
  Check DLQ message in AWS console or:
  aws sqs receive-message --queue-url {dlq-url} --max-number-of-messages 1

  Read failure_reason field in message payload.

STEP 2 — DIAGNOSE BY FAILURE REASON

  CONNECTION_TIMEOUT / HTTP_503:
    → Source is temporarily down
    → Check source website directly
    → If source recovering: wait 15 minutes; DLQ auto-retry will handle
    → If source down >2 hours: pause source via admin API

  AUTH_FAILURE (401/403):
    → Source credential has expired or been revoked
    → Rotate credential in AWS Secrets Manager: sc/{env}/sources/{source_id}/auth
    → Re-activate source: PATCH /sources/{id} {"health_status": "ACTIVE"}

  S3_WRITE_FAILURE:
    → Check S3 bucket permissions and availability
    → Verify IAM role has s3:PutObject on correct bucket prefix
    → Check S3 service health in AWS console

STEP 3 — REPLAY
  python infrastructure/scripts/reprocess.py --from-dlq {dlq-name}
  # This re-injects DLQ messages into the main queue for retry
```

### Runbook: Synthesis Queue Backed Up

```
SYMPTOM: sc-synthesis-queue-backed-up fires (>5000 messages)

STEP 1 — CHECK LLM PROVIDER STATUS
  OpenAI:    https://status.openai.com
  Anthropic: https://status.anthropic.com
  If provider degraded: template fallback is active; synthesis still completing
  Queue backup caused by increased latency. Likely self-resolving.

STEP 2 — CHECK SYNTHESIS WORKER TASK COUNT
  aws ecs describe-services --cluster sc-cluster-prod \
    --services sc-synthesis-worker-prod \
    --query 'services[0].runningCount'

  If task count is low: check if autoscaling is working
  aws application-autoscaling describe-scaling-activities \
    --service-namespace ecs

STEP 3 — MANUAL SCALE-OUT IF NEEDED
  aws ecs update-service --cluster sc-cluster-prod \
    --service sc-synthesis-worker-prod --desired-count 10

STEP 4 — MONITOR DRAIN
  Watch QueueDepth metric — should decrease within 20 minutes
```

### Runbook: RDS Connection Saturation

```
SYMPTOM: sc-rds-connection-saturation fires (>180 connections)

STEP 1 — IDENTIFY HEAVY CONSUMERS
  SELECT count(*), usename, application_name, state
  FROM pg_stat_activity
  GROUP BY usename, application_name, state
  ORDER BY count DESC;

STEP 2 — CHECK FOR LONG-RUNNING QUERIES
  SELECT pid, now() - pg_stat_activity.query_start AS duration,
         query, state
  FROM pg_stat_activity
  WHERE state != 'idle'
  ORDER BY duration DESC;

STEP 3 — IMMEDIATE RELIEF
  If synthesis or classification workers are holding idle connections:
  Reduce task count temporarily:
  aws ecs update-service --cluster sc-cluster-prod \
    --service sc-classification-worker-prod --desired-count 5

STEP 4 — MEDIUM TERM
  Verify PgBouncer connection pooler is configured (install if not)
  Consider upgrading RDS instance class if connection pressure is sustained
```

### Runbook: Monthly Backup Restore Test

```
SCHEDULE: First Sunday of each month (automated via GitHub Actions)
ESTIMATED TIME: 45-60 minutes

STEP 1 — Create point-in-time restore
  aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier sc-postgres-prod \
    --target-db-instance-identifier sc-postgres-restore-test \
    --restore-time $(date -u -v-1d +"%Y-%m-%dT03:00:00Z")

STEP 2 — Wait for restore to complete (~20 minutes)
  aws rds wait db-instance-available \
    --db-instance-identifier sc-postgres-restore-test

STEP 3 — Run verification queries
  psql $RESTORE_URL -c "SELECT COUNT(*) FROM pipeline.signals;"
  psql $RESTORE_URL -c "SELECT MAX(created_at) FROM pipeline.signals;"
  psql $RESTORE_URL -c "SELECT COUNT(*) FROM intelligence.entities;"

STEP 4 — Write results to compliance evidence
  aws s3 cp restore-test-results.json \
    s3://sc-compliance-evidence-prod/backups/$(date +%Y-%m)/restore-test.json

STEP 5 — Delete test instance
  aws rds delete-db-instance \
    --db-instance-identifier sc-postgres-restore-test \
    --skip-final-snapshot
```

---

---

*Document End — SC-DOC-009 DevOps & Infrastructure Specification v1.0.0*
*Next Document: SC-DOC-010 Sprint & Delivery Plan*
