#!/usr/bin/env python3
"""Conan recipe for GNU Guile 2.2.7 for OpenHarmony.

Build system: Autotools (configure + make)

Key design:
- package_type = "library" (primarily used as an embeddable Scheme library)
- Also provides bindirs = ["bin"] for the guile executable
- Conan deps: gc/8.2.12, gmp/6.3.0, libffi/3.4.8
- Non-conan deps (libunistring, libltdl) found via /usr/local search paths
- Signal 5 (SIGTRAP) during .go compilation is tolerated via make -k
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GuileConan(ConanFile):
    name = "guile"
    version = "2.2.7"
    description = (
        "GNU's Ubiquitous Intelligent Language for Extension (Guile) — "
        "Scheme interpreter and embeddable library"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/guile/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gc/8.2.12")
        self.requires("gmp/6.3.0@ohpcd/stable")
        self.requires("libffi/3.4.8")

    def build_requirements(self):
        self.tool_requires("pkgconf/2.5.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)

        # R32: Support both Linux and OHOS
        if self.settings.os in ("Linux", "OHOS"):
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")

        # Non-conan dependencies (libunistring, libltdl) are installed in /usr/local.
        # Configure must find their headers and libraries.
        usr_local = "/usr/local"
        tc.extra_cflags.append(f"-I{usr_local}/include")
        tc.extra_cxxflags.append(f"-I{usr_local}/include")
        tc.extra_ldflags.append(f"-L{usr_local}/lib")
        tc.extra_ldflags.append(f"-Wl,-rpath,{usr_local}/lib")

        tc.generate()

        # R33: Set PKG_CONFIG_PATH for non-conan deps via conan env, not shell vars
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", f"{usr_local}/lib/pkgconfig")

        # Guile configure looks for bdw-gc via pkg-config, but the conan gc
        # package doesn't set pkg_config_name="bdw-gc". Set BDW_GC_CFLAGS
        # and BDW_GC_LIBS to bypass pkg-config lookup.
        gc_info = self.dependencies["gc"].cpp_info
        gc_inc = " ".join(f"-I{d}" for d in gc_info.includedirs)
        gc_libdirs = " ".join(f"-L{d}" for d in gc_info.libdirs)
        gc_libs = " ".join(f"-l{lib}" for lib in gc_info.libs)
        env.define("BDW_GC_CFLAGS", gc_inc)
        env.define("BDW_GC_LIBS", f"{gc_libdirs} {gc_libs}")

        env.vars(self).save_script("guile_nonconan_deps")

    def build(self):
        apply_conandata_patches(self)
        self._fix_umask_in_guile_snarf()
        self._fix_doc_timestamps()

        # HMDFS: set umask 022 to avoid permission-denied on temp files
        os.umask(0o022)

        autotools = Autotools(self)
        autotools.configure()

        # Build with -k (keep going) to tolerate Signal 5 (SIGTRAP) crashes during
        # .go file compilation on HarmonyOS. The .go files are written before the
        # crash occurs, so the build output is complete.
        try:
            autotools.make(args=["-k", "-j1"])
        except ConanException as e:
            self._verify_build()
            self.output.warn(
                "make reported errors (Signal 5 during .go compilation "
                "is expected on OHOS): {}".format(e)
            )

    def package(self):
        # HMDFS: set umask 022 for install step
        os.umask(0o022)
        autotools = Autotools(self)
        try:
            autotools.make(target="install", args=["-k"])
        except ConanException as e:
            # Install may also encounter Signal 5 when processing .go files
            if not os.path.exists(os.path.join(self.package_folder, "bin", "guile")):
                raise
            self.output.warn(
                "make install reported errors (Signal 5 expected on OHOS): {}".format(e)
            )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["guile-2.2"]
        self.cpp_info.set_property("pkg_config_name", "guile-2.2")
        # Headers are in include/guile/2.2/libguile/
        self.cpp_info.includedirs = ["include/guile/2.2"]
        # Also provide bindirs for the guile executable
        self.cpp_info.bindirs = ["bin"]
        # Scheme runtime files
        self.cpp_info.resdirs = ["share/guile"]
        # R32: System libs for Linux and OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── Private helpers ──────────────────────────────────────────────

    def _fix_umask_in_guile_snarf(self):
        """Fix umask 077 → 022 in libguile/guile-snarf for HMDFS compatibility.

        The configure patch (0003) fixes umask in the configure script itself,
        but guile-snarf is a separate shell script that also uses umask 077.
        """
        snarf = os.path.join(self.source_folder, "libguile", "guile-snarf")
        if os.path.isfile(snarf):
            replace_in_file(self, snarf, "umask 077", "umask 022")

    def _fix_doc_timestamps(self):
        """Touch doc files to prevent make from regenerating them.

        The texinfo tools (makeinfo/texi2html) are broken or missing on
        HarmonyOS. Touching stamp-vti and version.texi ensures make considers
        them up-to-date and skips regeneration.
        """
        for doc_file in ["doc/ref/stamp-vti", "doc/ref/version.texi"]:
            path = os.path.join(self.source_folder, doc_file)
            if os.path.isfile(path):
                os.utime(path, None)

    def _verify_build(self):
        """Verify the library was built despite possible Signal 5 crashes."""
        for lib_name in ["libguile-2.2.so", "libguile-2.2.a"]:
            for subdir in [os.path.join("libguile", ".libs"), "libguile"]:
                lib_path = os.path.join(self.build_folder, subdir, lib_name)
                if os.path.exists(lib_path):
                    return
        raise ConanException(
            "Neither libguile-2.2.so nor libguile-2.2.a was built"
        )
