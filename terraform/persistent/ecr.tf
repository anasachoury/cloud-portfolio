# terraform/persistent/ecr.tf
# One repo per service; names match the CI matrix in ci.yaml and the
# image.repository fields in gitops/apps/*/values.yaml.
#  - IMMUTABLE tags: a pushed tag can never be silently overwritten, so the
#    tag committed to Git always identifies exactly one image digest
#  - scan_on_push: AWS-side vulnerability scan of every push (belt to CI's
#    trivy braces)
#  - lifecycle policy: untagged layers expire in 3 days, any image after 30
#    days. CI pushes a fresh sha-tagged image per commit; without a cap the
#    repo grows forever, and the storage line item is pure waste.

locals {
  services = ["frontend", "products", "orders"]
}

resource "aws_ecr_repository" "app" {
  for_each             = toset(local.services)
  name                 = each.key
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    stack = "persistent"
    repo  = "cloud-portfolio"
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  for_each   = aws_ecr_repository.app
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "expire untagged images after 3 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countNumber = 3
          countUnit   = "days"
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "expire all images after 30 days"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countNumber = 30
          countUnit   = "days"
        }
        action = { type = "expire" }
      },
    ]
  })
}
