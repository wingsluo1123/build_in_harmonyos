#!/usr/bin/env python3
"""OHOS-specific verification for the packaged scikit-learn 1.6.1 extensions.

HarmonyOS PC differs from the upstream Linux build in four ways that must hold
for every one of the 68 compiled modules, otherwise the package cannot load on
the platform at all. The static group below parses the ELF binaries themselves
(no external tool needed, no import needed), so it also runs inside a CI
AppSpawn worker that refuses dlopen of user-path objects (E212) — it verifies
the artifact exactly as the OHOS loader will read it:

  E077  every .so must carry a `.codesign` ELF section; OHOS refuses to map an
        unsigned executable mapping.
  E004  musl does not export the interpreter's symbols to dlopen'ed objects, so
        each extension must record its own DT_NEEDED on libpython3.x.so.
  musl  the C library DT_NEEDED must be `libc.so` (musl); any `libc.so.6` /
        `ld-linux-*` / glibc-only BLAS library would make the wheel
        un-loadable on HarmonyOS.
  aarch64 / ABI tag  e_machine must be EM_AARCH64 and the file name suffix must
        equal the *running* interpreter's EXT_SUFFIX (`.cpython-312-aarch64-
        linux-ohos.so` on the non-HNP OHOS CPython build).

The runtime group additionally checks the platform string and OpenMP thread
pinning through the public API, and only runs when importing sklearn works.
"""
import argparse
import json
import os
import struct
import sys

EM_AARCH64 = 183
DT_NULL, DT_NEEDED, DT_STRTAB = 0, 1, 5
PT_LOAD, PT_DYNAMIC = 1, 2

# scikit-learn 1.6.1's own meson build emits exactly this many extension
# modules, on every platform (fixed list of .pyx/C targets). Verifying the
# count is what makes a partial package fail instead of silently passing with
# "67/67 all good" — the destructive reverse check (move one .so away) must
# report a failure, so the per-file assertions alone are not enough.
EXPECTED_EXTENSIONS = 68

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
    """Every packaged extension, with the count pinned.

    The per-file assertions below only mean something if they run over the whole
    set: dropping one .so from the package must fail, not report 67/67 green.
    """
    sos = []
    for root, _dirs, files in os.walk(os.path.join(site_dir, "sklearn")):
        for f in sorted(files):
            if f.endswith(".so"):
                sos.append(os.path.join(root, f))
    assert len(sos) == EXPECTED_EXTENSIONS, (
        "expected %d compiled extensions under %s, found %d — a partial install "
        "(or a dropped artifact) must fail here, not pass at a lower count"
        % (EXPECTED_EXTENSIONS, site_dir, len(sos)))
    return sos


# ── static OHOS artifact checks ─────────────────────────────────────────────
def _make_static_checks(site_dir):
    def all_aarch64_elf():
        sos = _extensions(site_dir)
        assert sos, "no compiled extensions found under %s" % site_dir
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
        return "%d/%d extensions carry a .codesign section" % (len(sos), len(sos))

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
        offenders, blas_linked = [], []
        for so in sos:
            with open(so, "rb") as fh:
                data = fh.read()
            needed = _elf_needed(data)
            glibc = [n for n in needed
                     if n in ("libc.so.6", "libm.so.6", "libdl.so.2")
                     or n.startswith("ld-linux")]
            if glibc or "libc.so" not in needed:
                offenders.append((os.path.basename(so), needed))
            blas_linked += [n for n in needed
                            if "openblas" in n or n in ("libblas.so.3",
                                                        "liblapack.so.3")]
        assert not offenders, ("glibc-linked objects (un-loadable on HarmonyOS "
                               "musl): %s" % offenders[:3])
        assert not blas_linked, ("BLAS must be bound through scipy at runtime, "
                                 "not linked: %s" % blas_linked[:5])
        return ("%d/%d link musl libc.so only; no BLAS/OpenBLAS DT_NEEDED "
                "(scipy provides BLAS symbols at import time)"
                % (len(sos), len(sos)))

    def abi_tag_matches_interpreter():
        import sysconfig
        suffix = sysconfig.get_config_var("EXT_SUFFIX")
        sos = _extensions(site_dir)
        wrong = [os.path.basename(so) for so in sos if not so.endswith(suffix)]
        assert not wrong, ("%d extension(s) not tagged for this interpreter "
                           "%s: %s" % (len(wrong), suffix, wrong[:5]))
        assert suffix, "EXT_SUFFIX empty"
        return "all %d extensions named *%s" % (len(sos), suffix)

    def package_layout():
        """meson install (not a wheel) is what the recipe runs, so the Conan
        package must expose a plain site-packages/sklearn tree with the version
        pinned in code — the loader path PYTHONPATH is prepended by package_info."""
        import re
        pkg = os.path.join(site_dir, "sklearn")
        assert os.path.isfile(os.path.join(pkg, "__init__.py")), pkg
        with open(os.path.join(pkg, "__init__.py"), encoding="utf-8") as fh:
            src = fh.read()
        m = re.search(r'^__version__ = ["\']([^"\']+)["\']', src, re.M)
        assert m, "no __version__ in sklearn/__init__.py"
        assert m.group(1) == "1.6.1", m.group(1)
        for sub in ("utils", "linear_model", "ensemble", "model_selection",
                    "datasets", "metrics"):
            assert os.path.isdir(os.path.join(pkg, sub)), sub
        return ("site-packages/sklearn tree complete (%s, %d extensions, "
                "data/ present: %s)" % (m.group(1), len(_extensions(site_dir)),
                                        os.path.isdir(os.path.join(pkg, "datasets",
                                                                    "data"))))

    return [
        ("ohos_elf_aarch64", all_aarch64_elf),
        ("ohos_codesign", all_code_signed),
        ("ohos_libpython_dt_needed", all_link_libpython),
        ("ohos_musl_not_glibc", musl_not_glibc),
        ("ohos_abi_tag", abi_tag_matches_interpreter),
        ("package_layout", package_layout),
    ]


# ── runtime OHOS checks (only when the extensions can be imported) ─────────
def _runtime_checks():
    def platform_identity():
        import sklearn
        import sysconfig
        machine = sysconfig.get_platform()
        assert "aarch64" in machine or "ohos" in machine, machine
        assert sklearn.__version__ == "1.6.1", sklearn.__version__
        import importlib
        ext = [m for m in ("sklearn.tree._tree", "sklearn.utils._cython_blas")
               if importlib.import_module(m).__file__.endswith(".so")]
        assert len(ext) == 2, ext
        return ("sklearn %s on %s (musl/OHOS CPython %s), %d core extensions "
                "loaded from .so" % (sklearn.__version__, machine,
                                     sys.version.split()[0], len(ext)))

    def openmp_thread_control():
        """1.6.1's OpenMP surface is sklearn.utils._openmp_helpers:
        _openmp_parallelism_enabled() proves the libomp runtime linked on OHOS,
        _openmp_effective_n_threads(n) is what every parallel Cython kernel
        passes to `#pragma omp parallel num_threads(...)`. Forcing 1 thread and
        N threads must give bit-identical results on musl/HongMeng."""
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.utils._openmp_helpers import (_openmp_effective_n_threads,
                                                   _openmp_parallelism_enabled)
        assert _openmp_parallelism_enabled(), "OpenMP parallelism disabled"
        assert _openmp_effective_n_threads(1) == 1
        assert _openmp_effective_n_threads(3) == 3
        default = _openmp_effective_n_threads()
        rng = np.random.RandomState(0)
        X = np.vstack([rng.rand(60, 2) + s for s in ((0, 0), (3, 3), (6, 0))])
        km = KMeans(n_clusters=3, n_init=2, random_state=0).fit(X)
        base = km.predict(X)
        km._n_threads = 1
        one = km.predict(X)
        km._n_threads = min(8, default) or 4
        many = km.predict(X)
        assert (base == one).all() and (base == many).all(), \
            "Lloyd kernel is not thread-count invariant"
        Xg = rng.rand(200, 6)
        yg = (Xg[:, 0] > 0.5).astype(int)
        h1 = HistGradientBoostingClassifier(random_state=0, max_iter=20).fit(Xg, yg)
        h2 = HistGradientBoostingClassifier(random_state=0, max_iter=20).fit(Xg, yg)
        assert (h1.predict(Xg) == h2.predict(Xg)).all(), \
            "HistGradientBoosting (OpenMP binning + tree build) not reproducible"
        return ("OpenMP live: default_n_threads=%d, KMeans 1-vs-%d threads "
                "identical, HistGB repeat identical (acc %.3f)"
                % (default, km._n_threads, h1.score(Xg, yg)))

    def musl_spawn_and_mmap():
        """numpy's mmap loader goes through the OHOS (hmdfs) filesystem driver —
        the path model persistence and dataset caching take on the device."""
        import numpy as np
        from sklearn.datasets import load_iris
        from sklearn.decomposition import PCA
        X, _ = load_iris(return_X_y=True)
        tmp = os.path.join(tempdir(), "iris.npy")
        np.save(tmp, np.asarray(X, dtype=np.float64))
        back = np.load(tmp, mmap_mode="r")
        assert float(np.abs(np.asarray(back) - X).max()) == 0.0
        pca = PCA(n_components=2).fit(np.asarray(back))
        assert pca.explained_variance_ratio_[0] > 0.9
        return ("mmap read of a (150, 4) array on OHOS filesystem + PCA fit "
                "OK (evr[0]=%.4f)" % pca.explained_variance_ratio_[0])

    return [("ohos_platform_identity", platform_identity),
            ("ohos_openmp_thread_control", openmp_thread_control),
            ("ohos_mmap_and_fit", musl_spawn_and_mmap)]


def tempdir():
    import tempfile
    return tempfile.mkdtemp(prefix="skl-ohos-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", required=True,
                    help="site-packages dir of the packaged scikit-learn")
    ap.add_argument("--runtime", action="store_true",
                    help="also run the checks that import sklearn")
    ap.add_argument("--json", default="", help="write machine-readable counts")
    args = ap.parse_args()

    for name, fn in _make_static_checks(args.site_dir):
        check(name, fn)
    if args.runtime:
        for name, fn in _runtime_checks():
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
