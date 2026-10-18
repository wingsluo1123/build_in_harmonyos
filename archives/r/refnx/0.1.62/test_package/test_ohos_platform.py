#!/usr/bin/env python3
"""OHOS-specific verification for the packaged refnx 0.1.62 extensions.

refnx ships four compiled extension modules. HarmonyOS PC differs from an
upstream Linux build in four ways that must hold for every one of them, checks
that are performed by parsing the ELF images directly (pure stdlib, no readelf,
no import), so the group also runs inside a CI AppSpawn worker that refuses
dlopen of user-path objects (OHOS E212) — it verifies the artifact exactly as
the OHOS loader will read it:

  E077  every .so must carry a `.codesign` ELF section; OHOS refuses to map an
        unsigned executable mapping.
  E004  musl does not export the interpreter's symbols to dlopen'ed objects, so
        each extension must record its own DT_NEEDED on libpython3.x.so —
        without it PyModuleDef_Init is unresolvable and `import refnx` dies.
  musl  the C library DT_NEEDED must be `libc.so` (musl); any `libc.so.6` /
        `libm.so.6` / `ld-linux-*` means a glibc wheel was mistaken for an OHOS
        artifact. refnx's two C++ translation units additionally need the
        toolchain's libc++_shared (the SDK only ships a linker script named
        libc++.so), and _cyreflect is the OpenMP build so it alone links
        libomp.so.
  aarch64 / ABI tag  e_machine must be EM_AARCH64 and the file name suffix must
        equal the *running* interpreter's EXT_SUFFIX (`.cpython-312-aarch64-
        linux-ohos.so` for the registry's OHOS CPython).

The runtime group (needs only numpy, i.e. it survives a worker without scipy)
checks the platform identity, that the extensions were really dlopen'ed from
the Conan package directory, and that the packaged extension does real work on
a mmap'ed file living on the OHOS (hmdfs) filesystem.
"""
import argparse
import json
import os
import platform
import struct
import sys

EM_AARCH64 = 183
DT_NULL, DT_NEEDED, DT_STRTAB = 0, 1, 5
PT_LOAD, PT_DYNAMIC = 1, 2

# refnx 0.1.62's meson build emits exactly this many extension modules on every
# platform (fixed meson.build target list). Pinning the count is what makes a
# partial package fail instead of reporting "3/3 all good" — the destructive
# reverse check (move one .so aside) must produce a failure.
EXPECTED_EXTENSIONS = 4

# The OHOS-only link contract of each extension, taken from meson.build:
#   _cutil/_cevent are C (mycomplex/refcalc + the event reader), _creflect and
#   _cyreflect are C++, and only _cyreflect is compiled with OpenMP.
NEEDED_TAIL = {
    "_cutil.": ("libc.so",),
    "_creflect.": ("libc++_shared.so", "libc.so"),
    "_cyreflect.": ("libc++_shared.so", "libomp.so", "libc.so"),
    "_cevent.": ("libc.so",),
}

RESULTS = []


def check(name, fn):
    try:
        detail = fn()
    except Exception as exc:  # noqa: BLE001 - a failing check is still a result
        RESULTS.append((name, False, "%s: %s" % (type(exc).__name__, exc)))
        return
    RESULTS.append((name, True, detail or ""))


# ── minimal ELF64 reader ────────────────────────────────────────────────────
def _elf_sections(data):
    """[(name, sh_type, offset, size)] for an ELF64 image."""
    assert data[:4] == b"\x7fELF", "not an ELF image"
    assert data[4] == 2, "not ELF64"
    e_machine = struct.unpack_from("<H", data, 18)[0]
    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3a)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3c)[0]
    e_shstrndx = struct.unpack_from("<H", data, 0x3e)[0]
    raw = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name, sh_type = struct.unpack_from("<II", data, off)
        sh_offset, sh_size = struct.unpack_from("<QQ", data, off + 24)
        raw.append((sh_name, sh_type, sh_offset, sh_size))
    shstrtab_off = raw[e_shstrndx][2]
    out = []
    for sh_name, sh_type, sh_offset, sh_size in raw:
        start = shstrtab_off + sh_name
        end = data.index(b"\0", start)
        out.append((data[start:end].decode("ascii", "replace"), sh_type,
                    sh_offset, sh_size))
    return e_machine, out


def _elf_needed(data):
    """DT_NEEDED strings of an ELF64 shared object."""
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    loads, dyn = [], None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        p_offset = struct.unpack_from("<Q", data, off + 8)[0]
        p_vaddr = struct.unpack_from("<Q", data, off + 16)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
        if p_type == PT_LOAD:
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == PT_DYNAMIC:
            dyn = (p_offset, p_filesz)
    assert dyn, "no PT_DYNAMIC"

    def vaddr2off(vaddr):
        for seg_vaddr, seg_off, seg_sz in loads:
            if seg_vaddr <= vaddr < seg_vaddr + seg_sz:
                return seg_off + (vaddr - seg_vaddr)
        raise AssertionError("vaddr 0x%x outside any PT_LOAD" % vaddr)

    entries = []
    pos = dyn[0]
    while pos < dyn[0] + dyn[1]:
        d_tag, d_val = struct.unpack_from("<qQ", data, pos)
        if d_tag == DT_NULL:
            break
        entries.append((d_tag, d_val))
        pos += 16
    strtab_off = None
    for d_tag, d_val in entries:
        if d_tag == DT_STRTAB:
            strtab_off = vaddr2off(d_val)
    assert strtab_off is not None, "no DT_STRTAB"
    needed = []
    for d_tag, d_val in entries:
        if d_tag == DT_NEEDED:
            start = strtab_off + d_val
            needed.append(data[start:data.index(b"\0", start)].decode("ascii"))
    return needed


def _extensions(site_dir):
    """Every packaged extension, with the count pinned."""
    sos = []
    root_dir = os.path.join(site_dir, "refnx")
    for root, _dirs, files in os.walk(root_dir):
        for f in sorted(files):
            if f.endswith(".so"):
                sos.append(os.path.join(root, f))
    assert len(sos) == EXPECTED_EXTENSIONS, (
        "expected %d compiled extensions under %s, found %d — a partial install "
        "(or a dropped artifact) must fail here, not pass at a lower count"
        % (EXPECTED_EXTENSIONS, root_dir, len(sos)))
    return sos


def _legal_needed(name, needed):
    """True when `needed` is exactly the link contract recorded for `name`."""
    pylib = "libpython%d.%d.so" % sys.version_info[:2]
    for prefix, tail in NEEDED_TAIL.items():
        if name.startswith(prefix):
            return (len(needed) == len(tail) + 1
                    and needed[0].startswith(pylib)
                    and tuple(needed[1:]) == tail)
    return False


# ── static OHOS artifact checks ─────────────────────────────────────────────
def _make_static_checks(site_dir):
    def all_aarch64_elf():
        sos = _extensions(site_dir)
        bad = []
        for so in sos:
            with open(so, "rb") as fh:
                data = fh.read()
            try:
                machine, _ = _elf_sections(data)
            except AssertionError as exc:
                bad.append("%s (%s)" % (os.path.basename(so), exc))
                continue
            if machine != EM_AARCH64:
                bad.append("%s e_machine=%d" % (os.path.basename(so), machine))
        assert not bad, "non-aarch64/ELF64 objects: %s" % bad[:5]
        return "%d/%d extensions are ELF64 EM_AARCH64" % (len(sos), len(sos))

    def all_code_signed():
        sos = _extensions(site_dir)
        unsigned = []
        for so in sos:
            with open(so, "rb") as fh:
                data = fh.read()
            _, sections = _elf_sections(data)
            if ".codesign" not in [s[0] for s in sections]:
                unsigned.append(os.path.relpath(so, site_dir))
        assert not unsigned, ("%d unsigned extension(s) would fail OHOS E077 "
                             "dlopen: %s" % (len(unsigned), unsigned[:5]))
        return ("%d/%d extensions carry a .codesign section"
                % (len(sos), len(sos)))

    def all_link_libpython():
        sos = _extensions(site_dir)
        missing, spec = [], "libpython%d.%d" % sys.version_info[:2]
        for so in sos:
            with open(so, "rb") as fh:
                data = fh.read()
            if not any(n.startswith(spec) for n in _elf_needed(data)):
                missing.append(os.path.relpath(so, site_dir))
        assert not missing, ("%d object(s) lack a DT_NEEDED on %s — on musl "
                             "that means PyModuleDef_Init etc. are unresolvable "
                             "(E004): %s" % (len(missing), spec, missing[:5]))
        return "%d/%d declare DT_NEEDED %s.so*" % (len(sos), len(sos), spec)

    def musl_not_glibc():
        sos = _extensions(site_dir)
        offenders, wrong_tail = [], []
        for so in sos:
            with open(so, "rb") as fh:
                data = fh.read()
            needed = _elf_needed(data)
            glibc = [n for n in needed
                     if n in ("libc.so.6", "libm.so.6", "libdl.so.2")
                     or n.startswith("ld-linux")]
            if glibc or "libc.so" not in needed:
                offenders.append((os.path.basename(so), needed))
            elif not _legal_needed(os.path.basename(so), needed):
                wrong_tail.append((os.path.basename(so), needed))
        assert not offenders, ("glibc-linked objects (un-loadable on HarmonyOS "
                               "musl): %s" % offenders[:3])
        assert not wrong_tail, (
            "extension link contract changed (expected libc++_shared for the C++ "
            "modules, libomp only for the OpenMP _cyreflect): %s" % wrong_tail)
        return ("%d/%d link musl libc.so with the meson-declared tail "
                "(libc++_shared / libomp where applicable)" % (len(sos), len(sos)))

    def abi_tag_matches_interpreter():
        import sysconfig
        suffix = sysconfig.get_config_var("EXT_SUFFIX")
        assert suffix, "EXT_SUFFIX empty"
        sos = _extensions(site_dir)
        wrong = [os.path.basename(so) for so in sos if not so.endswith(suffix)]
        assert not wrong, ("%d extension(s) not tagged for this interpreter %s: "
                           "%s" % (len(wrong), suffix, wrong[:5]))
        return "all %d extensions named *%s" % (len(sos), suffix)

    def package_layout():
        """meson install (not a wheel) is what the recipe runs, so the Conan
        package must expose a plain site-packages/refnx tree, with the version
        module that meson generates at build time (tools/gitversion.py, which
        reads pyproject.toml because the sdist has no git checkout) resolving to
        the right release, and the sdist's data assets installed alongside."""
        import re
        pkg = os.path.join(site_dir, "refnx")
        init = os.path.join(pkg, "__init__.py")
        assert os.path.isfile(init), init
        with open(init, encoding="utf-8") as fh:
            src = fh.read()
        assert "from refnx.version import version as __version__" in src, \
            "refnx/__init__.py no longer pulls __version__ from refnx.version"
        vpath = os.path.join(pkg, "version.py")
        assert os.path.isfile(vpath), ("meson did not generate refnx/version.py "
                                       "— the gitversion step failed")
        with open(vpath, encoding="utf-8") as fh:
            vsrc = fh.read()
        m = re.search(r'^version = ["\']([^"\']+)["\']', vsrc, re.M)
        assert m, "no version assignment in refnx/version.py"
        assert m.group(1) == "0.1.62", m.group(1)
        for sub in ("_lib", "reflect", "reduce", "analysis", "dataset", "util"):
            assert os.path.isdir(os.path.join(pkg, sub)), sub
        data = os.path.join(pkg, "reflect", "tests", "theoretical.txt")
        assert os.path.isfile(data), data
        return ("site-packages/refnx tree complete (%s, %d extensions, "
                "data assets present)" % (m.group(1),
                                          len(_extensions(site_dir))))

    return [
        ("ohos_elf_aarch64", all_aarch64_elf),
        ("ohos_codesign", all_code_signed),
        ("ohos_libpython_dt_needed", all_link_libpython),
        ("ohos_musl_not_glibc", musl_not_glibc),
        ("ohos_abi_tag", abi_tag_matches_interpreter),
        ("package_layout", package_layout),
    ]


# ── runtime OHOS checks (numpy is enough; no scipy needed) ──────────────────
def _runtime_checks(site_dir):
    def platform_identity():
        import refnx
        from refnx._lib import _cutil
        assert refnx.__version__ == "0.1.62", refnx.__version__
        machine = platform.machine()
        assert "aarch64" in machine or "ohos" in machine.lower(), machine
        assert _cutil.__file__.endswith(".so"), _cutil.__file__
        assert struct.calcsize("P") == 8, "not LP64"
        return ("refnx %s on %s (OHOS CPython %s, LP64) with _cutil loaded from "
                "%s" % (refnx.__version__, machine, sys.version.split()[0],
                        os.path.basename(_cutil.__file__)))

    def dlopen_from_package_and_mmap():
        """The extension must be dlopen'able straight out of the Conan package
        (E004: that only works because the .so records its own DT_NEEDED on
        libpython3.12), and the packaged Cython helper must do real work on data
        read from a memory-mapped file on the OHOS (hmdfs) filesystem."""
        import tempfile

        import numpy as np
        from refnx._lib import _cutil, flatten, unique
        assert _cutil.__file__.startswith(site_dir), _cutil.__file__
        tmp = os.path.join(tempfile.mkdtemp(prefix="refnx-ohos-"), "data.npy")
        payload = np.arange(24000, dtype=np.float64).reshape(120, 200)
        np.save(tmp, payload)
        back = np.load(tmp, mmap_mode="r")
        assert float(np.abs(np.asarray(back) - payload).max()) == 0.0
        # a ragged structure: the Cython flattener must agree with the
        # pure-Python reference that ships in refnx._lib
        ragged = [[float(v) for v in row] for row in np.asarray(back)[:3]]
        assert list(_cutil.c_flatten(ragged)) == list(flatten(ragged))
        dupes = [3, 1, 3, 2, 1, 7, 7, 2]
        assert list(_cutil.c_unique(dupes)) == list(unique(dupes))
        return ("_cutil dlopen'ed from the package dir; mmap read of a (120, 200) "
                "array on the OHOS filesystem + c_flatten/c_unique agree with "
                "the pure-Python reference")

    def musl_allocator_and_abi():
        """A large ragged flatten walks the musl allocator hard, and a
        non-contiguous view proves the Cython wrapper does not assume C
        contiguity of its input."""
        import numpy as np
        from refnx._lib import _cutil, flatten
        assert np.__version__.startswith("2."), np.__version__
        n = 50000
        ragged = [np.arange(n * (i + 1), dtype=np.float64) for i in range(4)]
        got = np.asarray(list(_cutil.c_flatten(ragged)))
        want = np.asarray(list(flatten(ragged)))
        assert got.shape == want.shape, (got.shape, want.shape)
        assert float(np.abs(got - want).max()) == 0.0
        view = np.arange(1000.0)[::-1]
        assert not view.flags["C_CONTIGUOUS"]
        assert list(_cutil.c_flatten([view])) == list(flatten([view]))
        return ("musl allocator survived a %d-element ragged flatten "
                "(identical to the pure-Python reference) and a "
                "non-contiguous input view" % got.size)

    return [
        ("ohos_platform_identity", platform_identity),
        ("ohos_dlopen_and_mmap", dlopen_from_package_and_mmap),
        ("ohos_musl_allocator_and_abi", musl_allocator_and_abi),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", required=True,
                    help="site-packages dir of the packaged refnx")
    ap.add_argument("--runtime", action="store_true",
                    help="also run the checks that import refnx")
    ap.add_argument("--json", default="", help="write machine-readable counts")
    args = ap.parse_args()

    for name, fn in _make_static_checks(args.site_dir):
        check(name, fn)
    if args.runtime:
        for name, fn in _runtime_checks(args.site_dir):
            check(name, fn)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    for name, ok, detail in RESULTS:
        print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
    print("OHOS_PLATFORM_RESULT discovered=%d passed=%d failed=%d runtime=%s"
          % (len(RESULTS), passed, len(RESULTS) - passed, args.runtime))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"suite": "ohos-platform", "discovered": len(RESULTS),
                       "passed": passed, "failed": len(RESULTS) - passed,
                       "runtime": args.runtime,
                       "checks": [{"name": n, "ok": ok, "detail": d}
                                  for n, ok, d in RESULTS]}, fh)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
