#!/usr/bin/env python3
"""Render all frames for the architecture-explainer video.

Audio-driven timeline: each scene's length = its narration segment + padding.
Reads audio/s*.wav durations via ffprobe, renders 24 fps 1280x720 PNGs to
frames/. Encode afterwards with ffmpeg (see make_video.sh).
"""
import math
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio")
FRAMES = os.path.join(HERE, "frames")
FPS = 24
W, H = 12.8, 7.2  # inches at dpi=100 -> 1280x720

BG, FG, MUTED = "#0d1117", "#e6edf3", "#8b949e"
ACCENT, BLUE, GREEN, RED, PANEL = "#ff9900", "#58a6ff", "#3fb950", "#f85149", "#161b22"
BORDER = "#30363d"


def dur(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path])
    return float(out.strip())


N = 8
LEAD, TAIL = 0.25, 0.35  # per-scene audio padding
starts, lengths = [], []
t0 = 0.0
for i in range(1, N + 1):
    d = dur(os.path.join(AUDIO, f"s{i}.wav"))
    starts.append(t0)
    lengths.append(LEAD + d + TAIL)
    t0 += LEAD + d + TAIL
TOTAL = t0
print("timeline:", [(round(s, 2), round(l, 2)) for s, l in zip(starts, lengths)])
print("total:", round(TOTAL, 2), "s")


# ── helpers ─────────────────────────────────────────────────────────────────
def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def fade(tl, a, b):
    """0 -> 1 alpha ramp between seconds a..b (local scene time)."""
    return ease((tl - a) / (b - a)) if tl >= a else 0.0


def box(ax, x, y, w, h, alpha=1.0, fc=PANEL, ec=BORDER, lw=1.4):
    if alpha <= 0.01:
        return None
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                       boxstyle="round,pad=0.06,rounding_size=0.14",
                       linewidth=lw, edgecolor=ec, facecolor=fc,
                       alpha=alpha, zorder=3)
    ax.add_patch(p)
    return p


def txt(ax, x, y, s, size=14, color=FG, alpha=1.0, weight="normal",
        ha="center", va="center", family="DejaVu Sans", zorder=5):
    if alpha <= 0.01 or not s:
        return
    ax.text(x, y, s, fontsize=size, color=color, alpha=alpha,
            fontweight=weight, ha=ha, va=va, family=family, zorder=zorder)


def arrow(ax, x1, y1, x2, y2, alpha=1.0, color=MUTED, progress=1.0, lw=2.0):
    if alpha <= 0.01 or progress <= 0.01:
        return
    xe, ye = x1 + (x2 - x1) * progress, y1 + (y2 - y1) * progress
    a = FancyArrowPatch((x1, y1), (xe, ye), arrowstyle="-|>",
                        mutation_scale=16, linewidth=lw, color=color,
                        alpha=alpha, zorder=2, shrinkA=2, shrinkB=2)
    ax.add_patch(a)


def chip(ax, x, y, s, alpha=1.0, color=FG, fc=PANEL, size=13, weight="bold"):
    w = 0.22 + 0.118 * len(s)
    box(ax, x, y, w, 0.62, alpha=alpha, fc=fc, ec=BORDER)
    txt(ax, x, y, s, size=size, alpha=alpha, color=color, weight=weight)


def base(ax, title=None):
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), W, H, color=BG, zorder=0))
    ax.add_patch(plt.Rectangle((0, H - 0.14), W, 0.14, color=ACCENT, zorder=1))


# ── scenes ──────────────────────────────────────────────────────────────────
def scene1(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.05, "LIVE ARCHITECTURE EXPLAINER", 15, ACCENT,
        fade(tl, 0.3, 1.0), "bold")
    a = 0.85 + 0.15 * math.sin(2 * math.pi * 0.4 * tl)
    txt(ax, W / 2, 4.55, "cloud-portfolio", 58, FG, fade(tl, 0.6, 1.6) * a, "bold")
    txt(ax, W / 2, 3.62, "production-shaped microservices on Amazon EKS", 22,
        FG, fade(tl, 1.4, 2.4))
    chip(ax, W / 2, 2.55, "$20 AWS budget", fade(tl, 2.3, 3.3), FG, PANEL)
    txt(ax, W / 2, 1.5, "github.com/anasachoury/cloud-portfolio", 15, MUTED,
        fade(tl, 3.2, 4.2))


def scene2(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.5, "three services, one Helm chart", 24, FG,
        fade(tl, 0.2, 1.0), "bold")
    # browser + service boxes
    items = [("browser", 1.9, 5.9), ("frontend · nginx", 5.0, 5.9),
             ("products · FastAPI", 8.6, 5.9), ("orders · FastAPI", 5.0, 3.0),
             ("redis", 10.6, 3.0)]
    ta = [fade(tl, 0.4, 1.2), fade(tl, 1.1, 1.9), fade(tl, 1.9, 2.7),
          fade(tl, 2.9, 3.7), fade(tl, 3.9, 4.7)]
    for (label, x, y), a in zip(items, ta):
        box(ax, x, y, 3.0, 0.9, alpha=a)
        txt(ax, x, y, label, 15, alpha=a)
    # arrows
    arrow(ax, 3.4, 5.9, 3.5, 5.9, fade(tl, 1.7, 2.2), progress=fade(tl, 1.6, 2.3))
    arrow(ax, 6.5, 5.9, 7.1, 5.9, fade(tl, 2.6, 3.1), progress=fade(tl, 2.5, 3.2))
    arrow(ax, 5.0, 5.45, 5.0, 3.45, fade(tl, 3.6, 4.1), progress=fade(tl, 3.5, 4.2))
    arrow(ax, 8.6, 5.45, 5.6, 3.35, fade(tl, 4.4, 4.9), progress=fade(tl, 4.3, 5.0))
    arrow(ax, 6.5, 3.0, 9.1, 3.0, fade(tl, 5.1, 5.6), progress=fade(tl, 5.0, 5.7))
    # captions
    chip(ax, W / 2, 1.7, "one reusable chart · per-service values", fade(tl, 6.0, 7.0))
    chip(ax, W / 2, 0.9, "NetworkPolicy: default-deny + allow-lists",
         fade(tl, 7.5, 8.5), FG, "#1c2128")


def scene3(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.5, "the pipeline: four gates before anything ships", 23,
        FG, fade(tl, 0.2, 1.0), "bold")
    # git push source
    box(ax, 1.6, 4.4, 2.3, 0.95, alpha=fade(tl, 0.5, 1.3), fc="#12233d", ec=BLUE)
    txt(ax, 1.6, 4.4, "git push", 16, alpha=fade(tl, 0.5, 1.3), color=BLUE, weight="bold")
    # four gates
    gates = ["gitleaks", "semgrep", "trivy", "kubeconform"]
    gx = [4.3, 6.1, 7.9, 9.7]
    light = [fade(tl, 3.2, 4.2), fade(tl, 4.4, 5.4), fade(tl, 5.6, 6.6), fade(tl, 6.8, 7.8)]
    appear = [fade(tl, 1.0, 1.6), fade(tl, 1.2, 1.8), fade(tl, 1.4, 2.0), fade(tl, 1.6, 2.2)]
    for x, g, ap, li in zip(gx, gates, appear, light):
        on = li > 0.5
        box(ax, x, 4.4, 1.62, 0.95, alpha=ap,
            fc="#0f2a18" if on else PANEL, ec=GREEN if on else BORDER)
        txt(ax, x, 4.4, g, 12.5, alpha=ap, color=GREEN if on else FG, weight="bold")
        if on:
            txt(ax, x, 3.82, "PASS", 10.5, GREEN, li)
    # ECR
    box(ax, 11.6, 4.4, 1.7, 0.95, alpha=fade(tl, 9.3, 10.1), fc="#33220a", ec=ACCENT)
    txt(ax, 11.6, 4.4, "ECR", 16, alpha=fade(tl, 9.3, 10.1), color=ACCENT, weight="bold")
    # arrows source->gates
    for i, x in enumerate(gx):
        arrow(ax, 2.8, 4.4, x - 0.85, 4.4, fade(tl, 1.8, 2.2 + 0.15 * i),
              progress=fade(tl, 1.7, 2.4 + 0.15 * i))
    arrow(ax, 10.6, 4.4, 10.7, 4.4, fade(tl, 9.6, 10.2), color=ACCENT,
          progress=fade(tl, 9.5, 10.3), lw=2.5)
    # images flying to ECR
    for i, t_start in enumerate((11.2, 12.2, 13.2)):
        p = ease((tl - t_start) / 1.1)
        if 0 < p < 1:
            x = 6.0 + (11.0 - 6.0) * p
            y = 3.0 + 0.6 * math.sin(math.pi * p) * (1 if i % 2 else -1)
            box(ax, x, y, 0.5, 0.5, alpha=0.95, fc="#33220a", ec=ACCENT)
            txt(ax, x, y, "img", 9, color=ACCENT)
    # badges
    chip(ax, 6.4, 1.6, "SHA-pinned actions · checksummed installs", fade(tl, 8.0, 9.0))
    chip(ax, 6.4, 0.8, "OIDC federation — zero stored keys", fade(tl, 15.5, 16.5),
         "#0d1117", ACCENT)


def scene4(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.5, "GitOps: the repo is the source of truth", 24, FG,
        fade(tl, 0.2, 1.0), "bold")
    # repo box top
    box(ax, W / 2, 5.6, 4.2, 0.85, alpha=fade(tl, 0.5, 1.3), fc="#12233d", ec=BLUE)
    txt(ax, W / 2, 5.6, "gitops/  (this repo)", 15, alpha=fade(tl, 0.5, 1.3), color=BLUE, weight="bold")
    # argocd center
    box(ax, W / 2, 3.9, 2.6, 0.95, alpha=fade(tl, 1.3, 2.1), fc="#33220a", ec=ACCENT)
    txt(ax, W / 2, 3.9, "Argo CD", 17, alpha=fade(tl, 1.3, 2.1), color=ACCENT, weight="bold")
    arrow(ax, W / 2, 5.15, W / 2, 4.42, fade(tl, 1.9, 2.4), color=BLUE,
          progress=fade(tl, 1.8, 2.5), lw=2.2)
    # leaves
    leaves = ["frontend", "products", "orders", "ingress-nginx", "monitoring", "redis"]
    lx = [1.5, 3.55, 5.6, 7.65, 9.7, 11.45]
    ly = 1.7
    for i, (x, name) in enumerate(zip(lx, leaves)):
        ap = fade(tl, 2.6 + 0.55 * i, 3.4 + 0.55 * i)
        box(ax, x, ly, 1.85, 0.8, alpha=ap)
        txt(ax, x, ly, name, 11.5, alpha=ap)
        sx, sy = W / 2, 3.4
        pr = fade(tl, 2.4 + 0.55 * i, 3.2 + 0.55 * i)
        if pr > 0.01:
            # curve via quadratic control point
            mx, my = (sx + x) / 2, 2.9
            steps = 24
            pts_x, pts_y = [], []
            for k in range(steps + 1):
                u = pr * k / steps
                bx = (1 - u) ** 2 * sx + 2 * (1 - u) * u * mx + u ** 2 * x
                by = (1 - u) ** 2 * sy + 2 * (1 - u) * u * my + u ** 2 * (ly + 0.45)
                pts_x.append(bx)
                pts_y.append(by)
            ax.plot(pts_x, pts_y, color=MUTED, lw=1.6, alpha=fade(tl, 2.6 + 0.55 * i, 3.2 + 0.55 * i), zorder=2)
    # traveling pulses
    if tl > 8.0:
        for i, x in enumerate(lx):
            u = (tl * 0.30 + i * 0.167) % 1.0
            mx, my = (W / 2 + x) / 2, 2.9
            sx, sy = W / 2, 3.4
            bx = (1 - u) ** 2 * sx + 2 * (1 - u) * u * mx + u ** 2 * x
            by = (1 - u) ** 2 * sy + 2 * (1 - u) * u * my + u ** 2 * (ly + 0.45)
            ax.add_patch(Circle((bx, by), 0.07, color=ACCENT, zorder=4))
    chip(ax, W / 2, 0.6, "CI never touches the cluster — it only commits tags",
         fade(tl, 14.5, 15.5), "#0d1117", ACCENT)


def scene5(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.55, "the cluster is code (Terraform)", 24, FG,
        fade(tl, 0.2, 1.0), "bold")
    # typed terminal line
    cmd = "terraform apply  -var-file=cluster.tfvars"
    n = int(ease(fade(tl, 0.4, 2.2)) * len(cmd))
    txt(ax, 0.9, 5.85, "$ " + cmd[:n] + ("_" if (tl * 2) % 2 < 1 and n < len(cmd) else ""),
        14, GREEN, 1.0, "bold", ha="left", family="DejaVu Sans Mono")
    # VPC outline
    va = fade(tl, 1.6, 2.4)
    box(ax, 5.6, 3.5, 9.6, 3.3, alpha=va, fc="#10151d", ec=BORDER, lw=1.8)
    txt(ax, 1.4, 4.85, "VPC · eu-west-1 · 2 AZs", 12, MUTED, va, ha="left")
    # EKS + nodes
    box(ax, 5.6, 3.7, 8.4, 1.9, alpha=fade(tl, 2.4, 3.2), fc=PANEL)
    txt(ax, 5.6, 4.35, "EKS · spot t3.medium", 17, alpha=fade(tl, 2.4, 3.2), weight="bold")
    for i in range(3):
        na = fade(tl, 3.3 + 0.8 * i, 4.0 + 0.8 * i)
        nx = 2.6 + i * 2.4
        box(ax, nx, 3.15, 1.9, 0.8, alpha=na, fc="#0f2a18", ec=GREEN)
        txt(ax, nx, 3.15, f"node-{i+1}", 12, alpha=na, color=GREEN, weight="bold")
    # chips
    chip(ax, 3.4, 1.35, "NetworkPolicy ON (vpc-cni)", fade(tl, 5.4, 6.2), FG, "#1c2128")
    chip(ax, 8.0, 1.35, "cluster-autoscaler (IRSA)", fade(tl, 6.4, 7.2))
    chip(ax, 11.3, 1.35, "HPA", fade(tl, 7.4, 8.2), FG, "#1c2128")
    txt(ax, W / 2, 0.5, "public endpoint locked to admin CIDRs", 13, MUTED,
        fade(tl, 8.6, 9.4))


def scene6(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.55, "monitoring rebuilds from Git", 24, FG, fade(tl, 0.2, 1.0), "bold")
    # panel
    box(ax, 3.9, 3.4, 6.0, 4.0, alpha=fade(tl, 0.4, 1.2), fc=PANEL)
    txt(ax, 1.2, 5.05, "HPA replicas", 12, MUTED, fade(tl, 0.8, 1.6), ha="left")
    # axes
    ax.plot([1.1, 6.7], [1.6, 1.6], color=BORDER, lw=1, alpha=fade(tl, 0.6, 1.4), zorder=2)
    ax.plot([1.1, 1.1], [1.6, 4.9], color=BORDER, lw=1, alpha=fade(tl, 0.6, 1.4), zorder=2)
    # replicas step line (1 -> 4)
    rx = [1.2, 2.4, 2.4, 3.4, 3.4, 4.4, 4.4, 5.4, 5.4, 6.6]
    ry = [2.0, 2.0, 2.7, 2.7, 3.4, 3.4, 4.1, 4.1, 4.75, 4.75]
    p = fade(tl, 1.4, 4.6)
    if p > 0:
        k = max(2, int(p * len(rx)))
        ax.plot(rx[:k], ry[:k], color=BLUE, lw=2.4, zorder=3)
    # error spike
    ex = [5.0, 5.3, 5.6, 5.9, 6.2, 6.6]
    ey = [1.6, 3.6, 4.3, 4.3, 2.2, 1.6]
    p2 = fade(tl, 5.2, 8.6)
    if p2 > 0:
        k = max(2, int(p2 * len(ex)))
        ax.plot(ex[:k], ey[:k], color=RED, lw=2.0, zorder=3)
        txt(ax, 4.55, 4.55, "error ratio", 10.5, RED, fade(tl, 5.6, 6.4))
    # alert chip flash
    if 5.4 < tl < 8.2:
        on = (tl * 2.2) % 1 > 0.35
        chip(ax, 10.3, 4.9, "FastAPIHighErrorRate", 1.0 if on else 0.25,
             FG, "#3a1518" if on else PANEL)
    chip(ax, 10.3, 3.7, "dashboard = ConfigMap", fade(tl, 1.8, 2.8))
    chip(ax, 10.3, 2.85, "alerts = PrometheusRule", fade(tl, 2.6, 3.6))
    chip(ax, 10.3, 2.0, "no persistent volumes", fade(tl, 3.6, 4.6), FG, "#1c2128")
    chip(ax, 3.9, 0.7, "12h retention · rebuilt every session", fade(tl, 4.8, 5.8), FG, "#1c2128")


def scene7(ax, tl):
    base(ax)
    txt(ax, W / 2, 6.55, "built to be torn down", 24, FG, fade(tl, 0.2, 1.0), "bold")
    # terminal
    cmd = "make down"
    n = int(ease(fade(tl, 0.4, 1.4)) * len(cmd))
    txt(ax, 0.9, 5.75, "$ " + cmd[:n] + ("_" if (tl * 2) % 2 < 1 and n < len(cmd) else ""),
        15, GREEN, 1.0, "bold", ha="left", family="DejaVu Sans Mono")
    txt(ax, 1.4, 5.15, "apps deleted ✓  load balancer released ✓", 13, MUTED,
        fade(tl, 1.6, 2.4), ha="left")
    txt(ax, 1.4, 4.6, "cluster destroyed ✓  state safe in S3", 13, MUTED,
        fade(tl, 2.8, 3.6), ha="left")
    # cost counter
    txt(ax, W / 2, 3.35, "one session costs about", 18, MUTED, fade(tl, 4.4, 5.2))
    p = ease(fade(tl, 5.0, 7.2))
    val = 0.30 * p
    txt(ax, W / 2, 2.3, f"${val:4.2f}".replace(" ", "0"), 54, ACCENT,
        fade(tl, 4.8, 5.6) , "bold")
    txt(ax, W / 2, 1.15, "$20 budget  ·  ≈ 40 sessions", 17, FG, fade(tl, 8.6, 9.6), "bold")


def scene8(ax, tl):
    base(ax)
    checks = [("CI pipeline — green", 5.35), ("unit + smoke tests — 12 + 12", 4.65),
              ("everything — in the repo", 3.95)]
    for i, (c, y) in enumerate(checks):
        a = fade(tl, 0.4 + 0.6 * i, 1.2 + 0.6 * i)
        txt(ax, 2.2, y, "✓", 18, GREEN, a, "bold", ha="left")
        txt(ax, 2.8, y, c, 17, FG, a, ha="left")
    txt(ax, W / 2, 2.3, "github.com/anasachoury/cloud-portfolio", 26, FG,
        fade(tl, 2.6, 3.6), "bold")
    txt(ax, W / 2, 1.35, "Terraform · ArgoCD · Helm · Prometheus · GitHub Actions", 15,
        MUTED, fade(tl, 3.6, 4.6))
    a = 0.85 + 0.15 * math.sin(2 * math.pi * 0.4 * tl)
    txt(ax, W / 2, 0.6, "thanks for watching", 18, ACCENT, fade(tl, 4.6, 5.6) * a, "bold")


SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]


def main():
    os.makedirs(FRAMES, exist_ok=True)
    nframes = int(TOTAL * FPS)
    for k in range(nframes):
        t = k / FPS
        for s, st, ln in zip(SCENES, starts, lengths):
            if st <= t < st + ln:
                idx = SCENES.index(s)
                fig = plt.figure(figsize=(W, H), dpi=100)
                ax = fig.add_axes([0, 0, 1, 1])
                s(ax, t - st)
                fig.savefig(os.path.join(FRAMES, f"f{k:05d}.png"),
                            facecolor=BG)
                plt.close(fig)
                break
        if k % 240 == 0:
            print(f"frame {k}/{nframes} (t={t:.1f}s)", flush=True)
    print("done:", nframes, "frames")


if __name__ == "__main__":
    main()
