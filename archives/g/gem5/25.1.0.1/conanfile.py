#!/usr/bin/env python3
"""Conan recipe — gem5 25.1.0.1 for HarmonyOS PC (OHOS/aarch64, SCons).

gem5 is a modular discrete-event computer architecture simulator.  This
recipe builds the ARM ``gem5.opt`` binary with the OHOS platform toolchain
(hnp clang 15.0.4, libc++, OHOS sysroot, static conan zlib).

Platform adaptations (all validated in the stage-2 exploration build; see
notes.md for the evidence trail):

* SCons is bootstrapped from pip inside generate(): no ``scons`` recipe is
  published in the ohpcd remote (same approach as the merged dxx-rebirth 0.6
  recipe).  The pinned version was verified against Python 3.12 on OHOS.
* gem5 requires a ``python-config`` at configure time (SConstruct:486-503)
  and OHOS ships none.  generate() resolves a *complete* build-time CPython
  3.12 prefix with a fixed, runtime-verified candidate order: (1) the
  ``python/3.12.9`` package pulled with ``tool_requires`` (E543 pattern;
  ohpcd ships a signed OHOS binary with headers and libpython), (2) the
  public HNP installs under ``$HNP_PUBLIC_HOME/python.org/python_*``, and
  (3) the ambient interpreter, inspected with a corrected sysconfig probe.
  Every candidate must provide ``include/python3.12/Python.h`` and
  ``lib/libpython3.12.so*`` and must actually run; the recipe fails loudly
  instead of silently using a header-less runtime interpreter.  A
  ``python3-config`` shim is generated from the chosen prefix, SCons itself
  runs under that interpreter, libpython is linked/rpath'd against it, and
  the prefix's stdlib + lib-dynload are placed on PYTHONPATH so the
  embedded build-time host tools (gem5py) work even though SCons strips
  PYTHONHOME from child environments.
* SCons 4.x hardcodes ``env['SHELL'] = 'sh'`` in its POSIX platform and the
  bare name is resolved against the *child* PATH.  On CI workers that
  resolution fails (absent/shadowed shell), so every Configure probe and
  every build action dies silently — this produced the all-probes-fail
  signature on all four gem5 CI runs.  generate() pins the absolute system
  shell in the installed SCons copy (godot/gpsd/serf/vixl precedent).
* gem5's SCons ignores command-line variable assignments (verified during
  stage 2).  Compiler and flag overrides must arrive through the process
  environment: CC/CXX/PYTHON_CONFIG come from
  site_scons/gem5_scons/defaults.py, CCFLAGS_EXTRA/LINKFLAGS_EXTRA are
  appended in SConstruct:987-988.  This recipe only uses that hook.
* Four private compatibility headers are injected with -I (no upstream
  source edits): sys/cdefs.h (__containerof), ucontext.h (ucontext function
  prototypes), stdio.h (stdin/stdout/stderr macros), linux/socket.h
  (sockaddr_storage clash).
* zlib is a hard dependency of gem5.  It is consumed from the ohpcd
  ``zlib/1.3.1`` package as a static archive (R26) and injected through
  CCFLAGS_EXTRA/LINKFLAGS_EXTRA; gem5's own ``-lz`` then resolves to that
  static archive because the -L directory is seen before the sysroot.
* ucontext symbols (getcontext/makecontext/swapcontext) exist only in the
  OHOS runtime libc, not in the sysroot.  The runtime libc is linked by
  absolute path (/system/lib64/libc.so).  Do NOT use ``-L/system/lib64
  -lc``: it hijacks the libc++ resolution and breaks the link (reproduced
  in stage 2).
* An rpath for the discovered CPython lib directory is embedded so the
  executable can load libpython3.12.so.1.0 without LD_LIBRARY_PATH.  The
  embedded interpreter still needs PYTHONHOME=<site python prefix> at run
  time; test_package/test.sh discovers that prefix on the worker.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


# ────────────────────────────────────────────────────────────────────── #
# Private compatibility headers (content from the stage-2 exploration;
# kept byte-compatible with the files that produced the validated build).
# ────────────────────────────────────────────────────────────────────── #

_CDEFS_H = """\
/* gem5 conan recipe compat: the OHOS sysroot's <sys/cdefs.h> does not define
 * __containerof, but its own (FreeBSD-new-style) <sys/queue.h> uses it in
 * STAILQ_LAST / TAILQ_LAST.  Injected via CCFLAGS -I<compat>, which precedes
 * the system include dirs; include_next picks up the real header.
 */
#ifndef GEM5_OHOS_SYS_CDEFS_COMPAT_H
#define GEM5_OHOS_SYS_CDEFS_COMPAT_H

#include_next <sys/cdefs.h>

#ifndef __containerof
#define __containerof(x, T, m) \\
    ((T *)((char *)(x) - __builtin_offsetof(T, m)))
#endif

#endif /* GEM5_OHOS_SYS_CDEFS_COMPAT_H */
"""

_UCONTEXT_H = """\
/* gem5 conan recipe compat: the OHOS SDK's <ucontext.h> is a stub (only
 * forward-declares struct __ucontext, no ucontext_t functions).  The runtime
 * libc (/system/lib64/libc.so) still exports getcontext/makecontext/
 * swapcontext as weak symbols, so declare them here (injected via CCFLAGS).
 * The recipe links the runtime libc by absolute path
 * (/system/lib64/libc.so); do NOT add -L/system/lib64 to the link flags,
 * that would hijack the libc++ resolution.
 */
#ifndef GEM5_OHOS_UCONTEXT_COMPAT_H
#define GEM5_OHOS_UCONTEXT_COMPAT_H

#include_next <ucontext.h>

#ifdef __cplusplus
extern "C" {
#endif

int getcontext(ucontext_t *);
int setcontext(const ucontext_t *);
void makecontext(ucontext_t *, void (*)(void), int, ...);
int swapcontext(ucontext_t *, const ucontext_t *);

#ifdef __cplusplus
}
#endif

#endif /* GEM5_OHOS_UCONTEXT_COMPAT_H */
"""

_STDIO_H = """\
/* gem5 conan recipe compat: OHOS <stdio.h> defines object-like macros with
 * parentheses:
 *   #define stdin  (stdin)
 *   #define stdout (stdout)
 *   #define stderr (stderr)
 * which break C++ qualified uses (::stdin), member access (p.stdin) and
 * pointer-to-member (&Params::stdin) — gem5 uses all of these for its
 * BaseSemihosting stdin/stdout/stderr SimObject params.  The real globals
 * are declared as "extern FILE *const stdin;" so undefining the macros
 * keeps all expressions working.  include_next picks the real header.
 */
#ifndef GEM5_OHOS_STDIO_COMPAT_H
#define GEM5_OHOS_STDIO_COMPAT_H

#include_next <stdio.h>

#undef stdin
#undef stdout
#undef stderr

#endif /* GEM5_OHOS_STDIO_COMPAT_H */
"""

_LINUX_SOCKET_H = """\
/* gem5 conan recipe compat: OHOS sysroot's <linux/socket.h> (bionic-style
 * UAPI stub) unconditionally defines "struct sockaddr_storage", which
 * clashes with the definition in <sys/socket.h> (active because __MUSL__ is
 * not defined), breaking any TU that includes both (e.g.
 * src/dev/net/ethertap.cc).  The real header only contains _K_SS_MAXSIZE,
 * __kernel_sa_family_t and the conflicting struct.  Include libc's
 * <sys/socket.h> first, re-provide the two UAPI bits, and skip the real
 * body via its include guard (include_next would still trigger the
 * redefinition).
 */
#ifndef GEM5_OHOS_LINUX_SOCKET_COMPAT_H
#define GEM5_OHOS_LINUX_SOCKET_COMPAT_H

#include <sys/socket.h>

#ifndef _K_SS_MAXSIZE
#define _K_SS_MAXSIZE 128
#endif

#ifndef __GEM5_OHOS_KERNEL_SA_FAMILY_T
#define __GEM5_OHOS_KERNEL_SA_FAMILY_T
typedef unsigned short __kernel_sa_family_t;
#endif

/* Skip the real <linux/socket.h>; its only struct is already in <sys/socket.h>. */
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
#endif

#endif /* GEM5_OHOS_LINUX_SOCKET_COMPAT_H */
"""

# Interpreter discovery helper: locate the include dir, the shared libpython
# and the stdlib prefix of the CPython that will run SCons (as ``python3``).
_PY_DISCOVER_SCRIPT = """\
import glob
import json
import os
import sys

exe = os.path.realpath(sys.executable)
roots = []
for r in (sys.base_prefix, sys.prefix, os.path.dirname(os.path.dirname(exe))):
    r = os.path.realpath(r)
    if r and r not in roots:
        roots.append(r)
p = os.path.dirname(exe)
while p and p != "/":
    if p not in roots:
        roots.append(p)
    p = os.path.dirname(p)

ver = "%d.%d" % sys.version_info[:2]
prefix = None
include = None
libdir = None
libname = None
for r in roots:
    if prefix is None and os.path.isfile(
        os.path.join(r, "lib", "python" + ver, "os.py")
    ):
        prefix = r
    if include is None:
        for d in sorted(
            glob.glob(os.path.join(r, "include", "python3.*")), reverse=True
        ):
            if os.path.isfile(os.path.join(d, "Python.h")):
                include = d
                break
    if libdir is None:
        for d in (os.path.join(r, "lib"), os.path.join(r, "lib64")):
            hits = [
                h
                for h in sorted(glob.glob(os.path.join(d, "libpython" + ver + ".so*")))
                if not h.endswith(".a")
            ]
            if hits:
                libdir = d
                libname = os.path.basename(hits[0])
                break
    if prefix and include and libdir:
        break

if not (prefix and include and libdir):
    print(json.dumps({"error": "python dev files not found", "roots": roots}))
    sys.exit(1)

if libname and libname.startswith("lib"):
    libstem = libname.split(".so")[0][3:]
else:
    libstem = "python" + ver

print(
    json.dumps(
        {
            "version": ver,
            "full_version": sys.version.split()[0],
            "prefix": prefix,
            "include": include,
            "libdir": libdir,
            "libname": libname,
            "libstem": libstem,
        }
    )
)
"""


class Gem5Conan(ConanFile):
    name = "gem5"
    version = "25.1.0.1"
    description = (
        "Modular discrete-event computer architecture simulator "
        "(ARM gem5.opt, SE/FS modes)"
    )
    license = "BSD-3-Clause"
    homepage = "https://www.gem5.org/"
    url = "https://github.com/gem5/gem5"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # R26: consume zlib as the static conan package (OHOS also has a system
    # libz; the conan archive is the only zlib the build must resolve).
    default_options = {"zlib/*:shared": False}

    # ------------------------------------------------------------------ #
    # conan plumbing
    # ------------------------------------------------------------------ #

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Hard dependency: SConstruct errors out when zlib is missing.
        # 1.3.1.1 (not 1.3.1) is required to satisfy libpng/1.6.58's own
        # zlib constraint; the override forces protobuf/3.17.3's zlib/1.3.1
        # requirement up to 1.3.1.1 so the graph has a single zlib version.
        self.requires("zlib/1.3.1.1", override=True)
        # Optional features (all present in the ohpcd registry):
        #   protobuf  -> instruction trace generation/playback (HAVE_PROTOBUF)
        #   libpng    -> PNG image output for the frame buffer (HAVE_PNG)
        #   hdf5      -> HDF5 statistics output (HAVE_HDF5)
        #   capstone  -> CapstoneDisassembler (USE_CAPSTONE / HAVE_CAPSTONE)
        #   gperftools-> tcmalloc heap allocator (--with-tcmalloc; SConstruct
        #                auto-detects tcmalloc_minimal / tcmalloc)
        # NOTE: protobuf/3.17.3 (not 21.12) because gem5's protoio.cc links
        # google::protobuf::io::Gzip{In,Out}putStream, which requires a
        # protobuf built with zlib support; the ohpcd 3.17.3 package is
        # with_zlib=True while the 21.12 package is with_zlib=False.
        self.requires("protobuf/3.17.3")
        self.requires("libpng/1.6.58")
        self.requires("hdf5/1.14.6")
        self.requires("capstone/5.0.7")
        self.requires("gperftools/2.17.2")

    def build_requirements(self):
        # Self-contained build-time CPython 3.12: ohpcd ships a signed OHOS
        # binary of python/3.12.9 including include/python3.12/Python.h and
        # lib/libpython3.12.so (E543 pattern).  It is the primary candidate
        # for the interpreter that runs SCons and for the python3-config
        # shim, so CI no longer depends on whichever python3 the worker
        # sandbox happens to resolve.
        self.tool_requires("python/3.12.9")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # generate(): SCons bootstrap, python3-config shim, compat headers,
    # zlib wiring and the build environment
    # ------------------------------------------------------------------ #

    def generate(self):
        build_dir = self.build_folder
        scons_env = os.path.join(build_dir, "_scons_env")
        shim_dir = os.path.join(build_dir, "_ohos_shims")
        shim_bin = os.path.join(shim_dir, "bin")
        compat_dir = os.path.join(shim_dir, "compat")
        tmp_dir = os.path.join(build_dir, "_tmp")
        python_config = os.path.join(shim_dir, "python3-config")

        for directory in (
            scons_env,
            shim_bin,
            tmp_dir,
            os.path.join(compat_dir, "sys"),
            os.path.join(compat_dir, "linux"),
        ):
            os.makedirs(directory, exist_ok=True)

        # 1) SCons from pip (not published in ohpcd; dxx-rebirth precedent).
        if not os.path.isfile(os.path.join(scons_env, "SCons", "__init__.py")):
            self.run(
                "python3 -m pip install --quiet --no-input "
                f"--target={scons_env} scons==4.11.1",
                env="build",
            )

        # 1b) SCons hardcodes env['SHELL'] = 'sh' in SCons/Platform/posix.py
        #     and resolves the bare name against the spawned child's PATH.
        #     On CI workers that resolution fails, which kills every
        #     Configure probe and every build action silently.  Pin the
        #     absolute system shell in the installed copy (godot 4.7.2,
        #     gpsd 3.26, serf 1.3.10 and vixl 5.1.0 all pass CI this way).
        self._patch_scons_posix_shell(scons_env)

        # 2) Build-time CPython: ordered, runtime-verified candidates.
        discover = os.path.join(shim_dir, "discover_python.py")
        save(self, discover, _PY_DISCOVER_SCRIPT)
        py = self._resolve_build_python(discover)
        self._assert_python_dev_files(py)
        save(
            self,
            os.path.join(shim_dir, "build_python.json"),
            json.dumps(py, indent=2, sort_keys=True),
        )
        save(self, python_config, self._python_config_script(py))
        os.chmod(python_config, 0o755)
        # Self-check (CI red root cause): the generated python3-config
        # shim must resolve to a real include dir that actually contains
        # Python.h and a libdir that actually contains libpython,
        # otherwise SCons configure dies with "Checking for C header
        # file Python.h... no". We run the shim through the *same*
        # /system/bin/sh SCons will use and fail loudly here with a
        # diagnostic instead of deep inside configure.  It also asserts
        # the shim describes the very interpreter recorded in
        # build_python.json, i.e. the one build() runs SCons under.
        self._verify_python_config_shim(python_config, py)

        # 3) `cc` shim: ext/libelf/native-elf-format probes the native ELF
        #    format with plain `cc`/`readelf`; without `cc` the generated
        #    header gets empty ELFCLASS/ELFDATA2 values and libelf fails.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"
        cxx = (compilers or {}).get("cpp") or "clang++"
        cc_shim = os.path.join(shim_bin, "cc")
        save(self, cc_shim, f'#!/system/bin/sh\nexec "{cc}" "$@"\n')
        os.chmod(cc_shim, 0o755)

        # 4) OHOS compatibility headers (private -I, no source edits).
        save(self, os.path.join(compat_dir, "sys", "cdefs.h"), _CDEFS_H)
        save(self, os.path.join(compat_dir, "ucontext.h"), _UCONTEXT_H)
        save(self, os.path.join(compat_dir, "stdio.h"), _STDIO_H)
        save(self, os.path.join(compat_dir, "linux", "socket.h"), _LINUX_SOCKET_H)

        # 5) zlib (static) from the conan dependency.
        zlib_pkg = self.dependencies["zlib"].package_folder

        # 5b) Optional-feature dependencies (all static from ohpcd).
        # Each contributes its include dir to CCFLAGS_EXTRA and its lib dir
        # to LINKFLAGS_EXTRA; the HAVE_* kconfig variables and the protobuf
        # bin dir are applied to `env` right after it is created below.
        # gem5 flips the corresponding `def_bool $(HAVE_X)` Kconfig entries
        # (see src/{base,cpu,proto}/Kconfig) purely from these environment
        # variables; protobuf additionally needs its `protoc` binary on PATH
        # (gem5's ProtoBuf builder invokes ${PROTOC}, default "protoc", see
        # site_scons/gem5_scons/defaults.py).
        opt_deps = {
            # name: (conan require, kconfig env var, needs bin dir on PATH)
            "protobuf": ("protobuf", "HAVE_PROTOBUF", True),
            "libpng": ("libpng", "HAVE_PNG", False),
            "hdf5": ("hdf5", "HAVE_HDF5", False),
            "capstone": ("capstone", "HAVE_CAPSTONE", False),
            "gperftools": ("gperftools", None, False),  # tcmalloc auto-probe
        }
        opt_cc_extra = []
        opt_link_extra = []
        opt_rpath_extra = []
        opt_pkg_folders = {}
        for alias, (req_name, kconfig_var, need_bin) in opt_deps.items():
            dep = self.dependencies[req_name]
            opt_pkg_folders[req_name] = dep.package_folder
            opt_cc_extra.append(f"-I{os.path.join(dep.package_folder, 'include')}")
            opt_link_extra.append(f"-L{os.path.join(dep.package_folder, 'lib')}")
            # hdf5/capstone/protobuf packages publish shared libs; embed an
            # rpath for their lib dirs so the packaged gem5.opt loads them
            # without LD_LIBRARY_PATH (same approach as the CPython rpath).
            opt_rpath_extra.append(
                f"-Wl,-rpath,{os.path.join(dep.package_folder, 'lib')}"
            )
        # Transitive shared-lib rpaths: hdf5 dynamically links libaec (libsz);
        # its lib dir is not reachable through the direct deps above, so add
        # the lib dir of every direct dependency's own dependencies that ship
        # shared libraries under their package_folder/lib.  This keeps the
        # packaged binary self-contained at runtime.
        seen_rpaths = set(opt_rpath_extra)
        for direct_name, dep in self.dependencies.items():
            for trans in getattr(dep, "dependencies", {}).values():
                t_folder = trans.package_folder
                if not t_folder:
                    continue
                t_lib = os.path.join(t_folder, "lib")
                if not os.path.isdir(t_lib):
                    continue
                rp = f"-Wl,-rpath,{t_lib}"
                if rp not in seen_rpaths:
                    seen_rpaths.add(rp)
                    opt_rpath_extra.append(rp)

        # TMPDIR: respect the environment's writable temp dir when present
        # (the CI worker sets an app-private cache); fall back to a build-dir
        # temp for hosts whose /tmp is read-only (stage-2 exploration).
        env_tmpdir = os.environ.get("TMPDIR") or os.path.join(build_dir, "_tmp")
        os.makedirs(env_tmpdir, exist_ok=True)

        env = Environment()
        # The chosen interpreter's bin dir comes first (bare `python3` in any
        # spawned action then matches the SCons interpreter), then the shim
        # bin (cc).
        env.prepend_path("PATH", os.path.join(py["prefix"], "bin"))
        env.prepend_path("PATH", shim_bin)
        # Optional-feature wiring (5b): gem5's SConsopts *probe* these deps
        # with conf.CheckHeader/CheckLib/CheckPkgConfig and OVERWRITE the
        # CONF['HAVE_*'] flags from the probe results (they do not honour
        # HAVE_* env vars).  The probes run before CCFLAGS_EXTRA is appended
        # (SConstruct:987), so the include/lib/pkgconfig dirs must reach the
        # probe subprocesses through the environment variables SCons forwards
        # to them (defaults.py use_vars: CPATH/LIBRARY_PATH/PKG_CONFIG_PATH).
        for req_name, pkg_folder in opt_pkg_folders.items():
            inc_dir = os.path.join(pkg_folder, "include")
            lib_dir = os.path.join(pkg_folder, "lib")
            env.append_path("CPATH", inc_dir)
            env.append_path("LIBRARY_PATH", lib_dir)
            env.append_path(
                "PKG_CONFIG_PATH", os.path.join(lib_dir, "pkgconfig")
            )
        # HAVE_* env vars are harmless belt-and-braces for the kconfig
        # `def_bool $(HAVE_X)` entries, but the SConsopts probe result is
        # authoritative.
        for alias, (req_name, kconfig_var, need_bin) in opt_deps.items():
            if kconfig_var:
                env.define(kconfig_var, "1")
            if need_bin:
                env.prepend_path(
                    "PATH", os.path.join(opt_pkg_folders[req_name], "bin")
                )
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define_path("PYTHON_CONFIG", python_config)
        # PYTHONPATH must carry the chosen interpreter's stdlib and its
        # lib-dynload on top of the SCons install: gem5's build-time host
        # tools (gem5py/gem5py_m5, pybind11-embedded) do NOT get PYTHONHOME
        # through SCons's env whitelist (site_scons/gem5_scons/defaults.py
        # use_vars), and the conan python package was configured with
        # --prefix=/ so its compiled-in prefix does not resolve.  Without
        # this, embedded runs fail with e.g. ModuleNotFoundError: zlib.
        python_path = [py["stdlib"], py["dynload"], scons_env]
        env.define("PYTHONPATH", os.pathsep.join(python_path))
        env.define_path("PYTHONHOME", py["prefix"])
        env.define("TMPDIR", env_tmpdir)
        # SCons ignores the process SHELL; the authoritative fix is the
        # SCons/Platform/posix.py patch above.  Keeping the variable set is
        # harmless and covers auxiliary tools that read $SHELL themselves.
        env.define_path("SHELL", "/system/bin/sh")
        # APPEND the chosen CPython libdir (it also holds libpython3.12.so
        # for the conan python package, whose interpreter has no rpath).
        # PREPENDING it made every linker step load a foreign libxml2/libz
        # from the interpreter's lib dir instead of the OHOS SDK llvm/lib
        # copy that lld itself needs (reproduced: a poisoned prepended
        # libxml2.so.16 makes `lld` fail with "Error loading shared library
        # libxml2.so.16" — CI build #62144 showed the all-probes-fail
        # signature).  Nothing else provides libpython for CheckPythonLib.
        env.append_path("LD_LIBRARY_PATH", py["libdir"])
        env.define(
            "CCFLAGS_EXTRA",
            " ".join(
                [f"-I{compat_dir}", f"-I{os.path.join(zlib_pkg, 'include')}"]
                + opt_cc_extra
            ),
        )
        env.define(
            "LINKFLAGS_EXTRA",
            " ".join(
                [
                    # ucontext symbols live in the OHOS runtime libc; link it
                    # by absolute path (never -L/system/lib64).
                    "/system/lib64/libc.so",
                    # static libz.a from the conan package (R26)
                    f"-L{os.path.join(zlib_pkg, 'lib')}",
                    # optional-feature libs (protobuf/png/hdf5/
                    # capstone/tcmalloc) — -L dirs resolved before sysroot
                ]
                + opt_link_extra
                # rpaths for optional-feature shared libs AND libpython
                + opt_rpath_extra
                + [
                    # find libpython3.12.so.1.0 without LD_LIBRARY_PATH
                    f"-Wl,-rpath,{py['libdir']}",
                ]
            ),
        )
        env.vars(self).save_script("gem5_build_env")

        self.output.info(
            f"build python ({py['source']}): {py['prefix']} "
            f"({py['full_version']})"
        )
        self.output.info(f"python3-config shim -> {python_config}")
        self.output.info(f"zlib (static)       -> {zlib_pkg}")

    # ------------------------------------------------------------------ #
    # build-time CPython resolution (ordered, runtime-verified)
    # ------------------------------------------------------------------ #

    _LIBPY_GLOB = "libpython3.12.so*"

    @classmethod
    def _inspect_prefix(cls, prefix, source, exe=None):
        """Verify that *prefix* is a complete CPython 3.12 dev prefix.

        Required: a runnable ``bin/python3``, ``include/python3.12/Python.h``,
        ``lib/libpython3.12.so*`` and the stdlib (``lib/python3.12/os.py``).
        Returns a descriptor dict, or None when the prefix is incomplete.
        """
        if not prefix or not os.path.isdir(prefix):
            return None
        exe = exe or os.path.join(prefix, "bin", "python3")
        # No os.access(X_OK) pre-check here: on OHOS HMDFS the chmod bit
        # is ignored (mode 660), so os.access(..., X_OK) is always False
        # and would silently reject a perfectly runnable interpreter
        # (R49/E046). The subprocess probe below is the authoritative
        # executability test.
        if not os.path.isfile(exe):
            return None
        include = None
        for candidate in sorted(
            glob.glob(os.path.join(prefix, "include", "python3.12")),
            reverse=True,
        ):
            if os.path.isfile(os.path.join(candidate, "Python.h")):
                include = candidate
                break
        libdir = None
        libname = None
        for candidate in (
            os.path.join(prefix, "lib"),
            os.path.join(prefix, "lib64"),
        ):
            hits = [
                hit
                for hit in sorted(
                    glob.glob(os.path.join(candidate, cls._LIBPY_GLOB))
                )
                if not hit.endswith(".a")
            ]
            if hits:
                libdir = candidate
                libname = os.path.basename(hits[0])
                break
        stdlib = os.path.join(prefix, "lib", "python3.12")
        if not (include and libdir and os.path.isfile(os.path.join(stdlib, "os.py"))):
            return None
        libstem = libname.split(".so")[0]
        if libstem.startswith("lib"):
            libstem = libstem[3:]        # The interpreter must actually run: the conan python package ships
        # no rpath, so its lib dir has to be on the loader path, and a
        # runtime-only app python must not be mistaken for a dev prefix.
        probe_env = os.environ.copy()
        ld_paths = [libdir]
        if probe_env.get("LD_LIBRARY_PATH"):
            ld_paths.append(probe_env["LD_LIBRARY_PATH"])
        probe_env["LD_LIBRARY_PATH"] = ":".join(ld_paths)
        try:
            probe = subprocess.run(
                [exe, "-c", "import sys; print(sys.version.split()[0])"],
                capture_output=True,
                text=True,
                env=probe_env,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if probe.returncode != 0 or not probe.stdout.strip():
            return None
        return {
            "source": source,
            "exe": exe,
            "prefix": os.path.realpath(prefix),
            "include": include,
            "libdir": libdir,
            "libname": libname,
            "libstem": libstem,
            "stdlib": stdlib,
            "dynload": os.path.join(stdlib, "lib-dynload"),
            "full_version": probe.stdout.strip().splitlines()[-1],
        }

    def _resolve_build_python(self, discover_script):
        """Ordered candidate resolution for the interpreter that runs SCons.

        (1) conan tool_requires python/3.12.9 package folder (E543 pattern),
        (2) public HNP installs (``$HNP_PUBLIC_HOME/python.org/python_*``),
        (3) the ambient interpreter, via a corrected sysconfig probe.
        Every candidate is verified on disk and executed before it is used;
        none of the paths is hardcoded as a single point of failure.
        """
        tried = []

        # (1) conan tool_requires python/3.12.9
        py_dep = None
        for getter in (
            lambda: self.dependencies.build["python"],
            lambda: self.dependencies["python"],
        ):
            try:
                py_dep = getter()
                break
            except (KeyError, ConanException):
                continue
        if py_dep is not None:
            py = self._inspect_prefix(
                py_dep.package_folder, source="conan python/3.12.9"
            )
            if py:
                return py
            tried.append(py_dep.package_folder + " (conan python/3.12.9)")

        # (2) public HNP python installs
        hnp_bases = []
        for base in (os.environ.get("HNP_PUBLIC_HOME"), "/data/service/hnp"):
            if base and base not in hnp_bases:
                hnp_bases.append(base)
        for base in hnp_bases:
            prefixes = sorted(
                glob.glob(os.path.join(base, "python.org", "python_*")),
                reverse=True,
            )
            prefixes.append(os.path.join(base, "python.org", "python_3.12"))
            for prefix in dict.fromkeys(prefixes):
                py = self._inspect_prefix(
                    prefix, source=f"HNP public python ({base})"
                )
                if py:
                    return py
                tried.append(prefix + " (HNP)")

        # (3) ambient interpreter, corrected sysconfig discovery
        for exe in self._ambient_python_candidates():
            result = subprocess.run(
                [exe, discover_script], capture_output=True, text=True
            )
            if result.returncode != 0 or not result.stdout.strip():
                tried.append(exe + " (ambient: probe failed)")
                continue
            try:
                data = json.loads(result.stdout.strip().splitlines()[-1])
            except ValueError:
                tried.append(exe + " (ambient: bad probe output)")
                continue
            if "error" in data:
                tried.append(exe + " (ambient: " + str(data["error"]) + ")")
                continue
            py = self._inspect_prefix(
                data["prefix"], source="ambient interpreter"
            )
            if py:
                return py
            tried.append(exe + " (ambient: incomplete prefix)")

        self.fail(
            "no complete CPython 3.12 build prefix found for the gem5 "
            "build; a candidate must provide include/python3.12/Python.h, "
            "lib/libpython3.12.so* and a runnable interpreter. Tried: "
            + "; ".join(tried)
        )

    @staticmethod
    def _ambient_python_candidates():
        candidates = [
            os.path.expanduser("~/usr/local/bin/python3"),
            os.path.expanduser("~/.local/bin/python3"),
            "/data/service/hnp/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        for extra in sorted(
            glob.glob("/data/service/hnp/python.org/*/bin/python3"), reverse=True
        ):
            if extra not in candidates:
                candidates.append(extra)
        which = shutil.which("python3")
        if which and which not in candidates:
            candidates.append(which)
        # No os.access(X_OK) filter here either (see _inspect_prefix
        # note); the probe in _resolve_build_python is authoritative.
        return [exe for exe in candidates if exe and os.path.isfile(exe)]

    def _assert_python_dev_files(self, py):
        """Hard gate: the chosen prefix must have the dev files (no silent
        fallback to a header-less runtime interpreter)."""
        missing = []
        if not os.path.isfile(os.path.join(py["include"], "Python.h")):
            missing.append("Python.h (include dir: %s)" % py["include"])
        if not glob.glob(os.path.join(py["libdir"], self._LIBPY_GLOB)):
            missing.append("libpython3.12.so* (lib dir: %s)" % py["libdir"])
        if missing:
            self.fail(
                "build-time Python prefix %s (source: %s) is incomplete: %s"
                % (py.get("prefix"), py.get("source"), ", ".join(missing))
            )

    @staticmethod
    def _run_shim(shim, args):
        """Run the generated python3-config shim exactly like SCons will.

        The shim shebang is ``#!/system/bin/sh``; subprocess exec()s the
        kernel-resolved shell directly, so no PATH setup is needed for the
        shebang itself (printf is a shell builtin).  Returns (rc, stdout).
        """
        try:
            probe = subprocess.run(
                [shim] + list(args),
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return -1, ""
        return probe.returncode, probe.stdout.strip()

    def _verify_python_config_shim(self, python_config, py):
        """Run the shim and assert it reports the interpreter's real dev dirs.

        Guards the exact CI failure signature ("Checking for C header file
        Python.h... no") at generate() time:

        * ``python3-config --includes`` must print ``-I<dir>`` and
          ``<dir>/Python.h`` must exist,
        * ``python3-config --ldflags --embed`` must print ``-L<dir>`` and
          ``lib<stem>.so*`` must exist in that dir,
        * those dirs must equal exactly the interpreter build() will run
          SCons under (``py['include']``/``py['libdir']``/
          ``py['libstem']``) — i.e. shim and SCons interpreter are one
          and the same installation.

        Any mismatch fails the build here with resolved paths, instead of a
        terse "Python.h... no" deep inside SConstruct configure.
        """
        rc, includes = self._run_shim(python_config, ["--includes"])
        if rc != 0 or not includes:
            self.fail(
                "python3-config shim self-check failed: --includes returned "
                f"rc={rc} output={includes!r} (shim: {python_config})"
            )
        inc_dirs = [f[2:] for f in includes.split() if f.startswith("-I")]
        if not inc_dirs:
            self.fail(
                "python3-config shim self-check failed: --includes printed no "
                f"-I dir ({includes!r})"
            )
        include = inc_dirs[0]
        if not os.path.isfile(os.path.join(include, "Python.h")):
            self.fail(
                "python3-config shim self-check failed: include dir %s has no "
                "Python.h (SConstruct would report 'Python.h... no'). "
                "Resolved build python: %s (source: %s), recorded include: %s"
                % (include, py.get("prefix"), py.get("source"), py.get("include"))
            )
        rc, ldflags = self._run_shim(python_config, ["--ldflags", "--embed"])
        if rc != 0 or not ldflags:
            self.fail(
                "python3-config shim self-check failed: --ldflags --embed "
                f"returned rc={rc} output={ldflags!r}"
            )
        libdirs = [f[2:] for f in ldflags.split() if f.startswith("-L")]
        libstems = [f[2:] for f in ldflags.split() if f.startswith("-l")]
        libdir = libdirs[0] if libdirs else ""
        libstem = libstems[0] if libstems else ""
        if not libdir or not glob.glob(os.path.join(libdir, f"lib{libstem}.so*")):
            self.fail(
                "python3-config shim self-check failed: no libpython in "
                f"-L{libdir} -l{libstem} (ldflags: {ldflags!r})"
            )
        # Same-installation assertion: what the shim reports must be exactly
        # what build() will use (build_python.json / py descriptor).
        if (include, libdir, libstem) != (
            py["include"], py["libdir"], py["libstem"],
        ):
            self.fail(
                "python3-config shim self-check failed: shim reports "
                f"include={include} libdir={libdir} libstem={libstem} but "
                f"recorded SCons interpreter is include={py['include']} "
                f"libdir={py['libdir']} libstem={py['libstem']} (source: "
                f"{py.get('source')}, prefix: {py.get('prefix')})"
            )
        self.output.info(
            f"python3-config shim self-check OK: {python_config} "
            f"(--includes -> {include}; SCons runs under {py['exe']})"
        )

    @staticmethod
    def _patch_scons_posix_shell(scons_env):
        """Pin the absolute system shell in the installed SCons POSIX tool.

        SCons 4.x runs actions through ``[env['SHELL'], '-c', cmd]`` with
        ``env['SHELL'] = 'sh'`` hardcoded in SCons/Platform/posix.py, and the
        bare name is looked up in the spawned child's PATH.  On CI workers
        that lookup fails, so every Configure probe reports "no" without a
        visible error (and every later build action would fail the same way).
        SCons ignores the process ``SHELL`` variable, hence the installed
        copy is patched (godot 4.7.2, gpsd 3.26, serf 1.3.10 and vixl 5.1.0
        all pass CI with exactly this patch).
        """
        posix_py = os.path.join(scons_env, "SCons", "Platform", "posix.py")
        with open(posix_py, "r", encoding="utf-8") as handle:
            source = handle.read()
        if "'/system/bin/sh'" in source:
            return
        patched, count = re.subn(
            r"env\['SHELL'\]\s*=\s*'sh'",
            "env['SHELL'] = '/system/bin/sh'",
            source,
            count=1,
        )
        if count != 1:
            raise ConanException(
                "SCons POSIX shell patch failed: expected "
                "env['SHELL'] = 'sh' assignment not found in " + posix_py
            )
        with open(posix_py, "w", encoding="utf-8") as handle:
            handle.write(patched)
        # Drop stale bytecode so the patched source is what actually runs.
        pycache = os.path.join(scons_env, "SCons", "Platform", "__pycache__")
        if os.path.isdir(pycache):
            shutil.rmtree(pycache, ignore_errors=True)

    @staticmethod
    def _python_config_script(py):
        return textwrap.dedent(
            f"""\
            #!/system/bin/sh
            # Generated by the gem5 25.1.0.1 conan recipe (generate()).
            # Minimal python3-config replacement for the CPython that runs
            # SCons; gem5's SConstruct:486-503 requires one and OHOS ships
            # none.  Paths come from the verified build-time prefix
            # (source: {py['source']}; prefix: {py['prefix']}).
            for arg in "$@"; do
              case "$arg" in
                --includes|--cflags) printf -- "-I%s " "{py['include']}" ;;
                --ldflags) printf -- "-L%s -l%s " "{py['libdir']}" "{py['libstem']}" ;;
                --embed) printf -- "-l%s " "{py['libstem']}" ;;
                --prefix|--exec-prefix) printf "%s\\n" "{py['prefix']}" ;;
                --version) printf "%s\\n" "{py['full_version']}" ;;
                *) : ;;
              esac
            done
            echo
            """
        )

    # ------------------------------------------------------------------ #
    # build() / package()
    # ------------------------------------------------------------------ #

    def build(self):
        apply_conandata_patches(self)
        # 8 jobs matches the worker CPU affinity (nproc=8) and keeps the
        # per-process memory ceiling safe on the shared 32 GiB worker.
        # Can be lowered with -c tools.build:jobs=N.
        jobs = build_jobs(self) or 8
        jobs = min(jobs, 8)
        # Run SCons with the exact interpreter that the python3-config shim,
        # PYTHONHOME, rpath and LD_LIBRARY_PATH were generated from, instead
        # of whichever `python3` the worker PATH happens to resolve to.
        py_bin = "python3"
        meta_path = os.path.join(
            self.build_folder, "_ohos_shims", "build_python.json"
        )
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as handle:
                    py_bin = json.load(handle).get("exe") or py_bin
            except (OSError, ValueError):
                pass
        if not py_bin or not os.path.isfile(py_bin):
            self.fail(
                "SCons interpreter %r from build_python.json does not "
                "exist; python3-config shim and SCons would disagree"
                % py_bin
            )
        self.output.info(f"Running SCons with {py_bin}")
        self.run(f'"{py_bin}" -m SCons build/ARM/gem5.opt -j{jobs}')
        self.output.info(
            "Upstream test inventory and execution report: "
            "reports/test-report.md (R51)"
        )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "gem5.opt",
            src=os.path.join(self.build_folder, "build", "ARM"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        # Ship the upstream configs/ tree: gem5 is unusable without a config
        # script and configs/ is the canonical entry point set.  Build
        # intermediates (objects, generated python, ...) are not packaged.
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "configs"),
            dst=os.path.join(self.package_folder, "share", "gem5", "configs"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = [os.path.join("share", "gem5")]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
