# DEMO.md — recording script (~6 minutes)

Everything is one `make up` session. Record the terminal and the two UIs
side by side; every beat below is real (no cuts needed except the
time-lapses). Rehearse once before recording — the timings below are from
a rehearsed session, and rehearsing costs the same as recording (~$0.20/h).

| Time | Beat | Show | Say (one line each) |
|---|---|---|---|
| 0:00 | Cold open | repo README, architecture diagram | "Three services, one Helm chart, ArgoCD GitOps, secured pipeline, on Terraform — built to be torn down daily." |
| 0:15 | Bring it up | `make up` (time-lapse the terraform apply) | "Terraform creates the VPC and EKS; spot nodes, two AZs, NetworkPolicy enforcement switched on in the CNI." |
| 0:40 | ArgoCD | UI: root-app tree — app-of-apps unfolding | "One bootstrap app; the ApplicationSet fans out per service, platform apps come from the same repo. The cluster converged to Git in ~3 minutes." |
| 1:10 | Grafana | the Portfolio dashboard | "Dashboard and alert rules are ConfigMaps in Git — the cluster was empty 5 minutes ago." |
| 1:30 | Traffic | `k6 run -e TARGET=http://$LB scripts/loadtest.js` + request-rate panel | "80% browsing, 20% buying — the same mix as the load script." |
| 1:50 | HPA | HPA replicas panel, replicas climbing | "Pods scale on CPU; the autoscaler adds a node when the node group is full." |
| 2:20 | Self-heal | `kubectl -n orders set env deploy/orders DEMO=hack` → ArgoCD UI shows OutOfSync → reverts | "Git is the source of truth — a manual change lives for about three minutes." |
| 3:00 | Resilience | `kubectl -n products scale deploy/products --replicas=0` → 5xx-ratio panel rises, alert fires → orders answer 503 | "Downstream gone: errors surface in seconds, and the alert is the PrometheusRule from the repo." |
| 3:40 | Recovery | `scale --replicas=2` → error ratio drops to zero | "Back from Git — no human ran kubectl apply." |
| 4:00 | Load numbers | k6 summary + p95 panel | "p95 under 500ms with 1% error budget — thresholds in the script are the same numbers." |
| 4:20 | Teardown | `make down` (time-lapse: app deletion → LB gone → destroy) | "Apps first so the load balancer is released, then the cluster. This is the whole point: the cluster never idles." |
| 4:40 | Cost | `aws ce get-cost-and-usage` or billing console for today | "The session cost about a dollar-forty. The budget is twenty." |
| 5:00 | Close | README status table | "Repo in the description — thanks for watching." |

## Notes

- The demo needs `k6` locally (`brew install k6` / [downloads](https://grafana.com/docs/k6/latest/set-up/install-k6/));
  or use the README's `while true; do curl ...` loop as a weaker fallback.
- `$LB` = the ingress address: `kubectl -n ingress-nginx get svc ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'`.
- ArgoCD UI: `make fwd-argocd` → http://localhost:8080 (admin + printed password).
- Grafana: `make fwd-grafana` → http://localhost:3000 (admin / prom-operator).
- If the HPA beat looks flat, lower the CPU target in `gitops/apps/orders/values.yaml`
  and push — that itself is a nice GitOps moment ("a Git commit changes the scaling policy").
