import os
import re
from typing import List

import fitz
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_safe_upload_path(upload_dir: str, filename: str) -> tuple[str, str]:
    safe_name = secure_filename(filename)
    if not safe_name:
        raise ValueError("유효하지 않은 파일명입니다.")
    return safe_name, os.path.join(upload_dir, safe_name)


def extract_text_from_pdf(file_path: str) -> str:
    texts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            texts.append(page.get_text("text"))

    merged = "\n".join(texts).strip()
    if len(merged) < 30:
        raise ValueError("PDF에서 읽을 수 있는 텍스트를 찾지 못했습니다. (스캔본/OCR 필요 가능)")
    return merged


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def shrink_text(text: str, max_chars: int = 18000) -> str:
    cleaned = normalize_whitespace(text)
    if len(cleaned) <= max_chars:
        return cleaned
    head = cleaned[: max_chars // 2]
    tail = cleaned[-max_chars // 2 :]
    return f"{head}\n... (중략) ...\n{tail}"


def extract_relevant_passages(
    text: str,
    keywords: List[str],
    window: int = 2,
    max_chars: int = 12000,
) -> tuple[str, bool]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", False

    lowered_keywords = [k.lower().strip() for k in keywords if k and k.strip()]
    if not lowered_keywords:
        return shrink_text(text, max_chars=max_chars), True

    picked = set()
    for i, line in enumerate(lines):
        lower_line = line.lower()
        if any(kw in lower_line for kw in lowered_keywords):
            for j in range(max(0, i - window), min(len(lines), i + window + 1)):
                picked.add(j)

    if not picked:
        fallback_context = (
            "키워드 기반 직접 문맥을 충분히 찾지 못했습니다. 아래 키워드 중심으로 정의/개념/명령어 사용법 문제를 생성하세요:\n"
            + ", ".join(keywords)
        )
        return fallback_context, False

    selected = "\n".join(lines[idx] for idx in sorted(picked))
    return shrink_text(selected, max_chars=max_chars), True
