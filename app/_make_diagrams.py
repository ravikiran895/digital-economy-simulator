"""Generate architecture diagrams for the docs/ folder."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "docs")
os.makedirs(OUT, exist_ok=True)

C = {
    "faucet": "#3b82f6", "sink": "#ef4444", "core": "#8b5cf6",
    "good": "#10b981", "ink": "#1e293b", "muted": "#64748b",
    "bg": "#f8fafc", "card": "#ffffff",
}


def box(ax, x, y, w, h, text, color, text_color="white", fontsize=10, bold=True):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.5, edgecolor=color, facecolor=color, alpha=0.95)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            color=text_color, fontsize=fontsize,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, color="#64748b", style="-|>", lw=1.8):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=16, linewidth=lw, color=color)
    ax.add_patch(a)


# --------------------------------------------------------------------------- #
# Diagram 1: Economy architecture (faucet -> supply -> sink)
# --------------------------------------------------------------------------- #
fig, ax = plt.subplots(figsize=(11, 6.2))
fig.patch.set_facecolor(C["bg"]); ax.set_facecolor(C["bg"])
ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis("off")
ax.text(6, 6.6, "Virtual Economy Architecture", ha="center", fontsize=16,
        fontweight="bold", color=C["ink"])
ax.text(6, 6.15, "Currency is created by faucets, held as supply, and destroyed by sinks",
        ha="center", fontsize=10, color=C["muted"])

# Faucets (left)
ax.text(1.6, 5.3, "FAUCETS", ha="center", fontsize=11, fontweight="bold", color=C["faucet"])
for i, t in enumerate(["Daily login reward", "Quest / progression", "Event rewards"]):
    box(ax, 0.4, 4.3 - i * 0.85, 2.4, 0.6, t, C["faucet"], fontsize=9)

# Core supply (center)
box(ax, 4.4, 3.2, 3.2, 1.5, "CURRENCY SUPPLY\n(money in circulation)", C["core"], fontsize=11)
ax.text(6.0, 2.9, "→ inflation · velocity · price level", ha="center",
        fontsize=8.5, color=C["muted"], style="italic")

# Sinks (right)
ax.text(10.4, 5.3, "SINKS", ha="center", fontsize=11, fontweight="bold", color=C["sink"])
for i, t in enumerate(["Cosmetic purchases", "Upgrades / gear", "Marketplace fees", "Sink events"]):
    box(ax, 9.2, 4.3 - i * 0.72, 2.4, 0.55, t, C["sink"], fontsize=9)

# Arrows faucets -> supply
for i in range(3):
    arrow(ax, 2.8, 4.6 - i * 0.85, 4.4, 4.1 - i * 0.18, color=C["faucet"])
# Arrows supply -> sinks
for i in range(4):
    arrow(ax, 7.6, 4.0 - i * 0.0 + (1 - i) * 0.12, 9.2, 4.55 - i * 0.72, color=C["sink"])

# Feedback loop note
box(ax, 4.4, 1.0, 3.2, 0.8, "Inflation feeds back →\nrewards lose real value", C["good"], fontsize=9)
arrow(ax, 6.0, 3.2, 6.0, 1.8, color=C["good"], style="-|>")
arrow(ax, 4.4, 1.4, 1.6, 3.7, color=C["good"], style="-|>", lw=1.2)

plt.tight_layout()
fig.savefig(os.path.join(OUT, "economy_architecture.png"), dpi=150,
            bbox_inches="tight", facecolor=C["bg"])
plt.close(fig)
print("saved economy_architecture.png")


# --------------------------------------------------------------------------- #
# Diagram 2: Player lifecycle flow
# --------------------------------------------------------------------------- #
fig, ax = plt.subplots(figsize=(11, 5.5))
fig.patch.set_facecolor(C["bg"]); ax.set_facecolor(C["bg"])
ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")
ax.text(6, 5.5, "Player Lifecycle & Economy Loop", ha="center", fontsize=16,
        fontweight="bold", color=C["ink"])

stages = [
    ("Acquire", C["faucet"], "New users\njoin daily"),
    ("Engage", C["core"], "Earn rewards\n(faucet)"),
    ("Progress", C["good"], "Spend on upgrades\n(sink)"),
    ("Trade", "#f59e0b", "Marketplace\nfees (sink)"),
    ("Monetize", C["sink"], "Offers & bundles\n(revenue)"),
    ("Retain", C["core"], "Habit + goals\n→ D1/D7/D30"),
]
n = len(stages)
x0, w, gap = 0.4, 1.55, 0.35
y = 2.8
for i, (title, color, sub) in enumerate(stages):
    x = x0 + i * (w + gap)
    box(ax, x, y, w, 1.1, title, color, fontsize=11)
    ax.text(x + w / 2, y - 0.45, sub, ha="center", va="center",
            fontsize=8.5, color=C["muted"])
    if i < n - 1:
        arrow(ax, x + w, y + 0.55, x + w + gap, y + 0.55, color=C["muted"])

# Loop-back arrow from Retain to Engage
arrow(ax, x0 + (n - 1) * (w + gap) + w / 2, y + 1.1,
      x0 + 1 * (w + gap) + w / 2, y + 1.1, color=C["core"], style="-|>", lw=1.5)
ax.text(6, y + 1.55, "retained players re-enter the earn → spend loop",
        ha="center", fontsize=9, color=C["core"], style="italic")

ax.text(6, 0.7, "Healthy economies keep this loop balanced: enough faucet to feel rewarding,\n"
                "enough sink to stay valuable, enough monetization to fund the live service.",
        ha="center", fontsize=9.5, color=C["ink"])

plt.tight_layout()
fig.savefig(os.path.join(OUT, "lifecycle_flow.png"), dpi=150,
            bbox_inches="tight", facecolor=C["bg"])
plt.close(fig)
print("saved lifecycle_flow.png")
