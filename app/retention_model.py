"""
retention_model.py
------------------
Models how reward design choices move D1 / D7 / D30 retention and, through that,
the daily active user (DAU) curve.

Core idea
---------
Retention is not maximised by maximum generosity. The model captures the classic
live-service tension:

  * Too stingy  -> players feel no progress -> they churn early (low D1/D7).
  * Too generous -> players hit the ceiling fast -> "progression fatigue" -> they
    run out of goals and churn later (low D30).
  * Reward *frequency* matters more than reward *size* for early retention:
    frequent small wins build the daily habit.

We express each retention checkpoint as a baseline shaped by three levers, each
with diminishing or inverted-U returns so there is a genuine "sweet spot" to find.

Outputs are intentionally in familiar PM units (retention %, DAU count) so the
results are directly readable on a dashboard.
"""

from dataclasses import dataclass
from typing import List, Dict
import math


@dataclass
class RetentionConfig:
    """Levers that shape the retention curve."""

    # 1.0 == "balanced". <1 stingy, >1 generous. Drives an inverted-U on D30.
    reward_generosity: float = 1.0

    # Pacing: how fast players climb the progression curve.
    # 1.0 == balanced. Higher = faster ceiling = more late churn.
    progression_pacing: float = 1.0

    # How often rewards land (sessions/day with a meaningful reward).
    # Strong driver of early habit formation.
    reward_frequency: float = 3.0

    # Population & horizon
    new_users_per_day: int = 1_500
    days: int = 180
    starting_dau: int = 10_000


# --- Industry-ish anchor points for a healthy mid-core live game ---
# These are the retention rates the model returns at perfectly balanced settings.
BASE_D1 = 0.42
BASE_D7 = 0.20
BASE_D30 = 0.09


def _inverted_u(x: float, peak: float = 1.0, width: float = 0.6) -> float:
    """Return a 0..1 multiplier that peaks at `peak` and falls off either side.

    Used for generosity, where both too little and too much hurt retention.
    """
    return math.exp(-((x - peak) ** 2) / (2 * width ** 2))


def _diminishing(x: float, k: float = 1.2) -> float:
    """Saturating curve in 0..~1.3 for 'more is better but with diminishing returns'."""
    return 1 - math.exp(-x / k)


def retention_rates(cfg: RetentionConfig) -> Dict[str, float]:
    """Compute D1 / D7 / D30 retention from the design levers."""

    # Frequency mostly helps early habit (D1, D7), saturating quickly.
    freq_factor = _diminishing(cfg.reward_frequency, k=2.0)  # ~0..1

    # Generosity helps up to a point, then hurts (especially long-term).
    gen_factor_short = _inverted_u(cfg.reward_generosity, peak=1.1, width=0.8)
    gen_factor_long = _inverted_u(cfg.reward_generosity, peak=0.95, width=0.5)

    # Fast pacing feels great early but burns the content runway, hurting D30.
    pacing_short = 0.85 + 0.15 * min(cfg.progression_pacing, 1.5)
    pacing_long = _inverted_u(cfg.progression_pacing, peak=0.9, width=0.45)

    d1 = BASE_D1 * (0.6 + 0.5 * freq_factor) * (0.7 + 0.3 * gen_factor_short)
    d7 = BASE_D7 * (0.5 + 0.6 * freq_factor) * (0.6 + 0.4 * gen_factor_short) * pacing_short
    d30 = BASE_D30 * (0.5 + 0.5 * gen_factor_long) * pacing_long * (0.7 + 0.3 * freq_factor)

    # Clamp to sane ranges and keep monotonic ordering D1 >= D7 >= D30.
    d1 = min(max(d1, 0.0), 0.85)
    d7 = min(max(d7, 0.0), d1)
    d30 = min(max(d30, 0.0), d7)

    return {"D1": round(d1, 4), "D7": round(d7, 4), "D30": round(d30, 4)}


def _retention_curve(rates: Dict[str, float], horizon: int = 60) -> List[float]:
    """Interpolate a smooth daily retention curve through the D1/D7/D30 anchors.

    Uses a power-law decay r(n) = a * n^(-b), fit through the anchor points,
    which matches the shape of real retention curves well.
    """
    d1, d7, d30 = rates["D1"], rates["D7"], rates["D30"]
    curve = [1.0]  # day 0 = 100%
    # Fit b from D1 -> D30 (log-log slope), guard against zeros.
    if d1 > 0 and d30 > 0:
        b = -(math.log(d30) - math.log(d1)) / (math.log(30) - math.log(1))
    else:
        b = 0.7
    a = d1  # at n=1, r = a
    for n in range(1, horizon + 1):
        curve.append(a * (n ** -b))
    return curve


@dataclass
class RetentionState:
    day: int
    dau: int
    new_users: int
    retained_users: int


class RetentionModel:
    """Simulates DAU over time given a fixed acquisition rate and a retention curve."""

    def __init__(self, cfg: RetentionConfig):
        self.cfg = cfg
        self.rates = retention_rates(cfg)
        self.curve = _retention_curve(self.rates, horizon=cfg.days)

    def run(self) -> List[RetentionState]:
        """Cohort-based DAU simulation.

        Each day a new cohort arrives. Today's DAU = everyone still retained from
        every past cohort, plus today's new joiners. The starting_dau is treated
        as a single legacy cohort that decays along the same curve.
        """
        cfg = self.cfg
        history: List[RetentionState] = []
        cohort_sizes: List[int] = []  # index = age in days

        # Seed legacy population as one cohort assumed ~7 days old on average.
        legacy = cfg.starting_dau

        for day in range(cfg.days):
            cohort_sizes.append(cfg.new_users_per_day)

            # Sum retained users across all live cohorts.
            retained = 0
            for age, size in enumerate(reversed(cohort_sizes)):
                r = self.curve[min(age, len(self.curve) - 1)]
                retained += size * r

            # Decay the legacy block too.
            legacy_r = self.curve[min(day + 7, len(self.curve) - 1)]
            dau = int(retained + legacy * legacy_r)

            history.append(
                RetentionState(
                    day=day,
                    dau=dau,
                    new_users=cfg.new_users_per_day,
                    retained_users=int(retained),
                )
            )
        return history

    def summary(self) -> Dict[str, float]:
        out = dict(self.rates)
        out["D1_pct"] = round(self.rates["D1"] * 100, 1)
        out["D7_pct"] = round(self.rates["D7"] * 100, 1)
        out["D30_pct"] = round(self.rates["D30"] * 100, 1)
        return out


if __name__ == "__main__":
    cfg = RetentionConfig()
    model = RetentionModel(cfg)
    print("Retention rates:", model.summary())
    hist = model.run()
    print("Day 0 DAU:", hist[0].dau, "| Day", cfg.days - 1, "DAU:", hist[-1].dau)
