# Digital Product Scout & Factory

This module discovers online demand signals, scores digital-product opportunities, creates review-ready digital products, and stops before publishing.

## What it does

- Pulls demand signals from Google Suggest and selected Reddit communities.
- Converts raw phrases into commercial digital-product opportunities.
- Scores opportunities for demand, buyer intent, specificity, buildability, and saturation risk.
- Generates a product package for the strongest opportunities.
- Produces an XLSX workbook, CSV starter data, a buyer guide/checklist, listing copy, keywords, price guidance, and a manifest.
- Marks every generated product `AWAITING_APPROVAL`.
- Does **not** publish, list, charge customers, or connect to a marketplace without an explicit later approval step.

## Product types

The first version focuses on products that can be created reliably without manual design work:

- trackers
- planners
- checklists
- calculators
- operating templates
- simple business toolkits

It intentionally avoids automatically producing legal documents, regulated financial advice, medical material, copyrighted derivatives, or trademark-dependent products.

## Running locally

```bash
cd digital-product-bot
pip install -r requirements.txt
python bot.py
```

Generated files appear under `output/YYYY-MM-DD/`. Each product folder contains the product itself plus listing metadata and an approval-status file.

## Automated GitHub run

The workflow at `.github/workflows/digital-product-scout.yml` runs every weekday at 04:00 UTC (06:00 South Africa Standard Time) and can also be triggered manually.

The workflow uploads the generated product packages as a GitHub Actions artifact instead of committing them into the repository. This is deliberate because the current repository is public and commercial product drafts should not be written into source control.

## Configuration

Edit `config.json` to control:

- seed markets
- Reddit communities
- minimum score
- maximum products per run
- price bands
- excluded topics

## Approval gate

Every product package includes `status.json` with:

```json
{
  "status": "AWAITING_APPROVAL"
}
```

A future publishing phase should only accept products whose status has been deliberately changed to `APPROVED`.

## Notes

External sites can change or rate-limit public endpoints. The bot is designed to degrade gracefully: if one source fails, it continues with the remaining demand signals and records the source failure in the run report.
