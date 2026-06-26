output "service_url" {
  description = "Public URL of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.api.uri
}

output "artifact_registry" {
  description = "Docker image prefix for builds and pushes."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "gcp_wif_provider" {
  description = "Set this as the GitHub repo variable GCP_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "gcp_deploy_sa" {
  description = "Set this as the GitHub repo variable GCP_DEPLOY_SA."
  value       = google_service_account.deployer.email
}
