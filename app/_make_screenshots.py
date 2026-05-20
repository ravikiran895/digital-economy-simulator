"""Generate dashboard/screenshot PNGs using real simulation output (new model)."""
import os, sys
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

sys.path.append(os.path.dirname(__file__))
from economy_engine import EconomyConfig, EconomyEngine, to_records
from retention_model import RetentionConfig, RetentionModel
from marketplace_model import MarketConfig, MarketplaceModel
from monetization_model import MonetizationConfig, compute
from scenarios import PRESETS

OUT = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(OUT, exist_ok=True)
P = {"faucet":"#3b82f6","sink":"#ef4444","net":"#f59e0b","good":"#10b981",
     "accent":"#8b5cf6","muted":"#94a3b8","ink":"#1e293b"}
plt.rcParams.update({"axes.spines.top":False,"axes.spines.right":False,
                     "axes.grid":True,"grid.alpha":0.22,"font.size":9})

def run_scenario(p, days=180, dau=10000):
    mkt = MarketplaceModel(MarketConfig(days=days, active_traders=int(dau*0.4), transaction_fee_rate=p.fee_rate))
    mh = mkt.run(); vol = mkt.avg_volume_per_dau(mh, dau)
    eh = EconomyEngine(EconomyConfig(starting_dau=dau, days=days, daily_login_reward=p.daily_login_reward,
        quest_reward=p.quest_reward, reward_generosity=p.reward_generosity, cosmetic_spend=p.cosmetic_spend,
        upgrade_spend=p.upgrade_spend, marketplace_fee_rate=p.fee_rate, starting_supply_per_dau=p.starting_supply,
        equilibrium_supply_per_dau=p.equilibrium_supply)).run(vol)
    rh = RetentionModel(RetentionConfig(reward_generosity=p.reward_generosity, progression_pacing=p.progression_pacing,
        reward_frequency=p.reward_frequency, days=days, starting_dau=dau)).run()
    return pd.DataFrame(to_records(eh)), pd.DataFrame([r.__dict__ for r in rh]), mh, eh, rh, vol

healthy = PRESETS["Healthy Economy"]
df, rdf, mh, eh, rh, vol = run_scenario(healthy)
ek = EconomyEngine.health_summary(eh)
ret = RetentionModel(RetentionConfig(reward_generosity=healthy.reward_generosity,
    progression_pacing=healthy.progression_pacing, reward_frequency=healthy.reward_frequency,
    days=180, starting_dau=10000)).summary()
mon = compute(MonetizationConfig(whale_share=healthy.whale_share_pct/100, whale_spend=healthy.whale_spend,
    casual_spend=healthy.casual_spend), 10000, currency_sink_per_dau=eh[-1].sink_per_dau,
    currency_faucet_per_dau=eh[-1].faucet_per_dau)
mkpis = MarketplaceModel.summary(mh, int(10000*0.4))

# --- dashboard.png : KPI strip + 4 panels ---
fig = plt.figure(figsize=(13, 8)); fig.patch.set_facecolor("white")
gs = GridSpec(3, 2, height_ratios=[0.55, 1, 1], hspace=0.5, wspace=0.2)
axk = fig.add_subplot(gs[0, :]); axk.axis("off")
axk.text(0, 1.0, "Digital Economy Systems Simulator", fontsize=17, fontweight="bold", color=P["ink"], va="top")
axk.text(0, 0.62, "Product-strategy sandbox · Health: STABLE", fontsize=11, color=P["good"], va="top")
cards = [("30-Day Inflation", f"{ek['inflation_30d_pct']:+.1f}%", P["accent"]),
         ("Sink Efficiency", f"{ek['avg_sink_efficiency']:.2f}", P["net"]),
         ("D7 Retention", f"{ret['D7_pct']:.0f}%", P["faucet"]),
         ("ARPDAU", f"${mon.arpdau:.3f}", P["good"]),
         ("Whale Rev %", f"{mon.whale_revenue_share:.0f}%", P["sink"])]
for i,(lab,val,c) in enumerate(cards):
    x = 0.02 + i*0.20
    axk.text(x, 0.18, val, fontsize=18, fontweight="bold", color=c, va="bottom")
    axk.text(x, -0.18, lab, fontsize=8.5, color=P["muted"], va="bottom")
a1 = fig.add_subplot(gs[1,0])
a1.plot(df.day, df.faucet_per_dau, color=P["faucet"], label="Faucet/DAU")
a1.plot(df.day, df.sink_per_dau, color=P["sink"], label="Sink/DAU")
a1.fill_between(df.day, df.faucet_per_dau, df.sink_per_dau, color=P["net"], alpha=0.15)
a1.set_title("Faucet vs Sink (per DAU/day)", fontweight="bold"); a1.set_xlabel("Day"); a1.set_ylabel("Coins"); a1.legend(fontsize=8)
a2 = fig.add_subplot(gs[1,1])
a2.plot(df.day, df.price_level, color=P["accent"]); a2.axhline(1.0, color=P["muted"], ls="--", lw=1)
a2.set_title("Inflation: price level index", fontweight="bold"); a2.set_xlabel("Day"); a2.set_ylabel("Price (1.0=eq)")
a3 = fig.add_subplot(gs[2,0])
a3.plot(rdf.day, rdf.dau, color=P["good"]); a3.set_title("DAU over time", fontweight="bold"); a3.set_xlabel("Day"); a3.set_ylabel("Active users")
a4 = fig.add_subplot(gs[2,1])
a4.plot(df.day, df.sink_efficiency, color=P["net"]); a4.axhspan(0.90,1.12, color=P["good"], alpha=0.12); a4.axhline(1.0,color=P["muted"],ls="--",lw=1)
a4.set_title("Sink efficiency (healthy band shaded)", fontweight="bold"); a4.set_xlabel("Day"); a4.set_ylabel("Ratio")
fig.savefig(os.path.join(OUT,"dashboard.png"), dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
print("saved dashboard.png")

# --- economy_chart.png : scenario comparison ---
fig, (axa, axb) = plt.subplots(1, 2, figsize=(13, 4.8)); fig.patch.set_facecolor("white")
for name, color in [("Healthy Economy", P["good"]), ("Inflation Crisis", P["sink"]), ("Deflationary Squeeze", P["faucet"])]:
    d,_,_,_,_,_ = run_scenario(PRESETS[name])
    axa.plot(d.day, d.price_level, label=name, color=color)
axa.axhline(1.0, color=P["muted"], ls="--", lw=1)
axa.set_title("Price level across scenarios", fontweight="bold"); axa.set_xlabel("Day"); axa.set_ylabel("Price index"); axa.legend(fontsize=9)
# Retention inverted-U
gens = np.linspace(0.3, 2.0, 30); d7s=[]; d30s=[]
for g in gens:
    r = RetentionModel(RetentionConfig(reward_generosity=g, days=180, starting_dau=10000)).summary()
    d7s.append(r["D7"]*100); d30s.append(r["D30"]*100)
axb.plot(gens, d7s, label="D7", color=P["net"]); axb.plot(gens, d30s, label="D30", color=P["sink"])
axb.set_title("Retention vs generosity (inverted-U)", fontweight="bold"); axb.set_xlabel("Generosity ×"); axb.set_ylabel("Retention %"); axb.legend(fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(OUT,"economy_chart.png"), dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)
print("saved economy_chart.png")
