# cloud-portfolio

Production-shaped microservices platform on AWS EKS, built to be torn down daily.

Three services (nginx frontend, FastAPI products and orders, Redis) deployed
through one reusable Helm chart, managed by ArgoCD GitOps, delivered by a
security-gated GitHub Actions pipeline, on infrastructure defined in Terraform.

Built against a $20 AWS credit budget — the architecture optimizes for
create/destroy sessions instead of 24/7 uptime.

## Status

| Layer | State |
|---|---|
| Reusable Helm chart (deployment/service/HPA/ServiceMonitor/Ingress/NetworkPolicy) | done |
| GitOps: ArgoCD app-of-apps + ApplicationSet + platform apps | done |
| CI: gitleaks, semgrep, trivy (IaC + image), kubeconform chart gate | done |
| Terraform: VPC + EKS cluster stack, IRSA for cluster-autoscaler | done |
| App code (`services/`): FastAPI products/orders, nginx frontend, tests | done |
| Screenshots, load test, demo recording | todo |

## Layout

```
services/            app code: frontend (nginx), products, orders (FastAPI)
charts/microservice  the one reusable Helm chart
gitops/
  bootstrap/        root-app (app-of-apps entrypoint)
  apps-root/        ApplicationSet + platform Applications
  apps/             per-service values (what CI re-tags)
  platform/         values for platform apps + redis manifests
terraform/
  persistent/       state bucket, ECR, GitHub OIDC role  (create once)
  cluster/          VPC, EKS, IRSA                          (create/destroy)
.github/workflows/  ci.yaml
Makefile            up / down / kind / local targets
```

## Quickstart

```make
make help          # list all targets
make local-up      # run the app with docker compose (no cluster)
make kind-up       # kind cluster + metrics-server, for GitOps practice
make up            # full EKS session: terraform apply + kubeconfig + argocd
make down          # teardown: apps first (LB), wait for LBs, terraform destroy
```

## Operating model

- `make up` / `make down` bracket every cloud session; the cluster never idles.
- Persistent stack (state bucket, ECR, OIDC) and cluster stack (VPC, EKS) are
  separate Terraform stacks — only the cluster one gets destroyed.
- CI never touches the cluster: it builds, scans, pushes images to ECR, and
  commits new tags; ArgoCD does the deploying.
- Deploy-mode steps (ECR push, GitOps tag bump) stay disabled until the repo
  variable `DEPLOY_READY=true` is set — CI is fully green without an AWS
  account, and flips into deploy mode with one setting once ECR + the OIDC
  role exist and `ACCOUNT_ID` is filled in.

## Cost decisions

| Decision | Why |
|---|---|
| Spot t3.medium nodes | ~70-90% cheaper than on-demand; demo tolerates interruptions |
| Single NAT gateway | halves NAT cost; SPOF acceptable for a demo |
| No persistent volumes | monitoring/dashboards rebuild from Git on every cluster rebuild |
| Session-based cluster | control plane + NAT + LB bill only while testing |
| metrics-server + cluster-autoscaler | HPA and node scaling actually work |

Replace `ACCOUNT_ID` and the ECR registry URLs in `gitops/apps/*/values.yaml`
before applying.

> Pinned third-party actions are TODO (SHA-pin before depending on CI in anger).
