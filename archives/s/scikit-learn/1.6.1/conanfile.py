#!/usr/bin/env python3
"""Conan recipe for scikit-learn 1.6.1 on HarmonyOS PC (OHOS aarch64).

scikit-learn is a Python package with 68 Cython/C/C++ extension modules built by
its own meson build (`sklearn/meson.build` + `pyproject.toml` meson-python).

Key design decisions (all validated on-device, see notes.md):
  1. Build system is meson, NOT the PEP-517 pip path. The recipe drives
     `meson setup` + `ninja` + `meson install` directly so the install prefix is
     the Conan package folder (site-packages layout, same shape as numpy/2.5.2).
     meson/ninja/cython all come from the OHPCD Conan registry (tool_requires).
  2. numpy is a real Conan requirement: its C headers (numpy/_core/include) and
     its Cython declarations (cimport numpy -> numpy/__init__.pxd) are both
     needed, and the runtime needs the same numpy build.
  3. scipy is NOT published in the Conan registry. sklearn needs scipy only as
     *declarations* to compile — 2 .pyx files cimport them directly and 6 more
     take the same symbols through sklearn.utils._cython_blas
     (sklearn/utils/_cython_blas.pyx from scipy.linalg.cython_blas;
     arrayfuncs.pyx, svm/_lib{linear,svm,svm_sparse}.pyx,
     cluster/_k_means_lloyd.pyx, linear_model/_cd_fast.pyx via
     sklearn.utils._cython_blas; tree/_criterion.pyx from
     scipy.special.cython_special). Cython turns those into
     __Pyx_ImportFunction calls, so scipy is a RUNTIME-only dependency of the
     platform Python (OHOS wheels exist on
     pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi). When the target interpreter can
     import scipy the recipe uses its own .pxd files; otherwise it falls back to
     scipy 1.14.1's verbatim declarations shipped under pxds/ (BSD-3-Clause,
     declaration-only, never linked) passed to Cython with --include-dir.
  4. Upstream's build-time `import numpy` / `import scipy` version probes abort
     on workers whose build interpreter lacks them -> portability patch 0001
     makes both probes tolerant (they stay authoritative when importable).
  5. OHOS quirks (see knowledge/doc E004, E077, E212, E428):
     - musl does not export the interpreter's symbols to extensions, so every
       extension must link -lpython3.12 (meson native file c/cpp_link_args).
     - extensions must be code-signed before dlopen; DevBox lld signs, CI lld
       does not -> package() re-signs every packaged .so (idempotent).
     - posix_spawn does not search PATH -> sitecustomize shim resolves commands
       and signs before exec (numpy/2.5.2 same shim).
     - registry bin/cython has the builder's absolute shebang -> the recipe
       writes its own cython wrapper bound to the target interpreter.
     - CI AppSpawn sandbox may refuse dlopen of user-path .so (E212); the
       upstream suite is therefore executed out-of-band on a real device and the
       counts are declared in test_package/MANIFEST.yml + reports/test-report.md.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class ScikitLearnConan(ConanFile):
    name = "scikit-learn"
    version = "1.6.1"
    description = ("scikit-learn: machine learning in Python — Cython "
                   "extensions (classification, regression, clustering, "
                   "decomposition, model selection)")
    license = "BSD-3-Clause"
    homepage = "https://scikit-learn.org"
    url = "https://github.com/scikit-learn/scikit-learn"
    topics = ("python", "machine-learning", "cython", "meson", "harmonyos")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _hnp_bin = "/data/service/hnp/bin"

    # ── dependencies ────────────────────────────────────────────────────────
    def requirements(self):
        # numpy: build-time C headers + Cython declarations, and the numpy the
        # extensions bind against at runtime (ABI: built for numpy 2.x).
        self.requires("numpy/2.5.2")

    def build_requirements(self):
        self.tool_requires("python/3.12.9")
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("cython/3.3.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        for d in ("patches", "pxds"):
            src = os.path.join(self.recipe_folder, d)
            if os.path.isdir(src):
                copy(self, "*", src,
                     os.path.join(self.export_sources_folder, d))

    def validate(self):
        # R32: platform check must use `in ("Linux", "OHOS")`
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "scikit-learn 1.6.1 is adapted for Linux/OHOS only, got %s"
                % self.settings.os)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── build ───────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder
        builddir = os.path.join(self.build_folder, "builddir")
        tools = os.path.join(self.build_folder, "_ohos_tools")
        shim = os.path.join(self.build_folder, "_ohos_shim")
        os.makedirs(tools, exist_ok=True)
        os.makedirs(shim, exist_ok=True)

        py = self._target_python()
        pylib = self._python_libdir(py)
        sdk_llvm = self._sdk_llvm_libdir()
        penv = self._py_env(pylib, sdk_llvm)
        pyspec = self._py_spec(py, penv)
        meson_py = self._meson_entry(py)
        ninja_bin = self._ninja_bin()
        cython_site = self._pydep_site("cython", build=True)
        numpy_site = self._pydep_site("numpy")
        numpy_inc = self._numpy_include(numpy_site)
        pxd_root = self._exported_data_dir("pxds")
        for need in ("scipy/linalg/cython_blas.pxd",
                     "scipy/special/cython_special.pxd"):
            if not os.path.isfile(os.path.join(pxd_root, *need.split("/"))):
                raise ConanException("scipy Cython declaration %s is missing "
                                     "from the recipe (pxds/ tree)" % need)
        # Prefer the real scipy's own declarations when the target interpreter
        # can import it (no version skew); the vendored pxds/ then stay a
        # build-only fallback for workers without scipy.
        scipy_inc = self._scipy_declaration_root(py, penv)
        cython_inc = [p for p in (scipy_inc, pxd_root) if p]

        # Interpreter-visible module path for the whole build: meson itself,
        # Cython (tempita.py runs `from Cython import Tempita` under the target
        # interpreter), numpy (cimport numpy resolves through sys.path) and the
        # OHOS subprocess/auto-sign shim.
        build_pp = [shim, meson_site_path(meson_py), cython_site, numpy_site]

        self._create_sitecustomize(shim)
        cython_bin = self._create_cython_wrapper(py, cython_site, cython_inc,
                                                 build_pp)
        exe_wrapper = self._create_exe_wrapper(tools)
        native = os.path.join(shim, "ohos-native.ini")
        self._write_native_file(native, cython_bin, ninja_bin, exe_wrapper,
                                numpy_inc, pylib, pyspec, py)

        env_prefix = "PYTHONPATH=\"%s\" LD_LIBRARY_PATH=\"%s\"" % (
            ":".join(p for p in build_pp if p),
            ":".join(p for p in (pylib, sdk_llvm) if p))

        setup = ('%s "%s" "%s" setup "%s" "%s" --prefix="%s" '
                 '--buildtype=release --native-file="%s"'
                 % (env_prefix, py, meson_py, builddir, source,
                    self.package_folder, native))
        self.run(setup, cwd=self.build_folder)

        # OpenMP is detected by meson (required:false); clang on OHOS provides it.
        self.run('%s "%s" -C "%s"' % (env_prefix, ninja_bin, builddir),
                 cwd=self.build_folder)

    # ── package ─────────────────────────────────────────────────────────────
    def package(self):
        builddir = os.path.join(self.build_folder, "builddir")
        py = self._target_python()
        meson_py = self._meson_entry(py)
        shim = os.path.join(self.build_folder, "_ohos_shim")
        pylib = self._python_libdir(py)
        sdk_llvm = self._sdk_llvm_libdir()
        env_prefix = 'PYTHONPATH="%s:%s" LD_LIBRARY_PATH="%s"' % (
            shim, meson_site_path(meson_py),
            ":".join(p for p in (pylib, sdk_llvm) if p))
        # --no-rebuild: the tree was just built, and it removes meson's PATH
        # lookup of ninja (E428 root cause: conan's env wrapper resets PATH).
        self.run('%s "%s" "%s" install --no-rebuild -C "%s"'
                 % (env_prefix, py, meson_py, builddir),
                 cwd=self.build_folder)

        # License/docs that meson does not install.
        for pat in ("COPYING", "LICENSE", "AUTHORS*", "README*"):
            for f in glob.glob(os.path.join(self.source_folder, pat)):
                copy(self, os.path.basename(f), self.source_folder,
                     os.path.join(self.package_folder, "licenses"),
                     keep_path=False)

        if self.settings.os == "OHOS":
            self._sign_package_extensions()

    def _sign_package_extensions(self):
        """OHOS refuses to dlopen unsigned ELF (E077). DevBox lld signs its
        outputs, CI workers' lld does not, so re-sign every packaged .so
        (drop any stale .codesign first, then self-sign, then +x)."""
        sign = os.path.join(self._hnp_bin, "binary-sign-tool")
        objcopy = os.path.join(self._hnp_bin, "llvm-objcopy")
        count = 0
        for so in glob.glob(os.path.join(self.package_folder, "lib", "python*",
                                         "site-packages", "sklearn", "**",
                                         "*.so"), recursive=True):
            subprocess.run([objcopy, "--remove-section", ".codesign", so, so],
                           capture_output=True, text=True, timeout=120)
            r = subprocess.run([sign, "sign", "-inFile", so, "-outFile", so,
                                "-selfSign", "1", "-signAlg", "SHA256withECDSA"],
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                self.output.warning("re-sign failed: %s: %s"
                                    % (so, r.stderr[:120]))
                continue
            os.chmod(so, 0o755)
            count += 1
        self.output.info("scikit-learn: re-signed %d extension modules" % count)

    def package_info(self):
        # Consumed as a Python package, not linked as a C/C++ library.
        self.cpp_info.libs = []
        for site in self._site_packages_dirs():
            self.runenv_info.prepend_path("PYTHONPATH", site)
        # E004 belt-and-braces: libpython3.12 and the OHOS SDK C++ runtime are
        # needed by the extension .so at import time (the interpreter normally
        # already has both loaded; CI AppSpawn workers do not expose them).
        pydir = self._python_libdir("")
        if pydir and os.path.isdir(pydir):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", pydir)
        sdk_llvm = self._sdk_llvm_libdir()
        if sdk_llvm:
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", sdk_llvm)

    # ── helpers ─────────────────────────────────────────────────────────────
    def _site_packages_dirs(self):
        return sorted(glob.glob(os.path.join(self.package_folder, "lib",
                                             "python*", "site-packages")))

    def _dep_folder(self, name, build=False):
        """package_folder of a direct requirement. tool_requires live in the
        *build* context — `self.dependencies["meson"]` raises KeyError there."""
        groups = ([self.dependencies.build, self.dependencies] if build
                  else [self.dependencies, self.dependencies.build])
        for grp in groups:
            try:
                return str(grp[name].package_folder)
            except Exception:
                continue
        return ""

    def _pydep_site(self, dep_name, build=False):
        """site-packages dir of a Python-package dependency (numpy/cython)."""
        pkg = self._dep_folder(dep_name, build=build)
        if pkg:
            hits = sorted(glob.glob(os.path.join(pkg, "lib", "python*",
                                                 "site-packages")))
            if hits:
                return hits[0]
        raise ConanException("no site-packages found for dependency %s"
                             % dep_name)

    def _numpy_include(self, numpy_site):
        for cand in (os.path.join(numpy_site, "numpy", "_core", "include"),
                     os.path.join(numpy_site, "numpy", "core", "include")):
            if os.path.isdir(cand):
                return cand
        raise ConanException("numpy C header dir not found under %s"
                             % numpy_site)

    def _target_python(self):
        """Absolute path of the non-HNP target python (the one that will import
        the built package).

        The tool_requires CPython comes first: it is by construction an
        aarch64-linux-ohos build with its own libpython, whereas a worker's PATH
        python can be the HNP runtime, whose EXT_SUFFIX is '.cpython-312.so' —
        meson driven by it tags every extension for that interpreter instead of
        the platform ABI (published numpy/2.5.2 ships
        '*.cpython-312-aarch64-linux-ohos.so').  After it, the same resolution
        order as numpy/2.5.2.
        """
        candidates = []
        pkg = self._dep_folder("python", build=True)
        if pkg:
            candidates += [os.path.join(pkg, "bin", "python3"),
                           os.path.join(pkg, "bin", "python3.12")]
        candidates += [
            os.environ.get("SKLEARN_PYTHON"),
            os.environ.get("HMBS_PYTHON3"),
            os.environ.get("NUMPY_PYTHON"),
            os.path.expanduser("~/usr/local/bin/python3"),
            "/storage/Users/currentUser/usr/local/bin/python3",
            shutil.which("python3") or "",
        ]
        for py in candidates:
            if py and os.path.isfile(py) and os.access(py, os.X_OK):
                return py
        raise ConanException("no target python3 found; set SKLEARN_PYTHON")

    def _py_env(self, pylib, sdk_llvm):
        """Environment for invoking the target interpreter itself. A relocated
        CPython (libpython.so in its own lib dir) is not runnable without
        LD_LIBRARY_PATH, and the OHOS SDK dir must be present for libc++_shared."""
        env = dict(os.environ)
        parts = [p for p in (pylib, sdk_llvm) if p]
        if parts:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                parts + ([env["LD_LIBRARY_PATH"]]
                         if env.get("LD_LIBRARY_PATH") else []))
        return env

    def _py_spec(self, py, penv):
        r = subprocess.run([py, "-c",
                            "import sys; print('%d.%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=60, env=penv)
        if r.returncode != 0:
            raise ConanException("cannot query target python version: %s"
                                 % r.stderr[:150])
        return r.stdout.strip()

    def _meson_entry(self, py):
        """Absolute meson.py of the tool_requires meson package (its bin/meson
        wrapper has the builder's absolute python shebang, so we drive meson.py
        with the target interpreter instead)."""
        hits = []
        pkg = self._dep_folder("meson", build=True)
        if pkg:
            hits = glob.glob(os.path.join(pkg, "lib", "python*",
                                          "site-packages", "meson.py"))
        if hits:
            return hits[0]
        # Fall back on an interpreter importable meson (worker images differ).
        r = subprocess.run([py, "-c",
                            "import mesonbuild, os; print(os.path.dirname("
                            "os.path.dirname(mesonbuild.__file__)))"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            cand = os.path.join(r.stdout.strip(), "meson.py")
            if os.path.isfile(cand):
                return cand
        raise ConanException("meson not found: add tool_requires('meson/1.11.0')")

    def _ninja_bin(self):
        pkg = self._dep_folder("ninja", build=True)
        if pkg:
            cand = os.path.join(pkg, "bin", "ninja")
            if os.path.isfile(cand):
                return cand
        found = shutil.which("ninja") or os.path.join(self._hnp_bin, "ninja")
        if os.path.isfile(found):
            return found
        raise ConanException("ninja executable not found")

    def _python_libdir(self, py):
        """Dir holding libpython3.x.so (needed for -lpython and for dlopen of
        the extensions; musl does not export interpreter symbols — E004)."""
        for cand in (py, self._target_python_or_empty()):
            if cand and os.path.isfile(cand):
                prefix = os.path.dirname(os.path.dirname(
                    os.path.realpath(cand)))
                for libd in (os.path.join(prefix, "lib"),
                             os.path.join(prefix, "lib64")):
                    if os.path.isdir(libd) and any(
                            f.startswith("libpython3") for f in os.listdir(libd)):
                        return libd
        for cand in (os.path.expanduser("~/usr/local/lib"),
                     "/storage/Users/currentUser/usr/local/lib"):
            if os.path.isdir(cand) and any(f.startswith("libpython3")
                                           for f in os.listdir(cand)):
                return cand
        return ""

    def _target_python_or_empty(self):
        try:
            return self._target_python()
        except Exception:
            return ""

    def _sdk_llvm_libdir(self):
        """libc++_shared.so lives in the OHOS SDK llvm sysroot, which is on the
        loader path in a real-device shell but not inside a CI AppSpawn worker."""
        for pattern in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
                        "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib/aarch64-linux-ohos"):
            hits = sorted(glob.glob(pattern))
            if hits:
                return hits[-1]
        return ""

    def _create_cython_wrapper(self, py, cython_site, include_dirs, build_pp):
        """Cython entry point bound to the target interpreter.

        Registry bin/cython carries the builder's absolute python shebang, and
        Cython must see (a) numpy on sys.path for `cimport numpy` and (b) scipy's
        .pxd declarations through --include-dir (scipy is not published in the
        Conan registry; declaration-only — see notes.md)."""
        path = os.path.join(self.build_folder, "_ohos_tools", "cython")
        pp = ":".join([cython_site] + [p for p in build_pp if p])
        inc = " ".join('--include-dir "%s"' % d for d in include_dirs)
        content = ('#!/bin/sh\n'
                   'PYTHONPATH="%s:${PYTHONPATH:-}" exec "%s" -c '
                   '"from Cython.Compiler.Main import main; main(command_line=1)" '
                   '%s "$@"\n' % (pp, py, inc))
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)
        return path

    def _exported_data_dir(self, dirname):
        """Folder holding a data dir shipped by export_sources() (the cache puts
        exported sources under <cache>/p/<hash>/es, the local recipe dir under
        self.recipe_folder)."""
        for base in (self.export_sources_folder, self.recipe_folder):
            cand = os.path.join(str(base), dirname)
            if os.path.isdir(cand):
                return cand
        raise ConanException("%s/ not found in exported sources" % dirname)

    def _scipy_declaration_root(self, py, penv):
        """Parent dir of an importable scipy (so Cython finds scipy/**/*.pxd).
        Returns "" when scipy is absent, which is the expected CI case."""
        r = subprocess.run(
            [py, "-c", "import os, scipy; print(os.path.dirname("
                       "os.path.dirname(scipy.__file__)))"],
            capture_output=True, text=True, timeout=90, env=penv)
        out = r.stdout.strip()
        if r.returncode == 0 and out and os.path.isfile(
                os.path.join(out, "scipy", "linalg", "cython_blas.pxd")):
            self.output.info("scikit-learn: using scipy declarations from %s"
                             % out)
            return out
        self.output.info("scikit-learn: scipy not importable by the target "
                         "python -> using the vendored pxds/ declarations")
        return ""

    def _create_exe_wrapper(self, tools):
        path = os.path.join(tools, "exe_wrapper.sh")
        content = """#!/bin/sh
# exe_wrapper for HarmonyOS: sign the compiled binary, then run it.
BIN="$1"; shift
if [ -f "$BIN" ]; then
    if ! %s/llvm-readelf -S "$BIN" 2>/dev/null | grep -q '\\.codesign'; then
        %s/binary-sign-tool sign -inFile "$BIN" -outFile "$BIN" \\
            -selfSign 1 -signAlg SHA256withECDSA >/dev/null 2>&1
        chmod +x "$BIN" 2>/dev/null
    fi
fi
exec "$BIN" "$@"
""" % (self._hnp_bin, self._hnp_bin)
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, 0o755)
        return path

    def _write_native_file(self, path, cython_bin, ninja_bin, exe_wrapper,
                           numpy_inc, pylib, pyspec, py):
        """Meson native file: the build runs ON the OHOS device (build == host)."""
        link = "-lpython%s" % pyspec
        libs = ("-L%s" % pylib) if pylib else ""
        content = """[binaries]
c = '%s/clang'
cpp = '%s/clang++'
ar = '%s/llvm-ar'
ranlib = '%s/llvm-ranlib'
strip = '%s/llvm-strip'
nm = '%s/llvm-nm'
objcopy = '%s/llvm-objcopy'
ninja = '%s'
cython = '%s'
exe_wrapper = '%s'

[properties]
# Skips meson's `run_command(python, '-c', 'import numpy ...')` lookup, which a
# CI worker's build interpreter cannot always perform.
numpy-include-dir = '%s'

[built-in options]
# musl does not export the interpreter's symbols to dlopen'ed objects (E004):
# every extension must record a DT_NEEDED on libpython.
c_link_args = ['%s', '%s']
cpp_link_args = ['%s', '%s']

[build_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
""" % (self._hnp_bin, self._hnp_bin, self._hnp_bin, self._hnp_bin,
       self._hnp_bin, self._hnp_bin, self._hnp_bin, ninja_bin, cython_bin,
       exe_wrapper, numpy_inc, libs, link, libs, link)
        with open(path, "w") as f:
            f.write(content)

    def _create_sitecustomize(self, directory):
        """OHOS subprocess compatibility shim (identical to numpy/2.5.2).

        1. posix_spawn does not search PATH for bare command names.
        2. Unsigned ELF cannot exec — sign it right before the first spawn.
        """
        path = os.path.join(directory, "sitecustomize.py")
        content = '''"""HarmonyOS subprocess compatibility shim (PATH lookup + auto-sign)."""
import os
import shutil
import subprocess

_HNP_BIN = "/data/service/hnp/bin"
_SIGN_TOOL = os.path.join(_HNP_BIN, "binary-sign-tool")
_READELF = os.path.join(_HNP_BIN, "llvm-readelf")


def _is_unsigned_elf(path):
    try:
        with open(path, "rb") as fh:
            if fh.read(4) != b"\\x7fELF":
                return False
        out = subprocess.run([_READELF, "-SW", path], capture_output=True,
                             text=True, timeout=15)
        return ".codesign" not in out.stdout
    except Exception:
        return False


def _sign_elf(path):
    # A hung sign tool would silently stall the whole build -> bounded waits.
    try:
        signed = path + ".signed"
        cmd = [_SIGN_TOOL, "sign", "-inFile", path, "-outFile", signed,
               "-selfSign", "1", "-signAlg", "SHA256withECDSA",
               "-keyAlias", "meson"]
        subprocess.run(cmd, capture_output=True, timeout=30)
        if os.path.exists(signed) and os.path.getsize(signed) > 0:
            os.replace(signed, path)
            os.chmod(path, 0o755)
            return True
    except Exception:
        pass
    return False


def _resolve_command(command):
    if not isinstance(command, (str, bytes, os.PathLike)):
        return None
    command = os.fspath(command)
    if os.path.dirname(command):
        return command if os.path.isfile(command) else None
    return shutil.which(command)


if not getattr(subprocess.Popen.__init__, "_ohos_path_fix", False):
    _orig = subprocess.Popen.__init__

    def _patched(self, args, *a, **kw):
        exe = kw.get("executable")
        target = None
        if exe is not None:
            r = _resolve_command(exe)
            if r is not None:
                kw["executable"] = r
                target = r
        elif isinstance(args, (list, tuple)) and args:
            r = _resolve_command(args[0])
            if r is not None:
                args = list(args)
                args[0] = r
                target = r
        elif isinstance(args, (str, bytes, os.PathLike)):
            r = _resolve_command(args)
            if r is not None:
                args = r
                target = r
        if target and _is_unsigned_elf(target):
            _sign_elf(target)
        _orig(self, args, *a, **kw)

    _patched._ohos_path_fix = True
    subprocess.Popen.__init__ = _patched
'''
        with open(path, "w") as f:
            f.write(content)


def meson_site_path(meson_py):
    """site-packages dir holding meson.py + mesonbuild/ (needed on PYTHONPATH)."""
    return os.path.dirname(os.path.abspath(meson_py))
