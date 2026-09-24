"""NIST CSF 2.0 structure: Functions, Categories, and Subcategories.

Source: NIST's own official OSCAL catalog, `nist.gov/CSF/v2.0/json/
NIST_CSF_v2.0_catalog-min.json` from github.com/usnistgov/oscal-content
(public domain / CC0-1.0 -- see that repo's LICENSE.md; this is a work of
the US government, so unlike ISO/CIS it may be reproduced verbatim, not
just as ID + paraphrase). A local copy is checked in at
app/compliance/data/nist_csf_2_0_catalog.json so imports don't depend on
live network access.

This OSCAL catalog is NIST's electronic edition of the CSF and mixes the
CSF 2.0 structure with retained CSF 1.1 categories/subcategories, each
withdrawn one marked with a `{"name": "status", "value": "withdrawn"}`
prop (e.g. PR.AC-*, PR.IP-*, DE.CM-8, RS.RP-01). Filtering those out here
(_is_withdrawn) yields exactly 6 Functions, 22 Categories and 106
Subcategories -- the counts docs/research/control_mapping.md's section 1b
independently reports.
"""

from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

CSF_VERSION = "2.0"
CSF_EFFECTIVE_DATE = dt.date(2024, 2, 26)
CSF_SOURCE_URL = "https://csrc.nist.gov/pubs/cswp/29/final"
CATALOG_SOURCE_NOTE = (
    "github.com/usnistgov/oscal-content nist.gov/CSF/v2.0/json/"
    "NIST_CSF_v2.0_catalog-min.json (public domain / CC0-1.0)"
)

_CATALOG_PATH = Path(__file__).parent / "data" / "nist_csf_2_0_catalog.json"


def _is_withdrawn(node: dict) -> bool:
    return any(p.get("name") == "status" and p.get("value") == "withdrawn" for p in node.get("props", []))


def _statement(node: dict) -> str:
    for part in node.get("parts", []):
        if part.get("name") == "statement":
            return part.get("prose", node.get("title", node["id"]))
    return node.get("title", node["id"])


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    with open(_CATALOG_PATH) as f:
        return json.load(f)


@lru_cache(maxsize=1)
def csf_functions() -> list[tuple[str, str]]:
    catalog = _load_catalog()["catalog"]
    return [(g["id"], g["title"].title()) for g in catalog["groups"]]


@lru_cache(maxsize=1)
def csf_categories() -> list[tuple[str, str, str]]:
    """(category_id, function_id, title) for active (non-withdrawn) categories."""
    catalog = _load_catalog()["catalog"]
    rows = []
    for group in catalog["groups"]:
        for category in group["controls"]:
            if _is_withdrawn(category):
                continue
            rows.append((category["id"], group["id"], category["title"]))
    return rows


@lru_cache(maxsize=1)
def csf_subcategories() -> list[tuple[str, str, str]]:
    """(subcategory_id, category_id, statement) for active (non-withdrawn) subcategories."""
    catalog = _load_catalog()["catalog"]
    rows = []
    for group in catalog["groups"]:
        for category in group["controls"]:
            if _is_withdrawn(category):
                continue
            for subcategory in category.get("controls", []):
                if _is_withdrawn(subcategory):
                    continue
                rows.append((subcategory["id"], category["id"], _statement(subcategory)))
    return rows


@lru_cache(maxsize=1)
def withdrawn_ids() -> frozenset[str]:
    """Every withdrawn CSF 1.1 category/subcategory ID in the source catalog,
    for the "never appears" guardrail test."""
    catalog = _load_catalog()["catalog"]
    ids = set()
    for group in catalog["groups"]:
        for category in group["controls"]:
            if _is_withdrawn(category):
                ids.add(category["id"])
            for subcategory in category.get("controls", []):
                if _is_withdrawn(subcategory):
                    ids.add(subcategory["id"])
    return frozenset(ids)


# Backwards-compatible module-level constants (used by csf_import.py and tests).
CSF_FUNCTIONS = csf_functions()
CSF_CATEGORIES = csf_categories()
CSF_SUBCATEGORIES = csf_subcategories()
WITHDRAWN_CSF_1_1_IDS = withdrawn_ids()
