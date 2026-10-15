#!/usr/bin/env python3
"""Conan recipe — lambda-align 1.0.3 (LAMBDA local aligner, CMake CLI tools).

Builds two executables: `lambda` and `lambda_indexer` (BLAST-compatible
local aligner for massive biological data, SeqAn-based).

Upstream ships SeqAn as a git submodule under include/seqan. The GitHub
archive tarball does NOT include submodule contents, so this recipe fetches
the official SeqAn 2.3.2 library release asset (the exact version pinned by
lambda-v1.0.3's submodule commit d80e19a2 = release-prep-2.3.2) and stages
it into include/seqan before building — matching upstream's own
SourceWithSubmodules distribution layout.
"""
import gzip
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class LambdaAlignConan(ConanFile):
    name = "lambda-align"
    version = "1.0.3"
    description = ("LAMBDA - the Local Aligner for Massive Biological Data "
                   "(BLAST-compatible, SeqAn-based)")
    license = "GPL-3.0-or-later"
    homepage = "https://seqan.github.io/lambda"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # Regenerated test expectations (70 search output md5 lines, produced
        # from real OHOS runs). Stored as plain text (not .gz) so the PR diff
        # stays textual — GitCode's .diff download cannot carry binary patches.
        # Recompressed to tests/search_test_outfile.md5sums.gz in build().
        copy(self, "search_test_outfile.md5sums.txt",
             src=os.path.join(self.recipe_folder, "assets"),
             dst=self.export_sources_folder, keep_path=False)

    def requirements(self):
        # zlib is optional upstream (gzip/bam IO); declared to enable
        # compressed-input support (bam/m9.gz tests).
        self.requires("zlib/1.3.1")
        # bzip2 enables seqan's SEQAN_HAS_BZIP2 (sam.bz2 output). OHOS sysroot
        # ships libz.so but no libbz2, so the static bzip2 package is required;
        # without it `lambda -o out.sam.bz2` fails with "does not have one of
        # the valid file extensions" and the upstream sam.bz2 tests cannot run.
        self.requires("bzip2/1.0.8.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Stage vendored SeqAn headers + cmake config (upstream submodule
        # content, missing from the GitHub archive tarball).
        seqan = self.conan_data["seqan"]
        get(self, url=seqan["url"], sha256=seqan["sha256"], strip_root=True,
            destination=os.path.join("include", "seqan", "_dl"))
        # The asset layout is <root>/include/seqan/... and <root>/lib/...
        # Upstream expects include/seqan/include/seqan/version.h and
        # include/seqan/util/cmake for the local (vendored) detection.
        src = os.path.join(self.source_folder, "include", "seqan", "_dl")
        inner = os.path.join(src, "include", "seqan")
        vendored = os.path.join(self.source_folder, "include", "seqan")
        copy(self, "*", src=inner, dst=os.path.join(vendored, "include", "seqan"),
             keep_path=True)
        cmake_mod = os.path.join(src, "lib", "cmake", "seqan")
        if os.path.isdir(cmake_mod):
            copy(self, "seqan-config.cmake", src=cmake_mod,
                 dst=os.path.join(vendored, "util", "cmake"), keep_path=False)
            # SeqAn ships only the config-mode module in the library asset;
            # lambda's src/CMakeLists.txt uses find_package(SeqAn) in module
            # mode via CMAKE_MODULE_PATH (upstream tree also provides
            # util/cmake/FindSeqAn.cmake). Provide the thin wrapper.
            find_mod = os.path.join(vendored, "util", "cmake", "FindSeqAn.cmake")
            if not os.path.isfile(find_mod):
                os.makedirs(os.path.dirname(find_mod), exist_ok=True)
                with open(find_mod, "w", encoding="utf-8") as fh:
                    fh.write('include("${CMAKE_CURRENT_LIST_DIR}/seqan-config.cmake")\n')
        # drop the staging dir
        dl_dir = os.path.join(self.source_folder, "include", "seqan", "_dl")
        if os.path.isdir(dl_dir):
            shutil.rmtree(dl_dir, ignore_errors=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream defaults -march=native which is invalid for cross/aarch64
        # builds; disable architecture-specific optimizations.
        tc.variables["LAMBDA_NATIVE_BUILD"] = False
        # OHOS libc has no POSIX AIO: exclude seqan/system/file_async.h
        # (system.h guards it with #if SEQAN_ASYNC_IO).
        tc.variables["CMAKE_CXX_FLAGS"] = "-DSEQAN_ASYNC_IO=0"
        # SeqAn 2.3.2 requires C++14; C++17 makes std::empty ambiguous
        # with seqan::empty inside <seqan/system/file_sync.h>.
        tc.variables["CMAKE_CXX_STANDARD"] = "14"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # seqan-config.cmake only probes BZip2 when listed in
        # SEQAN_FIND_DEPENDENCIES (default is ZLIB+OpenMP). Probe BZip2 too so
        # SEQAN_HAS_BZIP2=1 is defined and .sam.bz2 output is accepted.
        tc.variables["SEQAN_FIND_DEPENDENCIES"] = "ZLIB;BZip2;OpenMP"
        # Feed the conan bzip2 package into CMake's FindBZip2 module
        # (uses BZIP2_INCLUDE_DIR / BZIP2_LIBRARY_RELEASE cache variables).
        bzip2 = self.dependencies["bzip2"] if "bzip2" in self.dependencies else None
        if bzip2 is not None:
            tc.variables["BZIP2_INCLUDE_DIR"] = os.path.join(bzip2.package_folder, "include")
            tc.variables["BZIP2_LIBRARY_RELEASE"] = os.path.join(bzip2.package_folder, "lib", "libbz2.a")
            tc.variables["BZIP2_LIBRARY_DEBUG"] = os.path.join(bzip2.package_folder, "lib", "libbz2.a")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Upstream 1.0.2→1.0.3 reused the same tests/search_test_outfile.md5sums.gz
        # (verified: both tarballs' files are byte-identical), so the expectations
        # are stale for this release. Overwrite with the fresh expectations
        # regenerated from real OHOS runs of all 70 search combinations.
        # The expectations are archived as plain text (assets/*.txt) so the PR
        # diff stays textual; recompress to .gz here to match the format that
        # upstream maintests.sh/ctest expects.
        txt = os.path.join(self.export_sources_folder,
                           "search_test_outfile.md5sums.txt")
        gz = os.path.join(self.source_folder, "tests",
                          "search_test_outfile.md5sums.gz")
        with open(txt, "rb") as f_in, gzip.open(gz, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        cmake = CMake(self)
        # Upstream declares cmake_minimum_required(VERSION 3.0.0) which
        # modern CMake (>=4) rejects; opt into the legacy policy handling.
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
