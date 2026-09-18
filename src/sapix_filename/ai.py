from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from sapix_filename.errors import AiExtractionError


_COVER_ID_RE = re.compile(
    r"\b(((?:[A-Z]{1,4}\d{0,4}[A-Z]?\d?|\d{2,4}[A-Z]?\d?)-\d{2}))\b",
    re.IGNORECASE,
)


_MATH_BASIC_TEST_RE = re.compile(r"\b(\d{2}[①-⑳])\b")


_GS_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(GTK-\d{2}[①-⑳]?|GS-\d{2}|\d{2}[①-⑳]?)(?![A-Za-z0-9①-⑳])",
    re.IGNORECASE,
)


_SUBJECT_RE = re.compile(r"(国語|算数|理科|社会)")


@dataclass(frozen=True)
class CoverFields:
    gs_token: str | None
    math_token: str | None
    cover_id: str | None
    subject: str | None


def _get_client(api_key_env: str) -> OpenAI:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise AiExtractionError(f"Missing API key env var: {api_key_env}")
    return OpenAI(api_key=api_key)


def _image_data_url(png_bytes: bytes) -> str:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _request_output_text(client: OpenAI, *, model: str, content: list[dict]) -> str:
    try:
        resp = client.responses.create(
            model=model,
            input=[{"role": "user", "content": content}],
        )
    except RateLimitError as e:
        raise AiExtractionError(
            "OpenAI API quota/rate limit exceeded. "
            "Either wait, add billing, or disable AI features. "
            f"Details: {e}"
        ) from e
    except AuthenticationError as e:
        raise AiExtractionError(
            "OpenAI API authentication failed. Check your API key. "
            f"Details: {e}"
        ) from e
    except (APIConnectionError, APIError) as e:
        raise AiExtractionError(
            "OpenAI API request failed. Please retry later. "
            f"Details: {e}"
        ) from e

    return (resp.output_text or "").strip()


def extract_document_tag_from_pngs(
    png_pages: list[bytes],
    *,
    model: str,
    api_key_env: str,
) -> str | None:
    if not png_pages:
        return None

    client = _get_client(api_key_env)
    prompt = (
        "You are classifying only the cover page of a scanned Japanese study handout. Determine which label applies.\n"
        "- If the cover page contains the phrase '入試演習問題', return 'Exam'.\n"
        "- Else if the cover page contains the phrase '国語' AND also contains '問題・解答用紙', return 'Question'. "
        "Treat spaces or line breaks inside '問題・解答用紙' as the same phrase.\n"
        "- Else if the cover page explicitly contains an answer/explanation heading, return 'Answer'. "
        "Accept only headings where '解答' and '解説' are adjacent or separated only by 'と', '・', spaces, or line breaks, "
        "such as '解答と解説', '解答解説', or '解答・解説'. "
        "Do not infer Answer from general explanatory text, the lesson topic, photos, diagrams, later pages, or words like '裁判'/'審査'.\n"
        "- Else return 'NONE'.\n"
        "Return ONLY one of: Exam, Question, Answer, NONE."
    )

    content: list[dict] = [{"type": "input_text", "text": prompt}]
    for png in png_pages:
        content.append({"type": "input_image", "image_url": _image_data_url(png)})

    text = _request_output_text(client, model=model, content=content)
    if not text:
        return None

    normalized = text.strip().upper()
    if normalized == "NONE":
        return None
    if normalized == "EXAM":
        return "Exam"
    if normalized == "QUESTION":
        return "Question"
    if normalized == "ANSWER":
        return "Answer"
    return None


def _parse_cover_field(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.upper() == "NONE":
        return None
    return text


def _match_or_none(pattern: re.Pattern[str], text: str | None, *, upper: bool = False) -> str | None:
    if text is None:
        return None
    m = pattern.search(text)
    if not m:
        m = pattern.search(text.replace(" ", ""))
    if not m:
        return None
    return m.group(1).upper() if upper else m.group(1)


def extract_cover_fields_from_png(
    png_bytes: bytes,
    *,
    model: str,
    api_key_env: str,
) -> CoverFields:
    client = _get_client(api_key_env)

    prompt = (
        "You are reading the cover (first page) of a scanned Japanese study handout. "
        "Extract the following fields and return them as a single JSON object with exactly these keys:\n"
        '- "gs_token": if the page contains the phrase \'GS特訓\', the token that follows it. '
        "Formats: 'GTK-01①' (GTK, two digits, optional circled number), 'GS-01' (GS, two digits), or bare two digits like '01'. Otherwise null.\n"
        '- "math_token": if the page contains the exact phrase \'算数基礎力定着テスト\', the token that follows it: '
        "two digits and a circled number like '06①'. Otherwise null.\n"
        '- "cover_id": the identifier printed inside a rectangular box on the cover. '
        "Formats include: 'H350-01', '62A-01', 'WS-01', 'SS-01', 'SSWK-01', '640-01', '61-01'. Otherwise null.\n"
        '- "subject": the subject if present. Allowed: 国語, 算数, 理科, 社会. Otherwise null.\n'
        "Return ONLY the JSON object, no markdown fences, no extra text."
    )

    content: list[dict] = [
        {"type": "input_text", "text": prompt},
        {"type": "input_image", "image_url": _image_data_url(png_bytes)},
    ]

    text = _request_output_text(client, model=model, content=content)
    if not text:
        return CoverFields(None, None, None, None)

    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()

    try:
        data = json.loads(text)
    except ValueError:
        return CoverFields(None, None, None, None)
    if not isinstance(data, dict):
        return CoverFields(None, None, None, None)

    gs_token = _match_or_none(
        _GS_TOKEN_RE, _parse_cover_field(data.get("gs_token")), upper=True
    )
    math_token = _match_or_none(
        _MATH_BASIC_TEST_RE, _parse_cover_field(data.get("math_token"))
    )
    cover_id = _match_or_none(
        _COVER_ID_RE, _parse_cover_field(data.get("cover_id")), upper=True
    )
    subject = _match_or_none(
        _SUBJECT_RE, _parse_cover_field(data.get("subject"))
    )

    return CoverFields(
        gs_token=gs_token,
        math_token=math_token,
        cover_id=cover_id,
        subject=subject,
    )


def extract_footer_page_number_from_png(
    png_bytes: bytes,
    *,
    model: str,
    api_key_env: str,
) -> int | None:
    client = _get_client(api_key_env)

    prompt = (
        "You are reading a scanned PDF page footer. Extract the page number printed in the footer. "
        "Return ONLY an integer like 1, 2, 3. If there is no page number, return 'NONE'."
    )

    content: list[dict] = [
        {"type": "input_text", "text": prompt},
        {"type": "input_image", "image_url": _image_data_url(png_bytes)},
    ]

    text = _request_output_text(client, model=model, content=content)
    if not text or text.upper() == "NONE":
        return None

    m = re.search(r"\b(\d{1,4})\b", text)
    if not m:
        return None
    return int(m.group(1))
