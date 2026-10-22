# terraform/persistent/main.tf
#
# The create-once stack: S3 state bucket, ECR repos, GitHub OIDC role.
# It outlives every EKS session; terraform/cluster is the stack that gets
# created and destroyed per session.
#
# ── bootstrap ordering (automated by `make persist-up`) ──────────────────
# This stack's own state should live in the bucket it creates — the classic
# chicken-and-egg problem, solved in three moves:
#   1. terraform init -backend=false    # state stays local for now
#   2. terraform apply                  # creates the bucket (+ ECR + role)
#   3. terraform init -force-copy       # migrates the state into the bucket
#
# ── bucket name: three one-time edits ───────────────────────────────────
# Pick a globally unique name and replace "yourname-tfstate-xxxx" in all of:
#   - this backend block
#   - the aws_s3_bucket.state resource in s3.tf
#   - the backend block in terraform/cluster/main.tf
# (Backend blocks cannot reference variables, hence the literal.)

terraform {
  required_version = ">= 1.10" # S3 backend native state locking (no DynamoDB)

  backend "s3" {
    bucket       = "yourname-tfstate-xxxx"
    key          = "persistent/terraform.tfstate"
    region       = "eu-west-1"
    use_lockfile = true
    encrypt      = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
