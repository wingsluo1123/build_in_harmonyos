#!/usr/bin/env python3
"""Generate a minimal, valid PDF fixture at test time.

Deliberately generated rather than committed: the PR must not add binary files
(CI applies the diff with `git apply`), so the fixture is synthesised here and its
xref offsets are computed, not hand-written.

The page carries:
  * one real text-showing operator (BT/Tj) so `pdftotext` has something to extract —
    a blank page would let a broken extractor "succeed" with an empty file, which is
    exactly the failure mode a side-effect assertion must avoid; and
  * one real 2x2 DeviceRGB FlateDecode image XObject, because xpdf's `pdfimages`
    writes **no file at all** for an image-less page (verified on a real 4.06 build:
    exit code 0, zero output files). Without an embedded image that tool's output
    cannot be asserted on at all.

The catalog additionally carries a `/Names /EmbeddedFiles` entry with one embedded
file, for the same reason: with zero attachments `pdfdetach -list` only prints
"0 embedded files", which cannot show that detaching *works*. An attachment lets the
test assert the listing by name AND a `-save` extraction round-trip.
"""
import sys
import zlib

TEXT_STR = b"Hello Xpdf OHOS"
ATTACH_NAME = b"ohos-attach.txt"
# Single line, no trailing newline: the shell test greps it as a fixed string.
ATTACH_BYTES = b"XPDF-OHOS-ATTACH-PAYLOAD-9f3a"

CONTENT = (b"q 120 0 0 120 72 560 cm /Im1 Do Q\n"
           b"BT /F1 18 Tf 72 500 Td (Hello Xpdf OHOS) Tj ET\n")

# 2x2 RGB: red, green / blue, white
IMAGE_RAW = bytes([
    255, 0, 0, 0, 255, 0,
    0, 0, 255, 255, 255, 255,
])


def build() -> bytes:
    comp = zlib.compress(IMAGE_RAW)

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R /Names << /EmbeddedFiles 9 0 R >> >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> /XObject << /Im1 6 0 R >> >> "
        b"/Contents 4 0 R >>",
        b"<< /Length " + str(len(CONTENT)).encode() + b" >>\nstream\n" + CONTENT + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length "
        + str(len(comp)).encode() + b" >>\nstream\n" + comp + b"\nendstream",
        # 7: the embedded file itself (uncompressed, so a -save round-trip is byte-exact)
        b"<< /Type /Embeddedfile /Length " + str(len(ATTACH_BYTES)).encode()
        + b" >>\nstream\n" + ATTACH_BYTES + b"\nendstream",
        # 8: file specification -> embedded stream (Catalog::readEmbeddedFile needs
        #     /EF /F to be an indirect reference, Catalog.cc:946)
        b"<< /Type /Filespec /F (" + ATTACH_NAME + b") /UF (" + ATTACH_NAME
        + b") /EF << /F 7 0 R >> >>",
        # 9: /Names /EmbeddedFiles name tree leaf
        b"<< /Names [(" + ATTACH_NAME + b") 8 0 R] >>",
    ]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_at = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n")
    out += b"startxref\n" + str(xref_at).encode() + b"\n%%EOF\n"
    return bytes(out)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"
    data = build()
    with open(path, "wb") as f:
        f.write(data)
    # Echo, one value per line: (1) the text encoded on the page, (2) the embedded
    # file's name, (3) the embedded file's payload. The shell test asserts against
    # these instead of hardcoding a second copy of each string that could drift apart.
    sys.stdout.write(TEXT_STR.decode("ascii") + "\n")
    sys.stdout.write(ATTACH_NAME.decode("ascii") + "\n")
    sys.stdout.write(ATTACH_BYTES.decode("ascii") + "\n")
