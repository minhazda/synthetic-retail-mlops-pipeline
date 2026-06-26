terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Remote state in GCS (versioned bucket) so the deployment can be managed
  # from any clone and survives loss of the local working directory.
  backend "gcs" {
    bucket = "avian-silicon-500616-s8-tfstate"
    prefix = "retail-forecasting"
  }
}
