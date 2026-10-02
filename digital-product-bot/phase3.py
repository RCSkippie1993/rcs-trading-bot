from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

import bot
import etsy_adapter
import phase2
import phase3_assets
import phase3_checks
import phase3_copy

MARKER_RE = re.compile(r"<!--\s*DIGITAL_PRODUCT_QUEUE:([A-Za-z0-9_=-]+)\s*-->")
COMMAND_RE = re.compile(r"^\s*/(approve|reject|publish)\s+([a-z0-9-]+)\s*$", re.I)


def decode_queue(issue_body: str) -> list[dict]:
    match = MARKER_RE.search(issue_body or "")
    if not match:
        raise ValueError("Approval dashboard queue payload is missing")
    raw = base64.urlsafe_b64decode(match.group(1).encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def decision_from_row(row: dict) -> phase2.Decision:
    market = row["market_evidence"]
    evidence = phase2.MarketEvidence(
        platform_hits=dict(market.get("platform_hits", {})),
        sampled_prices_usd=list(market.get("sampled_prices_usd", [])),
        median_price_usd=market.get("median_price_usd"),
        evidence_queries=list(market.get("evidence_queries", [])),
        errors=list(market.get("errors", [])),
    )
    return phase2.Decision(
        phrase=row["phrase"],
        base_score=int(row["base_score"]),
        commercial_score=int(row["commercial_score"]),
        decision=row["decision"],
        kind=row["kind"],
        signal_count=int(row.get("signal_count", 1)),
        sources=list(row.get("sources", [])),
        market_evidence=evidence,
        reasons=list(row.get("reasons", [])),
    )


def post_comment(repo: str, issue_number: int, body: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(body)
        return
    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"body": body},
        timeout=20,
    )
    response.raise_for_status()


def finalise(decision: phase2.Decision, output_root: Path) -> tuple[Path, Path, dict, dict]:
    config = bot.load_config()
    brand = phase3_assets.load_brand()
    product_root = output_root / "approved-products"
    product_root.mkdir(parents=True, exist_ok=True)

    zip_path = Path(phase2.enrich_product(decision, product_root, config))
    folder = product_root / bot.slugify(decision.phrase)
    listing_path = folder / "listing.json"
    base_listing = json.loads(listing_path.read_text(encoding="utf-8"))

    marketplace = phase3_copy.build_listing(decision, base_listing, brand)

    for old in folder.glob("listing-image-*.png"):
        old.unlink()

    images = phase3_assets.create_listing_images(folder, decision, marketplace, brand)
    marketplace["listing_images"] = images
    (folder / "marketplace-listing.json").write_text(json.dumps(marketplace, indent=2), encoding="utf-8")

    status_path = folder / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update({
        "status": "APPROVED_NOT_PUBLISHED",
        "approved_by": os.environ.get("GITHUB_ACTOR", "repository-owner"),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "publishing_enabled": False,
        "phase3_version": "3.6",
    })
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    readiness = phase3_checks.validate(folder, zip_path, marketplace, require_etsy=False)
    marketplace["publish_readiness"] = readiness["ready"]
    (folder / "marketplace-listing.json").write_text(json.dumps(marketplace, indent=2), encoding="utf-8")

    phase2._rewrite_zip(folder, zip_path)
    return folder, zip_path, marketplace, readiness


def _reject(slug: str, row: dict, output_root: Path) -> Path:
    out = output_root / "rejections"
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "slug": slug,
        "phrase": row["phrase"],
        "decision": "REJECTED_BY_OWNER",
        "actor": os.environ.get("GITHUB_ACTOR"),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    path = out / f"{slug}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> int:
    event_path = Path(os.environ["GITHUB_EVENT_PATH"])
    event = json.loads(event_path.read_text(encoding="utf-8"))
    comment = event.get("comment", {}).get("body", "")
    issue_body = event.get("issue", {}).get("body", "")
    issue_number = int(event.get("issue", {}).get("number", 0))
    repo = os.environ["GITHUB_REPOSITORY"]

    match = COMMAND_RE.match(comment)
    if not match:
        print("No supported command found")
        return 0
    action, slug = match.group(1).lower(), match.group(2).lower()

    queue = decode_queue(issue_body)
    row = next((item for item in queue if item.get("slug") == slug), None)
    if not row:
        post_comment(repo, issue_number, f"Could not find `{slug}` in the current approval queue.")
        return 0

    output_root = Path(os.environ.get("PHASE3_OUTPUT_DIR", "phase3-output"))

    if action == "reject":
        _reject(slug, row, output_root)
        post_comment(repo, issue_number, f"Recorded **REJECT** for `{slug}`. No product was published.")
        return 0

    decision = decision_from_row(row)
    folder, delivery_zip, marketplace, readiness = finalise(decision, output_root)

    if not readiness["ready"]:
        summary = phase3_checks.failure_summary(readiness)
        post_comment(
            repo,
            issue_number,
            f"Finalised `{slug}`, but its marketplace package failed the offline readiness check: **{summary}**. "
            "No publishing action was attempted.",
        )
        return 1

    if action == "approve":
        pricing = marketplace["pricing"]
        post_comment(
            repo,
            issue_number,
            f"Approved and upgraded `{slug}`. Phase 3.6 generated **7 marketplace images**, improved listing copy, "
            f"and pricing guidance (floor **USD {pricing['floor_price_usd']:.2f}**, recommended **USD {pricing['recommended_price_usd']:.2f}**, "
            f"premium **USD {pricing['premium_price_usd']:.2f}**). All offline readiness checks passed. "
            "It remains **APPROVED_NOT_PUBLISHED**.",
        )
        return 0

    publish_readiness = phase3_checks.validate(folder, delivery_zip, marketplace, require_etsy=True)
    phase2._rewrite_zip(folder, delivery_zip)
    if not publish_readiness["ready"]:
        summary = phase3_checks.failure_summary(publish_readiness)
        post_comment(
            repo,
            issue_number,
            f"`{slug}` passed the product-quality checks but is **not ready to create an Etsy draft**: {summary}. "
            "No listing was created.",
        )
        return 0

    try:
        result = etsy_adapter.create_draft(folder, delivery_zip, marketplace)
    except etsy_adapter.EtsyConfigurationError as exc:
        post_comment(repo, issue_number, f"Etsy connection is incomplete for `{slug}`: {exc}. No listing was created.")
        return 0
    except requests.RequestException as exc:
        post_comment(
            repo,
            issue_number,
            f"Etsy rejected the draft request for `{slug}`: **{exc}**. The approved files remain intact and offline.",
        )
        raise

    status_path = folder / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update({
        "status": "ETSY_DRAFT_CREATED",
        "publishing_enabled": True,
        "etsy": result,
    })
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    phase2._rewrite_zip(folder, delivery_zip)

    post_comment(
        repo,
        issue_number,
        f"Created an Etsy **draft** for `{slug}` (listing ID **{result['listing_id']}**), uploaded the 7 listing images "
        "and digital ZIP. The Etsy listing was **not activated**.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
