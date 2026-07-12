from __future__ import annotations

import pytest

from sapix_filename.ai import (
    CoverFields,
    extract_cover_fields_from_png,
)
from sapix_filename.errors import AiExtractionError


def _patch_ai_response(monkeypatch: pytest.MonkeyPatch, output_text: str) -> None:
    monkeypatch.setattr("sapix_filename.ai._get_client", lambda api_key_env: object())
    monkeypatch.setattr(
        "sapix_filename.ai._request_output_text",
        lambda client, *, model, content: output_text,
    )


def test_extract_cover_fields_all_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(
        monkeypatch,
        '{"gs_token": "gtk-01①", "math_token": "06①", "cover_id": "h350-01", "subject": "社会"}',
    )
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields == CoverFields(
        gs_token="GTK-01①",
        math_token="06①",
        cover_id="H350-01",
        subject="社会",
    )


def test_extract_cover_fields_all_null(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(
        monkeypatch,
        '{"gs_token": null, "math_token": null, "cover_id": null, "subject": null}',
    )
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields == CoverFields(None, None, None, None)


def test_extract_cover_fields_none_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(
        monkeypatch,
        '{"gs_token": "NONE", "math_token": "NONE", "cover_id": "NONE", "subject": "NONE"}',
    )
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields == CoverFields(None, None, None, None)


def test_extract_cover_fields_markdown_fenced_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(
        monkeypatch,
        '```json\n{"gs_token": null, "math_token": null, "cover_id": "WS-01", "subject": "国語"}\n```',
    )
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields.cover_id == "WS-01"
    assert fields.subject == "国語"


def test_extract_cover_fields_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(monkeypatch, "not a json")
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields == CoverFields(None, None, None, None)


def test_extract_cover_fields_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(monkeypatch, "")
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields == CoverFields(None, None, None, None)


def test_extract_cover_fields_invalid_field_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ai_response(
        monkeypatch,
        '{"gs_token": "XYZ99", "math_token": "abc", "cover_id": 123, "subject": "英語"}',
    )
    fields = extract_cover_fields_from_png(b"png", model="m", api_key_env="ENV")
    assert fields == CoverFields(None, None, None, None)


def test_extract_cover_fields_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_ENV", raising=False)
    with pytest.raises(AiExtractionError):
        extract_cover_fields_from_png(b"png", model="m", api_key_env="MISSING_ENV")
