from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from sapix_filename.errors import PageNumberValidationError
from sapix_filename.pdf import detect_filename_tag, propose_filename_stem, validate_page_numbers


_JP_FONT = "HeiseiKakuGo-W5"


def _ensure_japanese_font_registered() -> None:
    if _JP_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(_JP_FONT))


def _make_pdf(path: Path, *, token: str | None, page_numbers: list[int | None]) -> None:
    c = canvas.Canvas(str(path))
    for idx, num in enumerate(page_numbers):
        if idx == 0 and token is not None:
            c.setFont("Helvetica", 14)
            c.drawString(72, 750, f"[{token}]")

        if num is not None:
            c.setFont("Helvetica", 12)
            c.drawString(300, 30, str(num))

        c.showPage()
    c.save()


def test_propose_filename_stem_found(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _make_pdf(pdf, token="350-01", page_numbers=[1, 2, 3])
    assert propose_filename_stem(pdf, enable_ai=False) == "350-01"


def test_propose_filename_stem_not_found(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _make_pdf(pdf, token=None, page_numbers=[1, 2, 3])
    assert propose_filename_stem(pdf, enable_ai=False) is None


def test_propose_filename_stem_second_format(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "算数基礎力定着テスト06①")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "算数基礎力定着テスト06①"


def test_propose_filename_stem_ws_subject(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "国語")
    c.drawString(72, 730, "WS-01")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "国語WS-01"


def test_propose_filename_stem_ss_subject(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "算数")
    c.drawString(72, 730, "SS-01")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "算数SS-01"


def test_propose_filename_stem_sswk_example(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "SSWK-01")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "SSWK-01"


def test_propose_filename_stem_gs_tokun_gtk(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "GTK-01①")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "算数GTK-01①"


def test_propose_filename_stem_gs_tokun_gs_with_subject(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "社会GS-01")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "社会GS-01"


def test_propose_filename_stem_gs_tokun_bare_number(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "社会")
    c.drawString(72, 710, "01")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "社会01"


def test_propose_filename_stem_gs_tokun_gs_no_subject(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "GS-01")
    c.showPage()
    c.save()
    assert propose_filename_stem(pdf, enable_ai=False) == "GS-01"


def test_validate_page_numbers_ok_with_missing_numbers(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _make_pdf(pdf, token="350-01", page_numbers=[1, None, 2, 3])
    validate_page_numbers(pdf, enable_ai=False)


def test_validate_page_numbers_duplicate(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _make_pdf(pdf, token="350-01", page_numbers=[1, 2, 2, 3])
    with pytest.raises(PageNumberValidationError):
        validate_page_numbers(pdf, enable_ai=False)


def test_validate_page_numbers_non_consecutive(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _make_pdf(pdf, token="350-01", page_numbers=[1, 3, 4])
    with pytest.raises(PageNumberValidationError):
        validate_page_numbers(pdf, enable_ai=False)


def test_validate_page_numbers_ignored_when_two_pages(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    _make_pdf(pdf, token="350-01", page_numbers=[1, 2])
    validate_page_numbers(pdf, enable_ai=False)


def test_detect_filename_tag_answer(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "350-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "解答と解説")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf) == "Answer"


def test_detect_filename_tag_answer_without_to(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "350-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "解答解説")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf) == "Answer"


def test_detect_filename_tag_answer_with_middle_dot(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "350-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "解答・解説")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf) == "Answer"


def test_detect_filename_tag_does_not_infer_answer_from_topic_words(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "640-13")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "三権分立")
    c.drawString(72, 680, "内閣と裁判所")
    c.drawString(72, 660, "最高裁判所裁判官の国民審査")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf, enable_ai=False) is None


def test_detect_filename_tag_ignores_answer_text_after_cover(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "640-13")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "デイリーサピックス")
    c.drawString(72, 680, "小学6年 社会")
    c.showPage()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "今回の学習内容")
    c.drawString(72, 680, "解答と解説")
    c.drawString(72, 660, "テキストの中に出てきた問題の答えです。")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf, enable_ai=False) is None


def test_detect_filename_tag_sends_only_cover_to_ai(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "640-13")
    c.showPage()
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "解答と解説")
    c.showPage()
    c.save()

    page_counts: list[int] = []

    def fake_extract_document_tag_from_pngs(
        png_pages: list[bytes],
        *,
        model: str,
        api_key_env: str,
    ) -> None:
        page_counts.append(len(png_pages))
        return None

    monkeypatch.setattr(
        "sapix_filename.pdf.extract_document_tag_from_pngs",
        fake_extract_document_tag_from_pngs,
    )

    assert detect_filename_tag(pdf, enable_ai=True) is None
    assert page_counts == [1]


def test_detect_filename_tag_question(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "350-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "国語")
    c.drawString(72, 680, "問題・解答用紙")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf) == "Question"


def test_detect_filename_tag_question_with_spaced_phrase_before_answer(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "350-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "国語")
    c.drawString(72, 680, "問題 ・")
    c.drawString(72, 660, "解答用紙")
    c.drawString(72, 640, "解答と解説")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf) == "Question"


def test_detect_filename_tag_exam(tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "61-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "入試演習問題")
    c.showPage()
    c.save()
    assert detect_filename_tag(pdf) == "Exam"
