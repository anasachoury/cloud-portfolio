#!/usr/bin/env python3
"""Generate docs/demo-thumb.png — YouTube thumbnail (1280x720).

Typography-only on purpose: a thumbnail must stay legible at ~320px wide,
so a service diagram would turn to noise. Dark background matching the
repo's terminal-demo aesthetic; one accent color (AWS orange).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

W, H = 12.8, 7.2  # inches at 100dpi -> 1280x720
BG = "#0d1117"        # github dark
FG = "#e6edf3"        # github dark foreground
ACCENT = "#ff9900"    # aws orange
MUTED = "#8b949e"

fig = plt.figure(figsize=(W, H), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
ax.add_patch(plt.Rectangle((0, 0), W, H, color=BG))

# subtle top accent bar
ax.add_patch(plt.Rectangle((0, H - 0.16), W, 0.16, color=ACCENT))

# eyebrow
ax.text(0.9, 6.15, "LIVE SESSION  ·  $20 AWS BUDGET", fontsize=19,
        color=ACCENT, fontweight="bold", family="DejaVu Sans", va="center")

# title
ax.text(0.85, 4.85, "Microservices platform", fontsize=60,
        color=FG, fontweight="bold", family="DejaVu Sans", va="center")
ax.text(0.85, 3.85, "on EKS \u2014 built to be", fontsize=60,
        color=FG, fontweight="bold", family="DejaVu Sans", va="center")
ax.text(0.85, 2.85, "torn down daily", fontsize=60,
        color=ACCENT, fontweight="bold", family="DejaVu Sans", va="center")

# tech strip
ax.text(0.9, 1.95, "Terraform   ·   ArgoCD GitOps   ·   security-gated CI",
        fontsize=25, color=MUTED, family="DejaVu Sans", va="center")

# bottom-left badge: cluster up->down loop
badge = FancyBboxPatch((0.85, 0.55), 5.9, 0.95,
                      boxstyle="round,pad=0.12,rounding_size=0.18",
                      linewidth=0, facecolor="#161b22")
ax.add_patch(badge)
ax.text(3.80, 1.02, "make up  ->  demo  ->  make down", fontsize=20,
        color=FG, fontweight="bold", family="DejaVu Sans",
        ha="center", va="center")

# bottom-right badge: cost
badge2 = FancyBboxPatch((8.35, 0.55), 3.6, 0.95,
                        boxstyle="round,pad=0.12,rounding_size=0.18",
                        linewidth=0, facecolor=ACCENT)
ax.add_patch(badge2)
ax.text(10.15, 1.02, "one session: ~$1.30", fontsize=20,
        color="#0d1117", fontweight="bold", family="DejaVu Sans",
        ha="center", va="center")

fig.savefig("/home/z/my-project/download/cloud-portfolio/docs/demo-thumb.png",
            facecolor=BG)
print("wrote docs/demo-thumb.png")
