import json
import math
import os
from pathlib import Path

from bot.readiness import ReadinessThresholds, evaluate_portfolio, evaluate_symbol


def _fmt_pf(value: float) -> str:
    return "inf" if math.isinf(value) else f"{value:.2f}"


def _discover_state_files() -> list[Path]:
    explicit = os.getenv("RCS_FORWARD_STATE", "").strip()
    if explicit:
        return [Path(explicit)]

    state_dir = Path(os.getenv("RCS_STATE_DIR", "state"))
    files = sorted(state_dir.glob("forward_*.json"))
    legacy = state_dir / "forward_state.json"
    if legacy.exists() and legacy not in files:
        files.append(legacy)
    return files


def _symbol_from_path(path: Path, raw: dict) -> str:
    if raw.get("symbol"):
        return str(raw["symbol"])
    stem = path.stem.replace("forward_", "")
    return stem.replace("_", ".").upper() if stem else "UNKNOWN"


def main():
    thresholds = ReadinessThresholds(
        min_closed_trades=int(os.getenv("RCS_GATE_MIN_TRADES", "30")),
        min_total_return_pct=float(os.getenv("RCS_GATE_MIN_RETURN_PCT", "0")),
        min_profit_factor=float(os.getenv("RCS_GATE_MIN_PROFIT_FACTOR", "1.20")),
        max_drawdown_pct=float(os.getenv("RCS_GATE_MAX_DRAWDOWN_PCT", "10")),
        min_positive_symbol_pct=float(os.getenv("RCS_GATE_MIN_POSITIVE_SYMBOL_PCT", "60")),
    )

    state_files = _discover_state_files()
    results = []
    missing = []

    for path in state_files:
        if not path.exists():
            missing.append(str(path))
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_symbol(raw, thresholds)
        result["symbol"] = _symbol_from_path(path, raw)
        result["state_file"] = str(path)
        results.append(result)

    portfolio = evaluate_portfolio(results, thresholds)

    lines = [
        "RCS Trading Bot — PHASE 3 FORWARD-PAPER DECISION DASHBOARD",
        f"Portfolio status: {portfolio['status']}",
        "",
        "Decision gates (research thresholds, not a profit guarantee):",
        f"- Minimum closed paper trades per symbol: {thresholds.min_closed_trades}",
        f"- Total return after modeled costs: > {thresholds.min_total_return_pct:.2f}%",
        f"- Profit factor: >= {thresholds.min_profit_factor:.2f}",
        f"- Maximum drawdown: <= {thresholds.max_drawdown_pct:.2f}%",
        f"- Positive-return symbols: >= {thresholds.min_positive_symbol_pct:.1f}%",
        "",
    ]

    if results:
        lines.append("Per-symbol forward results:")
        for row in results:
            lines.append(
                f"- {row['symbol']}: {row['status']} | trades={row['closed_trades']} | "
                f"return={row['total_return_pct']:.2f}% | PF={_fmt_pf(row['profit_factor'])} | "
                f"DD={row['max_drawdown_pct']:.2f}% | win={row['win_rate_pct']:.1f}%"
            )
        lines.extend([
            "",
            f"Symbols with enough data: {portfolio.get('symbols_with_enough_data', 0)}/{portfolio['symbols']}",
            f"Positive-return symbols with enough data: {portfolio['positive_symbol_pct']:.1f}%",
            f"Symbols passing all individual gates: {portfolio['review_ready_symbols']}",
        ])
    else:
        lines.append("No forward-paper state files contain enough data yet.")

    if missing:
        lines.extend(["", "Missing state files:"] + [f"- {item}" for item in missing])

    lines.extend([
        "",
        "Interpretation:",
        "- INSUFFICIENT DATA: keep paper trading; sample size is below the minimum gate.",
        "- NOT READY: one or more risk/performance gates failed; do not move to live capital.",
        "- READY FOR MANUAL REVIEW: paper gates passed; this is not automatic permission to trade live.",
    ])

    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    text = "\n".join(lines) + "\n"
    (reports / "forward_readiness.txt").write_text(text, encoding="utf-8")
    (reports / "forward_readiness.json").write_text(
        json.dumps({"portfolio": portfolio, "symbols": results}, indent=2, default=str),
        encoding="utf-8",
    )
    print(text, end="")


if __name__ == "__main__":
    main()
