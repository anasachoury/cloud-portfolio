# terraform/persistent/variables.tf

variable "region" {
  description = "AWS region for this stack; must match the region hardcoded in both backend blocks (persistent + cluster)"
  type        = string
  default     = "eu-west-1"
}
