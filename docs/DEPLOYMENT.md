# Cloud deployment — GCP Cloud Run (Terraform + keyless CI/CD)

This deploys the forecasting API to **Google Cloud Run** using **Terraform** for
infrastructure-as-code and **GitHub Actions** for continuous deployment. Cloud
Run **scales to zero**, so the service costs ~$0 when idle and stays within the
always-free tier for portfolio-level traffic.

No service-account keys are created or stored: CI authenticates to GCP with
**Workload Identity Federation** (short-lived OIDC tokens). The first image is
built in the cloud with **Cloud Build**, so **no local Docker is required**.

## What gets created

| Resource | Purpose |
|----------|---------|
| Artifact Registry repo | Stores the Docker images |
| Cloud Run service | Serves the API (`/health`, `/predict`, `/metadata`), min instances 0 |
| Public IAM binding | Makes the demo endpoint reachable without auth |
| Workload Identity Pool + Provider | Lets *this* GitHub repo authenticate to GCP, keylessly |
| Deployer service account | Scoped to push images and deploy Cloud Run only |

## Prerequisites

- A GCP project with **billing enabled** (free tier is sufficient).
- [`gcloud`](https://cloud.google.com/sdk/docs/install) and
  [`terraform`](https://developer.hashicorp.com/terraform/install) installed.
- Authenticate once:
  ```bash
  gcloud auth login                      # user login (opens a browser)
  gcloud auth application-default login  # credentials Terraform/ADC will use
  gcloud config set project YOUR_PROJECT_ID
  ```

## One-time setup

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: set project_id (region/github_repo defaults are fine)
terraform init
```

### Step 1 — Bootstrap the registry, then build the first image (no local Docker)

Cloud Run needs an image to exist before the service can be created, so we create
the registry first, build one image with Cloud Build, then apply the rest.

```bash
# Create just the enabled APIs + registry
terraform apply \
  -target=google_project_service.enabled \
  -target=google_artifact_registry_repository.repo

# Build the first image in the cloud and push it to Artifact Registry.
PROJECT_ID=$(grep project_id terraform.tfvars | cut -d'"' -f2)
gcloud builds submit .. \
  --tag "us-central1-docker.pkg.dev/$PROJECT_ID/retail-forecasting/api:bootstrap"
# then set that exact ref as `image` in terraform.tfvars
```

> Prefer local Docker instead of Cloud Build? `docker build -t <IMAGE> .. && docker push <IMAGE>` also works.

### Step 2 — Apply the full stack

```bash
terraform apply
terraform output service_url   # your live API URL
```

Smoke-test it:

```bash
curl "$(terraform output -raw service_url)/health"
```

## Wire up continuous deployment

`terraform output` prints the three values CI needs. Add them as **repository
variables** (not secrets — they're non-sensitive identifiers) under
**Settings → Secrets and variables → Actions → Variables**:

| GitHub variable | Value from |
|-----------------|------------|
| `GCP_PROJECT_ID` | your project id |
| `GCP_WIF_PROVIDER` | `terraform output gcp_wif_provider` |
| `GCP_DEPLOY_SA` | `terraform output gcp_deploy_sa` |

From then on, every push to `main` that touches `src/`, the `Dockerfile`, or
requirements builds a new image and deploys it (see
[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)). Terraform
ignores image changes so it never reverts a deployment.

## Teardown

```bash
cd terraform
terraform destroy
```

## Cost notes

- `min_instances = 0` → no charge while idle (cold start ~a few seconds).
- 512 MiB / 1 vCPU with `cpu_idle = true` bills CPU only during requests.
- Cloud Run's always-free tier covers typical demo/portfolio traffic.
