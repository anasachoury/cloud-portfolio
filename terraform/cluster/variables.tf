variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "cluster_name" {
  type    = string
  default = "portfolio"
}

variable "k8s_version" {
  description = "Must be an EKS version in STANDARD support — check the EKS docs before applying; extended support bills the control plane at ~6x"
  type        = string
  default     = "1.36" # verify current standard-support versions
}

variable "admin_cidrs" {
  description = "CIDRs allowed to reach the Kubernetes API (your IP /32). No default on purpose — an open API server next to a DevSecOps README is a bad look"
  type        = list(string)
}

variable "node_desired" {
  description = "Desired spot node count: 2 normally, 3 for the monitoring/load-test weekend"
  type        = number
  default     = 2
}
