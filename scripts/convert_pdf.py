#!/usr/bin/env python3
"""
PDF → 슬라이드 이미지 변환 스크립트.
PDF 파일을 1920x1080 JPG 이미지로 변환하고 meta.json을 생성한다.
1장씩 변환하여 메모리 사용량을 최소화한다 (GitHub Actions 대응).
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from pdf2image import convert_from_path
from PIL import Image

# --- 설정 ---
OUTPUT_DIR = "Web/slides"
META_PATH = "Web/meta.json"
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
JPG_QUALITY = 85
DPI = 150  # 1920x1080 출력에는 150 DPI로 충분. 200→150 변경 (메모리 절약)


def get_total_pages(pdf_path: str) -> int:
    """pdfinfo로 총 페이지 수를 미리 확인한다."""
    result = subprocess.run(
        ["pdfinfo", pdf_path], capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError(f"pdfinfo로 페이지 수를 확인할 수 없습니다: {pdf_path}")


def convert_pdf_to_slides(pdf_path: str) -> None:
    """PDF를 슬라이드 이미지로 변환한다. 1장씩 처리하여 메모리를 절약한다."""

    pdf_filename = os.path.basename(pdf_path)
    total_pages = get_total_pages(pdf_path)
    print(f"[1/4] PDF 확인: {pdf_filename} ({total_pages}페이지)")

    # 기존 slides 폴더 전체 삭제 후 재생성
    print(f"[2/4] {OUTPUT_DIR}/ 폴더 초기화")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 1장씩 변환 (메모리 절약: 한번에 1페이지만 메모리에 로드)
    print(f"[3/4] 이미지 변환 중 ({TARGET_WIDTH}x{TARGET_HEIGHT}, JPG {JPG_QUALITY}%, DPI {DPI})")
    for page_num in range(1, total_pages + 1):
        # first_page/last_page로 1장씩만 렌더링
        pages = convert_from_path(
            pdf_path, dpi=DPI, first_page=page_num, last_page=page_num
        )
        page = pages[0]

        # 1920x1080으로 리사이즈
        resized = page.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)
        if resized.mode != "RGB":
            resized = resized.convert("RGB")

        filename = f"slide_{page_num:03d}.jpg"
        filepath = os.path.join(OUTPUT_DIR, filename)
        resized.save(filepath, "JPEG", quality=JPG_QUALITY)

        # 메모리 즉시 해제
        del pages, page, resized

        file_size_kb = os.path.getsize(filepath) / 1024
        print(f"       [{page_num}/{total_pages}] {filename} ({file_size_kb:.0f} KB)")

    # meta.json 생성
    print(f"[4/4] meta.json 생성")
    meta = {
        "total_pages": total_pages,
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_pdf": pdf_filename,
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"\n완료! {total_pages}장 변환됨 → {OUTPUT_DIR}/")
    print(f"meta.json → {META_PATH}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"사용법: python {sys.argv[0]} <PDF 파일 경로>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"에러: 파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    convert_pdf_to_slides(pdf_path)
