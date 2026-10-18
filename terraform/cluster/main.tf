# terraform/cluster/main.tf
# The plan's config with the review fixes merged in:
#  - API server restricted to admin CIDRs (var.admin_cidrs, cluster.tfvars)
#  - vpc-cni addon with enableNetworkPolicy: without it, every NetworkPolicy
#    in the repo is an inert YAML decoration — EKS does not enforce them by default
#  - node count driven by var.node_desired (bump to 3 for the monitoring weekend)

terraform {
  required_version = ">= 1.10" # S3 backend native state locking (no DynamoDB)

  backend "s3" {
    bucket       = "yourname-tfstate-xxxx"
    key          = "cluster/terraform.tfstate"
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

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = var.cluster_name
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true # cost saving; SPOF is fine for a demo — documented tradeoff

  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.k8s_version
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  cluster_endpoint_public_access           = true
  cluster_endpoint_public_access_cidrs     = var.admin_cidrs
  enable_cluster_creator_admin_permissions = true

  cluster_addons = {
    vpc-cni = {
      before_compute       = true
      most_recent          = true
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }
    coredns    = { most_recent = true }
    kube-proxy = { most_recent = true }
  }

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      capacity_type  = "SPOT"
      min_size       = 1
      max_size       = 3
      desired_size   = var.node_desired
    }
  }
}
