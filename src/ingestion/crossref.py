from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


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
