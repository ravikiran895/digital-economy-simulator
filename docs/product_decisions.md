# Product Decisions

This document explains the *why* behind the simulator — the product reasoning a
PM or systems designer would bring to a live-service virtual economy. The code
implements these ideas; this is the thinking behind them.

---

## 1. Why model the economy as faucets and sinks at all?

Every virtual economy is, at its core, a **stock-and-flow system**. Currency is a
stock. It is filled by *faucets* (rewards the game hands out) and drained by
*sinks* (things players spend on). The single most important number in the whole
system is the ratio between the two — what this project calls **sink efficiency**.

When faucets persistently outrun sinks, currency accumulates faster than it can be
removed. Each coin buys less over time. This is inflation, and it is the silent
killer of live-service economies because it makes every reward feel worse without
any single visible "nerf."

> **Decision:** the engine treats sink efficiency (`sinks ÷ faucets`) as the
> headline health metric and flags any run outside the 0.85–1.15 band.

---

## 2. Why inflation kills engagement

Inflation is not just an economic abstraction — it directly damages the player
experience:

- **Reward erosion.** A "1,000 coin" daily reward that felt generous at launch
  feels trivial once prices have tripled. The reward number didn't change; its
  *real value* did.
- **New-player cliffs.** When veteran players hold vast currency reserves, prices
  on a free marketplace drift toward what whales will pay, pricing out newcomers.
- **Broken progression math.** Designers tune upgrade costs against an assumed
  currency value. Inflation invalidates that tuning, making content either
  trivially cheap or impossibly expensive.

> **Decision:** the model surfaces a `price_level` index (1.0 at launch) so the
> erosion of reward value is visible as a single line, not buried in raw supply
> numbers.

---

## 3. Why sinks matter more than rewards

It is tempting to drive engagement by *adding rewards*. This works for a week and
backfires over a quarter. The durable lever is **sinks** — giving players
compelling, repeatable things to spend on:

- **Cosmetics** — infinite, value-stable sinks because they don't affect power.
- **Upgrades / progression** — sinks that scale with content cadence.
- **Marketplace fees** — a sink that grows with engagement itself.
- **Sink events** — time-boxed deflationary pressure (limited cosmetics, prestige
  resets) used to mop up excess currency before it inflates prices.

> **Decision:** the simulator lets sinks scale with content growth over time
> (`content_growth`), reflecting that a healthy live game ships new sinks
> continuously — not just at launch.

---

## 4. Why retention is an inverted-U, not a straight line

The naive model says "more rewards → happier players → better retention." The
data-informed model says retention follows an **inverted-U** against generosity:

- **Too stingy** → no sense of progress → early churn (poor D1/D7).
- **Balanced** → steady, earned wins → strong retention across the board.
- **Too generous** → players exhaust the content runway and run out of goals →
  *progression fatigue* → late churn (poor D30).

The retention model encodes this explicitly: `D1`/`D7` respond mostly to reward
**frequency** (habit formation), while `D30` peaks near balanced generosity and
**declines** if you over-reward.

> **Decision:** the Retention tab plots a generosity sweep so the sweet spot is
> visible and the over-rewarding failure mode is undeniable in the chart.

---

## 5. Why a marketplace improves ownership (and stabilises the economy)

A player-to-player marketplace does three jobs simultaneously:

1. **Creates ownership.** Items with resale value feel *owned*, not rented. This
   raises willingness to invest time and money.
2. **Acts as a sink.** Every trade pays a fee, removing currency proportional to
   engagement — a self-scaling deflationary force.
3. **Adds an engagement loop.** Trading, flipping, and price-watching are
   retention behaviours in their own right.

The risk is instability: runaway prices or dead liquidity. The model includes
**price elasticity of demand** (demand falls as price rises) so the market settles
at equilibrium rather than spiralling, and it tracks **liquidity** (share of buy
intent filled) and **volatility** as stability guardrails.

> **Decision:** marketplace fees feed back into the economy engine as a real sink,
> so the two systems are coupled rather than analysed in isolation.

---

## 6. Why monetization and economy health are the same problem

Monetization events are not separate from the economy — they *are* economy events:

- A **seasonal offer** lifts revenue but often injects currency (a faucet),
  stoking inflation.
- A **premium bundle** is the strongest direct revenue lever and can double as a
  sink if it consumes currency.
- A **sink event** earns less directly but protects long-term reward value, which
  is what keeps monetization durable.

The whale dynamic matters here: a small share of players (~2%) typically drives a
majority of revenue, while casual players drive reach and marketplace liquidity.
A good LiveOps calendar **alternates faucet-style and sink-style events** to grow
ARPDAU without debasing the currency.

> **Decision:** the Monetization tab shows ARPDAU lift *and* the inflation side
> effect of each event type side by side, because optimising one while ignoring
> the other is the classic live-service mistake.

---

## Summary of headline metrics tracked

| Metric | What it tells you | Healthy direction |
| --- | --- | --- |
| Sink efficiency | Faucet/sink balance | ~1.0 |
| Price level / inflation | Reward value erosion | Flat / low |
| Currency velocity | Circulation & engagement | Steady, non-zero |
| D1 / D7 / D30 retention | Habit and long-term stickiness | Higher, balanced |
| Marketplace liquidity | Trade health | High (>80%) |
| Price volatility | Market stability | Low |
| ARPDAU | Revenue per active user | Higher, sustainably |

These are the numbers a product team would put on the wall — and the ones this
simulator is built to move.
