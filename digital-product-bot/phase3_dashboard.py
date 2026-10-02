from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

TITLE = "[Digital Product Bot] Approval Dashboard"
MARKER = "DIGITAL_PRODUCT_QUEUE"


def latest_report(output_root: Path) -> Path:
    reports = sorted(output_root.glob("**/phase2_report.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        raise FileNotFoundError("No phase2_report.json found")
    return reports[0]


def queue_payload(report: dict) -> list[dict]:
    rows = []
    for item in report.get("review_queue", []):
        row = dict(item)
        phrase = row["phrase"]
        import bot
        row["slug"] = bot.slugify(phrase)
        rows.append(row)
    return rows


def encode_queue(rows: list[dict]) -> str:
    raw = json.dumps(rows, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def dashboard_body(report: dict, rows: list[dict]) -> str:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Digital Product Approval Dashboard",
        "",
        f"Updated: **{updated}**",
        "",
        "This is the human approval gate for the digital-product bot. The scout can research and manufacture drafts, but it cannot publish a product without an explicit command from the repository owner.",
        "",
        "## Current queue",
        "",
        "| Decision | Commercial | Base | Product | Type | Slug |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['decision']} | {row['commercial_score']} | {row['base_score']} | "
            f"{row['phrase'].replace('|', '/')} | {row['kind']} | `{row['slug']}` |"
        )

    created = report.get("decision_counts", {}).get("CREATE", 0)
    watch = report.get("decision_counts", {}).get("WATCH", 0)
    rejected = report.get("decision_counts", {}).get("REJECT", 0)
    production_batch = report.get("production_batch", [])

    lines += [
        "",
        "## Produced for review",
        "",
    ]

    if production_batch:
        lines += [
            "| Product | Factory | Family | Commercial | Status |",
            "|---|---|---|---:|---|",
        ]
        for item in production_batch:
            lines.append(
                f"| {item['phrase'].replace('|','/')} | {item['factory']} | {item['family']} | "
                f"{item['commercial_score']} | **{item['status']}** |"
            )
    else:
        lines.append("No products were produced in this run.")

    lines += [
        "",
        f"Queue summary: **{created} CREATE**, **{watch} WATCH**, **{rejected} REJECT**. "
        f"**{len(production_batch)}** products were manufactured for review.",
        "",
        "## Commands",
        "",
        "Post one command as a new comment on this issue:",
        "",
        "- `/approve <slug>` — build the final marketplace-quality package and keep it offline.",
        "- `/reject <slug>` — record that the product should not proceed.",
        "- `/publish <slug>` — rebuild/finalise it and attempt to create an **Etsy draft listing**. This never activates the listing.",
        "",
        "Example:",
        "",
        "`/approve social-media-content-calendar-template-excel`",
        "",
        "Only comments from the repository owner are acted on. Etsy publishing also requires repository secrets for the Etsy API connection.",
        "",
        "## Safety / quality gate",
        "",
        "- Products remain general productivity tools; regulated legal, tax, medical and investment-advice products are excluded.",
        "- Approval and publishing are separate actions.",
        "- `/publish` creates a draft only; activation remains manual in Etsy.",
        "",
        f"<!-- {MARKER}:{encode_queue(rows)} -->",
    ]
    return "\n".join(lines)


def upsert_issue(body: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base = f"https://api.github.com/repos/{repo}"
    session = requests.Session()
    session.headers.update(headers)

    response = session.get(f"{base}/issues", params={"state": "open", "per_page": 100}, timeout=20)
    response.raise_for_status()
    existing = next(
        (issue for issue in response.json() if issue.get("title") == TITLE and "pull_request" not in issue),
        None,
    )
    if existing:
        response = session.patch(f"{base}/issues/{existing['number']}", json={"body": body}, timeout=20)
    else:
        response = session.post(f"{base}/issues", json={"title": TITLE, "body": body}, timeout=20)
    response.raise_for_status()
    return response.json()


def main() -> int:
    output_root = Path(os.environ.get("OUTPUT_DIR", "digital-product-output"))
    report_path = latest_report(output_root)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = queue_payload(report)
    issue = upsert_issue(dashboard_body(report, rows))
    print(json.dumps({"issue_number": issue["number"], "issue_url": issue["html_url"], "queue_count": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
