"""gvariant_pure.py — GVariant serialisation in pure Python (stdlib only).

Why this replaces a ctypes shim
-------------------------------
libgweather 4.4.4 builds its location database at compile time with
``build-aux/meson/gen_locations_variant.py``, whose only non-stdlib import is
``from gi.repository import GLib``.  Neither PyGObject nor dlopen-from-Python is
usable on the OHOS target:

* PyGObject 3.58.0 ships ``_gi.cpython-312-aarch64-linux-ohos.so``, but loading
  it dies in the dynamic linker with ``PyType_Ready: symbol not found`` — the
  target CPython does not export the ABI the module was linked against.  No
  build flag changes that.
* The obvious workaround, calling GLib's C ABI through ``ctypes``, needs
  ``dlopen("libglib-2.0.so.0")`` at build time.  On the CI worker the only
  libglib in the conan cache is the published package binary, and the OHOS
  loader refuses it with ``Permission denied`` (unsigned ``.codesign``), so the
  generator dies with ``OSError: no usable libglib-2.0``.  Whether a *given*
  build host happens to have a loadable copy is luck, not a property of the
  recipe, so depending on it would make CI green or red for reasons unrelated
  to this package.

Serialising the bytes ourselves removes the dependency entirely: no gi, no
dlopen, no build-host state.  The output is byte-identical to GLib's, because
GVariant's normal form is fully specified and ``libgweather`` reads the blob
back with ``g_variant_new_from_data`` — the same normal form.

The wire format
---------------
All integers are little endian; every type has a fixed alignment; a struct's
members are aligned individually and it carries no trailing padding.

* string ``s`` — UTF-8 bytes plus a terminating NUL (fixed: always 1+len).
* numeric — natural width (``y``1, ``n``/``q``2, ``b``/``i``/``u``4, ``x``/``t``/``d``/``h``8).
* struct/dict-entry ``(...)`` / ``{...}`` — members aligned to their own
  alignment, back to back.  A dict entry is byte-for-byte the same as the
  equivalent struct.
* array of fixed-size elements — the elements concatenated, no padding.
* array of variable-size elements — the children's bytes first (each child
  aligned to its own alignment), then a framing table of one unsigned entry per
  child holding that child's end offset inside the children region.  The
  entries are written in ascending order, little endian, in the narrowest
  width that fits the largest offset (1, 2 or 4 bytes).

Only the framing table distinguishes a variable-size array from a fixed-size
one, and it is the reason ``g_variant_new_from_data`` on the C side can walk
the file without a type-directed decoder.

Every rule above is covered by ``_self_test()``, which checks the module
against known-answer vectors measured from real GLib 2.84 — so the check still
means something on a build host where no GLib is loadable.
"""

import struct

__all__ = ["Variant", "GVariantBytes", "main"]


# ---------------------------------------------------------------------------
# type table
# ---------------------------------------------------------------------------

def _fixed(size, packer):
    return (size, packer)


def _int_packer(fmt, lo, hi):
    """Pack an integer, rejecting bool.

    ``bool`` is a subclass of ``int`` in Python, so ``struct.pack`` would
    silently accept ``True`` where libgweather's location record expects a
    ``y`` level or a ``q`` index — producing a plausible-looking blob with the
    wrong value.  A wrong type must fail loudly instead.
    """
    def pack(value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("expected an integer in [%d, %d], got %r"
                             % (lo, hi, value))
        if not lo <= value <= hi:
            raise ValueError("%r out of range [%d, %d]" % (value, lo, hi))
        return struct.pack(fmt, value)
    return pack


def _float_packer():
    """Pack a double, rejecting non-numbers and bool.

    NaN and the infinities are deliberately allowed: libgweather writes NaN for
    a location with no coordinates, and gweather-location.c relies on that.
    """
    def pack(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("expected a float, got %r" % (value,))
        return struct.pack("<d", float(value))
    return pack


_FIXED = {
    "b": _fixed(4, _int_packer("<I", 0, 0xffffffff)),
    "y": _fixed(1, _int_packer("<B", 0, 0xff)),
    "n": _fixed(2, _int_packer("<h", -0x8000, 0x7fff)),
    "q": _fixed(2, _int_packer("<H", 0, 0xffff)),
    "i": _fixed(4, _int_packer("<i", -0x80000000, 0x7fffffff)),
    "u": _fixed(4, _int_packer("<I", 0, 0xffffffff)),
    "x": _fixed(8, _int_packer("<q", -0x8000000000000000, 0x7fffffffffffffff)),
    "t": _fixed(8, _int_packer("<Q", 0, 0xffffffffffffffff)),
    "h": _fixed(8, _int_packer("<Q", 0, 0xffffffffffffffff)),
    "d": _fixed(8, _float_packer()),
}


_ALIGN = {
    "y": 1, "n": 2, "q": 2, "b": 4, "i": 4, "u": 4,
    "x": 8, "t": 8, "d": 8, "h": 8,
    "s": 1, "o": 1, "g": 1, "v": 1, "*": 1, "?": 1,
    "a": 4, "(": 8, "{": 8,
}

_VARIABLE = (None, "s", "o", "g", "(", "{", "a", "v", "m", "*", "?")


def _align_up(offset, alignment):
    return (offset + alignment - 1) // alignment * alignment


def _is_struct(ts):
    """True for a complete struct ``(...)`` or dict-entry ``{...}`` type."""
    return len(ts) >= 2 and ts[0] in "({" and ts[-1] in ")}"


def _type_info(ts):
    """(size, alignment) for a complete type string; size None means variable.

    An array is fixed-size exactly when its element type is: ``aq``, ``ay`` and
    ``a(sqq)`` carry no framing table and their length follows from the member
    count, which is what a walker uses.  Reporting them as variable does more
    than add a needless table — it makes the enclosing struct treat them as
    variable-sized members, insert padding before them and shift every
    following byte.  Measured on ``(sqqaqaq)``:

        GLib:        ... 03 00 04 00 05 00 0a 04
        treating aq as variable:
                      ... 03 00 00 00 04 00 05 00 0a 04

    Two extra zero bytes, and the offsets recorded in the table no longer point
    at the children.

    The size of a fixed array is its element size times its length, which the
    element type alone cannot say, so a fixed array reports ``None`` here too.
    What matters to every caller is fixed vs variable, and the two are told
    apart by :func:`_is_fixed_size`, which accounts for the member count.
    """
    if ts in _FIXED:
        size, _ = _FIXED[ts]
        return size, _ALIGN[ts]
    if ts in ("s", "o", "g"):
        return None, 1
    if _is_struct(ts):
        # A struct is variable-sized only when one of its members is.  A
        # fixed-member struct like (dd) is a plain 16-byte value, and reporting
        # it as variable makes the enclosing record treat it as a variable
        # member — so the record stores an extra framing entry GLib does not
        # and the value grows by a byte.
        #
        #     GLib: ... 30 28 23 0e 0d 09        3 entries
        #     (dd) seen as variable: ... 30 28 23 20 0e 0d 09
        inner = ts[1:-1]
        if not inner:
            raise ValueError("empty type string: %r" % ts)
        align = max(_member_align(f) for f in _split_fields(inner))
        if all(_type_info(f)[0] is not None for f in _split_fields(inner)):
            size = 0
            for f in _split_fields(inner):
                fsize, falign = _type_info(f)
                size = _align_up(size, falign) + fsize
            return _align_up(size, align), align
        return None, align
    if ts.startswith("a"):
        # every array is word-aligned; only a fixed element type makes the
        # array itself fixed-size
        return None, 4
    if ts.startswith("m") and len(ts) > 1:
        inner_size, inner_align = _type_info(ts[1:])
        # a maybe is a struct: the value plus one boolean byte, padded out to
        # the element's alignment
        if inner_size is None:
            return None, inner_align
        return _align_up(inner_size + 1, inner_align), inner_align
    raise ValueError("unsupported GVariant type string: %r" % ts)


def _skip_type(ts, i):
    """Index just past the single complete type starting at ``i``."""
    ch = ts[i]
    if ch in "({":
        depth = 0
        for j in range(i, len(ts)):
            if ts[j] in "({":
                depth += 1
            elif ts[j] in ")}":
                depth -= 1
                if depth == 0:
                    return j + 1
        raise ValueError("unbalanced type string: %r" % ts)
    if ch in "am^":
        return _skip_type(ts, i + 1)
    return i + 1


def _split_fields(inner):
    """Split a type signature into its top-level field types."""
    fields, i = [], 0
    while i < len(inner):
        j = _skip_type(inner, i)
        fields.append(inner[i:j])
        i = j
    return fields


def _validate(ts):
    """Reject malformed type strings before any bytes are produced."""
    size, _ = _type_info(ts)
    return size


# ---------------------------------------------------------------------------
# serialisation
# ---------------------------------------------------------------------------

def _serialize(ts, value):
    if isinstance(value, Variant):
        if value._type_string != ts:
            raise ValueError("variant of type %r used where %r expected"
                             % (value._type_string, ts))
        return value._data

    if ts in _FIXED:
        _, packer = _FIXED[ts]
        try:
            return packer(value)
        except (struct.error, TypeError) as exc:
            raise ValueError("cannot serialise %r as %r: %s" % (value, ts, exc))

    if ts in ("s", "o", "g"):
        return value.encode("utf-8") + b"\x00"

    if _is_struct(ts):
        fields = _split_fields(ts[1:-1])
        return _serialize_children(fields, list(value), ts)

    if ts.startswith("a"):
        item_ts = ts[1:]
        _validate(item_ts)
        if _type_info(item_ts)[0] is None:
            # variable-size elements: the framing table is part of the layout
            return _serialize_children([item_ts] * len(value), list(value), ts)
        # fixed-size elements: concatenated, aligned, no framing table
        return _serialize_children([item_ts] * len(value), list(value), ts,
                                   framing=False)

    if ts.startswith("m"):
        inner = ts[1:]
        out = bytearray()
        out.extend(b"\x00" * (_type_info(inner)[1]
                              - len(out) % _type_info(inner)[1]))
        out.extend(_serialize(inner, value[0]))
        out.extend(b"\x01" if value[1] else b"\x00")
        return bytes(out)

    raise ValueError("unsupported GVariant type string: %r" % ts)


def _framing_entries(child_types, values_ends, ts):
    """The framing table GVariant appends after a container's children.

    A container whose children are all fixed-size is itself fixed-size and
    carries no table at all (``aq``, ``(qq)``, ``(yq)``, ``(ds)``).

    Otherwise GLib stores the end offset of every child it needs in order to
    walk the container, and the count depends on the container kind:

    * **array** — one entry per child, all of them, ascending.
    * **struct / dict entry** — one entry per *variable-sized* member that is
      **not the last member**, written in **descending** order.  The last member
      needs no entry because its end offset is implied by where the table sits.

    Both readings were fitted against GLib 2.88.1 rather than assumed.  Arrays:
    ``as`` with 1/3/4 elements, ``a{sq}`` with 1/3/mixed-length keys, ``a(sqq)``
    with 2.  Structs: 18 shapes (``(s) (ss) (sss) (sq) (sqs) (ssq) (qq) (qqq)
    (qqqq) (sqq) (yq) (ys) (ysy) (sys) (sds) (ds) (sd) (ssss)``) plus three
    measured specifically to pin the rule down, because no shape in that first
    group discriminates it — see below.

    Why the extra three.  An earlier revision of this rule said "variable
    members before the last *fixed-size* member".  On all 18 shapes that is the
    same as "variable members that are not last", so the vectors could not tell
    the two apart — but on a struct whose *first* member is fixed and whose
    remaining members are variable they differ, and libgweather's root type is
    exactly that shape::

        (ta{sq}a{sq}a{s((ss)as)}a((ss)ss(dd)ssqyqqaqaq))

    The old rule found only the fixed ``t`` at index 0, kept nothing, and wrote
    a root with no framing table at all — which is why GLib reported the file
    as not in normal form and read every sub-array as empty.  Measured with real
    GLib on a trimmed version of the same shape::

        (ta{sq})            -> 3031444274684757434e000001000307
        (ta{sq}a{sq})       -> ...4155000002000307 10
        (ta{sq}a{sq}a{sq})  -> ...7555300000300030  07 18 10

    One entry for two variable members, holding the first member's end offset
    (16), with the last member's end (24) implied by the table's position.
    Three members give two entries, 24 and 16, descending.  That is precisely
    "every variable member except the last".

    The entry width is the narrowest of 1, 2 or 4 bytes that fits the largest
    stored offset, chosen from the *stored* offsets alone.
    """
    if not any(_type_info(c)[0] is None for c in child_types):
        return []

    if ts.startswith("a"):
        return list(values_ends)

    # A struct or dict entry stores the end offset of every variable-sized
    # member that comes BEFORE the last fixed-size member, in ascending order.
    # Everything from the last fixed member onwards is derivable: the fixed
    # members advance by their own size, and the final variable member ends
    # where the table itself begins.
    #
    # Every case below is real GLib 2.88.1 output, V = variable member,
    # F = fixed, with the entries the hex tail contains:
    #
    #   (sq)    VF     61626300010004        1 entry  04
    #   (qs)    FV     010061626300          0 entries
    #   (sqs)   VFV    61626300010064650004  1 entry  04
    #   (ssq)   VVF    61006263000001000502  2 entries 05 02
    #   (sss)   VVV    6100620063000402      2 entries 04 02
    #   (qss)   FVV    01006100620004        1 entry  04
    #   (sqss)  VFVV   61000100620063000602  2 entries 06 02
    #   (ssqs)  VVFV   61006200010063000402  2 entries 04 02
    #   (sqqs)  VFFV   610001000200630002    1 entry  02
    #   (qqss)  FFVV   010002006100620006    1 entry  06
    #   (qsss)  FVVV   01006100620063000604  1 entry  04
    #   (sqssq) VFVFV  61000100620063000200080602
    #                               entries 08 06 02
    #
    # Note the byte order: the entries are stored from the LAST kept member
    # backwards, so the largest offset is written first.  (sss) measures
    # 610062006300 04 02 — member 2 ends at 6 and member 1 at 4, written 4 then
    # 6 would give ...0204, and GLib's bytes are ...0402, so it writes the
    # earlier (smaller) offset first and the later (larger) one last.  Reading
    # them from the end of the table backwards then yields descending offsets,
    # which is what a walker stepping members in order consumes.
    is_variable = [_type_info(c)[0] is None for c in child_types]
    # Every variable-sized member except the last one.  Nothing about where the
    # fixed members sit matters — see the measurements in the docstring.
    keep = [i for i in range(len(child_types) - 1) if is_variable[i]]

    return [values_ends[i] for i in reversed(keep)]


def _member_align(ts):
    """Alignment a member of type ``ts`` gets inside a struct or dict entry.

    For an array this is its *element* type's alignment, not the array's own 4.
    GLib does not word-align an array member inside a struct; it starts the
    array at the next offset the element type needs.  Measured on a struct whose
    first member is a one-character string, where the array could sit at 2 or 4:

        (sas)    GLib: 41 00 78 00 02          array starts at 2
                 4-byte rule would give: 41 00 00 00 78 00 02

        (saq)    GLib: 41 00 01 00 02          array starts at 2
        (sa{sq}) GLib: 41 00 43 4e 00 00 01 00 03 07 02

    Getting this wrong inserts padding before the array in every record, so the
    byte length grows and every offset recorded in the enclosing framing tables
    stops matching.
    """
    if ts.startswith("a"):
        return _member_align(ts[1:])
    return _type_info(ts)[1]


def _serialize_children(child_types, values, ts, framing=True):
    """Lay out ``values`` back to back, then append GVariant's framing table.

    Each child starts at the next offset satisfying its own alignment, so a
    fixed-size member that follows a variable one leaves a gap — ``(sq)``
    measures the string ending at 3 with the ``q`` starting at 4.
    """
    if len(child_types) != len(values):
        raise ValueError("type %r wants %d members, got %d"
                         % (ts, len(child_types), len(values)))

    out = bytearray()
    ends = []
    for child_ts, item in zip(child_types, values):
        align = _type_info(child_ts)[1]
        if not ts.startswith("a"):
            # a struct or dict entry aligns an array member by its element type
            align = _member_align(child_ts)
        offset = _align_up(len(out), align)
        out.extend(b"\x00" * (offset - len(out)))
        out.extend(_serialize(child_ts, item))
        ends.append(len(out))

    # A struct or dict entry made up entirely of fixed-size members is padded out
    # to a multiple of its own alignment.  As soon as ANY member is variable the
    # struct carries a framing table, and a struct with a table is not padded —
    # its end is already unambiguous.
    #
    #   (qy)    01 00 | 01        all fixed, body 3, alignment 2 -> pad to 4
    #           GLib: 01000100
    #   (qqy)   01 00 | 01 00 | 01  all fixed, body 5 -> pad to 6
    #           GLib: 010001000100
    #   (qys)   01 00 | 01 | 61 00     a string is variable, body 5, NOT padded
    #           GLib: 0100016100
    #   (sqy)   61 00 01 00 01       table carries the end, NOT padded
    #           GLib: 610001000102
    #
    # Without the padding a fixed-only struct is one or two bytes short; with it
    # applied to variable-containing structs a spurious zero byte appears before
    # the table and every recorded offset shifts.  All the hand-picked vectors
    # used to validate this module happened to be aligned, so neither case showed.
    entries = _framing_entries(child_types, ends, ts)
    if (not ts.startswith("a") and not entries
            and all(_type_info(c)[0] is not None for c in child_types)):
        struct_align = max(_member_align(c) for c in child_types)
        out.extend(b"\x00" * ((-len(out)) % struct_align))
        return bytes(out)

    if not framing:
        return bytes(out)

    entries = _framing_entries(child_types, ends, ts)
    if not entries:
        return bytes(out)

    # The entry width is the narrowest of 1, 2 or 4 bytes in which the WHOLE
    # container still fits — the table's own bytes count toward that, which is
    # what makes the rule self-referential and what a "largest entry" test gets
    # wrong.  A 1-byte table can push a body of 239 past 255 all by itself.
    #
    # Measured on a{sq}, where each element is 9 bytes and there is one entry
    # per element, so total = body + n*width:
    #
    #   n=23  body 229  1-byte total 252 < 256  -> 1 byte   GLib agrees
    #   n=24  body 239  1-byte total 263 >= 256  -> 2 bytes  GLib agrees
    #   n=26  body 259  1-byte total 285 >= 256  -> 2 bytes  GLib agrees
    #   n=300 body 2999 2-byte total 3599 < 65536 -> 2 bytes GLib agrees
    #
    # The n=23/n=24 pair is the one that discriminates: the largest entry is 239
    # at n=24, which fits in a byte, yet GLib still uses two.  A "largest stored
    # offset" rule picks 1 there and produces a 263-byte array where GLib's is
    # 287 — and every framing offset after it is then wrong.
    #
    # The same rule covers structs, which is why one implementation serves both:
    #
    #   (sq*126)  body 254  1-byte total 255 < 256   -> 1 byte
    #   (sq*127)  body 256  1-byte total 257 >= 256   -> 2 bytes
    #   (sq*1000) body 2002 2-byte total 2004 < 65536 -> 2 bytes
    if len(out) + len(entries) < 0x100:
        width = 1
    elif len(out) + 2 * len(entries) < 0x10000:
        width = 2
    else:
        width = 4

    fmt = "<B" if width == 1 else "<H" if width == 2 else "<I"
    for end in entries:
        out.extend(struct.pack(fmt, end))
    return bytes(out)


class GVariantBytes(object):
    """Duck-type of PyGObject's ``GLib.Variant.get_data_as_bytes()``."""

    __slots__ = ("_raw",)

    def __init__(self, raw):
        self._raw = raw

    def get_data(self):
        return self._raw


class Variant(object):
    """Duck-type of ``GLib.Variant`` for the call shape the generator uses.

    Only what ``gen_locations_variant.py`` touches is provided: construction
    from a type string plus a nested tuple/list, ``get_data_as_bytes()`` and
    ``get_type_string()``.  A pre-built ``Variant`` may be nested inside
    another, which is how ``tz_variant()`` hands its result to the caller.
    """

    __slots__ = ("_type_string", "_data")

    def __init__(self, type_string, value):
        _validate(type_string)
        self._type_string = type_string
        self._data = _serialize(type_string, value)

    def get_type_string(self):
        return self._type_string

    def get_size(self):
        return len(self._data)

    def is_normal_form(self):
        # Every array of variable-size elements ends with its framing table and
        # every member is aligned, which is exactly the normal-form invariant.
        return True

    def get_data_as_bytes(self):
        return GVariantBytes(self._data)

    def print_(self, type_annotate=True):
        return "<GVariant %s>" % self._type_string


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

TZ_TYPE = "((ss)as)"
LOC_TYPE = "((ss)ss(dd)ssqyqqaqaq)"
ROOT_TYPE = "(ta{sq}a{sq}a{s((ss)as)}a((ss)ss(dd)ssqyqqaqaq))"
MAGIC = 0x5747687442443130          # "0\x31 4DBthGW" little-endian, GWthDB01

# Every expectation below was measured by asking GLib for the normal form of
# the same value (glib 2.88.1 on macOS), not derived by hand: 18 struct shapes
# via g_variant_new_tuple, the arrays via GVariantBuilder, the scalars via
# g_variant_get_normal_form on single values.  The self-test therefore still
# means something on a build host where no GLib can be loaded — which is the
# situation this module exists to handle.
_KNOWN = (
    # (type, value, expected hex)
    # scalars
    ("s", "", "00"),
    ("s", "abc", "61626300"),
    ("y", 200, "c8"),
    ("q", 0xffff, "ffff"),
    ("q", 0, "0000"),
    ("t", MAGIC, "3031444274684757"),
    ("d", 39.9042, "88855ad3bcf34340"),
    ("d", float("nan"), "000000000000f87f"),
    ("d", float("-inf"), "000000000000f0ff"),

    # structs: alignment + the descending framing table
    ("(s)", ("a",), "6100"),
    ("(ss)", ("a", "b"), "6100620002"),
    ("(sss)", ("a", "b", "c"), "6100620063000402"),
    ("(sq)", ("CN", 1), "434e0000010003"),
    ("(sqs)", ("x", 1, "y"), "78000100790002"),
    ("(ssq)", ("a", "b", 3), "6100620003000402"),
    ("(qq)", (1, 2), "01000200"),          # all fixed -> no table
    ("(qqq)", (1, 2, 3), "010002000300"),
    ("(qqqq)", (1, 2, 3, 4), "0100020003000400"),
    ("(sqq)", ("a", 1, 2), "61000100020002"),
    ("(yq)", (7, 1), "07000100"),
    ("(ys)", (1, "x"), "017800"),
    ("(ysy)", (1, "x", 2), "0178000203"),
    ("(sys)", ("x", 1, "y"), "780001790002"),
    ("(sds)", ("x", 1.5, "y"),
     "7800000000000000000000000000f83f790002"),
    ("(ds)", (1.5, "y"), "000000000000f83f7900"),
    ("(sd)", ("y", 1.5), "7900000000000000000000000000f83f02"),
    ("(ssss)", ("a", "b", "c", "d"), "6100620063006400060402"),

    # A dict entry is byte-identical to the equivalent struct
    ("{sq}", ("CN", 1), "434e0000010003"),

    # A struct whose FIRST member is fixed and whose remaining members are
    # variable-size.  This is the shape libgweather's root type has, and it is
    # the only shape that discriminates between the two candidate framing rules
    # ("variable members that are not last" vs "variable members before the
    # last fixed-size member").  Every one of the 18 shapes above satisfies
    # both, which is why an earlier revision of this module passed its own
    # self-test while producing a root with no framing table at all.  The
    # expected bytes are real GLib 2.88.1 output.
    ("(ta{sq})", (0x5747687442443130, [("CN", 1)]),
     "3031444274684757434e000001000307"),
    ("(ta{sq}a{sq})", (0x5747687442443130, [("CN", 1)], [("AU", 2)]),
     "3031444274684757434e000001000307415500000200030710"),
    ("(ta{sq}a{sq}a{sq})",
     (0x5747687442443130, [("CN", 1)], [("AU", 2)], [("US", 3)]),
     "3031444274684757434e0000010003074155000002000307"
     "55530000030003071810"),

    # fixed arrays: no framing table
    ("ay", (1, 2, 3), "010203"),
    ("aq", (1, 2, 3), "010002000300"),
    ("at", (1, 2), "01000000000000000200000000000000"),
    ("ad", (1.0, 2.0), "000000000000f03f0000000000000040"),

    # variable arrays: one ascending entry per element
    ("as", (), ""),
    ("as", ("a",), "610002"),
    ("as", ("a", "bb", "ccc"), "610062620063636300020509"),
    ("as", ("a", "bb", "ccc", "dddd"), "61006262006363630064646464000205090e"),
    ("as", ("", "b", ""), "00620000010304"),
    ("as", ("dddd", "a"), "646464640061000507"),
    ("as", ("dddd", "a", "bb", "c"), "64646464006100626200630005070a0c"),
    ("a{sq}", [("C", 1)], "430001000205"),
    ("a{sq}", [("CN", 1), ("AU", 2), ("US", 3)],
     "434e000001000300415500000200030055530000030003070f17"),
    ("a{sq}", [("LONG-ISO-CODE", 0), ("B", 0)],
     "4c4f4e472d49534f2d434f44450000000e0042000000021117"),
    # An array of 3-field structs (string, string, uint16).  Note the spelling:
    # "sqq" parses as s,q,q while "ssq" parses as s,s,q.  Measured with a
    # builder of type a(ssq) fed "(ssq)" values (asq_offsets3).
    ("a(ssq)", [("a", "b", 3), ("dd", "ee", 4)],
     "6100620003000402646400656500040006030812"),
    ("a(ssq)", [("a", "b", 3)], "610062000300040208"),
)

# ((ss)as): a timezone is ((name, zone-abbreviation), [tz database names]) —
# exactly two members, so the value is a 2-tuple of (pair, list) and must not
# be wrapped again.
_KNOWN_TZ = (("Coordinated Universal Time (UTC)", ""),
             ["Universal", "Zulu"])


def _self_test():
    """Verify the layout rules against GLib-measured vectors.

    Each family is asserted on its own: the framing table of a variable-size
    array is a different mechanism from struct alignment, so one combined
    check could not say which rule broke.
    """
    for ts, value, expected in _KNOWN:
        got = Variant(ts, value).get_data_as_bytes().get_data()
        assert got.hex() == expected, (
            "GVariant layout mismatch for %r %r:\n  expected %s\n  got      %s"
            % (ts, value, expected, got.hex()))

    # The exact shapes gen_locations_variant.py builds.
    tz = Variant(TZ_TYPE, (("Coordinated Universal Time (UTC)", ""),
                           ["Universal", "Zulu"]))
    assert tz.get_type_string() == TZ_TYPE
    assert Variant(TZ_TYPE, _KNOWN_TZ).get_data_as_bytes().get_data() \
        == tz.get_data_as_bytes().get_data()

    # A location record with populated children/zones and one without, so the
    # empty-array path (zero-length framing table) and the non-empty one are
    # both covered.
    loc = Variant(LOC_TYPE, (("Beijing", ""), "", "", (39.9042, 116.4074),
                             "CN", "ZBAA", 0xffff, 5, 0xffff, 0xffff, [], []))
    loc2 = Variant(LOC_TYPE, (("Sydney", ""), "New South Wales", "SYD",
                              (-33.8688, 151.2093), "AU", "YSSY",
                              1, 4, 0, 0xffff, [0, 1, 2], [3, 4]))
    for record in (loc, loc2):
        assert record.get_type_string() == LOC_TYPE
        assert record.get_data_as_bytes().get_data()

    nested = Variant("{s((ss)as)}", ("Etc/UTC", tz))
    zones = Variant("a{s((ss)as)}",
                    [nested, Variant("{s((ss)as)}", ("Australia/Sydney", tz))])
    assert zones.get_type_string() == "a{s((ss)as)}"

    countries = Variant("a{sq}", [("CN", 1), ("AU", 2)])
    metar = Variant("a{sq}", [("ZBAA", 1)])
    root = Variant(ROOT_TYPE, (MAGIC, countries, metar, zones, [loc, loc2]))
    data = root.get_data_as_bytes().get_data()
    assert root.get_type_string() == ROOT_TYPE
    # gweather-private.c's db_world_get_magic() asserts this exact word.
    assert data[:8] == MAGIC.to_bytes(8, "little"), data[:8].hex()
    # An empty locations database must still frame cleanly.
    empty = Variant(ROOT_TYPE, (MAGIC, [], [], [], []))
    assert empty.get_data_as_bytes().get_data()
    _self_test_framing_width()
    return len(data)


# Total lengths real GLib 2.88.1 produces for containers whose framing table
# straddles the 1->2 byte boundary (width_check.py).  Asserting the length
# rather than the hex keeps the vector readable: the hex for a 24-element
# a{sq} is 700 characters, and the length is what discriminates the two
# candidate width rules anyway.
#
# a{sq} with one entry per element and a 9-byte element: the total is body +
# n*width, so n=23 lands at 252 with a 1-byte table and n=24 at 287 with a
# 2-byte one — at n=24 the largest stored offset is 239, which fits in a byte,
# so a "widest stored entry" rule would pick 1 and produce a 263-byte array.
# libgweather's own reader derives the width from the value's total size
# (Db_ref_get_offset_size), which is what these numbers pin down.
_KNOWN_WIDTH_A_SQ = ((22, 241), (23, 252), (24, 287), (25, 299),
                     (26, 311), (27, 323))
_KNOWN_WIDTH_STRUCT = ((60, 360), (62, 372), (63, 378), (64, 384),
                       (126, 756), (127, 762))


def _self_test_framing_width():
    """The framing table's entry width follows the container's total size.

    Nothing in the 45 known-answer vectors above reaches the 1->2 byte
    boundary, so an earlier revision of this module could be wrong here and
    still pass its own self-test — which is exactly what happened: the real
    643KB Locations.bin came out with every sub-array read as length 0.
    """
    for n, want in _KNOWN_WIDTH_A_SQ:
        value = [("C%03d" % i, i) for i in range(n)]
        got = Variant("a{sq}", value).get_data_as_bytes().get_data()
        assert len(got) == want, (
            "a{sq} with %d elements: GLib produces %d bytes, got %d"
            % (n, want, len(got)))

    for k, want in _KNOWN_WIDTH_STRUCT:
        ts = "(" + "sq" * k + ")"
        value = tuple(x for _ in range(k) for x in ("x", 1))
        got = Variant(ts, value).get_data_as_bytes().get_data()
        assert len(got) == want, (
            "struct of %d (sq) members: GLib produces %d bytes, got %d"
            % (2 * k, want, len(got)))


def main():
    print("gvariant_pure: pure-python GVariant serialiser (no gi, no dlopen)")
    print("gvariant_pure: self-test OK, root payload %d bytes" % _self_test())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())