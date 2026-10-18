#!/usr/bin/env python3
"""Conan recipe for ReZound 0.13.1beta — graphical audio editor (FOX toolkit).

ReZound builds one native C++ GUI application: ``bin/rezound`` plus its data
files (presets/key bindings/menu definitions, a demo impulse response and the
logo).  No library is produced, hence ``package_type = "application"``.

Dependencies
  fox/1.6.57        GUI toolkit.  Both the library (``libFOX-1.6``) and the
                    ``reswrap`` resource compiler are mandatory:
                    configure.ac:739 aborts without fox and :746 aborts when
                    ``reswrap`` is not on PATH.
  boost/1.91.0.1.3  Headers only — configure.ac:136 probes
                    ``boost/detail/atomic_count.hpp`` with AC_MSG_ERROR and
                    only src/backend/CAtomicCounter.h uses it.

OHOS adaptation notes
  * ``fox-config`` as installed by the fox package reports ``prefix="/"``
    (upstream bakes the prefix before the DESTDIR staging; the ``--prefix=``
    override only rewrites the script's internal variable, not the already
    computed ``includedir``/``libdir``).  ``fox-config --cflags``/``--libs``
    therefore emit ``-I//include/fox-1.6`` / ``-L//lib``, so the real search
    paths have to be injected: a private aggregated prefix is staged inside the
    build folder and handed to configure through CPPFLAGS/LDFLAGS plus
    ``--with-fox-prefix=`` (the option AX_PATH_GENERIC uses to locate
    ``<prefix>/bin/fox-config``).  Nothing is written outside the build folder
    (R49/E524).
  * The optional back-ends (OSS/PortAudio/JACK/PulseAudio) and FFTW3 have no
    OHOS counterpart; they are switched off explicitly so the configuration is
    deterministic instead of depending on what pkg-config happens to see.
  * ``ac_cv_c_bigendian=no`` is stated for aarch64: AC_C_BIGENDIAN
    (configure.ac:180) cannot run a target binary while cross compiling.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Optional audio/FFT back-ends probed by configure.ac.  None of them exist for
# OHOS, so they are disabled instead of being probed and failing.
DISABLED_BACKENDS = (
    "--disable-oss",
    "--disable-portaudio",
    "--disable-jack",
    "--disable-pulse",
    "--disable-fftw3",
    "--disable-ladspa",
)


class RezoundConan(ConanFile):
    name = "rezound"
    version = "0.13.1beta"
    description = (
        "ReZound aims to be a stable, open source, and graphical audio "
        "editor for the X Window System"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://rezound.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # fox carries libFOX-1.6, fox-config and the reswrap resource compiler.
        self.requires("fox/1.6.57", transitive_headers=True)
        # boost is used through headers only (boost/detail/atomic_count.hpp).
        self.requires("boost/1.91.0.1.3", transitive_headers=True)

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports the armv8 (aarch64) OHOS target, "
                f"got {self.settings.arch}"
            )

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so url/sha256 are passed explicitly (accountsservice
        # pattern).
        source_data = self.conan_data["sources"]
        get(
            self,
            url=source_data["url"],
            sha256=source_data["sha256"],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        if str(self.settings.os) != "OHOS":
            AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(DISABLED_BACKENDS)

        env = tc.environment()
        env.define("ac_cv_c_bigendian", "no")

        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-linux-ohos",
                    "--host=aarch64-linux-ohos",
                ]
            )

        # The aggregated prefix is what makes configure actually find the
        # toolkit and everything fox-config links into (see module docstring).
        deps_prefix = self._stage_dependency_prefix()
        tc.configure_args.append(f"--with-fox-prefix={deps_prefix}")
        env.prepend_path("PATH", os.path.join(deps_prefix, "bin"))
        env.append("CPPFLAGS", f"-I{os.path.join(deps_prefix, 'include')}")
        env.append("LDFLAGS", f"-L{os.path.join(deps_prefix, 'lib')}")
        tc.extra_ldflags.append(f"-L{os.path.join(deps_prefix, 'lib')}")
        self._add_runtime_library_paths(env)
        tc.generate(env)

    def _stage_dependency_prefix(self):
        """Mirror the dependencies' headers, libraries and tools into one tree.

        The tree lives in the build folder and holds symlinks only, so a build
        never writes into a shared prefix (R49/E524).  It exists because
        fox-config and the ``--with-fox-prefix`` discovery used by
        AX_PATH_GENERIC expect a single prefix layout
        (``include/fox-1.6``, ``lib``, ``bin/fox-config``) while the graph
        spreads those files over fox, libx11, libxext, libpng, boost and
        friends.
        """
        root = os.path.join(self.build_folder, "deps-prefix")
        include_root = os.path.join(root, "include")
        library_root = os.path.join(root, "lib")
        binary_root = os.path.join(root, "bin")
        for path in (include_root, library_root, binary_root):
            os.makedirs(path, exist_ok=True)
        for _, dependency in self.dependencies.items():
            folder = dependency.package_folder
            if not folder:
                continue
            for include_dir in dependency.cpp_info.includedirs or ["include"]:
                self._link_tree(self._resolve(folder, include_dir), include_root)
            for lib_dir in dependency.cpp_info.libdirs or ["lib"]:
                self._link_flat(self._resolve(folder, lib_dir), library_root)
            for bin_dir in dependency.cpp_info.bindirs or []:
                self._link_flat(self._resolve(folder, bin_dir), binary_root)
        return root

    @staticmethod
    def _resolve(folder, relative):
        return relative if os.path.isabs(relative) else os.path.join(folder, relative)

    @classmethod
    def _link_tree(cls, source, destination_root):
        """Link every file below `source` into `destination_root` (layout kept).

        Linking the directory itself is not enough: X11 headers and the fox-1.6
        headers arrive from different packages that all have to contribute to
        the same tree.
        """
        if not os.path.isdir(source):
            return
        for current, _, files in os.walk(source):
            relative = os.path.relpath(current, source)
            destination = (
                destination_root
                if relative == "."
                else os.path.join(destination_root, relative)
            )
            os.makedirs(destination, exist_ok=True)
            for name in files:
                cls._link_file(
                    os.path.join(current, name), os.path.join(destination, name)
                )

    @classmethod
    def _link_flat(cls, source, destination_root):
        """Link the direct children of `source` into `destination_root`."""
        if not os.path.isdir(source):
            return
        for name in sorted(os.listdir(source)):
            cls._link_file(
                os.path.join(source, name), os.path.join(destination_root, name)
            )

    @staticmethod
    def _link_file(source, destination):
        """Link `source` to `destination`, keeping the first provider."""
        if os.path.exists(destination) or os.path.islink(destination):
            return
        os.symlink(source, destination)

    def _add_runtime_library_paths(self, environment):
        # configure runs the programs it compiles (libtool probes, AC_CHECK_LIB
        # "can we run it" tests) and so does reswrap, which is invoked by make.
        # Both load the X11/fox stack from the conan cache, which is not on the
        # default loader search path.
        for _, dependency in self.dependencies.items():
            folder = dependency.package_folder
            if not folder:
                continue
            for lib_dir in dependency.cpp_info.libdirs or ["lib"]:
                path = self._resolve(folder, lib_dir)
                if os.path.isdir(path):
                    environment.prepend_path("LD_LIBRARY_PATH", path)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make trips over the HMDFS jobserver fifo.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Standalone GUI binary, no library information to export.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
