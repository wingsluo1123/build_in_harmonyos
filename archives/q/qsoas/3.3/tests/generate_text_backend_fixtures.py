#!/usr/bin/env python3
"""Generate the deterministic fixtures used by upstream text-backend tests.

This is a dependency-free equivalent of tests/text-backends/generate-data.rb.
It exists because Ruby is not part of the published OHOS build/test closure.
"""

from __future__ import annotations

import math
from pathlib import Path


def ruby_float(value: float) -> str:
    """Match the compact decimal form used by Ruby Float#to_s here."""
    return repr(value)


def write_fixture(path: Path, separator: str, prefix: str, suffix: str,
                  encoding: str | None) -> None:
    rows = []
    for index in range(200):
        x_value = index / 199.0 * 2.0 * math.pi
        rows.append((x_value, math.sin(x_value), index, math.cos(x_value)))

    text = "".join(
        prefix + separator.join(ruby_float(float(value)) if not isinstance(value, int)
                                else str(value) for value in row) + suffix + "\n"
        for row in rows
    )
    if encoding is None:
        path.write_text(text, encoding="utf-8")
    else:
        byte_order_mark = b"\xff\xfe" if encoding == "utf-16-le" else b"\xfe\xff"
        path.write_bytes(byte_order_mark + text.encode(encoding))


def main() -> None:
    output = Path.cwd() / "data"
    output.mkdir(exist_ok=True)
    separators = {
        "tab": "\t",
        "space": " ",
        "tabs": "\t\t",
        "spaces": "   ",
        "comma": ",",
        "colon": ";",
    }
    decorations = {
        "": ("", ""),
        "-p1": ("  ", ""),
        "-p2": ("\t", ""),
        "-s1": ("", "  "),
        "-s2": ("", "\t"),
        "-sp1": ("  ", "  "),
        "-sp2": ("\t", "\t"),
    }
    encodings = {
        "": None,
        "-UTF-16LE": "utf-16-le",
        "-UTF-16BE": "utf-16-be",
    }
    for separator_name, separator in separators.items():
        for encoding_suffix, encoding in encodings.items():
            for decoration, (prefix, suffix) in decorations.items():
                name = f"gen-{separator_name}{decoration}{encoding_suffix}.dat"
                write_fixture(output / name, separator, prefix, suffix, encoding)


if __name__ == "__main__":
    main()
