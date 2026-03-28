from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sapix_filename.errors import AiExtractionError
from sapix_filename.errors import PageNumberValidationError
from sapix_filename.pdf import detect_filename_tag, propose_filename_stem, validate_page_numbers


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sapix-filename")
    p.add_argument("pdf", type=Path, help="Target PDF file")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename the file on disk (default: print only)",
    )
    p.add_argument(
        "--name-only",
        action="store_true",
        help="Print only the proposed filename (default: print mv command)",
    )
    p.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI extraction (default: AI enabled)",
    )
    p.add_argument(
        "--ai-model",
        default="gpt-5.4-mini",
        help="OpenAI model name for vision extraction",
    )
    p.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable name that stores the OpenAI API key",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(sys.argv[1:] if argv is None else argv)
    pdf_path: Path = ns.pdf
    enable_ai = not ns.no_ai
    ai_model: str = ns.ai_model
    api_key_env: str = ns.api_key_env

    if not pdf_path.exists():
        print(f"File not found: {pdf_path}", file=sys.stderr)
        return 2

    try:
        validate_page_numbers(
            pdf_path,
            enable_ai=False,
        )
    except PageNumberValidationError as e:
        print(str(e), file=sys.stderr)
        return 1

    try:
        stem = propose_filename_stem(
            pdf_path,
            enable_ai=enable_ai,
            ai_model=ai_model,
            api_key_env=api_key_env,
        )
    except AiExtractionError as e:
        print(str(e), file=sys.stderr)
        stem = None
    if stem is None:
        print(str(pdf_path.name))
        return 0

    if stem.startswith("算数基礎力定着テスト"):
        tag_part = ""
    else:
        tag = detect_filename_tag(
            pdf_path,
            enable_ai=enable_ai,
            ai_model=ai_model,
            api_key_env=api_key_env,
        )
        tag_part = f"_{tag}" if tag is not None else ""
    new_name = f"{stem}{tag_part}_{pdf_path.stem}{pdf_path.suffix}"
    if not ns.apply:
        if ns.name_only:
            print(new_name)
            return 0
        src = pdf_path.resolve()
        dst = src.with_name(new_name)
        print(f'mv "{src}" "{dst}"')
        return 0

    new_path = pdf_path.with_name(new_name)
    if new_path.exists():
        print(f"Target already exists: {new_path}", file=sys.stderr)
        return 1

    pdf_path.rename(new_path)
    print(str(new_path.name))
    return 0
