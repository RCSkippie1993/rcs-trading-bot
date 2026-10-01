# Digital Product Scout & Factory — Phase 2

This module discovers online demand signals, researches market competition, classifies opportunities, creates review-ready digital products, and stops before publishing.

## Phase 2 pipeline

1. **Discover** — gathers search-demand signals from Google Suggest and attempts additional community signals where available.
2. **Score** — scores demand, buyer intent, specificity and buildability.
3. **De-duplicate** — groups close commercial variants so, for example, an Excel and Google Sheets wording of the same underlying product do not both consume creation slots.
4. **Research** — checks sampled public search results for Etsy and Gumroad listing evidence and visible price snippets.
5. **Decide** — assigns every researched idea to `CREATE`, `WATCH` or `REJECT`.
6. **Create** — only `CREATE` ideas are turned into full product packages.
7. **Preview** — generates a marketplace-style PNG preview image for each created product.
8. **Review gate** — every generated package remains `AWAITING_APPROVAL`; nothing is published automatically.

## What a created package contains

- editable XLSX workbook
- starter CSV
- buyer/setup guide
- listing title and descriptions
- keywords
- configured and market-informed price guidance
- market research evidence
- automatically generated listing preview PNG
- manifest
- approval status file
- ZIP bundle

## Review queue

Every run produces `review_queue.csv` and `phase2_report.json`. The queue shows:

- Create / Watch / Reject decision
- commercial score
- original demand score
- product type
- Etsy and Gumroad search-result proxy hits
- observed median price sample when available
- demand-signal count

Marketplace competition figures are deliberately labelled as **proxies**. They are sampled public search-result links, not exhaustive marketplace inventory counts.

## Product types

The factory focuses on products it can create reliably without manual specialist work:

- trackers
- planners
- checklists
- calculators
- operating templates
- simple business toolkits

It excludes legal documents/advice, tax or investment advice, medical products, copyrighted derivatives and obvious trademark-dependent products.

## Running locally

```bash
cd digital-product-bot
pip install -r requirements.txt
python phase2.py
```

Generated files appear under `output/YYYY-MM-DD/`.

## Automated GitHub run

`.github/workflows/digital-product-scout.yml` runs every weekday at 04:00 UTC (06:00 South Africa Standard Time) and can also be triggered manually.

The workflow runs syntax checks plus Phase 1 and Phase 2 self-tests before the live research run. Outputs are uploaded as a GitHub Actions artifact instead of being committed into this public repository.

## Configuration

`config.json` controls:

- seed markets
- community sources
- demand threshold
- Create and Watch thresholds
- duplicate similarity threshold
- number of ideas researched per run
- maximum products created per run
- marketplace domains
- price bands
- excluded topics

## Approval gate

Every created product includes:

```json
{
  "status": "AWAITING_APPROVAL",
  "publishing_enabled": false
}
```

A later publishing phase must require an explicit `APPROVED` status before any listing action is allowed.

## Reliability

External sources can change, rate-limit or block automated requests. Phase 2 records source failures rather than silently treating them as verified data. The product generator can continue when one source is unavailable, but the report preserves those limitations for review.
