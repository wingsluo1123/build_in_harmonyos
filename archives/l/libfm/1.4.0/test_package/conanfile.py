#!/usr/bin/env python3
"""test_package — libfm 1.4.0 consumer tests

Builds and REALLY EXECUTES upstream test cases against the packaged library:
  1. test-fm-path.c               — upstream unit test (src/tests/, TEST_PROGS)
  2. libfm-file-search-cli-demo.c — upstream CLI demo (src/tests/)
  3. test_libfm_extra_consumer.c  — HarmonyOS-specific non-assertion runtime
     test: links fm_xml_file_get_type() at build time (NEEDED contains
     libfm-extra.so.4) and dlopen()/dlsym() verifies the shared library
     closure loads on OHOS.

The upstream test sources are copied verbatim from the tarball (src/tests/).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class LibfmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # direct require so glib's cpp_info is aggregated (absolute include
        # dirs) instead of skipped as a transitive dep in the test context
        self.requires("glib/2.88.0")

    def _cc(self):
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp.get("c", "/data/service/hnp/bin/clang")

    def _build_one(self, src_name, out_name, extra_link):
        libfm = self.dependencies["libfm"]
        incs = ["-I" + p for p in libfm.cpp_info.includedirs]
        # upstream fm.h includes <gio/gio.h> etc. — add glib include dirs
        glib = self.dependencies["glib"]
        for p in glib.cpp_info.includedirs:
            incs.append("-I" + p)
        libdirs = ["-L" + p for p in libfm.cpp_info.libdirs if os.path.isdir(p)]
        # libfm.so exports glib symbols (no --exclude-libs on the fm target):
        # linking -lfm provides the one and only glib instance. Linking a
        # second static glib copy here would split the GType system and break
        # GObject signals in upstream demos (files-added → instance '(null)').
        libs = ["-l" + l for l in libfm.cpp_info.libs] + extra_link + ["-lm"]

        cc = self._cc()
        src = os.path.join(self.source_folder, src_name)
        out = os.path.join(self.build_folder, out_name)
        self.run(f'{cc} {src} -o {out} {" ".join(incs)} {" ".join(libdirs)} {" ".join(libs)} -ldl -lm')
        return out

    def build(self):
        # Upstream unit test: links -lfm (real build-time dependency on the package)
        self._build_one("test-fm-path.c", "test-fm-path", ["-lpthread"])
        # Upstream CLI demo: links -lfm
        self._build_one("libfm-file-search-cli-demo.c", "file-search-cli-demo", ["-lpthread"])
        # HarmonyOS-specific consumer test: links -lfm-extra
        self._build_one("test_libfm_extra_consumer.c", "test_libfm_extra_consumer", [])

    def test(self):
        if can_run(self):
            bf = self.build_folder
            # 1) upstream unit test — glib test framework prints "ok N /FmPath/..."
            self.run(os.path.join(bf, "test-fm-path"), env="conanrun")
            # 2) upstream CLI demo — prints "finished" on rc 0
            self.run(os.path.join(bf, "file-search-cli-demo"), env="conanrun")
            # 3) HarmonyOS runtime usability test
            self.run(os.path.join(bf, "test_libfm_extra_consumer"), env="conanrun")
