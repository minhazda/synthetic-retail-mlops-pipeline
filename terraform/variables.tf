variable "project_id" {
  type        = string
  description = "GCP project ID to deploy into."
}

variable "region" {
  type        = string
  default     = "us-central1" # has an always-free Cloud Run allowance
  description = "GCP region for Artifact Registry and Cloud Run."
}

variable "service_name" {
  type        = string
  default     = "retail-forecasting-api"
  description = "Cloud Run service name."
}

variable "repository_id" {
  type        = string
  default     = "retail-forecasting"
  description = "Artifact Registry repository ID."
}

variable "image" {
  type        = string
  description = "Full Artifact Registry image ref to deploy. Built + pushed during bootstrap before the first apply (see docs/DEPLOYMENT.md)."
}

variable "min_instances" {
  type        = number
  default     = 0 # scale to zero => ~$0 when idle (free-tier friendly)
  description = "Minimum number of Cloud Run instances."
}

variable "max_instances" {
  type        = number
  default     = 2
  description = "Maximum number of Cloud Run instances."
}

variable "github_repo" {
  type        = string
  default     = "minhazda/synthetic-retail-mlops-pipeline"
  description = "owner/repo allowed to deploy via Workload Identity Federation."
}
