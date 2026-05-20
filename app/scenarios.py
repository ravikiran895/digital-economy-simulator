"""
scenarios.py
------------
Scenario presets and the Product Insights engine.

Two jobs:
  1. PRESETS — one-click economy configurations that each tell a clear story
     (Healthy, Whale-Driven, Inflation Crisis, Hyper-Generous, Sink Starvation).
     These make the demo interactive and memorable.

  2. INSIGHTS — turn raw metrics into the kind of written analysis a product
     manager would put in a deck: what's happening, why, and the tradeoff. This
     is what elevates the tool from "charts" to "analysis".
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Preset:
    name: str
    emoji: str
    blurb: str
    # Economy levers
    reward_generosity: float
    daily_login_reward: int
    quest_reward: int
    cosmetic_spend: int
    upgrade_spend: int
    fee_rate: float
    starting_supply: int
    equilibrium_supply: int
    # Retention levers
    progression_pacing: float
    reward_frequency: float
    # Monetization levers
    whale_share_pct: float
    whale_spend: float
    casual_spend: float


# Values below are tuned (see engine tests) so each scenario lands in a
# distinct, legible health regime.
PRESETS: Dict[str, Preset] = {
    "Healthy Economy": Preset(
        name="Healthy Economy", emoji="🟢",
        blurb="Faucets and sinks balanced; inflation near zero; retention solid. The target state.",
        reward_generosity=1.0, daily_login_reward=105, quest_reward=65,
        cosmetic_spend=70, upgrade_spend=80, fee_rate=0.05,
        starting_supply=6000, equilibrium_supply=6000,
        progression_pacing=1.0, reward_frequency=3.5,
        whale_share_pct=2.0, whale_spend=12.0, casual_spend=0.15,
    ),
    "Whale-Driven Economy": Preset(
        name="Whale-Driven Economy", emoji="🐋",
        blurb="Revenue concentrated in a tiny high-spend cohort; healthy economy but fragile revenue base.",
        reward_generosity=1.05, daily_login_reward=105, quest_reward=65,
        cosmetic_spend=75, upgrade_spend=80, fee_rate=0.06,
        starting_supply=6000, equilibrium_supply=6000,
        progression_pacing=1.0, reward_frequency=3.0,
        whale_share_pct=1.5, whale_spend=35.0, casual_spend=0.08,
    ),
    "Inflation Crisis": Preset(
        name="Inflation Crisis", emoji="🔥",
        blurb="Rewards flooding in, sinks too weak. Prices climb, rewards lose value, players disengage.",
        reward_generosity=1.5, daily_login_reward=100, quest_reward=60,
        cosmetic_spend=30, upgrade_spend=30, fee_rate=0.03,
        starting_supply=6000, equilibrium_supply=6000,
        progression_pacing=1.2, reward_frequency=4.0,
        whale_share_pct=2.0, whale_spend=12.0, casual_spend=0.15,
    ),
    "Hyper-Generous Rewards": Preset(
        name="Hyper-Generous Rewards", emoji="🎁",
        blurb="Players are over-rewarded. Great D1, but goals evaporate — progression fatigue tanks D30.",
        reward_generosity=1.9, daily_login_reward=140, quest_reward=90,
        cosmetic_spend=40, upgrade_spend=45, fee_rate=0.04,
        starting_supply=6000, equilibrium_supply=6000,
        progression_pacing=1.6, reward_frequency=6.0,
        whale_share_pct=1.8, whale_spend=10.0, casual_spend=0.12,
    ),
    "Sink Starvation": Preset(
        name="Sink Starvation", emoji="🏜️",
        blurb="Almost nothing to spend on. Currency piles up, inflation accelerates, ownership feels hollow.",
        reward_generosity=1.3, daily_login_reward=100, quest_reward=60,
        cosmetic_spend=10, upgrade_spend=10, fee_rate=0.02,
        starting_supply=6000, equilibrium_supply=6000,
        progression_pacing=1.0, reward_frequency=3.0,
        whale_share_pct=2.0, whale_spend=12.0, casual_spend=0.15,
    ),
    "Deflationary Squeeze": Preset(
        name="Deflationary Squeeze", emoji="🧊",
        blurb="Sinks slightly outpace faucets. Prices drift down, players hoard, the economy cools.",
        reward_generosity=0.85, daily_login_reward=100, quest_reward=60,
        cosmetic_spend=70, upgrade_spend=72, fee_rate=0.06,
        starting_supply=6000, equilibrium_supply=6000,
        progression_pacing=0.9, reward_frequency=2.5,
        whale_share_pct=2.0, whale_spend=12.0, casual_spend=0.15,
    ),
}


def generate_insights(
    *,
    sink_efficiency: float,
    inflation_30d_pct: float,
    faucet_per_dau: float,
    sink_per_dau: float,
    fee_per_dau: float,
    d7_pct: float,
    d30_pct: float,
    reward_generosity: float,
    arpdau: float,
    whale_share_pct: float,
    whale_revenue_pct: float,
    liquidity_pct: float,
    velocity: float,
) -> List[str]:
    """Return a list of written, PM-style insight paragraphs.

    Each insight names the mechanism and the tradeoff, not just the number.
    """
    insights: List[str] = []

    # --- Faucet/sink balance & inflation ---
    gap = faucet_per_dau - sink_per_dau
    gap_pct = (gap / max(faucet_per_dau, 1e-9)) * 100
    if inflation_30d_pct > 3:
        fee_share = (fee_per_dau / max(sink_per_dau, 1e-9)) * 100
        insights.append(
            f"**Inflation is rising (+{inflation_30d_pct:.1f}% / 30d).** Faucets generate "
            f"{faucet_per_dau:.0f} coins/DAU/day against only {sink_per_dau:.0f} in sinks — a "
            f"{gap_pct:.0f}% surplus that accumulates as excess supply. Marketplace fees cover just "
            f"{fee_share:.0f}% of total sink pressure, so they can't stabilise circulation alone. "
            f"Add direct sinks (cosmetics, upgrade costs) or trim rewards to close the gap."
        )
    elif inflation_30d_pct < -3:
        insights.append(
            f"**The economy is deflating ({inflation_30d_pct:.1f}% / 30d).** Sinks remove "
            f"{sink_per_dau:.0f} coins/DAU/day versus {faucet_per_dau:.0f} created, so currency is "
            f"draining faster than it's earned. Players hoard, spending slows, and rewards start to "
            f"feel stingy. Loosen rewards or reduce sink costs to restore circulation."
        )
    else:
        insights.append(
            f"**Currency supply is well balanced.** Faucets ({faucet_per_dau:.0f}/DAU/day) and sinks "
            f"({sink_per_dau:.0f}/DAU/day) are within a few percent, holding 30-day inflation at "
            f"{inflation_30d_pct:+.1f}%. This keeps reward value stable — the foundation everything "
            f"else (progression tuning, pricing, monetization) is built on."
        )

    # --- Velocity / circulation ---
    if velocity < 0.02:
        insights.append(
            f"**Currency velocity is low ({velocity:.3f} turns/day).** Coins are sitting idle rather "
            f"than circulating — a sign players have little reason to spend. Low velocity often "
            f"precedes inflation, because idle currency is just supply waiting to devalue rewards."
        )

    # --- Retention & generosity tradeoff ---
    if reward_generosity > 1.4 and d30_pct < d7_pct * 0.45:
        insights.append(
            f"**Progression fatigue is showing.** At {reward_generosity:.1f}× generosity, D7 is healthy "
            f"({d7_pct:.1f}%) but D30 has fallen to {d30_pct:.1f}% — players hit their goals too fast and "
            f"run out of reasons to return. Counter-intuitively, *reducing* rewards here would likely "
            f"lift long-term retention by stretching the content runway."
        )
    elif reward_generosity < 0.8:
        insights.append(
            f"**Rewards may be too thin.** At {reward_generosity:.1f}× generosity, early players feel "
            f"little progress, which suppresses D7 ({d7_pct:.1f}%). A modest reward bump would likely "
            f"improve early-funnel retention without threatening the economy."
        )
    else:
        insights.append(
            f"**Retention design is in a healthy zone.** D7 {d7_pct:.1f}% / D30 {d30_pct:.1f}% reflects "
            f"a generosity setting ({reward_generosity:.1f}×) that rewards players without exhausting "
            f"their goals too quickly."
        )

    # --- Monetization concentration ---
    if whale_revenue_pct >= 60:
        insights.append(
            f"**Revenue is highly whale-concentrated.** ~{whale_share_pct:.1f}% of players drive "
            f"{whale_revenue_pct:.0f}% of revenue (ARPDAU ${arpdau:.3f}). This is efficient but fragile: "
            f"losing a handful of high-spenders dents revenue disproportionately. Broadening casual "
            f"conversion would make ARPDAU more durable."
        )
    else:
        insights.append(
            f"**Revenue is reasonably distributed.** Whales (~{whale_share_pct:.1f}% of players) drive "
            f"{whale_revenue_pct:.0f}% of an ARPDAU of ${arpdau:.3f} — concentrated, as expected, but "
            f"not dangerously dependent on a few accounts."
        )

    # --- Marketplace health ---
    if liquidity_pct < 70:
        insights.append(
            f"**The marketplace is illiquid ({liquidity_pct:.0f}% of buy intent filled).** Buyers can't "
            f"find what they want, which suppresses both the fee sink and the ownership loop. Increasing "
            f"listing supply or rebalancing rarity drop rates would deepen the market."
        )

    return insights
