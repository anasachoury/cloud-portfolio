# cloud-portfolio

Production-shaped microservices platform on AWS EKS, built to be torn down daily.

Three services (nginx frontend, FastAPI products and orders, Redis) deployed
through one reusable Helm chart, managed by ArgoCD GitOps, delivered by a
security-gated GitHub Actions pipeline, on infrastructure defined in Terraform.

Built against a $20 AWS credit budget — the architecture optimizes for
create/destroy sessions instead of 24/7 uptime.

## Architecture

```
                         ┌──────────── GitHub ────────────┐
                         │  ci.yaml: 4 security gates     │
                         │  tests -> build -> trivy scan   │
                         │  -> push ECR -> commit new tag  │
                         └───────┬ OIDC────────▲──────────┘
                                 │             │ git commit (image tag)
                 assume-role,    │             │
                 no static keys  ▼             │
   ┌ ECR repos ◄────────────────────────────  │
   │                                            ▼
   │            ┌── ArgoCD (app-of-apps) ── gitops/ in this repo
   │            │   root-app -> ApplicationSet (3 services)
   │            │             -> platform apps (ingress, monitoring,
   │            │                autoscaler, redis, rules+dashboard)
   ▼            ▼
┌───────────────────────── EKS (terraform/cluster) ────────────────────┐
│  ingress-nginx ─► frontend ─┬─► products (FastAPI)                     │
│      (ALB)                  │        ▲                                │
│                             ├────────┘   NetworkPolicy: only allowed  │
│                             └─► orders (FastAPI) ─► redis (in-mem)    │
│  Prometheus ──scrapes── ServiceMonitors │ kube-state-metrics          │
│  Grafana ◄── dashboard + rules from Git  │ cluster-autoscaler (IRSA)   │
└───────────────────────────────────────────────────────────────────────┘
```

CI never touches the cluster. It builds, scans, pushes images to ECR and
commits new tags; ArgoCD notices the commit and deploys. The blast radius of
a compromised CI token is "push a commit" — not "kubectl apply".

## Status

| Layer | State |
|---|---|
| Reusable Helm chart (deployment/service/HPA/ServiceMonitor/Ingress/NetworkPolicy) | done |
| GitOps: ArgoCD app-of-apps + ApplicationSet + platform apps | done |
| CI: gitleaks, semgrep, trivy (IaC + image), kubeconform chart gate | done |
| Terraform: VPC + EKS cluster stack, IRSA for cluster-autoscaler | done |
| Terraform: persistent stack (state bucket, ECR, GitHub OIDC role) | done |
| App code (`services/`): FastAPI products/orders, nginx frontend, tests | done |
| Monitoring: Grafana dashboard + PrometheusRule alerts | done |
| Local smoke test (`make smoke` — no docker, no cluster) | done |
| Load test: k6 script + thresholds (numbers from first session) | ready |
| Demo recording script (docs/DEMO.md) | done |

## Layout

```
services/            app code: frontend (nginx), products, orders (FastAPI)
charts/microservice  the one reusable Helm chart
scripts/             smoke.py (native e2e test), loadtest.js (k6)
docs/                DEMO.md — the recording script
gitops/
  bootstrap/        root-app (app-of-apps entrypoint)
  apps-root/        ApplicationSet + platform Applications
  apps/             per-service values (what CI re-tags)
  platform/         values for platform apps, redis, monitoring extras
terraform/
  persistent/       state bucket, ECR, GitHub OIDC role  (create once)
  cluster/          VPC, EKS, IRSA                          (create/destroy)
.github/workflows/  ci.yaml
Makefile            up / down / persist / smoke / kind / local targets
```

## Quickstart

```make
make help          # list all targets
make smoke         # end-to-end test of the services — no docker needed
make local-up      # run the app with docker compose (no cluster)
make kind-up       # kind cluster + metrics-server, for GitOps practice
make persist-up    # once per AWS account (see first session below)
make up            # full EKS session: terraform apply + kubeconfig + argocd
make down          # teardown: apps first (LB), wait for LBs, terraform destroy
```

## First AWS session

One-time setup, ~15 minutes:

1. **Bucket name** — replace `yourname-tfstate-xxxx` with a globally unique
   name in three places (they must stay in sync; backend blocks cannot use
   variables):
   - `terraform/persistent/main.tf` (backend + resource in `s3.tf`)
   - `terraform/cluster/main.tf` (backend)
2. **Apply the persistent stack** — `make persist-up`. It bootstraps the
   chicken-and-egg problem (state bucket created by the stack whose state
   lives in it) via `init -backend=false` -> `apply` -> `init -force-copy`,
   then prints the go-live checklist with the real account id inlined.
3. **Go live** — run the printed commands: sed the account id into
   `gitops/apps/*/values.yaml` and `ci.yaml`, set the repo variable
   `DEPLOY_READY=true`, push.
4. From then on: every session is `make up` ... `make down`.

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
- Teardown order matters: ArgoCD apps first (`--wait`, cascade finalizers),
  which releases the ALB; wait for the LBs to actually vanish (billed per
  hour), then `terraform destroy`.

## Security, layer by layer

| Layer | Mechanism |
|---|---|
| CI supply chain | every action pinned to a commit SHA; helm/kubeconform/yq from pinned URLs verified by sha256; enforced by semgrep in CI |
| Secrets | gitleaks scans full history; zero static AWS keys — GitHub OIDC federation scoped to `main` of this repo only |
| Images | trivy fs (IaC + deps) and image scans gate the pipeline; ECR `IMMUTABLE` tags + scan-on-push on the registry side |
| Admission shape | containers run non-root with read-only rootfs, dropped capabilities, seccomp RuntimeDefault |
| Network | default-deny NetworkPolicies per service; only the documented traffic matrix opens up (frontend->products/orders, orders->products/redis, monitoring scrapes, DNS egress). Requires vpc-cni `enableNetworkPolicy=true` — set in the cluster stack |
| EKS API | public endpoint restricted to admin CIDRs (`cluster.tfvars`) |

## Monitoring

No persistent volumes: dashboards, rules and alert history are all rebuilt
from Git on every cluster rebuild — a documented tradeoff against the budget.

- `gitops/platform/monitoring-extras/` — Grafana dashboard (request rate, 5xx
  ratio, p95 latency, HPA replicas, restarts, pod count) as a ConfigMap
  (sidecar picks up `grafana_dashboard: "1"`), plus a PrometheusRule with
  `FastAPIHighErrorRate`, `ServiceDown`, `HPAMaxedOut`.
- Alert expressions match the app metrics contract exactly:
  prometheus-fastapi-instrumentator groups status labels as `2xx`/`5xx`.
- `make fwd-grafana` → http://localhost:3000 (admin / prom-operator first login).

## Demo script

With the cluster up (`make up`, then get the LB address):

```bash
# 1. GitOps self-heal: edit a deployment field manually, watch ArgoCD revert it
kubectl -n orders set env deploy/orders KILLED=true
# 2. Resilience: products down -> orders 503s -> FastAPIHighErrorRate alert
kubectl -n products scale deploy/products --replicas=0
# 3. Autoscaling: hammer the frontend, watch HPA replicas climb in Grafana
while true; do curl -s http://$LB/api/orders/ >/dev/null & done
#    (or the k6 script: make load-test TARGET=http://$LB)
# 4. Recovery: bring products back, watch the error ratio recover
kubectl -n products scale deploy/products --replicas=2
```

The tag `kubectl scale` on deployments is deliberately absent from Git (HPA
owns replicas; the chart omits `replicas` when HPA is enabled so selfHeal
never fights the autoscaler) — scaling it manually is fine.

## Cost decisions

| Decision | Why |
|---|---|
| Spot t3.medium nodes | ~70-90% cheaper than on-demand; demo tolerates interruptions |
| Single NAT gateway | halves NAT cost; SPOF acceptable for a demo |
| No persistent volumes | monitoring/dashboards rebuild from Git on every cluster rebuild |
| Session-based cluster | control plane + NAT + LB bill only while testing |
| metrics-server + cluster-autoscaler | HPA and node scaling actually work |

Session math (eu-west-1): EKS control plane $0.10/h + NAT $0.045/h + ALB
$0.0225/h + 2x spot t3.medium ~$0.033/h ≈ **$0.20/hour** — roughly $1.60 per
eight-hour session, ~40 cluster-hours inside the $20 credit. ECR storage is
capped by the lifecycle policy (untagged 3d, all images 30d); monitoring
keeps 12h of metrics in memory.

> All third-party actions are pinned to commit SHAs (with version comments);
> tool binaries (helm, kubeconform, yq) are installed from pinned release URLs
> and verified against embedded sha256 checksums — enforced by semgrep in CI.
