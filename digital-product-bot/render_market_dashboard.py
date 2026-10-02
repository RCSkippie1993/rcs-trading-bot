from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import bot
import phase2
import phase3_copy
from market_probe import research_market_data

st.set_page_config(
    page_title="Digital Product Market Radar",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 3rem;}
      [data-testid="stMetricValue"] {font-size: 2rem;}
      .market-note {
        border: 1px solid rgba(128,128,128,.28);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 1rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def researched_market(phrase: str, config: dict) -> phase2.MarketEvidence:
    return phase2.MarketEvidence(**research_market_data(phrase, config))


@st.cache_data(ttl=900, show_spinner=False)
def run_market_scan(
    research_limit: int,
    create_threshold: int,
    watch_threshold: int,
    minimum_score: int,
) -> dict:
    config = bot.load_config()
    config = dict(config)
    config["phase2_research_candidates"] = research_limit
    config["create_threshold"] = create_threshold
    config["watch_threshold"] = watch_threshold
    config["minimum_score"] = minimum_score

    signals, source_errors = bot.discover_signals(config)
    raw = bot.build_opportunities(signals, config)
    clustered = phase2.cluster_opportunities(
        raw,
        float(config.get("duplicate_similarity_threshold", 0.78)),
    )

    decisions: list[phase2.Decision] = []
    for opportunity in clustered[:research_limit]:
        evidence = researched_market(opportunity.phrase, config)
        decisions.append(phase2.classify(opportunity, evidence, config))

    decisions.sort(key=lambda d: (d.commercial_score, d.base_score), reverse=True)

    return {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "signals_seen": len(signals),
        "raw_opportunities": len(raw),
        "distinct_families": len(clustered),
        "researched": len(decisions),
        "source_errors": source_errors,
        "decisions": [asdict(d) for d in decisions],
    }


def decision_frame(report: dict) -> pd.DataFrame:
    rows = []
    for item in report["decisions"]:
        evidence = item["market_evidence"]
        rows.append(
            {
                "Decision": item["decision"],
                "Commercial": item["commercial_score"],
                "Demand / Build": item["base_score"],
                "Product": phase3_copy.human_product_name(item["phrase"]),
                "Search Phrase": item["phrase"],
                "Type": item["kind"],
                "Signals": item["signal_count"],
                "Etsy Proxy": evidence["platform_hits"].get("etsy", 0),
                "Gumroad Proxy": evidence["platform_hits"].get("gumroad", 0),
                "Median Price USD": evidence.get("median_price_usd"),
                "Source Count": len(item.get("sources", [])),
                "Research Warnings": len(evidence.get("errors", [])),
            }
        )
    return pd.DataFrame(rows)


st.title("Digital Product Market Radar")
st.caption(
    "Live demand discovery and marketplace opportunity scoring for digital products. "
    "This dashboard researches opportunities only — it does not approve, create, list or publish products."
)

with st.sidebar:
    st.header("Scan settings")
    research_limit = st.slider("Ideas to research", min_value=6, max_value=30, value=12, step=1)
    create_threshold = st.slider("CREATE threshold", min_value=60, max_value=90, value=70)
    watch_threshold = st.slider("WATCH threshold", min_value=45, max_value=75, value=58)
    minimum_score = st.slider("Minimum demand/build score", min_value=45, max_value=80, value=62)
    if watch_threshold >= create_threshold:
        st.warning("WATCH should be lower than CREATE.")
    run_now = st.button("Run live market scan", type="primary", use_container_width=True)
    refresh = st.button("Clear cache & rescan", use_container_width=True)

if refresh:
    st.cache_data.clear()
    run_now = True

if "report" not in st.session_state:
    st.session_state["report"] = None

if run_now:
    if watch_threshold >= create_threshold:
        st.error("Set the WATCH threshold below the CREATE threshold before scanning.")
    else:
        with st.spinner("Scanning demand signals and marketplace evidence..."):
            st.session_state["report"] = run_market_scan(
                research_limit,
                create_threshold,
                watch_threshold,
                minimum_score,
            )

report = st.session_state["report"]

if not report:
    st.info(
        "Select the scan depth in the sidebar and click **Run live market scan**. "
        "A 12-idea scan normally provides a useful first market view."
    )
    st.stop()

df = decision_frame(report)
create_count = int((df["Decision"] == "CREATE").sum()) if not df.empty else 0
watch_count = int((df["Decision"] == "WATCH").sum()) if not df.empty else 0
reject_count = int((df["Decision"] == "REJECT").sum()) if not df.empty else 0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Demand signals", report["signals_seen"])
m2.metric("Raw ideas", report["raw_opportunities"])
m3.metric("Distinct markets", report["distinct_families"])
m4.metric("CREATE", create_count)
m5.metric("WATCH", watch_count)
m6.metric("REJECT", reject_count)

st.markdown(
    f'<div class="market-note"><b>Last scan:</b> {report["run_at_utc"]} &nbsp; '
    f'<b>Researched:</b> {report["researched"]} distinct opportunities.</div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Opportunity ranking", "Market segments", "Evidence", "Source health"]
)

with tab1:
    st.subheader("Ranked opportunities")
    if df.empty:
        st.warning("No opportunities were returned.")
    else:
        decision_filter = st.multiselect(
            "Show decisions",
            ["CREATE", "WATCH", "REJECT"],
            default=["CREATE", "WATCH"],
        )
        filtered = df[df["Decision"].isin(decision_filter)].copy()
        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Commercial": st.column_config.ProgressColumn(
                    "Commercial",
                    min_value=0,
                    max_value=100,
                    format="%d",
                ),
                "Demand / Build": st.column_config.ProgressColumn(
                    "Demand / Build",
                    min_value=0,
                    max_value=100,
                    format="%d",
                ),
                "Median Price USD": st.column_config.NumberColumn(
                    "Median Price USD",
                    format="$%.2f",
                ),
            },
        )

        creates = filtered[filtered["Decision"] == "CREATE"]
        if not creates.empty:
            top = creates.iloc[0]
            st.success(
                f"Highest CREATE opportunity: **{top['Product']}** — "
                f"commercial score {int(top['Commercial'])}/100."
            )

with tab2:
    st.subheader("Where the opportunity pool is clustering")
    if not df.empty:
        kind_summary = (
            df.groupby("Type")
            .agg(
                Opportunities=("Product", "count"),
                Avg_Commercial=("Commercial", "mean"),
                Create_Count=("Decision", lambda x: int((x == "CREATE").sum())),
                Watch_Count=("Decision", lambda x: int((x == "WATCH").sum())),
            )
            .reset_index()
            .sort_values(["Create_Count", "Avg_Commercial"], ascending=False)
        )
        kind_summary["Avg_Commercial"] = kind_summary["Avg_Commercial"].round(1)
        st.dataframe(kind_summary, use_container_width=True, hide_index=True)

        decision_summary = (
            df.groupby("Decision")
            .size()
            .rename("Count")
            .reset_index()
        )
        st.bar_chart(decision_summary.set_index("Decision"))

with tab3:
    st.subheader("Marketplace evidence")
    st.caption(
        "Etsy and Gumroad counts are sampled public-search proxies, not complete marketplace inventory counts. "
        "A low observed count can mean lower competition or limited indexing, so use it together with demand score."
    )
    evidence_cols = [
        "Decision",
        "Product",
        "Commercial",
        "Etsy Proxy",
        "Gumroad Proxy",
        "Median Price USD",
        "Research Warnings",
    ]
    st.dataframe(
        df[evidence_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Median Price USD": st.column_config.NumberColumn(
                "Median Price USD",
                format="$%.2f",
            )
        },
    )

with tab4:
    st.subheader("Research source health")
    source_errors = report.get("source_errors", [])
    if not source_errors:
        st.success("No discovery-source errors were reported in this run.")
    else:
        st.warning(f"{len(source_errors)} discovery-source warning(s) were reported.")
        for error in source_errors:
            st.code(error)

    evidence_errors = []
    for item in report["decisions"]:
        for error in item["market_evidence"].get("errors", []):
            evidence_errors.append(
                {
                    "Product": phase3_copy.human_product_name(item["phrase"]),
                    "Warning": error,
                }
            )
    if evidence_errors:
        st.markdown("#### Marketplace research warnings")
        st.dataframe(pd.DataFrame(evidence_errors), use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "CREATE / WATCH / REJECT are research classifications, not guarantees of sales or profitability. "
    "Products still require human approval in the GitHub approval dashboard."
)
