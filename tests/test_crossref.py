from __future__ import annotations

from dataclasses import asdict
import json
from types import SimpleNamespace

import requests

from ingestion.crossref import (
    audit_raw_lineage,
    fetch_source_records,
    load_raw_records,
    parse_crossref_payload,
    write_raw_lineage_handoff,
)


def _payload() -> dict:
    return {
        "message": {
            "items": [
                {
                    "DOI": " 10.1000/ABC.1 ",
                    "title": [" A paper title "],
                    "abstract": "<jats:p>Short abstract</jats:p>",
                    "author": [{"given": "Ada", "family": "Lovelace"}],
                    "subject": ["Artificial Intelligence"],
                    "published-online": {"date-parts": [[2026, 8, 1]]},
                    "updated": {"date-parts": [[2026, 8, 2]]},
                    "URL": "https://doi.org/10.1000/ABC.1",
                    "link": [{"content-type": "application/pdf", "URL": "https://example.test/paper.pdf"}],
                },
                {"title": ["No DOI"]},
                {"DOI": "10.1000/no-abstract", "title": ["Retained raw record"]},
            ]
        }
    }


def test_parse_uses_canonical_doi_and_keeps_missing_abstract() -> None:
    records = parse_crossref_payload(_payload())

    assert [record.paper_id for record in records] == ["10.1000/abc.1", "10.1000/no-abstract"]
    assert records[0].authors == ["Ada Lovelace"]
    assert records[0].published == "2026-08-01"
    assert records[0].pdf_url == "https://example.test/paper.pdf"
    assert records[1].summary == ""


def test_load_raw_records_round_trip(tmp_path) -> None:
    expected = parse_crossref_payload(_payload())
    snapshot = tmp_path / "crossref_records.json"
    snapshot.write_text(json.dumps([asdict(record) for record in expected]), encoding="utf-8")

    assert load_raw_records(snapshot) == expected


def test_fetch_retries_429_and_saves_both_raw_artifacts(monkeypatch, tmp_path) -> None:
    responses = [_response(429, {"Retry-After": "0"}), _response(200)]
    calls = []

    def fake_get(*args, **kwargs):
        calls.append((args, kwargs))
        response = responses.pop(0)
        if response.status_code == 200:
            response._content = json.dumps(_payload()).encode()
        return response

    monkeypatch.setattr("ingestion.crossref.requests.get", fake_get)
    monkeypatch.setattr("ingestion.crossref.time.sleep", lambda _: None)
    settings = SimpleNamespace(
        source_query="machine learning",
        source_filter="has-abstract:true",
        max_results=2,
        paths=SimpleNamespace(
            raw_api_response=tmp_path / "raw" / "crossref_response.json",
            raw_records_json=tmp_path / "raw" / "crossref_records.json",
        ),
    )

    records = fetch_source_records(settings)

    assert len(calls) == 2
    assert calls[0][1]["params"] == {"query": "machine learning", "filter": "has-abstract:true", "rows": 2}
    assert settings.paths.raw_api_response.exists()
    assert load_raw_records(settings.paths.raw_records_json) == records


def test_lineage_audit_and_handoff_identify_cleaning_ready_snapshot(tmp_path) -> None:
    raw_response = tmp_path / "raw" / "crossref_response.json"
    raw_records = tmp_path / "raw" / "crossref_records.json"
    raw_response.parent.mkdir()
    raw_response.write_text(json.dumps(_payload()), encoding="utf-8")
    raw_records.write_text(
        json.dumps([asdict(record) for record in parse_crossref_payload(_payload())]),
        encoding="utf-8",
    )
    settings = SimpleNamespace(
        paths=SimpleNamespace(
            raw_api_response=raw_response,
            raw_records_json=raw_records,
            raw_lineage_report=tmp_path / "raw" / "crossref_lineage_report.json",
            raw_handoff_markdown=tmp_path / "raw" / "crossref_handoff.md",
        )
    )

    report = write_raw_lineage_handoff(settings)

    assert report["snapshot_matches_reparse"] is True
    assert report["cleaning_input_ready"] is True
    assert report["duplicate_snapshot_paper_ids"] == []
    assert audit_raw_lineage(settings) == report
    assert settings.paths.raw_lineage_report.exists()
    assert settings.paths.raw_handoff_markdown.exists()


def _response(status_code: int, headers: dict[str, str] | None = None) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.headers.update(headers or {})
    response.url = "https://api.crossref.org/works"
    return response
