from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json, write_text


CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 503}
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.0


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Map a Crossref works response to the project's stable raw-record schema.

    DOI is the stable identifier.  Records without it cannot be traced through
    later pipeline stages and are therefore excluded.  Missing abstracts are
    intentionally retained here; the cleaning stage applies the content rule.
    """
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("Crossref payload must contain a 'message' object.")

    items = message.get("items")
    if not isinstance(items, list):
        raise ValueError("Crossref payload message must contain an 'items' list.")

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _text(item.get("DOI")).lower()
        if not doi:
            continue

        title = _first_text(item.get("title"))
        categories = _text_list(item.get("subject"))
        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=_text(item.get("abstract") or item.get("description")),
                authors=_authors(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=_publication_date(item),
                updated=_date_from_value(item.get("updated")),
                abs_url=_text(item.get("URL")),
                pdf_url=_pdf_url(item.get("link")),
                comment=_first_text(item.get("subtitle")),
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data, save raw lineage artifacts, then return records.

    A retry means an additional request: at most four total requests are made
    (the initial request plus ``MAX_RETRIES`` retries) for 429 and 503 only.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    response = _get_with_retry(params)
    payload = response.json()

    # Persist source evidence before parser logic can alter or reject anything.
    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the parsed raw-record snapshot produced by ``fetch_source_records``."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records snapshot must be a JSON list: {path}")

    fields = set(PaperRecord.__dataclass_fields__)
    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} must be a JSON object.")
        missing = fields - set(item)
        extra = set(item) - fields
        if missing or extra:
            raise ValueError(
                f"Raw record at index {index} has incompatible schema "
                f"(missing={sorted(missing)}, extra={sorted(extra)})."
            )
        string_fields = fields - {"authors", "categories"}
        if any(not isinstance(item[field], str) for field in string_fields):
            raise ValueError(f"Raw record at index {index} has invalid string fields.")
        if (
            not isinstance(item["authors"], list)
            or not isinstance(item["categories"], list)
            or any(not isinstance(value, str) for value in item["authors"])
            or any(not isinstance(value, str) for value in item["categories"])
        ):
            raise ValueError(f"Raw record at index {index} has invalid list fields.")
        records.append(PaperRecord(**item))
    return records


def audit_raw_lineage(settings: Settings) -> dict[str, Any]:
    """Verify that a Crossref response and its parsed snapshot are traceable.

    The report is intentionally based only on saved artifacts, so it can be
    rerun offline before a repair flow without calling Crossref again.
    """
    raw_payload = read_json(settings.paths.raw_api_response)
    if not isinstance(raw_payload, dict):
        raise ValueError("Raw Crossref response must be a JSON object.")
    message = raw_payload.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise ValueError("Raw Crossref response does not contain message.items.")

    raw_items = message["items"]
    reparsed_records = parse_crossref_payload(raw_payload)
    snapshot_records = load_raw_records(settings.paths.raw_records_json)
    raw_doi_ids = [_canonical_doi(item.get("DOI")) for item in raw_items if isinstance(item, dict)]
    raw_doi_ids = [doi for doi in raw_doi_ids if doi]
    snapshot_ids = [record.paper_id for record in snapshot_records]
    required_fields = ("paper_id", "title", "summary", "authors", "published")
    optional_fields = ("categories", "primary_category", "updated", "abs_url", "pdf_url", "comment")
    required_empty_counts = {field: _empty_field_count(snapshot_records, field) for field in required_fields}
    optional_empty_counts = {field: _empty_field_count(snapshot_records, field) for field in optional_fields}
    raw_id_set = set(raw_doi_ids)
    snapshot_id_set = set(snapshot_ids)

    report = {
        "source": "Crossref REST API",
        "raw_response_path": str(settings.paths.raw_api_response),
        "raw_records_path": str(settings.paths.raw_records_json),
        "raw_item_count": len(raw_items),
        "reparsed_record_count": len(reparsed_records),
        "snapshot_record_count": len(snapshot_records),
        "snapshot_matches_reparse": snapshot_records == reparsed_records,
        "raw_items_missing_doi": len(raw_items) - len(raw_doi_ids),
        "duplicate_snapshot_paper_ids": sorted(id_ for id_, count in Counter(snapshot_ids).items() if count > 1),
        "raw_doi_ids_not_in_snapshot": sorted(raw_id_set - snapshot_id_set),
        "snapshot_paper_ids_not_in_raw": sorted(snapshot_id_set - raw_id_set),
        "required_field_empty_counts": required_empty_counts,
        "optional_field_empty_counts": optional_empty_counts,
        "cleaning_input_ready": (
            snapshot_records == reparsed_records
            and not (raw_id_set - snapshot_id_set)
            and not (snapshot_id_set - raw_id_set)
            and not any(count > 1 for count in Counter(snapshot_ids).values())
        ),
        "records_with_empty_cleaning_fields": required_empty_counts,
        "sample_record": asdict(snapshot_records[0]) if snapshot_records else None,
        "notes": [
            "paper_id is the canonicalized Crossref DOI (trimmed and lowercased).",
            "HTML/JATS content in summary is preserved in the raw snapshot; cleaning removes markup.",
            "Empty title, summary, authors, or published values are retained in raw records so cleaning can apply its filtering rules.",
            "categories, updated, pdf_url, and comment are optional Crossref metadata.",
        ],
    }
    return report


def write_raw_lineage_handoff(settings: Settings) -> dict[str, Any]:
    """Persist CP1 lineage evidence and a concise handoff for downstream roles."""
    report = audit_raw_lineage(settings)
    write_json(settings.paths.raw_lineage_report, report)
    sample = report["sample_record"]
    sample_json = "null" if sample is None else json.dumps(sample, ensure_ascii=False, indent=2)
    handoff = "\n".join(
        [
            "# Crossref raw-lineage handoff",
            "",
            f"- Raw API snapshot: `{settings.paths.raw_api_response}`",
            f"- Parsed PaperRecord snapshot: `{settings.paths.raw_records_json}`",
            f"- Lineage audit: `{settings.paths.raw_lineage_report}`",
            f"- Snapshot matches reparse: `{report['snapshot_matches_reparse']}`",
            f"- Cleaning input ready: `{report['cleaning_input_ready']}`",
            "- `paper_id` is the canonicalized DOI; use it as the stable key for repair and comparison.",
            "- `summary` may contain JATS/HTML; strip markup only in cleaning, never in raw artifacts.",
            "- Empty categories are valid optional source metadata; do not infer categories.",
            "",
            "## Sample PaperRecord",
            "",
            "```json",
            sample_json,
            "```",
            "",
        ]
    )
    write_text(settings.paths.raw_handoff_markdown, handoff)
    return report


def _get_with_retry(params: dict[str, Any]) -> requests.Response:
    for attempt in range(MAX_RETRIES + 1):
        response = requests.get(CROSSREF_API_URL, params=params, timeout=30)
        if response.status_code not in RETRYABLE_STATUS_CODES:
            response.raise_for_status()
            return response
        if attempt == MAX_RETRIES:
            response.raise_for_status()
        time.sleep(_retry_delay_seconds(response, attempt))
    raise RuntimeError("Crossref retry loop ended unexpectedly.")


def _retry_delay_seconds(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            except (TypeError, ValueError, IndexError, OverflowError):
                pass
    return BACKOFF_SECONDS * (2**attempt)


def _text(value: object) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _canonical_doi(value: object) -> str:
    return _text(value).lower()


def _empty_field_count(records: list[PaperRecord], field: str) -> int:
    return sum(not getattr(record, field) for record in records)


def _first_text(value: object) -> str:
    if isinstance(value, list):
        return next((_text(item) for item in value if _text(item)), "")
    return _text(value)


def _text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _text(item))]


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = _text(author.get("literal")) or " ".join(
            part for part in (_text(author.get("given")), _text(author.get("family"))) if part
        )
        if name:
            authors.append(name)
    return authors


def _publication_date(item: dict[str, object]) -> str:
    for key in ("published-print", "published-online", "issued"):
        date = _date_from_value(item.get(key))
        if date:
            return date
    return ""


def _date_from_value(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
        return ""
    parts = date_parts[0]
    if not parts or not isinstance(parts[0], int):
        return ""
    year = parts[0]
    month = parts[1] if len(parts) > 1 and isinstance(parts[1], int) else 1
    day = parts[2] if len(parts) > 2 and isinstance(parts[2], int) else 1
    try:
        return datetime(year, month, day, tzinfo=UTC).date().isoformat()
    except ValueError:
        return ""


def _pdf_url(value: object) -> str:
    if not isinstance(value, list):
        return ""
    for link in value:
        if not isinstance(link, dict):
            continue
        content_type = _text(link.get("content-type")).lower()
        if content_type == "application/pdf":
            return _text(link.get("URL"))
    return ""
