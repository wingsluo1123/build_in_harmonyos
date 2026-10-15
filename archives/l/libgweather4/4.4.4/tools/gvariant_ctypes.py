"""gvariant_ctypes.py — GVariant serialisation for OHOS, without PyGObject.

Why this exists
---------------
libgweather 4.4.4 ships its location database as a GVariant blob and builds it
at compile time with ``build-aux/meson/gen_locations_variant.py``, whose only
non-stdlib import is ``from gi.repository import GLib``.  On OpenHarmony PC that
import cannot work: the packaged PyGObject 3.58.0 ships
``_gi.cpython-312-aarch64-linux-ohos.so``, but loading it dies in the dynamic
loader with

    ImportError: Error relocating .../gi/_gi.cpython-312-aarch64-linux-ohos.so:
                 PyType_Ready: symbol not found

so the ``Locations.bin`` custom target fails and the build stops.  This is not a
missing package — it is the target's CPython not exporting the ABI the module
was linked against, and there is no build flag that changes that.

What this provides
------------------
The generator needs exactly three things from ``GLib``:

* ``GLib.Variant(type_string, value)`` — construct a variant from a type
  signature and a nested Python tuple/list;
* ``variant.get_data_as_bytes().get_data()`` — the serialised bytes;
* ``variant.get_type_string()`` (used by the self-test below).

Everything else it needs (``xml.etree``, ``math``, ``struct``) is stdlib.  GVariant
serialisation itself is a plain C ABI on ``libglib-2.0.so.0`` — the very library
libgweather links against — so ``ctypes`` (stdlib, no new dependency) reaches it
directly.  The output is the same bytes PyGObject would have produced: the
construction path is GLib's own ``g_variant_new_tuple`` /
``g_variant_new_array``, and the bytes come from ``g_variant_get_normal_form``,
which is the canonical form ``g_variant_new_from_data`` expects when the library
mmaps the file back in.

Portability note
----------------
Some GLib builds keep the ``g_variant_*`` entry points out of the default symbol
table and expose them only to direct ``dlopen`` users, so plain
``CDLL`` attribute lookup can fail.  ``_resolve`` therefore tries the plain name,
GLib's ``_``-suffixed internal alias, and finally ``dlsym`` on an ``RTLD_LOCAL``
handle.
"""

import ctypes
import glob
import os

__all__ = ["Variant", "GVariantBytes", "main"]


# ---------------------------------------------------------------------------
# libglib discovery / symbol resolution
# ---------------------------------------------------------------------------

def _candidate_libglib():
    """Every path worth trying for libglib-2.0, most specific first.

    ``GW_LIBGLIB_DIR`` is set by the recipe to the glib package folder, which is
    the authoritative answer during a Conan build.  The rest are fallbacks so the
    module also works when run by hand.
    """
    names = ("libglib-2.0.so.0", "libglib-2.0.so", "libglib-2.0.0.dylib",
             "libglib-2.0.dylib")
    roots = []
    for var in ("GW_LIBGLIB_DIR", "LIBRARY_PATH", "LD_LIBRARY_PATH"):
        for part in os.environ.get(var, "").split(os.pathsep):
            if part:
                roots.append(part)
    conan_home = os.environ.get("CONAN_HOME") or os.path.join(
        os.path.expanduser("~"), ".conan2")
    for pat in (os.path.join(conan_home, "p", "*", "p", "lib"),
                os.path.join(conan_home, "p", "*", "lib"),
                os.path.expanduser("~/.harmonybrew/lib")):
        roots.extend(sorted(glob.glob(pat)))
    roots += ["/data/service/hnp/lib/aarch64-linux-ohos", "/usr/lib",
              "/usr/local/lib", "/system/lib64"]
    out = []
    for root in roots:
        for n in names:
            out.append(os.path.join(root, n))
    out.extend(names)          # last resort: let the loader search
    return out


def _open_libglib():
    errors = []
    for path in _candidate_libglib():
        try:
            return ctypes.CDLL(path), path
        except OSError as exc:
            errors.append("%s: %s" % (path, exc))
    raise OSError("no usable libglib-2.0; tried:\n  " + "\n  ".join(errors))

_GLIB, _GLIB_PATH = _open_libglib()


def _dlsym_handle():
    """An RTLD_LOCAL handle, for symbols absent from the default symtab."""
    try:
        libc = ctypes.CDLL(None)
        libc.dlopen.restype = ctypes.c_void_p
        libc.dlopen.argtypes = [ctypes.c_char_p, ctypes.c_int]
        libc.dlsym.restype = ctypes.c_void_p
        libc.dlsym.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        RTLD_NOW, RTLD_LOCAL = 2, 0
        handle = libc.dlopen(_GLIB_PATH.encode(), RTLD_NOW | RTLD_LOCAL)
        if not handle:
            return None, None
        return handle, libc.dlsym
    except Exception:
        return None, None


_DL_HANDLE, _DLSYM = _dlsym_handle()


def _resolve(name, restype, argtypes):
    """Return the callable for ``name``, tolerating GLib's ``_`` alias."""
    for candidate in (name, name + "_"):
        fn = getattr(_GLIB, candidate, None)
        if fn is not None:
            fn.restype = restype
            fn.argtypes = argtypes
            return fn
    if _DLSYM is not None:
        addr = _DLSYM(_DL_HANDLE, name.encode())
        if not addr:
            addr = _DLSYM(_DL_HANDLE, (name + "_").encode())
        if addr:
            return ctypes.CFUNCTYPE(restype, *argtypes)(addr)
    raise OSError("libglib does not export %s" % name)


_GType = ctypes.c_void_p


def _cstr(ptr):
    """Decode a GLib ``const char *`` return value."""
    if not ptr:
        return None
    text = ctypes.cast(ptr, ctypes.c_char_p).value
    return text.decode() if text is not None else None

_g_variant_type_checked = _resolve("g_variant_type_checked", _GType,
                                   [ctypes.c_char_p])
_g_variant_new_tuple = _resolve("g_variant_new_tuple", _GType,
                                [ctypes.POINTER(_GType), ctypes.c_size_t])
_g_variant_new_dict_entry = _resolve("g_variant_new_dict_entry", _GType,
                                     [_GType, _GType])
_g_variant_new_array = _resolve("g_variant_new_array", _GType,
                                [_GType, ctypes.POINTER(_GType), ctypes.c_size_t])
_g_variant_new_string = _resolve("g_variant_new_string", _GType,
                                 [ctypes.c_char_p])
_g_variant_new_double = _resolve("g_variant_new_double", _GType,
                                 [ctypes.c_double])
_g_variant_new_uint16 = _resolve("g_variant_new_uint16", _GType,
                                 [ctypes.c_uint16])
_g_variant_new_uint32 = _resolve("g_variant_new_uint32", _GType,
                                 [ctypes.c_uint32])
_g_variant_new_uint64 = _resolve("g_variant_new_uint64", _GType,
                                 [ctypes.c_uint64])
_g_variant_new_byte = _resolve("g_variant_new_byte", _GType, [ctypes.c_uint8])
_g_variant_ref_sink = _resolve("g_variant_ref_sink", _GType, [_GType])
_g_variant_get_normal_form = _resolve("g_variant_get_normal_form", _GType,
                                      [_GType])
_g_variant_is_normal_form = _resolve("g_variant_is_normal_form",
                                     ctypes.c_int, [_GType])
_g_variant_get_type_string = _resolve("g_variant_get_type_string", _GType,
                                      [_GType])
_g_variant_get_data = _resolve("g_variant_get_data",
                               ctypes.POINTER(ctypes.c_char), [_GType])
_g_variant_get_size = _resolve("g_variant_get_size", ctypes.c_size_t, [_GType])
_g_variant_unref = _resolve("g_variant_unref", None, [_GType])


# ---------------------------------------------------------------------------
# Python value -> GVariant
# ---------------------------------------------------------------------------

def _build(type_string, children):
    """Assemble already-built ``children`` into one instance of ``type_string``.

    Three GLib constructors, picked by the shape's first character, because each
    type family has its own and they are not interchangeable:

    * ``{kv}``  -> ``g_variant_new_dict_entry(key, value)``; its two arguments
      are the key and value *variants*, not a children array.  Passing an array
      there makes GLib read the child pointer as a GVariantType and abort with
      "g_variant_type_info_check: assertion failed: (0 <= index && index < 24)".
      Building it as a plain tuple instead does not help either: every enclosing
      ``a{sq}`` then fails with "g_variant_new_array: assertion
      'is_of_child_type' failed", because an array of dict entries demands
      dict-entry children specifically.
    * ``(...)`` -> ``g_variant_new_tuple``.
    * ``a...``  -> ``g_variant_new_array`` with the element type.

    A GVariantBuilder is deliberately not used: it returns NULL for a tuple whose
    slot holds a ``y`` (byte) child, which is exactly the shape of libgweather's
    location record (its ``level`` field is a byte).
    """
    t = _g_variant_type_checked(type_string.encode())
    if not t:
        raise ValueError("unknown GVariant type string: %r" % type_string)
    n = len(children)
    arr = (_GType * n)(*children) if n else None
    if type_string.startswith("a"):
        element = _g_variant_type_checked(type_string[1:].encode())
        if not element:
            raise ValueError("bad array element type in %r" % type_string)
        ptr = _g_variant_new_array(element, arr, n)
    elif type_string.startswith("{"):
        if n != 2:
            raise ValueError("dict entry needs 2 fields, got %d" % n)
        ptr = _g_variant_new_dict_entry(children[0], children[1])
    else:
        ptr = _g_variant_new_tuple(arr, n if arr is not None else 0)
    if not ptr:
        raise ValueError("GLib rejected %r" % type_string)
    return ptr


def _split_fields(inner):
    """Split a GVariant type signature into its top-level field types."""
    fields, i, n = [], 0, len(inner)
    while i < n:
        j = _skip_type(inner, i)
        fields.append(inner[i:j])
        i = j
    return fields


def _skip_type(inner, i):
    """Return the index just past the single complete type starting at ``i``."""
    ch = inner[i]
    if ch in "({":
        depth, j = 0, i
        while j < len(inner):
            if inner[j] in "({":
                depth += 1
            elif inner[j] in ")}":
                depth -= 1
                if depth == 0:
                    return j + 1
            j += 1
        raise ValueError("unbalanced type string: %r" % inner)
    if ch in "a^":
        # An array's element type is the next *complete* type, so skip over it:
        # an array of tuples spans all of "((ss)as)" before the next top-level
        # field begins.
        return _skip_type(inner, i + 1)
    return i + 1


def _pack(value, type_string):
    if isinstance(value, Variant):
        return value._ptr
    if type_string == "s":
        return _g_variant_new_string(value.encode("utf-8"))
    if type_string == "d":
        return _g_variant_new_double(value)
    if type_string == "q":
        return _g_variant_new_uint16(value)
    if type_string == "u":
        return _g_variant_new_uint32(value)
    if type_string == "t":
        return _g_variant_new_uint64(value)
    if type_string == "y":
        return _g_variant_new_byte(value)
    if type_string.startswith("a"):
        item = type_string[1:]
        return _build(type_string, [_pack(v, item) for v in value])
    if type_string.startswith("("):
        assert type_string.endswith(")"), type_string
        fields = _split_fields(type_string[1:-1])
        assert len(fields) == len(value), (type_string, len(fields), len(value))
        return _build(type_string,
                      [_pack(v, f) for v, f in zip(value, fields)])
    if type_string.startswith("{"):
        assert type_string.endswith("}"), type_string
        fields = _split_fields(type_string[1:-1])
        assert len(fields) == 2, type_string
        return _build(type_string, [_pack(value[0], fields[0]),
                                    _pack(value[1], fields[1])])
    raise ValueError("unsupported GVariant type string: %r" % type_string)


class GVariantBytes(object):
    """Duck-type of PyGObject's ``GLib.Variant.get_data_as_bytes()``."""

    __slots__ = ("_raw",)

    def __init__(self, raw):
        self._raw = raw

    def get_data(self):
        return self._raw


class Variant(object):
    """Duck-type of ``GLib.Variant`` for the call shape the generator uses."""

    __slots__ = ("_ptr", "_type_string")

    def __init__(self, type_string, value):
        ptr = _pack(value, type_string)
        if not ptr:
            raise ValueError("GLib rejected %r" % type_string)
        self._type_string = type_string
        self._ptr = _g_variant_ref_sink(ptr)

    def get_type_string(self):
        return _cstr(_g_variant_get_type_string(self._ptr))

    def is_normal_form(self):
        return bool(_g_variant_is_normal_form(self._ptr))

    def get_normal_form(self):
        normal = _g_variant_ref_sink(_g_variant_get_normal_form(self._ptr))
        if not normal:
            raise ValueError("could not normalise %r" % self._type_string)
        return _from_ptr(normal)

    def get_size(self):
        return int(_g_variant_get_size(self._ptr))

    def get_data_as_bytes(self):
        # The library reads Locations.bin with g_variant_new_from_data, so the
        # bytes must be in GVariant *normal form*; a freshly built variant is
        # not, because variable-size types need the trailing framing offset.
        normal = self.get_normal_form()
        try:
            size = int(_g_variant_get_size(normal._ptr))
            return GVariantBytes(ctypes.string_at(_g_variant_get_data(normal._ptr),
                                                  size))
        finally:
            _g_variant_unref(normal._ptr)

    def print_(self, type_annotate=True):
        fn = _resolve("g_variant_print", _GType, [_GType, ctypes.c_int])
        return _cstr(fn(self._ptr, 1 if type_annotate else 0))


def _from_ptr(ptr):
    obj = Variant.__new__(Variant)
    obj._type_string = None
    obj._ptr = ptr
    return obj


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

TZ_TYPE = "((ss)as)"
LOC_TYPE = "((ss)ss(dd)ssqyqqaqaq)"
ROOT_TYPE = "(ta{sq}a{sq}a{s((ss)as)}a((ss)ss(dd)ssqyqqaqaq))"
MAGIC = 0x5747687442443130          # "0\x314DBthGW" little-endian, GWthDB01


def _self_test():
    """Exercise exactly the three shapes gen_locations_variant.py builds.

    Each type family is covered on its own first, because the dict-entry shapes
    fail differently from the tuple/array ones: a wrong prototype there aborts
    the process inside GLib rather than returning NULL, so a single combined
    check cannot say which one broke.
    """
    tz = Variant(TZ_TYPE, (("Coordinated Universal Time (UTC)", ""),
                           ["Universal", "Zulu"]))
    assert tz.get_type_string() == TZ_TYPE, tz.get_type_string()
    assert tz.get_data_as_bytes().get_data()

    # Dict entries, in isolation, then inside their arrays.
    country = Variant("{sq}", ("CN", 1))
    assert country.get_type_string() == "{sq}", country.get_type_string()
    countries = Variant("a{sq}", [country, Variant("{sq}", ("AU", 2))])
    assert countries.get_type_string() == "a{sq}", countries.get_type_string()
    tzm = Variant("a{s((ss)as)}",
                  [Variant("{s((ss)as)}", ("Etc/UTC", tz)),
                   Variant("{s((ss)as)}", ("Australia/Sydney", tz))])
    assert tzm.get_type_string() == "a{s((ss)as)}", tzm.get_type_string()

    # A pre-built Variant used as a child (what tz_variant() hands back).
    nested = Variant("{s((ss)as)}", ("Etc/UTC", tz))
    assert nested.get_type_string() == "{s((ss)as)}", nested.get_type_string()

    loc = Variant(LOC_TYPE, (("Beijing", ""), "", "",
                            (39.9042, 116.4074), "CN", "ZBAA",
                            0xffff, 5, 0xffff, 0xffff, [], []))
    assert loc.get_type_string() == LOC_TYPE, loc.get_type_string()
    assert loc.get_data_as_bytes().get_data()

    # A location that actually has children and zones exercises the non-empty
    # array paths, which the empty lists above do not.
    loc2 = Variant(LOC_TYPE, (("Sydney", ""), "New South Wales", "SYD",
                              (-33.8688, 151.2093), "AU", "YSSY",
                              1, 4, 0, 0xffff, [0, 1, 2], [3, 4]))
    assert loc2.get_type_string() == LOC_TYPE
    locs = Variant("a" + LOC_TYPE, [loc, loc2])
    assert locs.get_type_string() == "a" + LOC_TYPE, locs.get_type_string()

    root = Variant(ROOT_TYPE, (MAGIC, [country], [Variant("{sq}", ("ZBAA", 1))],
                               [nested], [loc, loc2]))
    assert root.get_type_string() == ROOT_TYPE, root.get_type_string()
    data = root.get_data_as_bytes().get_data()
    assert data[:8] == MAGIC.to_bytes(8, "little"), data[:8].hex()
    return len(data)


def main():
    print("gvariant_ctypes: libglib = %s" % _GLIB_PATH)
    print("gvariant_ctypes: self-test OK, root payload %d bytes" % _self_test())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
