#!/usr/bin/env python3
"""Conan recipe for libskia — Google Skia 2D graphics library (milestone m146).

Upstream: https://skia.googlesource.com/skia (GitHub mirror google/skia).
Commit:    34769028da93df54a2e33ebe8985413924053bc1 (chrome/m146, 2026-06-02)

Build system: GN (meta-build) + ninja.
  * P1 source strategy: the conandata URL points to a VENDORED COMPLETE source
    tarball = official skia archive + third_party/externals (9 dirs actually
    referenced by the GN build graph, pinned to the DEPS revisions) + linux
    gn prebuilt in bin/gn. No git-sync-deps / fetch-gn network calls in build().
  * Host ninja comes from PATH (present on the OHOS device).
  * No Conan-level requires: Skia bundles its third_party (skia_use_system_*=false).

STATUS: W3 PASSED on OHOS device (2026-10-14): conan create 1213/1213 built
libskia.a (21MB ar archive) and packaged 377 headers; test_package smoke
"libskia smoke ok" (pixel RGBA(255,0,0,255)) passed. Build graph out/ is
pre-generated on the host (Plan C) because OHOS hmdfs refuses to exec
user-side ELF (gn); device runs only prestaged ninja/clang.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.layout import basic_layout


class LibskiaConan(ConanFile):
    name = "libskia"
    version = "146.20260602-git.3476902"
    description = "Skia 2D graphics library (m146), built as a static software-rasterizer."
    license = "BSD-3-Clause"
    homepage = "https://skia.org"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Skia bundles all third_party via DEPS; no Conan requires for a minimal
    # software-raster build. (W0: nothing to publish upstream of us.)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version])

    def _gn_args(self):
        # R33: compilers come from the Conan toolchain profile, never shell env.
        # profile [conf] tools.build:compiler_executables={"c": ..., "cpp": ...}
        comps = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = comps.get("c", "clang") if isinstance(comps, dict) else "clang"
        cxx = comps.get("cpp", "clang++") if isinstance(comps, dict) else "clang++"
        args = [
            'is_official_build=true',
            'target_os="linux"',  # OHOS is linux-like; avoid the win toolchain branch
            'target_cpu="arm64"',
            # Host tools gn/ninja run on the build machine; cc/cxx cross to OHOS.
            f'cc="{cc}"',
            f'cxx="{cxx}"',
            # No GPU / windowing backends on OHOS for the first pass.
            # m146: skia_enable_gpu was split into discrete_gpu + graphite.
            'skia_enable_discrete_gpu=false',
            'skia_enable_graphite=false',
            'skia_use_vulkan=false',
            'skia_use_gl=false',
            'skia_use_egl=false',
            'skia_use_dawn=false',
            'skia_use_angle=false',
            'skia_use_metal=false',
            'skia_use_webgpu=false',
            # Keep everything bundled (do not depend on system copies).
            # (skia_use_system_harfbuzz does not exist in m146; removed.)
            'skia_use_system_expat=false',
            'skia_use_system_freetype2=false',
            'skia_use_system_icu=false',
            'skia_use_system_libjpeg_turbo=false',
            'skia_use_system_libpng=false',
            'skia_use_system_libwebp=false',
            'skia_use_system_zlib=false',
            'skia_use_system_wuffs=false',
            # Trim optional surface/tools to shrink the build.
            'skia_enable_tools=false',
            'skia_enable_pdf=false',
            'skia_use_icu=false',
            'skia_enable_skottie=false',
            'skia_enable_svg=true',
        ]
        if self.options.shared:
            args.append('is_component_build=true')
        return args

    def _ninja_jobs(self):
        # OHOS device memory/process resources are precious (OOM / posix_spawn
        # EAGAIN kills the whole build; CI worker showed `posix_spawn failed:
        # Resource temporarily unavailable` at -j>2); cap at 2 everywhere.
        return 2

    def _normalize_graph_compilers(self, out):
        # The PRE-GENERATED graph (host gn gen) bakes the local device compiler
        # absolute paths (/storage/Users/currentUser/usr/local/bin/clang++) which
        # do not exist on CI workers (compiler at /data/service/hnp/bin/clang).
        # Rewrite every .ninja under out/ to bare names (clang/clang++) so PATH
        # resolution (buildenv-injected) picks the right compiler per environment:
        # local device -> usr/local/bin/clang, CI worker -> hnp/bin/clang.
        for dp, _dn, fn in os.walk(out):
            for f in fn:
                if not f.endswith(".ninja"):
                    continue
                p = os.path.join(dp, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        s = fh.read()
                except OSError:
                    continue
                ns = s
                for abs_cc in (
                    "/storage/Users/currentUser/usr/local/bin/clang++",
                    "/storage/Users/currentUser/usr/local/bin/clang",
                ):
                    ns = ns.replace(abs_cc, os.path.basename(abs_cc))
                if ns != s:
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(ns)

    def _verify_graph_sources(self, out):
        # P2 (review R19/R6): a host-pre-generated graph can silently drift
        # from the vendored source tree and produce a mismatched libskia.a.
        # Before ninja, stat every source file the graph references (../…
        # paths under out/); any missing file aborts with a clear message.
        src = os.path.dirname(out) if os.path.basename(out) == "out" else out
        refs = set()
        # Compile edges look like: build obj/<target>.o: cxx ../src/foo.cpp
        # (inputs are source files relative to out/). Ignore phony/stamp edges.
        pat = re.compile(
            r"^build\s+obj/[^:]+\.o\s*:\s*\S+\s+((?:\.\./[^ \t\r\n]+))", re.M
        )
        for dp, _dn, fn in os.walk(out):
            for f in fn:
                if not f.endswith(".ninja"):
                    continue
                p = os.path.join(dp, f)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                except OSError:
                    continue
                for m in pat.finditer(content):
                    cand = os.path.normpath(os.path.join(out, m.group(1)))
                    if cand.startswith(src):
                        refs.add(cand)
        missing = [p for p in refs if not os.path.exists(p)]
        if missing:
            raise ConanException(
                "Pre-generated graph references %d missing source file(s) "
                "(e.g. %s): source tree and out/ are out of sync — regenerate "
                "the graph on the host and repack the source tarball."
                % (len(missing), missing[0])
            )

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        out = os.path.join(src, "out")

        # Plan C: the vendored source tarball may ship a PRE-GENERATED ninja
        # graph (out/build.ninja, produced by gn on the host with device cc/cxx
        # paths baked in). If present, skip gn entirely (device gn may be
        # unavailable / not executable on OHOS hmdfs) and run ninja directly.
        if not os.path.exists(os.path.join(out, "build.ninja")):
            # P1: source tarball already contains the vendored third_party and
            # the linux-arm64 gn prebuilt (bin/gn). No git-sync-deps / fetch-gn.
            # NOTE: use os.chmod (syscall), NOT shell `chmod +x`: the Conan
            # build env PATH only contains buildenv-injected dirs (no
            # /system/bin), so the `chmod` executable is not found there.
            gn = os.path.join(src, "bin", "gn")
            os.chmod(gn, 0o755)
            # gn gen (cross compile: target arm64, cc/cxx from Conan profile).
            args_str = " ".join(self._gn_args())
            self.run(f'{gn} gen "{out}" --args=\'{args_str}\'', cwd=src)

        # Make the pre-generated graph environment-agnostic (see method doc).
        if os.path.exists(os.path.join(out, "build.ninja")):
            self._normalize_graph_compilers(out)
            # P2 (review): graph-vs-source consistency gate before ninja.
            self._verify_graph_sources(out)

        # ninja build the skia static library (ninja from PATH, bounded -j).
        ninja = shutil.which("ninja") or "ninja"
        jobs = self._ninja_jobs()
        self.run(f'{ninja} -C "{out}" -j {jobs} skia', cwd=src)

    def package(self):
        out = os.path.join(self.source_folder, "out")
        # Public headers (core + include root for SkUserConfig discovery).
        copy(self, "*.h",
             os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # encode/color paths pull in modules/skcms/skcms.h (forwarder to
        # src/skcms_public.h). package_info sets includedirs=["."], so the
        # relative chain must land under the package ROOT: modules/skcms/...
        skcms_dir = os.path.join(self.source_folder, "modules", "skcms")
        if os.path.isdir(skcms_dir):
            copy(self, "*.h", skcms_dir,
                 os.path.join(self.package_folder, "modules", "skcms"))
            copy(self, "*.h", os.path.join(skcms_dir, "src"),
                 os.path.join(self.package_folder, "modules", "skcms", "src"))
        # Built library.
        copy(self, "libskia.a", out, os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libskia.so", out, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # The produced artifact is libskia.{a,so} -> library base name "skia".
        self.cpp_info.libs = ["skia"]
        # Skia public headers are referenced as `#include "include/core/SkCanvas.h"`,
        # so the include search path must be the package root (which contains include/).
        self.cpp_info.includedirs = ["."]
        self.cpp_info.system_libs = ["pthread", "m", "dl"]
        # Skia core does not require special defines for a software build.
