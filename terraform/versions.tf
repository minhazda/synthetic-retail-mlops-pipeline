terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Optional: store state in a GCS bucket instead of locally. Create the bucket
  # first, then uncomment and run `terraform init -migrate-state`.
  # backend "gcs" {
  #   bucket = "your-tf-state-bucket"
  #   prefix = "retail-forecasting"
  # }
}
