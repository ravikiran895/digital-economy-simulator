# Monetization Strategy

How the simulator thinks about turning a healthy economy into durable revenue —
without debasing the currency that makes the game worth playing.

---

## The core tension

Every monetization decision pulls on two ropes at once:

- **Revenue now** — offers, bundles, and currency packs that lift ARPDAU today.
- **Economy health later** — keeping currency scarce enough that rewards and
  purchases stay meaningful.

Pull too hard on revenue and you inject currency, inflate prices, and erode the
value of everything players buy — including the things they pay you for. The job
is to grow revenue *while* defending the price level.

---

## ARPDAU as the north-star revenue metric

**ARPDAU** (Average Revenue Per Daily Active User) is the right lens for a live
service because it normalises revenue against engagement:

```
ARPDAU = total daily revenue / daily active users
```

In the simulator, ARPDAU is built bottom-up from two cohorts:

```
ARPDAU = whale_share × whale_spend  +  casual_share × casual_spend
```

This makes the whale dynamic explicit and lets you see how a single event
multiplier flows through to total daily revenue (`ARPDAU × DAU`).

---

## Whales vs casual players

A recurring pattern in free-to-play economies:

- **Whales** — roughly **1–3%** of DAU, but frequently **50–70%+** of revenue.
  They are price-insensitive and value prestige, exclusivity, and time savings.
- **Casual / non-paying players** — the vast majority. They rarely spend, but they
  provide **reach, social proof, and marketplace liquidity**. Whales need someone
  to be impressive *to*; casual players are the audience.

> **Strategic implication:** never design only for whales. Casual players are the
> liquidity and the social fabric that gives whale spending its meaning. The
> Monetization tab visualises this split directly.

---

## Event playbook

The simulator models four event states, each with a different revenue/economy
profile:

| Event | Revenue effect | Economy side effect | When to use |
| --- | --- | --- | --- |
| **None** | Baseline | Neutral | Steady-state weeks |
| **Seasonal offer** | Strong lift (~+60%) | Injects currency (inflationary) | Drive a spike; pair with a sink soon after |
| **Premium bundle** | Strongest lift (~+90%) | Mild sink if it consumes currency | Tentpole moments, new content drops |
| **Sink event** | Modest lift (~+10%) | Strong deflation | Cool down inflation, protect reward value |

The key insight the simulator makes visible: **a seasonal offer and a sink event
have opposite effects on the price level.** A calendar that only runs offers
slowly debases the economy; a calendar that alternates them grows ARPDAU while
holding inflation flat.

---

## A balanced LiveOps cadence (illustrative)

```
Week 1  Seasonal offer        → revenue spike, currency injected
Week 2  Steady state          → economy settles
Week 3  Premium bundle        → tentpole revenue, partial sink
Week 4  Sink event            → mop up excess currency, reset price level
        └── repeat ────────────────────────────────────────────────┘
```

This rhythm treats monetization and economy management as a **single feedback
loop**, not two separate teams optimising against each other.

---

## What "good" looks like

A monetization strategy is working when, over a quarter:

- ARPDAU trends **up**,
- price level stays **roughly flat** (inflation under control),
- whale revenue grows **without** casual engagement collapsing,
- and marketplace liquidity stays **healthy** (a sign currency still circulates).

If ARPDAU rises but the price level runs away, the revenue is borrowed from the
future — players will feel the erosion and churn. The simulator is designed to
catch exactly that tradeoff before it ships.
