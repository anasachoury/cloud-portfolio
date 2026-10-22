# terraform/persistent/outputs.tf
# `make persist-up` prints the go-live checklist with these values inlined.

output "account_id" {
  description = "AWS account id — goes into ci.yaml and the ECR image prefixes"
  value       = data.aws_caller_identity.current.account_id
}

output "ci_role_arn" {
  description = "Role GitHub Actions assumes via OIDC (role-to-assume in ci.yaml)"
  value       = aws_iam_role.github_ci.arn
}

output "ecr_registry" {
  description = "Registry host — prefix of every image.repository in gitops/apps/*"
  value       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}
