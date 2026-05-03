from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from sapix_filename.cli import main


_JP_FONT = "HeiseiKakuGo-W5"


def _ensure_japanese_font_registered() -> None:
    if _JP_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(_JP_FONT))


def _make_pdf(path: Path, *, token: str | None) -> None:
    c = canvas.Canvas(str(path))
    if token is not None:
        c.setFont("Helvetica", 14)
        c.drawString(72, 750, token)
        _ensure_japanese_font_registered()
        c.setFont(_JP_FONT, 12)
        c.drawString(72, 700, "解答と解説")
    c.setFont("Helvetica", 12)
    c.drawString(300, 30, "1")
    c.showPage()
    c.setFont("Helvetica", 12)
    c.drawString(300, 30, "2")
    c.showPage()
    c.setFont("Helvetica", 12)
    c.drawString(300, 30, "3")
    c.showPage()
    c.save()


def test_cli_prints_original_name_when_no_token(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    _make_pdf(pdf, token=None)
    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "orig.pdf"


def test_cli_prints_proposed_name(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    _make_pdf(pdf, token="350-01")
    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("350-01_Answer_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_prints_name_only_with_flag(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    _make_pdf(pdf, token="350-01")
    rc = main(["--no-ai", "--name-only", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "350-01_Answer_orig.pdf"


def test_cli_prints_question_tag(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "350-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "国語")
    c.drawString(72, 680, "問題・解答用紙")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("350-01_Question_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_prints_exam_tag(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "61-01")
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 700, "入試演習問題")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("61-01_Exam_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_prints_gs_tokun_gtk(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "GTK-01①")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("算数GTK-01①_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_prints_gs_tokun_gs_with_subject(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "社会GS-01")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("社会GS-01_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_gs_tokun_no_tag_even_with_answer_text(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "GS特訓")
    c.drawString(72, 730, "社会GS-01")
    c.drawString(72, 710, "解答と解説")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("社会GS-01_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_prints_second_format_math_basic_test(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "算数基礎力定着テスト06①")
    c.drawString(72, 720, "解答と解説")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("算数基礎力定着テスト06①_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'


def test_cli_prints_ws_subject(tmp_path: Path, capsys) -> None:
    pdf = tmp_path / "orig.pdf"
    c = canvas.Canvas(str(pdf))
    _ensure_japanese_font_registered()
    c.setFont(_JP_FONT, 12)
    c.drawString(72, 750, "国語")
    c.drawString(72, 730, "WS-01")
    c.showPage()
    c.save()

    rc = main(["--no-ai", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    src = pdf.resolve()
    dst = src.with_name("国語WS-01_orig.pdf")
    assert out == f'mv "{src}" "{dst}"'
