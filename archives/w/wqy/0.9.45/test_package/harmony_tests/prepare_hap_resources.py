#!/usr/bin/env python3
"""Stage the exact WQY TTC bytes and a per-build ID for the HarmonyOS HAP."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import uuid
import zlib
from pathlib import Path


EXPECTED_FONT_SIZE = 16_791_251
EXPECTED_FONT_SHA256 = "79c18ebe7b811951e8311bad7103ebeae8c337ed9988ea69e8a78a66cfe029b9"
FONT_NAME = "wqy-zenhei.ttc"
RUN_ID_NAME = "wqy-test-run-id.txt"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APP_ROOT = PROJECT_ROOT / "harmonyos_app"


def verify_font_bytes(
    font_bytes: bytes,
    *,
    expected_size: int = EXPECTED_FONT_SIZE,
    expected_sha256: str = EXPECTED_FONT_SHA256,
) -> str:
    """Reject any TTC bytes other than the version pinned by the Conan recipe."""
    if len(font_bytes) != expected_size:
        raise ValueError(f"TTC byte length mismatch: expected {expected_size}, got {len(font_bytes)}")
    actual = hashlib.sha256(font_bytes).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"TTC SHA-256 mismatch: expected {expected_sha256}, got {actual}")
    return actual


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _write_generated_icon(path: Path) -> None:
    """Generate a deterministic simple icon so the source tree stays text-only."""
    width = height = 64
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        for x in range(width):
            inside = 10 <= x < 54 and 10 <= y < 54
            stroke = inside and (x < 16 or x >= 48 or y < 16 or y >= 48)
            ink = inside and (x + y) % 10 < 3
            color = (16, 82, 112, 255) if stroke or ink else (246, 250, 252, 255)
            scanlines.extend(color)

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9)))
    png.extend(_png_chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def stage_resources(font_path: Path, app_root: Path) -> dict[str, object]:
    font_bytes = font_path.read_bytes()
    sha256 = verify_font_bytes(
        font_bytes,
        expected_size=EXPECTED_FONT_SIZE,
        expected_sha256=EXPECTED_FONT_SHA256,
    )

    rawfile_dir = app_root / "entry" / "src" / "main" / "resources" / "rawfile"
    rawfile_dir.mkdir(parents=True, exist_ok=True)
    staged_font = rawfile_dir / FONT_NAME
    staged_font.write_bytes(font_bytes)
    staged_sha256 = verify_font_bytes(
        staged_font.read_bytes(),
        expected_size=EXPECTED_FONT_SIZE,
        expected_sha256=EXPECTED_FONT_SHA256,
    )

    run_id = uuid.uuid4().hex
    (rawfile_dir / RUN_ID_NAME).write_text(run_id + "\n", encoding="ascii")

    for relative in (
        Path("AppScope/resources/base/media/app_icon.png"),
        Path("entry/src/main/resources/base/media/app_icon.png"),
    ):
        icon_path = app_root / relative
        if icon_path.with_suffix(".svg").is_file():
            icon_path.unlink(missing_ok=True)
            continue
        _write_generated_icon(icon_path)

    return {
        "font": str(staged_font),
        "byte_length": len(font_bytes),
        "sha256": staged_sha256,
        "run_id": run_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="TTC from the Conan package")
    parser.add_argument("--app-root", type=Path, default=DEFAULT_APP_ROOT)
    args = parser.parse_args()

    result = stage_resources(args.font, args.app_root)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
