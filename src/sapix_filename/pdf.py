from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from sapix_filename.ai import (
    extract_cover_id_from_png,
    extract_document_tag_from_pngs,
    extract_footer_page_number_from_png,
    extract_gs_token_from_png,
    extract_math_basic_test_token_from_png,
    extract_subject_from_png,
)
from sapix_filename.errors import AiExtractionError
from sapix_filename.errors import PageNumberValidationError


_FILENAME_TOKEN_RE = re.compile(
    r"\b(((?:[A-Z]{1,2}\d{0,4}[A-Z]?\d?|\d{2,4}[A-Z]?\d?)-\d{2}|\d{4,6}))\b",
    re.IGNORECASE,
)


_GS_TRIGGER_TEXT_RE = re.compile(r"GS特訓")


_GS_TOKEN_TEXT_RE = re.compile(
    r"(?<![A-Za-z0-9])(GTK-\d{2}[①-⑳]?|GS-\d{2}|\d{2}[①-⑳]?)(?![A-Za-z0-9①-⑳])",
    re.IGNORECASE,
)


_MATH_BASIC_TEST_TEXT_RE = re.compile(r"算数基礎力定着テスト\s*(\d{2}[①-⑳])")


_SUBJECT_TEXT_RE = re.compile(r"(国語|算数|理科|社会)")


@dataclass(frozen=True)
class PdfAnalysis:
    proposed_stem: str | None
    page_count: int


def _choose_best_filename_token(candidates: list[str]) -> str | None:
    if not candidates:
        return None

    def score(tok: str) -> tuple[int, int, int, int]:
        has_prefix_letter = 1 if re.match(r"^[A-Z]{1,2}\d{3}-\d{2}$", tok, re.IGNORECASE) else 0
        hyphen = 1 if "-" in tok else 0
        digits = sum(1 for c in tok if c.isdigit())
        length = len(tok)
        return (has_prefix_letter, hyphen, digits, -length)

    return sorted(candidates, key=score, reverse=True)[0]


def _extract_filename_tokens(text: str) -> list[str]:
    return [match.group(1) for match in _FILENAME_TOKEN_RE.finditer(text)]


def _page_region_to_png_bytes(page: fitz.Page, rect: fitz.Rect, *, zoom: float = 3.0) -> bytes:
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    return pix.tobytes("png")


def detect_filename_tag(
    pdf_path: Path,
    *,
    enable_ai: bool = False,
    ai_model: str = "gpt-5.4-mini",
    api_key_env: str = "OPENAI_API_KEY",
) -> str | None:
    with fitz.open(pdf_path) as doc:
        all_text_parts: list[str] = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            all_text_parts.append(page.get_text("text"))

        all_text = "\n".join(all_text_parts)
        if "入試演習問題" in all_text:
            return "Exam"
        if "国語" in all_text and "問題・解答用紙" in all_text:
            return "Question"
        if "解答と解説" in all_text:
            return "Answer"

        if not enable_ai:
            return None

        try:
            png_pages: list[bytes] = []
            for i in range(min(doc.page_count, 3)):
                page = doc.load_page(i)
                png_pages.append(_page_region_to_png_bytes(page, page.rect, zoom=2.5))
            return extract_document_tag_from_pngs(
                png_pages,
                model=ai_model,
                api_key_env=api_key_env,
            )
        except AiExtractionError:
            return None


def propose_filename_stem(
    pdf_path: Path,
    *,
    enable_ai: bool = True,
    ai_model: str = "gpt-5.4-mini",
    api_key_env: str = "OPENAI_API_KEY",
) -> str | None:
    first_page_png: bytes | None = None
    with fitz.open(pdf_path) as doc:
        if doc.page_count < 1:
            return None
        first_page = doc.load_page(0)
        text = first_page.get_text("text")
        if enable_ai:
            first_page_png = _page_region_to_png_bytes(first_page, first_page.rect, zoom=3.0)

    if _GS_TRIGGER_TEXT_RE.search(text):
        m_gs = _GS_TOKEN_TEXT_RE.search(text)
        if m_gs:
            tok = m_gs.group(1).upper()
            if tok.startswith("GTK-"):
                return f"算数{tok}"
            m_subj = _SUBJECT_TEXT_RE.search(text)
            subject = m_subj.group(1) if m_subj else None
            if subject:
                return f"{subject}{tok}"
            return tok
    elif enable_ai and first_page_png is not None:
        try:
            gs_tok = extract_gs_token_from_png(
                first_page_png,
                model=ai_model,
                api_key_env=api_key_env,
            )
        except AiExtractionError:
            gs_tok = None
        if gs_tok is not None:
            gs_tok = gs_tok.upper()
            if gs_tok.startswith("GTK-"):
                return f"算数{gs_tok}"
            try:
                subject = extract_subject_from_png(
                    first_page_png,
                    model=ai_model,
                    api_key_env=api_key_env,
                )
            except AiExtractionError:
                subject = None
            if subject:
                return f"{subject}{gs_tok}"
            return gs_tok

    m = _MATH_BASIC_TEST_TEXT_RE.search(text)
    if m:
        return f"算数基礎力定着テスト{m.group(1)}"

    matches = _extract_filename_tokens(text)
    if matches:
        tok = _choose_best_filename_token(matches)
        if tok is None:
            return None

        if tok.upper().startswith("WS-"):
            m_subj = _SUBJECT_TEXT_RE.search(text)
            if m_subj:
                return f"{m_subj.group(1)}{tok.upper()}"
        return tok.upper()

    if not enable_ai:
        return None

    if first_page_png is None:
        return None

    token = extract_math_basic_test_token_from_png(
        first_page_png,
        model=ai_model,
        api_key_env=api_key_env,
    )
    if token is not None:
        return f"算数基礎力定着テスト{token}"

    cover_id = extract_cover_id_from_png(
        first_page_png,
        model=ai_model,
        api_key_env=api_key_env,
    )
    if cover_id is not None:
        if cover_id.upper().startswith("WS-"):
            try:
                subject = extract_subject_from_png(
                    first_page_png,
                    model=ai_model,
                    api_key_env=api_key_env,
                )
            except AiExtractionError:
                subject = None
            if subject:
                return f"{subject}{cover_id.upper()}"
        return cover_id.upper()

    return None


def _extract_footer_page_number(page: fitz.Page) -> int | None:
    blocks = page.get_text("blocks")
    if not blocks:
        return None

    page_height = float(page.rect.height)
    footer_y_threshold = page_height * 0.85

    footer_text_parts: list[str] = []
    for block in blocks:
        x0, y0, x1, y1, text, _block_no, _block_type = block
        if float(y0) >= footer_y_threshold and isinstance(text, str):
            footer_text_parts.append(text)

    footer_text = " ".join(footer_text_parts)
    m = re.search(r"\b(\d{1,4})\b", footer_text)
    if not m:
        return None
    return int(m.group(1))


def validate_page_numbers(
    pdf_path: Path,
    *,
    enable_ai: bool = False,
    ai_model: str = "gpt-5.4-mini",
    api_key_env: str = "OPENAI_API_KEY",
) -> None:
    with fitz.open(pdf_path) as doc:
        page_count = doc.page_count
        if page_count <= 2:
            return

        numbers_in_order: list[int] = []
        pages_with_numbers = 0
        for i in range(page_count):
            page = doc.load_page(i)
            n = _extract_footer_page_number(page)
            if n is None and enable_ai:
                page_rect = page.rect
                footer_rect = fitz.Rect(
                    page_rect.x0,
                    page_rect.y0 + (page_rect.height * 0.80),
                    page_rect.x1,
                    page_rect.y1,
                )
                png_bytes = _page_region_to_png_bytes(page, footer_rect, zoom=3.0)
                n = extract_footer_page_number_from_png(
                    png_bytes,
                    model=ai_model,
                    api_key_env=api_key_env,
                )
            if n is None:
                continue
            pages_with_numbers += 1
            numbers_in_order.append(n)

        if not numbers_in_order:
            return

        seen: set[int] = set()
        prev: int | None = None
        for n in numbers_in_order:
            if n in seen:
                raise PageNumberValidationError(
                    f"Duplicate page number found in footer: {n}"
                )
            seen.add(n)

            if prev is not None and n != prev + 1:
                raise PageNumberValidationError(
                    f"Non-consecutive page numbers in footer: {prev} -> {n}"
                )
            prev = n

        if pages_with_numbers == page_count:
            if max(numbers_in_order) != page_count:
                raise PageNumberValidationError(
                    "Page number and actual page count do not match: "
                    f"max_footer={max(numbers_in_order)} actual_pages={page_count}"
                )


def analyze_pdf(pdf_path: Path) -> PdfAnalysis:
    proposed = propose_filename_stem(pdf_path)
    with fitz.open(pdf_path) as doc:
        count = doc.page_count
    return PdfAnalysis(proposed_stem=proposed, page_count=count)
