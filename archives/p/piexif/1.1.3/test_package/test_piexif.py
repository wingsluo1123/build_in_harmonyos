#!/usr/bin/env python3
"""HarmonyOS PC consumer regression tests for piexif 1.1.3 (test_package).

Runs against the installed package (site-packages path passed as argv[1]) and
exercises the real public API: dump/load round-trip, insert into a JPEG,
remove, and negative controls.
"""
import io
import struct
import sys
import unittest

if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
    sys.argv = sys.argv[:1]

import piexif  # noqa: E402  (imported after PYTHONPATH injection)


def minimal_jpeg():
    """Build a minimal valid 1x1 grayscale JPEG."""
    out = bytearray()
    out += b"\xff\xd8"                                                    # SOI
    out += b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" \
        + b"\x01\x01\x00" + struct.pack(">HH", 1, 1) + b"\x00\x00"        # APP0
    out += b"\xff\xdb" + struct.pack(">H", 67) + b"\x00" \
        + bytes([1]) * 64                                                 # DQT
    out += b"\xff\xc0" + struct.pack(">H", 11) + b"\x08" \
        + struct.pack(">HH", 1, 1) + b"\x01\x01\x11\x00"                  # SOF0
    out += b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00"  # SOS
    out += b"\x00"                                                        # data
    out += b"\xff\xd9"                                                    # EOI
    return bytes(out)


class PiexifConsumerTests(unittest.TestCase):
    """Consumer/regression tests (鸿蒙特有测试): real piexif API usage."""

    def test_version(self):
        self.assertEqual(piexif.VERSION, "1.1.3")

    def test_dump_load_roundtrip_bytes(self):
        exif_dict = {
            "0th": {piexif.ImageIFD.Make: b"HarmonyOS",
                    piexif.ImageIFD.Model: b"PC"},
            "Exif": {piexif.ExifIFD.DateTimeOriginal: b"2026:10:16 00:00:00",
                     piexif.ExifIFD.ExposureTime: (1, 125)},
            "GPS": {piexif.GPSIFD.GPSLatitudeRef: b"N"},
            "1st": {},
            "thumbnail": None,
        }
        loaded = piexif.load(piexif.dump(exif_dict))
        self.assertEqual(loaded["0th"][piexif.ImageIFD.Make], b"HarmonyOS")
        self.assertEqual(loaded["0th"][piexif.ImageIFD.Model], b"PC")
        self.assertEqual(loaded["Exif"][piexif.ExifIFD.ExposureTime], (1, 125))
        self.assertEqual(loaded["GPS"][piexif.GPSIFD.GPSLatitudeRef], b"N")

    def test_insert_load_remove_on_jpeg(self):
        jpeg = minimal_jpeg()
        self.assertEqual(jpeg[:2], b"\xff\xd8")
        exif_bytes = piexif.dump({
            "0th": {piexif.ImageIFD.Make: b"OHOS"},
            "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None,
        })
        buffer = io.BytesIO()
        piexif.insert(exif_bytes, jpeg, buffer)
        with_exif = buffer.getvalue()
        self.assertGreater(len(with_exif), len(jpeg))
        self.assertEqual(
            piexif.load(with_exif)["0th"][piexif.ImageIFD.Make], b"OHOS")
        cleaned_buffer = io.BytesIO()
        piexif.remove(with_exif, cleaned_buffer)
        cleaned = piexif.load(cleaned_buffer.getvalue())
        self.assertNotIn(piexif.ImageIFD.Make, cleaned["0th"])

    def test_insert_rejects_non_exif_payload(self):
        buffer = io.BytesIO()
        with self.assertRaises(ValueError):
            piexif.insert(b"not exif data", minimal_jpeg(), buffer)

    def test_split_segments_rejects_garbage(self):
        from piexif import _common
        with self.assertRaises(piexif.InvalidImageDataError):
            _common.split_into_segments(b"I'm not JPEG")

    def test_load_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            piexif.load("no-such-file-4c1f6a.jpg")


if __name__ == "__main__":
    unittest.main(verbosity=2)
