# SCRIPT.md — word-for-word narration for the demo video

Read this aloud while recording the beats in [DEMO.md](DEMO.md). Total spoken
content: ~600 words ≈ 4.5 minutes at a calm pace; time-lapses fill the rest.

**How to use it**

1. Rehearse once with the cluster already up (don't record the rehearsal).
2. On recording day: `make up`, wait for everything to be Synced, then press
   record and read. If you stumble — pause, breathe, say the line again, and
   cut the bad take in editing. Nobody records it clean in one pass.
3. `[SHOW]` cues are what's on screen; narration is what you say. Don't narrate
   during time-lapses — silence + fast terminal is the vibe.

---

## Recording setup (5 minutes, once)

- **OBS Studio** (free) — 1920x1080, 30 fps, dark terminal theme
- Terminal font bumped to ~16pt (it must be readable on a phone)
- Two browser windows tiled: ArgoCD left, Grafana right; terminal fullscreen
  behind them (OBS scene: Terminal | ArgoCD | Grafana — switch with a key)
- Quiet room, phone 20cm away, read SLOWER than feels natural
- Before pressing record: `make up` finished, all apps Synced, k6 installed,
  this file open on a second screen/phone

---

## The narration

### 0:00 — Cold open `[SHOW: README, architecture diagram]`

> This is a production-shaped microservices platform on AWS EKS — three
> services, one reusable Helm chart, GitOps delivery with ArgoCD, a
> security-gated CI pipeline, and all of it defined in Terraform.
>
> The twist: it's built to be torn down daily. The whole budget is twenty
> dollars, so the cluster only exists while I'm using it — and this video
> is one real session, start to finish.

### 0:15 — Bring it up `[SHOW: make up, time-lapse terraform apply]`

> Terraform is creating the VPC and the EKS cluster: spot nodes across two
> availability zones, and NetworkPolicy enforcement switched on in the CNI —
> because without that, every network policy in the repo is just decoration.

*(time-lapse: no narration)*

> And that's the boring part done — the cluster exists, but it's empty.
> Watch what fills it.

### 0:40 — ArgoCD `[SHOW: root-app tree in ArgoCD UI]`

> One bootstrap Application is all I ever install by hand. It pulls in the
> ApplicationSet that fans out one app per service, plus the platform apps —
> ingress, monitoring, autoscaling, Redis — everything from the same Git repo.
>
> No kubectl apply. The cluster converged to Git in about three minutes.

### 1:10 — Grafana `[SHOW: Portfolio dashboard]`

> The Grafana dashboard and the alert rules are just ConfigMaps in the repo —
> this cluster was empty five minutes ago, and the monitoring is already
> rebuilt from Git. No persistent volumes anywhere; that's a cost decision,
> and Git pays for it.

### 1:30 — Traffic `[SHOW: k6 run + request-rate panel]`

> Now let's give it something to do. The load script mixes eighty percent
> browsing with twenty percent buying — reads hit products, writes create
> orders through the frontend, down to Redis.

### 1:50 — HPA `[SHOW: HPA replicas panel]`

> And the pods scale on CPU. When the node group gets full, the cluster
> autoscaler adds a node — the whole stack flexes, top to bottom.

### 2:20 — Self-heal `[SHOW: kubectl set env ... KILLED=true, ArgoCD OutOfSync]`

> Now the part I like most. I'll make an unauthorized change by hand —
> setting an environment variable directly on the orders deployment.
>
> ArgoCD notices in seconds, marks it out of sync... and reverts it. Git is
> the source of truth. A manual change on this cluster lives for about
> three minutes.

### 3:00 — Resilience `[SHOW: scale products to 0, 5xx-ratio panel, alert]`

> Next: what happens when a service just... disappears? Scaling products to
> zero — that's a dead dependency for orders.
>
> Orders answers fast with 503s instead of hanging, the error ratio climbs
> on the dashboard, and the Prometheus alert from the repo fires. That's
> failure you can SEE — which is the whole point of the monitoring.

### 3:40 — Recovery `[SHOW: scale back to 2, error ratio drops]`

> And bringing it back is one command — the error ratio falls to zero, and
> no human had to run anything against the cluster. Git reconciled it.

### 4:00 — Load numbers `[SHOW: k6 summary, p95 panel]`

> Under load: p95 latency stayed under five hundred milliseconds with an
> error rate under one percent — and those numbers are thresholds in the
> load script itself, so they're checked, not vibes.

### 4:20 — Teardown `[SHOW: make down, time-lapse]`

> Then I destroy it. Apps first — so the load balancer is released — then
> the cluster. The architecture only bills while it exists.

*(time-lapse: no narration)*

### 4:40 — Cost `[SHOW: AWS billing console for today]`

> That entire session cost about a dollar thirty. The budget is twenty.

### 5:00 — Close `[SHOW: README, status table]`

> Everything you saw is in this repo — infrastructure, chart, services,
> pipeline, dashboards, and this script. Repo link is in the description.
> Thanks for watching.

---

## After recording (10 minutes)

- [ ] Trim the stumbles; time-lapse the two waits (4x)
- [ ] Export 1080p, upload YouTube **unlisted** first
- [ ] Watch it once end-to-end before making it public
- [ ] `sed -i 's|YOUR_VIDEO_URL|https://youtu.be/XXXX|' README.md` — both spots (the link and the commented thumbnail line)
- [ ] Commit + push
- [ ] Make it public (or keep unlisted for the resume — your call)
- [ ] Add the link to your resume bullet + post it on LinkedIn
- [ ] Revoke every GitHub token you ever pasted into chat
