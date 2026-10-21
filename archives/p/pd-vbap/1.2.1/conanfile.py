#!/usr/bin/env python3
"""pd-vbap 1.2.1 — VBAP (Vector Base Amplitude Panning) externals for Pure Data.

Upstream builds with pd-lib-builder (`Makefile.pdlibbuilder`, vendored in-tree).
On OHOS that vendored builder hard-fails before compiling anything:

    Makefile.pdlibbuilder:764: *** Command "cc -dumpmachine" did not return a
    target triplet, needed for a build.

because it defaults to `CC = $(PLATFORM)-cc|-gcc` (line 388/392) and the OHOS
machine ships neither `cc` nor `gcc` (only the bundled clang).  The recipe
therefore injects the compiler explicitly (R33: never rely on a shell `${CC}`
that only happens to exist in the developer session) and points PDINCLUDEDIR at
the `puredata` package's `include/pd`, which is the only packaged header set
carrying Pd's internal headers (`s_stuff.h`, `m_pd.h`, `g_canvas.h`, ...).
`libpd/0.16.1` ships `include/libpd` only (no `s_stuff.h`) and cannot be used to
compile externals.

Reusable knowledge entry for this class of problem: knowledge/operations/pd-externals-ohos/.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PdVbapConan(ConanFile):
    name = "pd-vbap"
    version = "1.2.1"
    description = "VBAP (Vector Base Amplitude Panning) externals for Pure Data"
    license = "MIT"
    homepage = "https://github.com/pure-data/vbap"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The artefacts are shared objects dlopen()ed by the Pd host; conan's
    # package_type "library" would require a declarable `shared` option, which
    # makes no sense here (a static Pd external does not exist).
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Header source only: Pd's internal headers live in include/pd of the
        # puredata package (the libpd package has include/libpd, no s_stuff.h).
        self.requires("puredata/0.54.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # filename= is required: the source URL ends in the tag name, and conan
        # chooses its unpacker from the file name (otherwise: BadZipFile).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="v1.2.1.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        # R32/R33: take the compiler from the Conan toolchain/profile conf, not
        # from an ambient ${CC} (absent in CI, present in some dev sessions).
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") or "clang"
        pd_include = os.path.join(self.dependencies["puredata"].package_folder,
                                  "include", "pd")
        # pd-lib-builder builds one <source>.pd_linux per entry of `class.sources`
        # (vbap / rvbap / define_loudspeakers).  -j1 per E525.
        self.run('make -j1 CC="{}" PDINCLUDEDIR="{}"'.format(cc, pd_include),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.pd_linux",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "pd-externals"))
        # Patches (help files, examples) are data files for the Pd host.
        copy(self, "*.pd",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "pd-vbap"))
        # Documentation files for the Pd host (explicit list: a "*.txt" glob also
        # sweeps conan's own conaninfo.txt into the package).
        for doc in ("README.txt", "CHANGELOG.txt", "LICENSE.txt"):
            copy(self, doc,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "pd-vbap"))

    def package_info(self):
        # The .pd_linux files are runtime plugins dlopen()ed by the Pd host, not
        # linkable libraries: exposing them through cpp_info.libs would make a
        # consumer emit -lvbap and fail at link time.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/pd-externals"]
        self.cpp_info.resdirs = ["share/pd-vbap"]
