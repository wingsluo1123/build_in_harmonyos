from __future__ import annotations

import importlib
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


SAMPLE = "中文字体测试"
FAMILIES = ("WenQuanYi Zen Hei", "WenQuanYi Zen Hei Mono")


def _name_table(family: str) -> bytes:
    encoded = family.encode("utf-16-be")
    return struct.pack(">HHH", 0, 1, 18) + struct.pack(">HHHHHH", 3, 1, 0x0409, 1, len(encoded), 0) + encoded


def _cmap_table(with_unicode: bool = True) -> bytes:
    if not with_unicode:
        return struct.pack(">HH", 0, 0)
    groups = b"".join(
        struct.pack(">III", ord(character), ord(character), glyph_id)
        for glyph_id, character in sorted(enumerate(SAMPLE, 1), key=lambda item: ord(item[1]))
    )
    subtable = struct.pack(">HHIII", 12, 0, 16 + len(groups), 0, len(SAMPLE)) + groups
    return struct.pack(">HHHHI", 0, 1, 3, 10, 12) + subtable


def _font_bytes(base_offset: int, family: str, *, with_unicode: bool, bad_table_range: bool) -> bytes:
    tables = {
        b"cmap": _cmap_table(with_unicode),
        b"maxp": struct.pack(">IH", 0x00005000, 32),
        b"name": _name_table(family),
    }
    records_size = 12 + 16 * len(tables)
    next_offset = base_offset + records_size
    records = []
    payload = []
    total_size = records_size + sum(map(len, tables.values()))
    for tag, data in tables.items():
        table_offset = next_offset
        if bad_table_range and tag == b"name":
            table_offset = 0xFFFFFFF0
        records.append(tag + struct.pack(">III", 0, table_offset, len(data)))
        payload.append(data)
        next_offset += len(data)
    header = struct.pack(">IHHHH", 0x00010000, len(tables), 0, 0, 0)
    return header + b"".join(records) + b"".join(payload)


def _synthetic_ttc(*, with_unicode: bool = True, bad_table_range: bool = False) -> bytes:
    header_size = 12 + len(FAMILIES) * 4
    first = _font_bytes(header_size, FAMILIES[0], with_unicode=with_unicode, bad_table_range=bad_table_range)
    second_offset = header_size + len(first)
    second = _font_bytes(second_offset, FAMILIES[1], with_unicode=with_unicode, bad_table_range=False)
    return b"ttcf" + struct.pack(">II", 0x00010000, 2) + struct.pack(">II", header_size, second_offset) + first + second


class TtcParserTests(unittest.TestCase):
    def _consumer_module(self):
        self.assertIsNotNone(importlib.util.find_spec("consumer_ttc"), "the TTC parser implementation is missing")
        return importlib.import_module("consumer_ttc")

    def _parse(self, data: bytes):
        consumer = self._consumer_module()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            path = Path(temporary_directory) / "synthetic.ttc"
            path.write_bytes(data)
            return consumer.parse_ttc(path)

    def test_reads_both_face_names_and_literal_cjk_glyph_mappings(self):
        faces = self._parse(_synthetic_ttc())
        self.assertEqual([face.index for face in faces], [0, 1])
        self.assertEqual([face.family_name for face in faces], list(FAMILIES))
        self.assertEqual([face.glyph_count for face in faces], [32, 32])
        for face in faces:
            self.assertEqual([face.glyph_id(ord(char)) for char in SAMPLE], [1, 2, 3, 4, 5, 6])

    def test_rejects_invalid_collection_magic(self):
        consumer = self._consumer_module()
        with self.assertRaises(consumer.TtcParseError):
            self._parse(b"bad!" + _synthetic_ttc()[4:])

    def test_rejects_truncated_face_offset_directory(self):
        consumer = self._consumer_module()
        truncated = b"ttcf" + struct.pack(">II", 0x00010000, 2) + struct.pack(">I", 20)
        with self.assertRaises(consumer.TtcParseError):
            self._parse(truncated)

    def test_rejects_table_range_past_end_of_collection(self):
        consumer = self._consumer_module()
        with self.assertRaises(consumer.TtcParseError):
            self._parse(_synthetic_ttc(bad_table_range=True))

    def test_rejects_face_without_unicode_cmap(self):
        consumer = self._consumer_module()
        with self.assertRaises(consumer.TtcParseError):
            self._parse(_synthetic_ttc(with_unicode=False))


if __name__ == "__main__":
    unittest.main()
