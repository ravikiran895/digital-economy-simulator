"""
simulator.py — Digital Economy Systems Simulator
=================================================
A product-strategy sandbox for digital economies.

Run locally:
    python -m streamlit run app/simulator.py

Layout (top to bottom):
  1. Scenario presets        — one-click economy archetypes
  2. Economy Health banner   — 🟢 / 🟠 / 🔴 status with reasons
  3. KPI card row            — the numbers a PM puts on the wall
  4. Product Insights panel  — written analysis of the current state
  5. Detail tabs             — economy, retention, marketplace, monetization

All four models (economy / retention / marketplace / monetization) are coupled:
marketplace fees feed the economy's sink, the economy's faucet/sink feeds the
monetization sink-efficiency metric, and generosity drives both economy and
retention.
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

sys.path.append(os.path.dirname(__file__))

from economy_engine import EconomyConfig, EconomyEngine, to_records
from retention_model import RetentionConfig, RetentionModel
from marketplace_model import MarketConfig, MarketplaceModel
from monetization_model import MonetizationConfig, compute as compute_monetization
from scenarios import PRESETS, generate_insights


# --------------------------------------------------------------------------- #
# Page config & styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Digital Economy Systems Simulator",
    page_icon="🪙",
    layout="wide",
)

P = {
    "faucet": "#3b82f6", "sink": "#ef4444", "net": "#f59e0b",
    "good": "#10b981", "accent": "#8b5cf6", "muted": "#94a3b8", "ink": "#1e293b",
}

st.markdown("""
<style>
  .block-container {padding-top: 2rem; padding-bottom: 2rem;}
  .kpi-card {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
  }
  .kpi-label {font-size: 0.72rem; letter-spacing: .04em; text-transform: uppercase;
              color: #64748b; font-weight: 600; margin-bottom: 4px;}
  .kpi-value {font-size: 1.7rem; font-weight: 700; color: #0f172a; line-height: 1.1;}
  .kpi-sub {font-size: 0.74rem; color: #94a3b8; margin-top: 2px;}
  .health-banner {border-radius: 16px; padding: 18px 22px; margin: 4px 0 6px 0;
                  border: 1px solid; }
  .insight-card {background:#f8fafc; border-left: 4px solid #8b5cf6; border-radius: 8px;
                 padding: 12px 16px; margin-bottom: 10px; font-size: 0.92rem; color:#1e293b;}
</style>
""", unsafe_allow_html=True)

plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.22, "font.size": 9, "figure.autolayout": True,
})


# --------------------------------------------------------------------------- #
# Session state from presets
# --------------------------------------------------------------------------- #
DEFAULT = PRESETS["Healthy Economy"]

def apply_preset(name: str):
    p = PRESETS[name]
    st.session_state.update({
        "generosity": p.reward_generosity,
        "login_reward": p.daily_login_reward,
        "quest_reward": p.quest_reward,
        "cosmetic": p.cosmetic_spend,
        "upgrade": p.upgrade_spend,
        "fee_rate": p.fee_rate,
        "start_supply": p.starting_supply,
        "eq_supply": p.equilibrium_supply,
        "pacing": p.progression_pacing,
        "frequency": p.reward_frequency,
        "whale_share_pct": p.whale_share_pct,
        "whale_spend": p.whale_spend,
        "casual_spend": p.casual_spend,
    })

# Initialise once.
for key, val in {
    "generosity": DEFAULT.reward_generosity, "login_reward": DEFAULT.daily_login_reward,
    "quest_reward": DEFAULT.quest_reward, "cosmetic": DEFAULT.cosmetic_spend,
    "upgrade": DEFAULT.upgrade_spend, "fee_rate": DEFAULT.fee_rate,
    "start_supply": DEFAULT.starting_supply, "eq_supply": DEFAULT.equilibrium_supply,
    "pacing": DEFAULT.progression_pacing, "frequency": DEFAULT.reward_frequency,
    "whale_share_pct": DEFAULT.whale_share_pct, "whale_spend": DEFAULT.whale_spend,
    "casual_spend": DEFAULT.casual_spend,
}.items():
    st.session_state.setdefault(key, val)


# --------------------------------------------------------------------------- #
# Header + positioning
# --------------------------------------------------------------------------- #
st.title("🪙 Digital Economy Systems Simulator")
st.markdown(
    "**A product-strategy sandbox for digital economies.** Pick a scenario or move "
    "the levers, and watch inflation, retention, marketplace health, and revenue "
    "respond — with written analysis of *why*."
)

# --------------------------------------------------------------------------- #
# Scenario presets
# --------------------------------------------------------------------------- #
st.markdown("##### Scenario presets")
preset_names = list(PRESETS.keys())
cols = st.columns(len(preset_names))
for col, name in zip(cols, preset_names):
    p = PRESETS[name]
    if col.button(f"{p.emoji} {name}", use_container_width=True, help=p.blurb):
        apply_preset(name)
        st.rerun()


# --------------------------------------------------------------------------- #
# Sidebar levers (bound to session state)
# --------------------------------------------------------------------------- #
sb = st.sidebar
sb.title("Economy Levers")
sb.caption("Fine-tune anything. Presets above set these in one click.")

sb.subheader("Population")
dau = sb.slider("Starting DAU", 1_000, 100_000, 10_000, 1_000)
days = sb.slider("Simulation days", 30, 365, 180, 30)

sb.subheader("Faucets (currency in)")
sb.slider("Reward generosity ×", 0.3, 2.0, key="generosity", step=0.05)
sb.slider("Daily login reward", 0, 400, key="login_reward", step=5)
sb.slider("Quest reward", 0, 400, key="quest_reward", step=5)

sb.subheader("Sinks (currency out)")
sb.slider("Cosmetic spend", 0, 300, key="cosmetic", step=5)
sb.slider("Upgrade / progression spend", 0, 300, key="upgrade", step=5)
sb.slider("Marketplace fee rate", 0.0, 0.20, key="fee_rate", step=0.01)

sb.subheader("Currency supply")
sb.slider("Starting supply / DAU", 1_000, 15_000, key="start_supply", step=500)
sb.slider("Equilibrium supply / DAU", 1_000, 15_000, key="eq_supply", step=500)

sb.subheader("Retention design")
sb.slider("Progression pacing ×", 0.5, 2.0, key="pacing", step=0.05)
sb.slider("Reward frequency (per day)", 1.0, 8.0, key="frequency", step=0.5)
sb.slider("New users / day", 0, 10_000, 1_500, 100, key="new_users")

sb.subheader("Monetization")
sb.slider("Whale share of DAU (%)", 0.5, 10.0, key="whale_share_pct", step=0.5)
sb.slider("Whale daily spend ($)", 1.0, 50.0, key="whale_spend", step=1.0)
sb.slider("Casual daily spend ($)", 0.0, 2.0, key="casual_spend", step=0.05)


# --------------------------------------------------------------------------- #
# Run the coupled models
# --------------------------------------------------------------------------- #
s = st.session_state

mkt_cfg = MarketConfig(days=days, active_traders=max(1, int(dau * 0.4)),
                       transaction_fee_rate=s.fee_rate)
mkt = MarketplaceModel(mkt_cfg)
mkt_hist = mkt.run()
vol_per_dau = mkt.avg_volume_per_dau(mkt_hist, dau)
mkt_kpis = MarketplaceModel.summary(mkt_hist, mkt_cfg.active_traders)

econ_cfg = EconomyConfig(
    starting_dau=dau, days=days,
    daily_login_reward=s.login_reward, quest_reward=s.quest_reward,
    reward_generosity=s.generosity, cosmetic_spend=s.cosmetic,
    upgrade_spend=s.upgrade, marketplace_fee_rate=s.fee_rate,
    starting_supply_per_dau=s.start_supply, equilibrium_supply_per_dau=s.eq_supply,
)
econ_hist = EconomyEngine(econ_cfg).run(marketplace_volume_per_dau=vol_per_dau)
econ_df = pd.DataFrame(to_records(econ_hist))
econ_kpis = EconomyEngine.health_summary(econ_hist)
fee_per_dau = vol_per_dau * s.fee_rate

ret_cfg = RetentionConfig(
    reward_generosity=s.generosity, progression_pacing=s.pacing,
    reward_frequency=s.frequency, new_users_per_day=s.new_users,
    days=days, starting_dau=dau,
)
ret = RetentionModel(ret_cfg)
ret_hist = ret.run()
ret_df = pd.DataFrame([r.__dict__ for r in ret_hist])
ret_rates = ret.summary()
window = min(30, len(ret_hist) - 1)
dau_trend = ((ret_hist[-1].dau - ret_hist[-1 - window].dau)
             / max(ret_hist[-1 - window].dau, 1) * 100) if window > 0 else 0.0

mon_cfg = MonetizationConfig(
    whale_share=s.whale_share_pct / 100, whale_spend=s.whale_spend,
    casual_spend=s.casual_spend,
)
mon = compute_monetization(
    mon_cfg, dau=dau,
    currency_sink_per_dau=econ_hist[-1].sink_per_dau,
    currency_faucet_per_dau=econ_hist[-1].faucet_per_dau,
)

# Health classification
emoji, label, reasons = EconomyEngine.classify_health(
    econ_kpis["avg_sink_efficiency"], econ_kpis["inflation_30d_pct"], dau_trend,
)


# --------------------------------------------------------------------------- #
# Health banner
# --------------------------------------------------------------------------- #
banner_colors = {
    "🟢": ("#dcfce7", "#16a34a", "#14532d"),
    "🟠": ("#fef3c7", "#d97706", "#7c2d12"),
    "🔴": ("#fee2e2", "#dc2626", "#7f1d1d"),
}
bg, border, text = banner_colors[emoji]
reasons_html = " · ".join(reasons[:2])
st.markdown(
    f"""<div class="health-banner" style="background:{bg};border-color:{border};">
    <span style="font-size:1.4rem;font-weight:700;color:{text};">{emoji} Economy Health: {label}</span>
    <div style="color:{text};opacity:.85;margin-top:4px;font-size:0.9rem;">{reasons_html}</div>
    </div>""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# KPI card row
# --------------------------------------------------------------------------- #
def kpi(col, label, value, sub=""):
    col.markdown(
        f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div></div>""",
        unsafe_allow_html=True,
    )

k = st.columns(5)
kpi(k[0], "30-Day Inflation", f"{econ_kpis['inflation_30d_pct']:+.1f}%",
    f"annualised {econ_kpis['annualised_inflation_pct']:+.0f}%")
kpi(k[1], "Sink Efficiency", f"{econ_kpis['avg_sink_efficiency']:.2f}",
    "sinks ÷ faucets · ~1.0 ideal")
kpi(k[2], "D7 Retention", f"{ret_rates['D7_pct']:.0f}%",
    f"D1 {ret_rates['D1_pct']:.0f}% · D30 {ret_rates['D30_pct']:.0f}%")
kpi(k[3], "ARPDAU", f"${mon.arpdau:.3f}",
    f"{mon.payer_conversion*100:.1f}% pay · {mon.whale_revenue_share:.0f}% whales")
kpi(k[4], "Marketplace Velocity", f"{mkt_kpis['avg_liquidity_pct']:.0f}%",
    f"liquidity · vol {mkt_kpis['price_volatility']:.3f}")


# --------------------------------------------------------------------------- #
# Product Insights panel
# --------------------------------------------------------------------------- #
st.markdown("### 🧠 Product Insights")
insights = generate_insights(
    sink_efficiency=econ_kpis["avg_sink_efficiency"],
    inflation_30d_pct=econ_kpis["inflation_30d_pct"],
    faucet_per_dau=econ_hist[-1].faucet_per_dau,
    sink_per_dau=econ_hist[-1].sink_per_dau,
    fee_per_dau=fee_per_dau,
    d7_pct=ret_rates["D7_pct"], d30_pct=ret_rates["D30_pct"],
    reward_generosity=s.generosity,
    arpdau=mon.arpdau, whale_share_pct=s.whale_share_pct,
    whale_revenue_pct=mon.whale_revenue_share,
    liquidity_pct=mkt_kpis["avg_liquidity_pct"],
    velocity=econ_hist[-1].velocity,
)
for ins in insights:
    st.markdown(f'<div class="insight-card">{ins}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Detail tabs
# --------------------------------------------------------------------------- #
st.markdown("### 📊 Detailed views")
tab1, tab2, tab3, tab4 = st.tabs([
    "💧 Economy", "📈 Retention", "🛒 Marketplace", "💳 Monetization",
])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(econ_df.day, econ_df.faucet_per_dau, color=P["faucet"], label="Faucet/DAU")
        ax.plot(econ_df.day, econ_df.sink_per_dau, color=P["sink"], label="Sink/DAU")
        ax.fill_between(econ_df.day, econ_df.faucet_per_dau, econ_df.sink_per_dau,
                        color=P["net"], alpha=0.15)
        ax.set_title("Faucet vs Sink (per DAU/day)", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Coins"); ax.legend(fontsize=8)
        st.pyplot(fig); plt.close(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(econ_df.day, econ_df.price_level, color=P["accent"])
        ax.axhline(1.0, color=P["muted"], ls="--", lw=1, label="equilibrium")
        ax.set_title("Price level (inflation index)", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Price (1.0 = equilibrium)"); ax.legend(fontsize=8)
        st.pyplot(fig); plt.close(fig)
    c3, c4 = st.columns(2)
    with c3:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(econ_df.day, econ_df.supply_per_dau, color=P["faucet"])
        ax.axhline(s.eq_supply, color=P["muted"], ls="--", lw=1, label="equilibrium")
        ax.set_title("Currency held per player", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Coins/DAU"); ax.legend(fontsize=8)
        st.pyplot(fig); plt.close(fig)
    with c4:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(econ_df.day, econ_df.sink_efficiency, color=P["net"])
        ax.axhspan(0.90, 1.12, color=P["good"], alpha=0.12, label="healthy band")
        ax.axhline(1.0, color=P["muted"], ls="--", lw=1)
        ax.set_title("Sink efficiency over time", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Ratio"); ax.legend(fontsize=8)
        st.pyplot(fig); plt.close(fig)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(ret_df.day, ret_df.dau, color=P["accent"])
        ax.set_title("DAU over time", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Active users")
        st.pyplot(fig); plt.close(fig)
    with c2:
        gens = np.linspace(0.3, 2.0, 25)
        d1s, d7s, d30s = [], [], []
        for g in gens:
            r = RetentionModel(RetentionConfig(
                reward_generosity=g, progression_pacing=s.pacing,
                reward_frequency=s.frequency, days=days, starting_dau=dau,
                new_users_per_day=s.new_users)).summary()
            d1s.append(r["D1"] * 100); d7s.append(r["D7"] * 100); d30s.append(r["D30"] * 100)
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(gens, d1s, label="D1", color=P["faucet"])
        ax.plot(gens, d7s, label="D7", color=P["net"])
        ax.plot(gens, d30s, label="D30", color=P["sink"])
        ax.axvline(s.generosity, color=P["muted"], ls="--", lw=1, label="current")
        ax.set_title("Retention vs reward generosity", fontweight="bold")
        ax.set_xlabel("Generosity ×"); ax.set_ylabel("Retention %"); ax.legend(fontsize=8)
        st.pyplot(fig); plt.close(fig)
    st.caption("Note the inverted-U: D30 peaks near balanced generosity and *falls* "
               "when players are over-rewarded — that's progression fatigue in the data.")

with tab3:
    mkt_df = pd.DataFrame([{
        "day": m.day, "transactions": m.transactions, "fees": m.fees_collected,
        "liquidity": m.liquidity, **{f"price_{kk}": vv for kk, vv in m.prices.items()},
    } for m in mkt_hist])
    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(mkt_df.day, mkt_df.transactions, color=P["faucet"])
        ax.set_title("Daily transactions", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Trades")
        st.pyplot(fig); plt.close(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        for tier, color in zip(["Common", "Rare", "Epic", "Legendary"],
                               [P["muted"], P["faucet"], P["accent"], P["net"]]):
            ax.plot(mkt_df.day, mkt_df[f"price_{tier}"], label=tier, color=color)
        ax.set_yscale("log")
        ax.set_title("Item prices by rarity (log)", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Price"); ax.legend(fontsize=7)
        st.pyplot(fig); plt.close(fig)
    c3, c4 = st.columns(2)
    with c3:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(mkt_df.day, mkt_df.liquidity * 100, color=P["good"])
        ax.set_ylim(0, 105)
        ax.set_title("Market liquidity", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Buy intent filled (%)")
        st.pyplot(fig); plt.close(fig)
    with c4:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(mkt_df.day, mkt_df.fees.cumsum(), color=P["sink"])
        ax.set_title("Cumulative fee sink", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Coins removed")
        st.pyplot(fig); plt.close(fig)

with tab4:
    event = st.radio("Active monetization event", [
        "None", "Seasonal offer (revenue+faucet)",
        "Premium bundle (revenue+sink)", "Sink event (deflationary)",
    ], horizontal=True)
    mult, extra_faucet, extra_sink = 1.0, 0.0, 0.0
    if event.startswith("Seasonal"):
        mult, extra_faucet = 1.6, 80.0
    elif event.startswith("Premium"):
        mult, extra_sink = 1.9, 30.0
    elif event.startswith("Sink"):
        mult, extra_sink = 1.1, 120.0

    ev_cfg = EconomyConfig(
        starting_dau=dau, days=days,
        daily_login_reward=s.login_reward, quest_reward=s.quest_reward,
        event_reward=extra_faucet, reward_generosity=s.generosity,
        cosmetic_spend=s.cosmetic, upgrade_spend=s.upgrade + extra_sink,
        marketplace_fee_rate=s.fee_rate,
        starting_supply_per_dau=s.start_supply, equilibrium_supply_per_dau=s.eq_supply,
    )
    ev_hist = EconomyEngine(ev_cfg).run(marketplace_volume_per_dau=vol_per_dau)
    ev_mon = compute_monetization(
        mon_cfg, dau=dau, event_revenue_mult=mult,
        currency_sink_per_dau=ev_hist[-1].sink_per_dau,
        currency_faucet_per_dau=ev_hist[-1].faucet_per_dau,
    )

    m = st.columns(4)
    kpi(m[0], "Event ARPDAU", f"${ev_mon.arpdau:.3f}",
        f"{(ev_mon.arpdau/mon.arpdau-1)*100:+.0f}% vs base" if mon.arpdau else "")
    kpi(m[1], "Daily revenue", f"${ev_mon.daily_revenue:,.0f}", "ARPDAU × DAU")
    kpi(m[2], "Payer conversion", f"{ev_mon.payer_conversion*100:.1f}%", "share of DAU paying")
    kpi(m[3], "Sink-monetization eff.", f"{ev_mon.sink_monetization_efficiency:.2f}",
        "sink ÷ faucet during event")

    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(6, 3.8))
        labels = ["Whales", "Dolphins", "Casual"]
        vals = [ev_mon.whale_revenue, ev_mon.dolphin_revenue, ev_mon.casual_revenue]
        ax.bar(labels, vals, color=[P["accent"], P["faucet"], P["muted"]])
        for i, v in enumerate(vals):
            ax.text(i, v, f"${v:,.0f}", ha="center", va="bottom", fontsize=8)
        ax.set_title("Daily revenue by cohort", fontweight="bold")
        ax.set_ylabel("Revenue ($)")
        st.pyplot(fig); plt.close(fig)
        st.caption(f"Whales are **{s.whale_share_pct:.1f}%** of players but "
                   f"**{ev_mon.whale_revenue_share:.0f}%** of revenue.")
    with c2:
        base_price = econ_df.price_level
        ev_price = pd.Series([e.price_level for e in ev_hist])
        fig, ax = plt.subplots(figsize=(6, 3.8))
        ax.plot(econ_df.day, base_price, label="No event", color=P["muted"])
        ax.plot(econ_df.day, ev_price, label=event.split(" (")[0], color=P["sink"])
        ax.axhline(1.0, color=P["muted"], ls=":", lw=1)
        ax.set_title("Inflation impact of the event", fontweight="bold")
        ax.set_xlabel("Day"); ax.set_ylabel("Price index"); ax.legend(fontsize=8)
        st.pyplot(fig); plt.close(fig)
    st.caption("The tradeoff: a *Seasonal offer* lifts revenue but injects currency "
               "(inflationary). A *Sink event* earns less but protects reward value. "
               "Good LiveOps calendars alternate the two.")

st.divider()
st.caption("Digital Economy Systems Simulator · Streamlit · Pandas · Matplotlib · "
           "models are illustrative, tuned for product reasoning not forecasting.")
