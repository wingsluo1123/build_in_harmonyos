#!/usr/bin/env python3
"""Conan recipe — vtable 1.2 (hand-written Makefile).

Upstream project: vtable-dumper 1.2 <https://github.com/lvc/vtable-dumper>.
The archive keeps the task slug ("vtable") so that the recipe name, the
archive path and the task branch stay aligned.

The tool lists the contents of the virtual tables of a C++ shared library.
It links libelf (shipped by elfutils) and the C++ runtime, which provides
__cxa_demangle. Upstream ships no automated test suite — the Makefile only
knows all/install/uninstall/clean and `make -n check` fails with
"No rule to make target 'check'" — so all coverage lives in test_package/
(see test_package/MANIFEST.yml for the upstream inventory).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class VtableConan(ConanFile):
    name = "vtable"
    version = "1.2"
    description = "Tool to list the contents of virtual tables in a C++ shared library."
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lvc/vtable-dumper"
    url = "https://github.com/lvc/vtable-dumper"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("elfutils/0.195.1")

    def layout(self):
        # Upstream builds in-source (plain Makefile), so source == build folder.
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dependency_dirs(self):
        """Collect include/lib dirs of the host dependency closure.

        libelf.so.1 is needed at link time and, together with its own
        dependency libzstd.so.1, at run time.
        """
        includes, libs = [], []
        for dep in self.dependencies.host.values():
            component = dep.cpp_info.aggregated_components()
            includes += [d for d in component.includedirs if d not in includes]
            libs += [d for d in component.libdirs if d not in libs]
        return includes, libs

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler and flags come from Conan, never from shell variables
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c", "clang")
        includes, libs = self._dependency_dirs()
        cflags = " ".join(["-fPIC", "-O2"] + [f"-I{d}" for d in includes])
        # --disable-new-dtags keeps DT_RPATH instead of DT_RUNPATH: RPATH of an
        # executable is inherited while resolving the NEEDED entries of the
        # libraries it loads, so libelf.so.1 finds its own libzstd.so.1 without
        # the consumer having to export LD_LIBRARY_PATH.
        ldflags = " ".join(
            [f"-L{d}" for d in libs]
            + ["-Wl,--disable-new-dtags"]
            + [f"-Wl,-rpath,{d}" for d in libs]
        )
        # CXXLIB: upstream Makefile hardcodes -lstdc++; the patch makes the
        # runtime library name overridable, and libc++ is what OHOS ships.
        # The upstream Makefile builds in-source, so it must run in the source
        # folder (basic_layout keeps the build folder separate) and the binary
        # is picked up from there by package().
        self.run(
            'make -j1 CC={} CFLAGS="{}" LDFLAGS="{}" CXXLIB="-lc++"'.format(
                cc, cflags, ldflags
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "vtable-dumper", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
