"""
monetization_model.py
---------------------
Turns engagement and economy state into revenue metrics.

Metrics produced
----------------
  * ARPDAU                  — average revenue per daily active user
  * payer_conversion        — share of DAU that spends on a given day
  * whale_revenue_share     — % of revenue from the whale cohort
  * sink_monetization_eff   — how much currency pressure is backed by sinks vs
                              free faucet injection (does monetization protect or
                              debase the economy?)

Cohort model
------------
Players split into whales / dolphins / casual, each with a spend level and a
daily conversion probability. ARPDAU is the blended average. Events apply a
revenue multiplier and may inject or consume currency, linking monetization back
to the economy's inflation.
"""

from dataclasses import dataclass


@dataclass
class MonetizationConfig:
    whale_share: float = 0.02       # fraction of DAU
    whale_spend: float = 12.0       # $ per whale per day (when paying)
    dolphin_share: float = 0.08
    dolphin_spend: float = 1.2
    casual_spend: float = 0.15      # blended $ per casual per day
    whale_convert: float = 0.85     # P(spend today | whale)
    dolphin_convert: float = 0.40
    casual_convert: float = 0.03


@dataclass
class MonetizationResult:
    arpdau: float
    daily_revenue: float
    payer_conversion: float
    whale_revenue: float
    dolphin_revenue: float
    casual_revenue: float
    whale_revenue_share: float
    sink_monetization_efficiency: float


def compute(
    cfg: MonetizationConfig,
    dau: int,
    event_revenue_mult: float = 1.0,
    currency_sink_per_dau: float = 0.0,
    currency_faucet_per_dau: float = 0.0,
) -> MonetizationResult:
    """Compute monetization metrics for a single representative day."""
    casual_share = max(0.0, 1.0 - cfg.whale_share - cfg.dolphin_share)

    whale_pp = cfg.whale_share * cfg.whale_convert * cfg.whale_spend
    dolphin_pp = cfg.dolphin_share * cfg.dolphin_convert * cfg.dolphin_spend
    casual_pp = casual_share * cfg.casual_convert * cfg.casual_spend

    arpdau = (whale_pp + dolphin_pp + casual_pp) * event_revenue_mult
    daily_revenue = arpdau * dau

    whale_rev = whale_pp * event_revenue_mult * dau
    dolphin_rev = dolphin_pp * event_revenue_mult * dau
    casual_rev = casual_pp * event_revenue_mult * dau
    total_rev = max(whale_rev + dolphin_rev + casual_rev, 1e-9)

    payer_conversion = (
        cfg.whale_share * cfg.whale_convert
        + cfg.dolphin_share * cfg.dolphin_convert
        + casual_share * cfg.casual_convert
    )

    sink_eff = currency_sink_per_dau / max(currency_faucet_per_dau, 1e-9)
    sink_eff = round(min(sink_eff, 2.0), 3)

    return MonetizationResult(
        arpdau=round(arpdau, 4),
        daily_revenue=round(daily_revenue, 2),
        payer_conversion=round(payer_conversion, 4),
        whale_revenue=round(whale_rev, 2),
        dolphin_revenue=round(dolphin_rev, 2),
        casual_revenue=round(casual_rev, 2),
        whale_revenue_share=round(whale_rev / total_rev * 100, 1),
        sink_monetization_efficiency=sink_eff,
    )


if __name__ == "__main__":
    r = compute(MonetizationConfig(), dau=10_000,
                currency_sink_per_dau=156, currency_faucet_per_dau=160)
    print(r)
