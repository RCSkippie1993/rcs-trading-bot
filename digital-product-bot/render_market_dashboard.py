from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

import bot
import phase2
import phase3_copy
from market_probe import research_market_data
from market_segments import segment_for_phrase
from product_format import factory_readiness, readiness_label

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
    config = dict(bot.load_config())
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
        "seed_markets": len(config.get("seed_markets", [])),
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
        ready, fmt, readiness_reason = factory_readiness(item["phrase"])
        total_market_hits = sum(evidence["platform_hits"].values())
        market_confirmed = total_market_hits > 0 or evidence.get("median_price_usd") is not None
        rows.append(
            {
                "Decision": item["decision"],
                "Commercial": item["commercial_score"],
                "Demand / Build": item["base_score"],
                "Product": phase3_copy.human_product_name(item["phrase"]),
                "Segment": segment_for_phrase(item["phrase"]),
                "Market Confirmed": market_confirmed,
                "Factory": readiness_label(item["phrase"]),
                "Factory Ready": ready,
                "Preferred Format": fmt,
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


def opportunity_table(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("No opportunities match this view.")
        return
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Commercial": st.column_config.ProgressColumn(
                "Commercial", min_value=0, max_value=100, format="%d"
            ),
            "Demand / Build": st.column_config.ProgressColumn(
                "Demand / Build", min_value=0, max_value=100, format="%d"
            ),
            "Median Price USD": st.column_config.NumberColumn(
                "Median Price USD", format="$%.2f"
            ),
        },
    )


st.title("Digital Product Market Radar")
st.caption(
    "Broad-market demand discovery and opportunity scoring for digital products. "
    "The radar researches opportunities only — it does not approve, create, list or publish products."
)

with st.sidebar:
    st.header("Scan settings")
    research_limit = st.slider(
        "Distinct ideas to research",
        min_value=12,
        max_value=40,
        value=30,
        step=1,
        help="The radar scans all seed markets first, then performs slower marketplace research on the strongest distinct candidates.",
    )
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
        with st.spinner("Scanning the broad market universe and researching the strongest opportunities..."):
            st.session_state["report"] = run_market_scan(
                research_limit,
                create_threshold,
                watch_threshold,
                minimum_score,
            )

report = st.session_state["report"]

if not report:
    with st.spinner("Running the first broad live market scan..."):
        report = run_market_scan(
            research_limit,
            create_threshold,
            watch_threshold,
            minimum_score,
        )
        st.session_state["report"] = report

df = decision_frame(report)
create_count = int((df["Decision"] == "CREATE").sum()) if not df.empty else 0
watch_count = int((df["Decision"] == "WATCH").sum()) if not df.empty else 0
reject_count = int((df["Decision"] == "REJECT").sum()) if not df.empty else 0

r1 = st.columns(4)
r1[0].metric("Seed markets", report["seed_markets"])
r1[1].metric("Demand signals", report["signals_seen"])
r1[2].metric("Raw ideas", report["raw_opportunities"])
r1[3].metric("Distinct markets", report["distinct_families"])

r2 = st.columns(4)
r2[0].metric("Researched", report["researched"])
r2[1].metric("CREATE", create_count)
r2[2].metric("WATCH", watch_count)
r2[3].metric("REJECT", reject_count)

st.markdown(
    f'<div class="market-note"><b>Last scan:</b> {report["run_at_utc"]} &nbsp; '
    f'<b>Universe:</b> {report["seed_markets"]} seed markets &nbsp; '
    f'<b>Deep research:</b> {report["researched"]} distinct opportunities.</div>',
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Top 10 CREATE",
        "Emerging opportunities",
        "Full ranking",
        "Market segments",
        "Evidence",
        "Source health",
    ]
)

with tab1:
    st.subheader("Top 10 CREATE opportunities")
    creates = df[df["Decision"] == "CREATE"].sort_values(
        ["Commercial", "Demand / Build"], ascending=False
    ).head(10)
    opportunity_table(
        creates[
            [
                "Decision", "Commercial", "Demand / Build", "Product", "Segment",
                "Market Confirmed", "Factory", "Etsy Proxy", "Gumroad Proxy", "Median Price USD", "Signals"
            ]
        ] if not creates.empty else creates
    )
    if not creates.empty:
        top = creates.iloc[0]
        st.success(
            f"Current leader: **{top['Product']}** in **{top['Segment']}** — "
            f"commercial score {int(top['Commercial'])}/100."
        )
    else:
        st.info("No researched opportunity currently clears the CREATE threshold.")

with tab2:
    st.subheader("Emerging opportunities")
    st.caption(
        "WATCH ideas within five points of the current CREATE threshold. "
        "These are the candidates most likely to move into CREATE if future demand evidence strengthens."
    )
    emerging = df[
        (df["Decision"] == "WATCH")
        & (df["Commercial"] >= create_threshold - 5)
    ].sort_values(["Commercial", "Demand / Build"], ascending=False)
    if emerging.empty:
        emerging = df[df["Decision"] == "WATCH"].sort_values(
            ["Commercial", "Demand / Build"], ascending=False
        ).head(10)
    opportunity_table(
        emerging[
            [
                "Decision", "Commercial", "Demand / Build", "Product", "Segment",
                "Market Confirmed", "Factory", "Etsy Proxy", "Gumroad Proxy", "Median Price USD", "Signals"
            ]
        ] if not emerging.empty else emerging
    )

with tab3:
    st.subheader("Full researched ranking")
    if df.empty:
        st.warning("No opportunities were returned.")
    else:
        decision_filter = st.multiselect(
            "Show decisions",
            ["CREATE", "WATCH", "REJECT"],
            default=["CREATE", "WATCH"],
        )
        segment_options = sorted(df["Segment"].dropna().unique().tolist())
        segment_filter = st.multiselect(
            "Filter market segments",
            segment_options,
            default=[],
        )
        filtered = df[df["Decision"].isin(decision_filter)].copy()
        if segment_filter:
            filtered = filtered[filtered["Segment"].isin(segment_filter)]
        opportunity_table(filtered)

with tab4:
    st.subheader("Where the opportunity pool is clustering")
    if not df.empty:
        segment_summary = (
            df.groupby("Segment")
            .agg(
                Opportunities=("Product", "count"),
                Avg_Commercial=("Commercial", "mean"),
                Best_Commercial=("Commercial", "max"),
                Create_Count=("Decision", lambda x: int((x == "CREATE").sum())),
                Watch_Count=("Decision", lambda x: int((x == "WATCH").sum())),
            )
            .reset_index()
            .sort_values(
                ["Create_Count", "Best_Commercial", "Avg_Commercial"],
                ascending=False,
            )
        )
        segment_summary["Avg_Commercial"] = segment_summary["Avg_Commercial"].round(1)
        st.dataframe(segment_summary, use_container_width=True, hide_index=True)

        kind_summary = (
            df.groupby("Type")
            .agg(
                Opportunities=("Product", "count"),
                Avg_Commercial=("Commercial", "mean"),
                Create_Count=("Decision", lambda x: int((x == "CREATE").sum())),
            )
            .reset_index()
            .sort_values(["Create_Count", "Avg_Commercial"], ascending=False)
        )
        kind_summary["Avg_Commercial"] = kind_summary["Avg_Commercial"].round(1)
        st.markdown("#### Product-format mix")
        st.dataframe(kind_summary, use_container_width=True, hide_index=True)

        st.markdown("#### Decision mix")
        cols = st.columns(3)
        for col, label, value in zip(
            cols,
            ["CREATE", "WATCH", "REJECT"],
            [create_count, watch_count, reject_count],
        ):
            col.metric(label, value)

with tab5:
    st.subheader("Marketplace evidence")
    st.caption(
        "Etsy and Gumroad counts are sampled public-search proxies, not complete marketplace inventory counts. "
        "A low observed count can mean lower competition or limited indexing, so use it together with demand score."
    )
    evidence_cols = [
        "Decision",
        "Product",
        "Segment",
        "Commercial",
        "Market Confirmed",
        "Factory",
        "Etsy Proxy",
        "Gumroad Proxy",
        "Median Price USD",
        "Research Warnings",
    ]
    opportunity_table(df[evidence_cols] if not df.empty else df)

with tab6:
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
                    "Segment": segment_for_phrase(item["phrase"]),
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
