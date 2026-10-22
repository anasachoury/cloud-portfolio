# terraform/persistent/s3.tf
# State bucket for both Terraform stacks.
#  - versioning: every state change is a new version — history and rollback
#  - SSE-S3: encrypted at rest, free (a KMS key would cost ~$1/month of the
#    budget; the state holds no secrets, only resource IDs)
#  - public access blocked + BucketOwnerEnforced: the obvious hardening
#  - force_destroy=true is a documented demo tradeoff: it lets the final
#    `make persist-down` empty the bucket instead of leaving orphaned state
#    versions behind. Production would keep it false and archive instead.

resource "aws_s3_bucket" "state" {
  bucket        = "yourname-tfstate-xxxx" # must equal the backend blocks (see main.tf)
  force_destroy = true

  tags = {
    stack = "persistent"
    repo  = "cloud-portfolio"
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
