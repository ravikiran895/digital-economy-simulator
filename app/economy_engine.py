"""
economy_engine.py
-----------------
Core simulation of a virtual economy as a faucet/sink system, with a *stable*
price model that produces realistic inflation and deflation instead of runaway
or collapsing values.

The price model (why it's stable)
---------------------------------
Earlier versions normalised net currency flow by the *current* supply, which
blows up as supply drains toward zero. This version uses a quantity-theory-style
relationship instead:

    price_level(t) = ( supply_per_dau(t) / equilibrium_supply ) ** price_elasticity

Intuition: prices scale with how much currency players hold relative to an
equilibrium target, but sub-linearly (elasticity < 1), the way real prices
respond to money supply. This gives us, for free:

  * a genuine equilibrium  (supply == equilibrium  ->  price == 1.0, inflation 0)
  * smooth inflation        (supply grows           ->  prices rise, decelerating)
  * smooth deflation        (supply shrinks         ->  prices fall, bounded)
  * no numerical blow-ups   (price is bounded by the supply ratio)

Inflation is then simply the day-over-day change in the price level — a small,
interpretable number. Nothing here depends on Streamlit/pandas/matplotlib.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple


@dataclass
class EconomyConfig:
    """All tunable levers for the economy simulation (per-DAU, per-day)."""

    # --- Population & horizon ---
    starting_dau: int = 10_000
    days: int = 180

    # --- Faucets (currency created per DAU per day) ---
    daily_login_reward: float = 100.0
    quest_reward: float = 60.0
    event_reward: float = 0.0
    reward_generosity: float = 1.0          # global multiplier on faucets

    # --- Sinks (currency destroyed per DAU per day) ---
    cosmetic_spend: float = 70.0
    upgrade_spend: float = 80.0
    marketplace_fee_rate: float = 0.05
    sink_event_bonus: float = 0.0

    # --- Stock & price model ---
    starting_supply_per_dau: float = 6_000.0
    equilibrium_supply_per_dau: float = 6_000.0  # supply at which price == 1.0
    price_elasticity: float = 0.40               # how strongly price tracks supply

    # --- Content growth (sinks grow as new content ships) ---
    content_growth: float = 0.0006               # daily growth in sink capacity

    def faucet_total(self) -> float:
        base = self.daily_login_reward + self.quest_reward + self.event_reward
        return base * self.reward_generosity

    def sink_total(self, marketplace_volume_per_dau: float = 0.0) -> float:
        direct = self.cosmetic_spend + self.upgrade_spend + self.sink_event_bonus
        fees = marketplace_volume_per_dau * self.marketplace_fee_rate
        return direct + fees


@dataclass
class EconomyState:
    day: int
    dau: int
    supply_per_dau: float
    total_supply: float
    faucet_per_dau: float
    sink_per_dau: float
    net_flow_per_dau: float
    inflation_rate: float       # daily, as a fraction
    price_level: float          # index, 1.0 == equilibrium
    velocity: float             # currency turns per day
    sink_efficiency: float      # sinks / faucets (1.0 == balanced)


class EconomyEngine:
    def __init__(self, config: EconomyConfig):
        self.config = config

    def run(self, marketplace_volume_per_dau: float = 0.0) -> List[EconomyState]:
        c = self.config
        history: List[EconomyState] = []

        supply = c.starting_supply_per_dau
        eq = max(c.equilibrium_supply_per_dau, 1.0)
        prev_price = (supply / eq) ** c.price_elasticity
        sink_capacity = 1.0

        for day in range(c.days):
            dau = c.starting_dau
            faucet = c.faucet_total()
            sink = c.sink_total(marketplace_volume_per_dau) * sink_capacity
            net_flow = faucet - sink

            supply = max(1.0, supply + net_flow)
            total_supply = supply * dau

            # Stable price model (quantity-theory style, sub-linear).
            price_level = (supply / eq) ** c.price_elasticity
            inflation = price_level / prev_price - 1.0
            prev_price = price_level

            throughput = faucet + sink
            velocity = throughput / max(supply, 1.0)
            sink_efficiency = sink / max(faucet, 1e-9)

            history.append(EconomyState(
                day=day, dau=dau,
                supply_per_dau=round(supply, 2),
                total_supply=round(total_supply, 2),
                faucet_per_dau=round(faucet, 2),
                sink_per_dau=round(sink, 2),
                net_flow_per_dau=round(net_flow, 2),
                inflation_rate=round(inflation, 6),
                price_level=round(price_level, 4),
                velocity=round(velocity, 5),
                sink_efficiency=round(sink_efficiency, 4),
            ))

            sink_capacity *= (1 + c.content_growth)

        return history

    @staticmethod
    def health_summary(history: List[EconomyState]) -> Dict[str, float]:
        """Headline KPIs from a finished run, with realistic inflation figures."""
        if not history:
            return {}
        last = history[-1]
        first = history[0]

        # Recent inflation over a trailing 30-day window (the PM-intuitive figure).
        window = min(30, len(history) - 1)
        if window > 0:
            ref_price = history[-1 - window].price_level
            inflation_30d = last.price_level / max(ref_price, 1e-9) - 1.0
            # Annualise the trailing window rate (bounded, since the price model is).
            annualised = (1 + inflation_30d) ** (365.0 / window) - 1.0
        else:
            inflation_30d = 0.0
            annualised = 0.0

        avg_efficiency = sum(h.sink_efficiency for h in history) / len(history)
        supply_growth = (last.supply_per_dau - first.supply_per_dau) / max(first.supply_per_dau, 1.0)

        return {
            "final_price_level": round(last.price_level, 3),
            "inflation_30d_pct": round(inflation_30d * 100, 2),
            "annualised_inflation_pct": round(max(-99.0, min(999.0, annualised * 100)), 1),
            "avg_sink_efficiency": round(avg_efficiency, 3),
            "supply_growth_pct": round(supply_growth * 100, 1),
            "final_velocity": round(last.velocity, 4),
        }

    @staticmethod
    def classify_health(
        sink_efficiency: float,
        inflation_30d_pct: float,
        dau_trend_pct: float = 0.0,
    ) -> Tuple[str, str, List[str]]:
        """Return (emoji, label, reasons) describing overall economy health.

        Thresholds are deliberately product-readable:
          * Sink efficiency near 1.0 is healthy.
          * 30-day inflation within +-3% is healthy; beyond +-8% is critical.
          * A collapsing DAU trend (< -15% over the window) is critical on its own.
        """
        reasons: List[str] = []
        score = 0  # 0 healthy, 1 risk, 2 critical

        # Sink efficiency
        if 0.90 <= sink_efficiency <= 1.12:
            reasons.append(f"Sink efficiency {sink_efficiency:.2f} is in the healthy band.")
        elif 0.75 <= sink_efficiency < 0.90:
            score = max(score, 1)
            reasons.append(f"Faucets outpace sinks (efficiency {sink_efficiency:.2f}) — inflation pressure.")
        elif 1.12 < sink_efficiency <= 1.35:
            score = max(score, 1)
            reasons.append(f"Sinks outpace faucets (efficiency {sink_efficiency:.2f}) — currency-starvation risk.")
        else:
            score = 2
            side = "far exceed" if sink_efficiency < 0.75 else "far below"
            reasons.append(f"Severe imbalance: sink efficiency {sink_efficiency:.2f} — faucets {side} sinks.")

        # Inflation
        if abs(inflation_30d_pct) <= 3:
            reasons.append(f"30-day inflation {inflation_30d_pct:+.1f}% is stable.")
        elif abs(inflation_30d_pct) <= 8:
            score = max(score, 1)
            tag = "Inflation" if inflation_30d_pct > 0 else "Deflation"
            reasons.append(f"{tag} elevated at {inflation_30d_pct:+.1f}% over 30 days.")
        else:
            score = 2
            tag = "Runaway inflation" if inflation_30d_pct > 0 else "Deflationary spiral"
            reasons.append(f"{tag}: {inflation_30d_pct:+.1f}% over 30 days.")

        # DAU trend
        if dau_trend_pct < -15:
            score = 2
            reasons.append(f"DAU is collapsing ({dau_trend_pct:+.0f}% over the window).")
        elif dau_trend_pct < -5:
            score = max(score, 1)
            reasons.append(f"DAU is declining ({dau_trend_pct:+.0f}%).")

        if score == 0:
            return "🟢", "Stable", reasons
        if score == 1:
            label = "Inflation Risk" if inflation_30d_pct > 0 or sink_efficiency < 0.9 else "Deflation Risk"
            return "🟠", label, reasons
        return "🔴", "Economy Collapse", reasons


def to_records(history: List[EconomyState]) -> List[dict]:
    return [asdict(h) for h in history]


if __name__ == "__main__":
    for name, cfg in {
        "balanced (default)": EconomyConfig(),
        "inflation crisis": EconomyConfig(reward_generosity=1.8, cosmetic_spend=15, upgrade_spend=15),
        "sink starvation": EconomyConfig(reward_generosity=1.5, cosmetic_spend=5, upgrade_spend=5),
        "deflationary": EconomyConfig(reward_generosity=0.6, cosmetic_spend=120, upgrade_spend=140),
    }.items():
        h = EconomyEngine(cfg).run(marketplace_volume_per_dau=120)
        s = EconomyEngine.health_summary(h)
        status = EconomyEngine.classify_health(s["avg_sink_efficiency"], s["inflation_30d_pct"])
        print(f"{name:22s} | infl30d={s['inflation_30d_pct']:+6.2f}% | ann={s['annualised_inflation_pct']:+7.1f}% "
              f"| eff={s['avg_sink_efficiency']:.2f} | {status[0]} {status[1]}")
