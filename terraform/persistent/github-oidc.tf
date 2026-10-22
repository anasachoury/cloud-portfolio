# terraform/persistent/github-oidc.tf
# CI authenticates to AWS with no long-lived keys: GitHub Actions presents an
# OIDC token, the trust policy below decides which repo/branch may assume the
# role. (This is GITHUB's OIDC provider — a different federation from the
# EKS cluster OIDC provider used for IRSA in terraform/cluster. Two lookalike
# mechanisms, two different trust roots.)
#
# Trust is scoped to this repo's main branch. PR runs never get AWS creds:
# the deploy-mode steps in ci.yaml are main-only anyway, and a compromised
# pull request cannot push images or read the registry.

locals {
  github_repo = "anasachoury/cloud-portfolio"
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]

  # AWS stopped validating GitHub's thumbprints in 2023 (GitHub rotates its
  # intermediate CAs, which broke pinning); the list below holds the published
  # historical values and is kept for form and for portability.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_policy_document" "github_ci_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${local.github_repo}:ref:refs/heads/main"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "github_ci" {
  name               = "github-ci"
  assume_role_policy = data.aws_iam_policy_document.github_ci_trust.json

  tags = {
    stack = "persistent"
    repo  = "cloud-portfolio"
  }
}

data "aws_iam_policy_document" "github_ci_ecr" {
  statement {
    # GetAuthorizationToken is account-scoped by design and cannot be
    # resource-scoped; it grants nothing beyond a login token.
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    actions = [
      # push side: docker push
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
      # pull side: trivy image scan and ad-hoc debugging
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]

    resources = [for r in aws_ecr_repository.app : r.arn]
  }
}

resource "aws_iam_role_policy" "github_ci_ecr" {
  name   = "github-ci-ecr"
  role   = aws_iam_role.github_ci.id
  policy = data.aws_iam_policy_document.github_ci_ecr.json
}
