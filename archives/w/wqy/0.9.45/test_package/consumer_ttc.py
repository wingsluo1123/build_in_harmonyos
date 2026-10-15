from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import struct
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


EXPECTED_SIZE = 16_791_251
EXPECTED_SHA256 = "79c18ebe7b811951e8311bad7103ebeae8c337ed9988ea69e8a78a66cfe029b9"
EXPECTED_FAMILIES = (
    "WenQuanYi Zen Hei",
    "WenQuanYi Zen Hei Mono",
    "WenQuanYi Zen Hei Sharp",
)
SAMPLE_TEXT = "中文字体测试"


class TtcParseError(ValueError):
    """Raised when a TTC or one of its font tables is malformed."""


def _range(data: bytes, offset: int, length: int, label: str) -> None:
    if offset < 0 or length < 0 or offset > len(data) or length > len(data) - offset:
        raise TtcParseError(f"{label} range [{offset}, {offset + length}) is outside {len(data)} bytes")


def _u16(data: bytes, offset: int, label: str) -> int:
    _range(data, offset, 2, label)
    return struct.unpack_from(">H", data, offset)[0]


def _u32(data: bytes, offset: int, label: str) -> int:
    _range(data, offset, 4, label)
    return struct.unpack_from(">I", data, offset)[0]


@dataclass(frozen=True)
class CmapLookup:
    format: int
    data: bytes = field(repr=False, compare=False)
    start: int
    length: int
    groups: tuple[tuple[int, int, int], ...] = ()
    group_starts: tuple[int, ...] = ()
    format4_segments: tuple[tuple[int, int, int, int, int], ...] = ()

    def glyph_id(self, codepoint: int) -> int:
        if not 0 <= codepoint <= 0x10FFFF:
            return 0
        if self.format == 12:
            index = bisect.bisect_right(self.group_starts, codepoint) - 1
            if index < 0:
                return 0
            first, last, first_glyph = self.groups[index]
            return first_glyph + codepoint - first if codepoint <= last else 0
        if self.format == 4 and codepoint <= 0xFFFF:
            for first, last, delta, range_offset, range_word in self.format4_segments:
                if first <= codepoint <= last:
                    if range_offset == 0:
                        return (codepoint + delta) & 0xFFFF
                    glyph_offset = range_word + range_offset + 2 * (codepoint - first)
                    if glyph_offset + 2 > self.start + self.length:
                        raise TtcParseError("cmap format 4 glyph array reference is out of range")
                    glyph = _u16(self.data, glyph_offset, "cmap format 4 glyph ID")
                    return (glyph + delta) & 0xFFFF if glyph else 0
        return 0


@dataclass(frozen=True)
class FaceInfo:
    index: int
    family_name: str
    glyph_count: int
    _cmap: CmapLookup = field(repr=False, compare=False)

    def glyph_id(self, codepoint: int) -> int:
        return self._cmap.glyph_id(codepoint)


@dataclass(frozen=True)
class CoverageReport:
    byte_length: int
    sha256: str
    sample_text: str
    faces: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _name(data: bytes, offset: int, length: int) -> str:
    _range(data, offset, length, "name table")
    if length < 6:
        raise TtcParseError("name table is shorter than its header")
    table_format = _u16(data, offset, "name format")
    count = _u16(data, offset + 2, "name record count")
    strings_offset = _u16(data, offset + 4, "name strings offset")
    if table_format not in (0, 1):
        raise TtcParseError(f"unsupported name table format {table_format}")
    records_end = 6 + count * 12
    if records_end > length or strings_offset < records_end or strings_offset > length:
        raise TtcParseError("name table record or string directory is out of range")
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for index in range(count):
        record = offset + 6 + 12 * index
        platform = _u16(data, record, "name platform")
        encoding = _u16(data, record + 2, "name encoding")
        language = _u16(data, record + 4, "name language")
        name_id = _u16(data, record + 6, "name ID")
        byte_length = _u16(data, record + 8, "name string length")
        string_offset = _u16(data, record + 10, "name string offset")
        if name_id != 1:
            continue
        string_start = offset + strings_offset + string_offset
        if string_start < offset + strings_offset or string_start + byte_length > offset + length:
            raise TtcParseError("family name string is outside the name table")
        raw = data[string_start : string_start + byte_length]
        try:
            if platform in (0, 3):
                value = raw.decode("utf-16-be")
                platform_priority = 0 if platform == 3 and encoding in (1, 10) else 1
            elif platform == 1 and encoding == 0:
                value = raw.decode("mac_roman")
                platform_priority = 2
            else:
                continue
        except UnicodeDecodeError:
            continue
        if value:
            candidates.append(((platform_priority, 0 if language in (0, 0x0409) else 1, index), value))
    if not candidates:
        raise TtcParseError("name table has no decodable family name (name ID 1)")
    return min(candidates, key=lambda candidate: candidate[0])[1]


def _format12(data: bytes, start: int, table_end: int) -> CmapLookup:
    _range(data, start, 16, "cmap format 12 header")
    length = _u32(data, start + 4, "cmap format 12 length")
    if length < 16 or start + length > table_end:
        raise TtcParseError("cmap format 12 subtable is outside cmap table")
    count = _u32(data, start + 12, "cmap format 12 group count")
    if count > (length - 16) // 12:
        raise TtcParseError("cmap format 12 groups exceed subtable length")
    groups = []
    previous_end = -1
    for index in range(count):
        group = start + 16 + index * 12
        first = _u32(data, group, "cmap group start")
        last = _u32(data, group + 4, "cmap group end")
        first_glyph = _u32(data, group + 8, "cmap group glyph")
        if first > last or last > 0x10FFFF or first <= previous_end:
            raise TtcParseError("cmap format 12 groups are invalid or overlap")
        if first_glyph + last - first > 0xFFFFFFFF:
            raise TtcParseError("cmap format 12 glyph range overflows")
        groups.append((first, last, first_glyph))
        previous_end = last
    frozen_groups = tuple(groups)
    return CmapLookup(12, data, start, length, frozen_groups, tuple(group[0] for group in frozen_groups))


def _format4(data: bytes, start: int, table_end: int) -> CmapLookup:
    _range(data, start, 14, "cmap format 4 header")
    length = _u16(data, start + 2, "cmap format 4 length")
    subtable_end = start + length
    if length < 16 or subtable_end > table_end:
        raise TtcParseError("cmap format 4 subtable is outside cmap table")
    seg_count_x2 = _u16(data, start + 6, "cmap format 4 segment count")
    if seg_count_x2 == 0 or seg_count_x2 & 1:
        raise TtcParseError("cmap format 4 segment count is invalid")
    count = seg_count_x2 // 2
    end_codes = start + 14
    reserved_pad = end_codes + count * 2
    start_codes = reserved_pad + 2
    deltas = start_codes + count * 2
    range_offsets = deltas + count * 2
    glyph_array = range_offsets + count * 2
    if glyph_array > subtable_end:
        raise TtcParseError("cmap format 4 segment arrays exceed subtable length")
    segments = []
    previous_end = -1
    for index in range(count):
        last = _u16(data, end_codes + 2 * index, "cmap format 4 end code")
        first = _u16(data, start_codes + 2 * index, "cmap format 4 start code")
        delta = struct.unpack_from(">h", data, deltas + 2 * index)[0]
        range_word = range_offsets + 2 * index
        range_offset = _u16(data, range_word, "cmap format 4 range offset")
        if first > last or first <= previous_end:
            raise TtcParseError("cmap format 4 segments are invalid or overlap")
        if range_offset and range_word + range_offset >= subtable_end:
            raise TtcParseError("cmap format 4 glyph array offset is out of range")
        segments.append((first, last, delta, range_offset, range_word))
        previous_end = last
    return CmapLookup(4, data, start, length, format4_segments=tuple(segments))


def _cmap(data: bytes, offset: int, length: int) -> CmapLookup:
    _range(data, offset, length, "cmap table")
    if length < 4 or _u16(data, offset, "cmap version") != 0:
        raise TtcParseError("cmap table header is invalid")
    count = _u16(data, offset + 2, "cmap encoding record count")
    records_end = 4 + count * 8
    if records_end > length:
        raise TtcParseError("cmap encoding records exceed table length")
    candidates = []
    table_end = offset + length
    for index in range(count):
        record = offset + 4 + index * 8
        platform = _u16(data, record, "cmap platform")
        encoding = _u16(data, record + 2, "cmap encoding")
        subtable_offset = _u32(data, record + 4, "cmap subtable offset")
        if not (platform == 0 or (platform == 3 and encoding in (1, 10))):
            continue
        subtable = offset + subtable_offset
        if subtable < offset + records_end or subtable + 2 > table_end:
            raise TtcParseError("Unicode cmap subtable offset is out of range")
        format_number = _u16(data, subtable, "cmap format")
        priority = (0 if format_number == 12 else 1, 0 if platform == 3 and encoding == 10 else 1, index)
        if format_number == 12:
            lookup = _format12(data, subtable, table_end)
        elif format_number == 4:
            lookup = _format4(data, subtable, table_end)
        else:
            continue
        candidates.append((priority, lookup))
    if not candidates:
        raise TtcParseError("face has no supported Unicode cmap format 4 or 12")
    return min(candidates, key=lambda candidate: candidate[0])[1]


def _parse_ttc_data(data: bytes) -> list[FaceInfo]:
    _range(data, 0, 12, "TTC header")
    if data[:4] != b"ttcf":
        raise TtcParseError("invalid TTC collection magic")
    version = _u32(data, 4, "TTC version")
    if version not in (0x00010000, 0x00020000):
        raise TtcParseError(f"unsupported TTC version 0x{version:08x}")
    count = _u32(data, 8, "TTC face count")
    if count == 0 or count > (len(data) - 12) // 4:
        raise TtcParseError("TTC face offset directory is truncated or empty")
    directory_end = 12 + count * 4
    offsets = [_u32(data, 12 + 4 * index, "TTC face offset") for index in range(count)]
    faces = []
    for index, face_offset in enumerate(offsets):
        _range(data, face_offset, 12, f"face {index} sfnt header")
        scaler_type = data[face_offset : face_offset + 4]
        if scaler_type not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"):
            raise TtcParseError(f"face {index} has unsupported sfnt signature {scaler_type!r}")
        table_count = _u16(data, face_offset + 4, f"face {index} table count")
        if table_count == 0 or table_count > (len(data) - face_offset - 12) // 16:
            raise TtcParseError(f"face {index} table directory is truncated or empty")
        table_records_end = face_offset + 12 + table_count * 16
        tables: dict[bytes, tuple[int, int]] = {}
        for table_index in range(table_count):
            record = face_offset + 12 + table_index * 16
            tag = data[record : record + 4]
            table_offset = _u32(data, record + 8, f"face {index} table offset")
            table_length = _u32(data, record + 12, f"face {index} table length")
            _range(data, table_offset, table_length, f"face {index} {tag.decode('ascii', 'replace')} table")
            if tag in tables:
                raise TtcParseError(f"face {index} contains duplicate table {tag!r}")
            tables[tag] = (table_offset, table_length)
        if table_records_end > len(data):
            raise TtcParseError(f"face {index} table directory exceeds collection")
        try:
            name_offset, name_length = tables[b"name"]
            maxp_offset, maxp_length = tables[b"maxp"]
            cmap_offset, cmap_length = tables[b"cmap"]
        except KeyError as error:
            raise TtcParseError(f"face {index} is missing required table {error.args[0]!r}") from error
        family_name = _name(data, name_offset, name_length)
        if maxp_length < 6:
            raise TtcParseError(f"face {index} maxp table is shorter than six bytes")
        glyph_count = _u16(data, maxp_offset + 4, f"face {index} glyph count")
        if glyph_count == 0:
            raise TtcParseError(f"face {index} has zero glyphs")
        faces.append(FaceInfo(index, family_name, glyph_count, _cmap(data, cmap_offset, cmap_length)))
    if directory_end > len(data):
        raise TtcParseError("TTC face offset directory exceeds collection")
    return faces


def parse_ttc(path: Path) -> list[FaceInfo]:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise TtcParseError(f"cannot read TTC file {path}: {error}") from error
    return _parse_ttc_data(data)


def consume_ttc(path: Path) -> CoverageReport:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise TtcParseError(f"cannot read TTC file {path}: {error}") from error
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != EXPECTED_SIZE:
        raise TtcParseError(f"TTC size mismatch: expected {EXPECTED_SIZE}, got {len(data)}")
    if digest != EXPECTED_SHA256:
        raise TtcParseError(f"TTC SHA-256 mismatch: expected {EXPECTED_SHA256}, got {digest}")
    faces = _parse_ttc_data(data)
    if tuple(face.family_name for face in faces) != EXPECTED_FAMILIES:
        raise TtcParseError(f"unexpected TTC face families: {[face.family_name for face in faces]!r}")
    face_summaries = []
    for face in faces:
        glyphs = {character: face.glyph_id(ord(character)) for character in SAMPLE_TEXT}
        missing = [character for character, glyph in glyphs.items() if glyph <= 0 or glyph >= face.glyph_count]
        if missing:
            raise TtcParseError(f"face {face.index} has missing/out-of-range glyphs for {missing!r}")
        face_summaries.append({
            "index": face.index,
            "family_name": face.family_name,
            "glyph_count": face.glyph_count,
            "sample_coverage": f"{len(glyphs) - len(missing)}/{len(SAMPLE_TEXT)}",
            "glyph_ids": list(glyphs.values()),
        })
    return CoverageReport(len(data), digest, SAMPLE_TEXT, tuple(face_summaries))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the packaged WenQuanYi Zen Hei TTC")
    parser.add_argument("ttc", type=Path)
    arguments = parser.parse_args(argv)
    try:
        report = consume_ttc(arguments.ttc)
    except TtcParseError as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", **report.as_dict()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
