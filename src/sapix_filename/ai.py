from __future__ import annotations

import base64
import os
import re

from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from sapix_filename.errors import AiExtractionError


_COVER_ID_RE = re.compile(
    r"\b(((?:[A-Z]{1,2}\d{0,4}[A-Z]?\d?|\d{2,4}[A-Z]?\d?)-\d{2}))\b",
    re.IGNORECASE,
)


_MATH_BASIC_TEST_RE = re.compile(r"\b(\d{2}[①-⑳])\b")


_GS_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(GTK-\d{2}[①-⑳]?|GS-\d{2}|\d{2}[①-⑳]?)(?![A-Za-z0-9①-⑳])",
    re.IGNORECASE,
)


_SUBJECT_RE = re.compile(r"(国語|算数|理科|社会)")


def _get_client(api_key_env: str) -> OpenAI:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise AiExtractionError(f"Missing API key env var: {api_key_env}")
    return OpenAI(api_key=api_key)


def _image_data_url(png_bytes: bytes) -> str:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


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
        "You are classifying a scanned Japanese study handout. Determine which label applies.\n"
        "- If the document contains the phrase '入試演習問題', return 'Exam'.\n"
        "- Else if the document contains the phrase '国語' AND also contains '問題・解答用紙', return 'Question'.\n"
        "- Else if the document contains the phrase '解答と解説', return 'Answer'.\n"
        "- Else return 'NONE'.\n"
        "Return ONLY one of: Exam, Question, Answer, NONE."
    )

    content: list[dict] = [{"type": "input_text", "text": prompt}]
    for png in png_pages:
        content.append({"type": "input_image", "image_url": _image_data_url(png)})

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

    text = (resp.output_text or "").strip()
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


def extract_gs_token_from_png(
    png_bytes: bytes,
    *,
    model: str,
    api_key_env: str,
) -> str | None:
    client = _get_client(api_key_env)

    prompt = (
        "You are reading the first page of a scanned Japanese study handout. "
        "If the page contains the phrase 'GS特訓', extract the token that follows it. "
        "Accepted formats: 'GTK-01①' (GTK followed by two digits and optional circled number), or 'GS-01' (GS followed by two digits). "
        "Return ONLY the token (e.g., GTK-01①, GS-01). If the phrase is not present or you cannot find the token, return 'NONE'."
    )

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": _image_data_url(png_bytes)},
                    ],
                }
            ],
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

    text = (resp.output_text or "").strip()
    if not text or text.upper() == "NONE":
        return None

    m = _GS_TOKEN_RE.search(text)
    if not m:
        return None
    return m.group(1).upper()


def extract_math_basic_test_token_from_png(
    png_bytes: bytes,
    *,
    model: str,
    api_key_env: str,
) -> str | None:
    client = _get_client(api_key_env)

    prompt = (
        "You are reading the top-left area of the first page of a scanned Japanese handout. "
        "If the page contains the exact phrase '算数基礎力定着テスト', extract the token that follows it: "
        "two digits and a circled number like '06①'. "
        "Return ONLY that token (e.g., 06①). If the phrase is not present or you cannot find the token, return 'NONE'."
    )

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": _image_data_url(png_bytes)},
                    ],
                }
            ],
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

    text = (resp.output_text or "").strip()
    if not text or text.upper() == "NONE":
        return None

    m = _MATH_BASIC_TEST_RE.search(text)
    if not m:
        return None
    return m.group(1)


def extract_subject_from_png(
    png_bytes: bytes,
    *,
    model: str,
    api_key_env: str,
) -> str | None:
    client = _get_client(api_key_env)

    prompt = (
        "You are reading the cover of a scanned Japanese study handout. "
        "Extract the subject if present. Allowed subjects are: 国語, 算数, 理科, 社会. "
        "Return ONLY one of those subjects. If none are present, return 'NONE'."
    )

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": _image_data_url(png_bytes)},
                    ],
                }
            ],
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

    text = (resp.output_text or "").strip()
    if not text or text.upper() == "NONE":
        return None
    m = _SUBJECT_RE.search(text)
    if not m:
        return None
    return m.group(1)


def extract_cover_id_from_png(
    png_bytes: bytes,
    *,
    model: str,
    api_key_env: str,
) -> str | None:
    client = _get_client(api_key_env)

    prompt = (
        "You are extracting an identifier printed inside a rectangular box on the cover of a scanned Japanese study handout. "
        "Return ONLY the identifier. Accepted formats include: 'H350-01', '62A-01', 'WS-01', '640-01', '61-01'. "
        "If you cannot find it, return 'NONE'."
    )

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": _image_data_url(png_bytes),
                        },
                    ],
                }
            ],
        )
    except RateLimitError as e:
        raise AiExtractionError(
            "OpenAI API quota/rate limit exceeded. "
            "Either wait, add billing, or run with --no-ai. "
            f"Details: {e}"
        ) from e
    except AuthenticationError as e:
        raise AiExtractionError(
            "OpenAI API authentication failed. Check your API key. "
            f"Details: {e}"
        ) from e
    except (APIConnectionError, APIError) as e:
        raise AiExtractionError(
            "OpenAI API request failed. Please retry later or run with --no-ai. "
            f"Details: {e}"
        ) from e

    text = (resp.output_text or "").strip()
    if not text or text.upper() == "NONE":
        return None

    m = _COVER_ID_RE.search(text)
    if m:
        return m.group(1).upper()

    m = _COVER_ID_RE.search(text.replace(" ", ""))
    if m:
        return m.group(1).upper()

    return None


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

    try:
        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": _image_data_url(png_bytes),
                        },
                    ],
                }
            ],
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

    text = (resp.output_text or "").strip()
    if not text or text.upper() == "NONE":
        return None

    m = re.search(r"\b(\d{1,4})\b", text)
    if not m:
        return None
    return int(m.group(1))
