#!/usr/bin/env python3
"""Conan recipe — AFLplusplus 4.33c (Makefile-based fuzzer)."""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AflplusplusConan(ConanFile):
    name = "aflplusplus"
    version = "4.33c"
    description = (
        "AFL++ is a fast instrumented fuzzer with many enhancements "
        "over the original AFL."
    )
    license = "Apache-2.0"
    homepage = "https://github.com/AFLplusplus/AFLplusplus"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ── build targets ──────────────────────────────────────────────
    PROGS = [
        "afl-fuzz", "afl-showmap", "afl-tmin",
        "afl-gotcpu", "afl-analyze",
    ]

    # Shell scripts that ship in the source root (no compilation needed).
    SH_PROGS = [
        "afl-plot", "afl-cmin", "afl-cmin.bash", "afl-cmin.py",
        "afl-whatsup", "afl-addseeds", "afl-system-config",
        "afl-persistent-config",
    ]
    # afl-cc is the compiler wrapper — it requires LLVM to build
    # (GNUmakefile.llvm), so we exclude it from the OHOS build.
    # afl-wine-trace is Windows-only, also excluded.

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # AFL++ builds in-source (GNUmakefile).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compilers from Conan conf, never from bare shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cxx", "clang++")

        # Build only the core fuzzing tools (no LLVM/GCC plugins).
        # SYS=Linux: OHOS is ABI-compatible but not listed in the Makefile;
        # this ensures we get Linux linker flags (-ldl -lrt -lm).
        # NO_PYTHON=1: CI has no python3-config to satisfy the Python check.
        self.run(
            "make -f GNUmakefile -j2 {}"
            ' CC="{}" CXX="{}"'
            " NO_PYTHON=1"
            " PREFIX=/"
            " SYS=Linux".format(" ".join(self.PROGS), cc, cxx)
        )

        # Upstream test suite (test/test-all.sh) requires LLVM, GCC,
        # QEMU, Frida, and UniCorn — none available in OHOS CI.
        # We verify the core binaries via test_package instead.

    def package(self):
        # Manual install — the upstream "make install" tries to install
        # afl-cc (needs LLVM) and fails when it's missing.
        dst_bin = os.path.join(self.package_folder, "bin")
        dst_include = os.path.join(self.package_folder, "include", "afl")
        dst_share_afl = os.path.join(self.package_folder, "share", "afl")
        dst_doc = os.path.join(self.package_folder, "share", "doc", "afl")
        dst_man = os.path.join(self.package_folder, "share", "man", "man8")

        os.makedirs(dst_bin, exist_ok=True)
        os.makedirs(dst_include, exist_ok=True)
        os.makedirs(dst_share_afl, exist_ok=True)
        os.makedirs(dst_doc, exist_ok=True)
        os.makedirs(dst_man, exist_ok=True)

        # Compiled binaries.
        for p in self.PROGS:
            src = os.path.join(self.source_folder, p)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, p))
                os.chmod(os.path.join(dst_bin, p), 0o755)

        # Shell scripts (exist in source root).
        for s in self.SH_PROGS:
            src = os.path.join(self.source_folder, s)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, s))
                os.chmod(os.path.join(dst_bin, s), 0o755)

        # Headers.
        headers_dir = os.path.join(self.source_folder, "include")
        if os.path.isdir(headers_dir):
            for h in os.listdir(headers_dir):
                hp = os.path.join(headers_dir, h)
                if os.path.isfile(hp):
                    shutil.copy2(hp, os.path.join(dst_include, h))

        # Testcases + dictionaries (bundled corpus for afl-fuzz).
        for sub in ("testcases", "dictionaries"):
            src_sub = os.path.join(self.source_folder, sub)
            if os.path.isdir(src_sub):
                dst_sub = os.path.join(dst_share_afl, sub)
                if os.path.exists(dst_sub):
                    shutil.rmtree(dst_sub)
                shutil.copytree(src_sub, dst_sub)

        # Injections dictionary.
        inj = os.path.join(self.source_folder, "injections.dic")
        if os.path.isfile(inj):
            shutil.copy2(inj, os.path.join(dst_share_afl, "injections.dic"))

        # Documentation.
        docs_src = os.path.join(self.source_folder, "docs")
        if os.path.isdir(docs_src):
            for f in os.listdir(docs_src):
                fp = os.path.join(docs_src, f)
                if os.path.isfile(fp) and f.endswith(".md"):
                    shutil.copy2(fp, os.path.join(dst_doc, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/afl"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
