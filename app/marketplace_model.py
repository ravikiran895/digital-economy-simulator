"""
marketplace_model.py
--------------------
Simulates a player-to-player marketplace: listings, supply/demand price discovery,
rarity tiers, transaction fees (a key currency sink), and transaction volume.

Why a marketplace matters for the economy
------------------------------------------
A trading marketplace does three things at once:
  1. Creates *ownership* — items have resale value, which raises perceived worth.
  2. Acts as a *sink* — every trade pays a fee that removes currency from supply.
  3. Generates *engagement* — trading is its own retention loop.

But it can destabilise the economy: if inflation outpaces item supply, prices
spike; if too many items flood in, prices crash and the fee sink dries up.

Model summary
-------------
For each rarity tier we track supply (listings) and demand (buyers). Price moves
toward equilibrium via a simple tatonnement adjustment:

    price(t+1) = price(t) * (1 + k * (demand - supply) / scale) * (1 + inflation)

Transaction volume = min(supply, demand) * price. Fees on that volume feed back
into the economy engine as a sink.
"""

from dataclasses import dataclass, field
from typing import List, Dict
import math


@dataclass
class RarityTier:
    name: str
    base_price: float
    drop_rate: float          # relative share of items that are this rarity
    demand_weight: float      # relative buyer interest


DEFAULT_TIERS: List[RarityTier] = [
    RarityTier("Common", base_price=20.0, drop_rate=0.60, demand_weight=0.35),
    RarityTier("Rare", base_price=120.0, drop_rate=0.28, demand_weight=0.35),
    RarityTier("Epic", base_price=600.0, drop_rate=0.10, demand_weight=0.22),
    RarityTier("Legendary", base_price=3000.0, drop_rate=0.02, demand_weight=0.08),
]


@dataclass
class MarketConfig:
    days: int = 180
    active_traders: int = 4_000           # subset of DAU who trade
    listings_per_trader: float = 0.8      # new listings created per trader per day
    buy_intent_per_trader: float = 0.7    # purchase attempts per trader per day
    transaction_fee_rate: float = 0.05    # marketplace cut (sink)
    price_elasticity: float = 0.08        # how fast prices chase imbalance
    demand_shock_amplitude: float = 0.15  # seasonal demand wobble
    tiers: List[RarityTier] = field(default_factory=lambda: list(DEFAULT_TIERS))


@dataclass
class MarketState:
    day: int
    transactions: int
    volume: float                 # coin value traded
    fees_collected: float         # the sink
    avg_price_index: float        # index, 1.0 at day 0
    prices: Dict[str, float]
    liquidity: float              # fraction of demand actually filled


class MarketplaceModel:
    """Daily supply/demand simulation across rarity tiers."""

    def __init__(self, cfg: MarketConfig):
        self.cfg = cfg
        self.prices = {t.name: t.base_price for t in cfg.tiers}
        self._base_avg = self._weighted_avg_price()

    def _weighted_avg_price(self) -> float:
        c = self.cfg
        return sum(self.prices[t.name] * t.demand_weight for t in c.tiers)

    def run(self, inflation_series: List[float] | None = None) -> List[MarketState]:
        """Run the marketplace.

        Parameters
        ----------
        inflation_series:
            Optional per-day inflation (fractions) from the EconomyEngine. Prices
            ride on top of inflation so the marketplace reflects the wider economy.
        """
        c = self.cfg
        history: List[MarketState] = []

        for day in range(c.days):
            inflation = 0.0
            if inflation_series and day < len(inflation_series):
                inflation = inflation_series[day]

            # Seasonal demand wobble (a soft sine cycle ~30 days).
            shock = 1 + c.demand_shock_amplitude * math.sin(2 * math.pi * day / 30.0)

            total_transactions = 0
            total_volume = 0.0
            filled = 0.0
            wanted = 0.0

            for t in c.tiers:
                supply = c.active_traders * c.listings_per_trader * t.drop_rate

                # Demand falls as the real price rises above the (inflation-adjusted)
                # base — basic price elasticity of demand. This is what lets the
                # market settle at an equilibrium instead of compounding forever.
                fair_price = t.base_price * (1 + inflation)
                price_ratio = self.prices[t.name] / max(fair_price, 1e-9)
                demand_elasticity = price_ratio ** -0.8  # >1 price -> <1 demand
                demand = (
                    c.active_traders * c.buy_intent_per_trader
                    * t.demand_weight * shock * demand_elasticity
                )

                # Price discovery: excess demand pushes price up, excess supply down.
                imbalance = (demand - supply) / max(supply + demand, 1.0)
                price = self.prices[t.name] * (1 + c.price_elasticity * imbalance)
                price *= (1 + inflation)               # ride wider inflation
                price = max(price, t.base_price * 0.2)  # floor: items keep some worth
                self.prices[t.name] = price

                trades = min(supply, demand)
                total_transactions += trades
                total_volume += trades * price
                filled += trades
                wanted += demand

            fees = total_volume * c.transaction_fee_rate
            avg_index = self._weighted_avg_price() / max(self._base_avg, 1e-9)
            liquidity = filled / max(wanted, 1e-9)

            history.append(
                MarketState(
                    day=day,
                    transactions=int(total_transactions),
                    volume=round(total_volume, 2),
                    fees_collected=round(fees, 2),
                    avg_price_index=round(avg_index, 4),
                    prices={k: round(v, 2) for k, v in self.prices.items()},
                    liquidity=round(liquidity, 4),
                )
            )

        return history

    @staticmethod
    def summary(history: List[MarketState], active_traders: int) -> Dict[str, float]:
        if not history:
            return {}
        total_volume = sum(h.volume for h in history)
        total_fees = sum(h.fees_collected for h in history)
        total_tx = sum(h.transactions for h in history)
        avg_liquidity = sum(h.liquidity for h in history) / len(history)
        price_drift = history[-1].avg_price_index - history[0].avg_price_index
        # Volatility: std dev of day-over-day price index change.
        deltas = [
            history[i].avg_price_index - history[i - 1].avg_price_index
            for i in range(1, len(history))
        ]
        mean_d = sum(deltas) / len(deltas) if deltas else 0.0
        var = sum((d - mean_d) ** 2 for d in deltas) / len(deltas) if deltas else 0.0
        return {
            "total_transactions": int(total_tx),
            "total_volume": round(total_volume, 0),
            "total_fee_sink": round(total_fees, 0),
            "avg_daily_volume_per_trader": round(total_volume / len(history) / max(active_traders, 1), 2),
            "avg_liquidity_pct": round(avg_liquidity * 100, 1),
            "price_drift_pct": round(price_drift * 100, 1),
            "price_volatility": round(math.sqrt(var), 4),
        }

    def avg_volume_per_dau(self, history: List[MarketState], dau: int) -> float:
        """Mean daily traded coin value per DAU, for feeding the economy fee sink."""
        if not history or dau <= 0:
            return 0.0
        return sum(h.volume for h in history) / len(history) / dau


if __name__ == "__main__":
    cfg = MarketConfig()
    mkt = MarketplaceModel(cfg)
    hist = mkt.run()
    print("Marketplace summary:", MarketplaceModel.summary(hist, cfg.active_traders))
