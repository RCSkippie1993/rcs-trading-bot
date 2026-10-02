from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


class EtsyConfigurationError(RuntimeError):
    pass


def missing_settings() -> list[str]:
    required = ["ETSY_SHOP_ID", "ETSY_API_KEY", "ETSY_ACCESS_TOKEN", "ETSY_TAXONOMY_ID"]
    return [name for name in required if not os.environ.get(name)]


def configured() -> bool:
    return not missing_settings()


def _headers() -> dict[str, str]:
    return {
        "x-api-key": os.environ["ETSY_API_KEY"],
        "Authorization": f"Bearer {os.environ['ETSY_ACCESS_TOKEN']}",
        "Accept": "application/json",
    }


def create_draft(folder: Path, delivery_zip: Path, listing: dict[str, Any]) -> dict[str, Any]:
    missing = missing_settings()
    if missing:
        raise EtsyConfigurationError("Missing Etsy settings: " + ", ".join(missing))

    shop_id = os.environ["ETSY_SHOP_ID"]
    taxonomy_id = int(os.environ["ETSY_TAXONOMY_ID"])
    base = "https://openapi.etsy.com/v3/application"
    session = requests.Session()
    session.headers.update(_headers())

    payload = {
        "quantity": 999,
        "title": listing["title"][:140],
        "description": listing["description"],
        "price": float(listing["price_usd"]),
        "who_made": "i_did",
        "when_made": "2020_2026",
        "taxonomy_id": taxonomy_id,
        "is_supply": "false",
        "should_auto_renew": "false",
        "type": "download",
        "tags": listing.get("etsy_tags", []),
    }
    response = session.post(
        f"{base}/shops/{shop_id}/listings",
        data=payload,
        timeout=30,
    )
    response.raise_for_status()
    created = response.json()
    listing_id = created.get("listing_id")
    if not listing_id:
        raise RuntimeError("Etsy did not return a listing_id")

    image_ids = []
    for image_path in sorted(folder.glob("listing-image-*.png")):
        with image_path.open("rb") as fh:
            img_response = session.post(
                f"{base}/shops/{shop_id}/listings/{listing_id}/images",
                files={"image": (image_path.name, fh, "image/png")},
                timeout=45,
            )
        img_response.raise_for_status()
        image_ids.append(img_response.json().get("listing_image_id"))

    with delivery_zip.open("rb") as fh:
        file_response = session.post(
            f"{base}/shops/{shop_id}/listings/{listing_id}/files",
            files={"file": (delivery_zip.name, fh, "application/zip")},
            data={"name": delivery_zip.name, "rank": 1},
            timeout=60,
        )
    file_response.raise_for_status()

    return {
        "platform": "etsy",
        "listing_id": listing_id,
        "state": created.get("state", "draft"),
        "uploaded_image_ids": [x for x in image_ids if x],
        "digital_file_uploaded": True,
        "activated": False,
    }
