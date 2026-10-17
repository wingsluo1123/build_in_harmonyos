#!/usr/bin/env python3
"""Build the PNG wallpaper fixtures for the wpmeta consumer test.

usage: make_wallpaper.py <variant: normal|dark> <output .png>

Why this exists
---------------
This repository must not carry new binary files inside a PR: the platform CI
`checkout-pr` step fetches the PR as a `.diff` from GitCode and applies it with
`git apply`, and that diff attaches no binary data section for added binary
files (only a one-line "differ" placeholder). git then reports

    error: missing binary patch data for '.../ohos_wallpaper.png'
    error: binary patch does not apply to '.../ohos_wallpaper.png'

and the checkout step fails before anything is built. The dbskkd-cdb
test_package documents the same platform constraint and rebuilds its binary
.cdb fixture at test time from committed plain text.

The two wallpaper fixtures are therefore generated here, at test time, with no
committed binary input at all: the pixel data is computed procedurally. Output
is deterministic (fixed zlib level 9, filter byte 0 on every scanline, no
timestamps), so the PNG is byte-identical on every run and the C4 copy-mapping
assertion (`cmp` of the packaged copy against the generated fixture) remains
meaningful.

Both variants are valid 64x64 PNGs (wpmeta derives the output file name
`64x64.png` from the decoded dimensions) and are byte-distinct from each other,
so a swapped or corrupted copy is detected.
"""
import struct
import sys
import zlib

WIDTH = HEIGHT = 64


def pixels(variant):
    """Deterministic 64x64 RGB pixel data for the requested variant.

    normal: blue gradient, bright at the top-left.
    dark:   purple/black gradient with the opposite brightness direction.

    The two variants share no pixel value, so their PNG encodings differ.
    """
    out = bytearray()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if variant == "normal":
                r = 2 + (x * 120) // (WIDTH - 1)
                g = 60 + (y * 100) // (HEIGHT - 1)
                b = 136 + ((x + y) * 100) // (WIDTH + HEIGHT - 2)
            else:  # dark
                r = 90 - (x * 70) // (WIDTH - 1)
                g = 20 + (y * 30) // (HEIGHT - 1)
                b = 120 - (y * 90) // (HEIGHT - 1)
            out += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
    return bytes(out)


def png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(rgb):
    """Encode WIDTH x HEIGHT RGB bytes as a deterministic 8-bit RGB PNG."""
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    # every scanline is prefixed with filter byte 0 (None)
    stride = WIDTH * 3
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride]
                   for y in range(HEIGHT))
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(raw, 9))
            + png_chunk(b"IEND", b""))


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("normal", "dark"):
        raise SystemExit(__doc__)
    variant, out_path = sys.argv[1], sys.argv[2]
    data = encode_png(pixels(variant))
    with open(out_path, "wb") as fh:
        fh.write(data)
    print(f"generated {out_path} ({len(data)} bytes, {WIDTH}x{HEIGHT} PNG, "
          f"variant={variant})")


if __name__ == "__main__":
    main()
