#!/usr/bin/env python3
"""Conan recipe for mm-common 1.0.8 — build tools and data of the GNOME C++ bindings.

mm-common is the helper module shared by libsigc++/glibmm/gtkmm/pangomm/...
It compiles no code; it installs

  bin/mm-common-get, bin/mm-common-prepare        command line helpers
  share/aclocal/mm-*.m4                           Autoconf macros for aclocal
  share/mm-common/{build,doctool,doctags}/        build support data for modules
  share/pkgconfig/mm-common-{util,libstdc++}.pc   metadata for the data files
  share/doc/mm-common/*                           README/OVERVIEW + skeletonmm.tar.*

Adaptation notes (HarmonyOS):

* The upstream 1.0.8 release tarball is ``meson dist`` output: it contains no
  generated ``configure``, so the Autotools path would need autoreconf plus
  maintainer-mode autoconf/automake/libtool. Meson is the supported build path
  (and one of the installed .pc files is produced by Meson's pkgconfig module),
  so this recipe builds with Meson.
* The build stays offline: ``-Duse-network=false`` makes
  util/meson_aux/libstdcxx-tag.py copy the shipped doctags/libstdc++.tag
  instead of downloading it from gcc.gnu.org.
* patches/0001 makes the two installed helpers compute their data directory
  from their own location. Conan configures Meson with ``--prefix=/`` and
  stages the install through DESTDIR, so the configure-time prefix baked in by
  upstream would point outside the package folder and the helpers would not
  find share/mm-common/.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

MM_COMMON_GET = "mm-common-get"


class MmCommonConan(ConanFile):
    name = "mm-common"
    version = "1.0.8"
    description = ("Build support scripts, Autoconf macros and documentation "
                   "data shared by the GNOME C++ bindings (libsigc++, glibmm, "
                   "gtkmm, ...)")
    license = "GPL-2.0-or-later"
    homepage = "https://gtkmm.gnome.org/"
    url = "https://gitlab.gnome.org/GNOME/mm-common"
    topics = ("gnome", "gtkmm", "build-tools", "autoconf", "pkg-config")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"use_network": [True, False]}
    default_options = {"use_network": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # CI/worker machines have no network access: copy the tag file that is
        # shipped in the tarball instead of downloading it from gcc.gnu.org.
        # The upstream option is a combo (choices 'false', 'if-no-local-tag-file',
        # 'true'), so it must be passed as a *string*: a bare boolean in the
        # Meson machine file is rejected by Meson >= 1.12 for combo options.
        tc.project_options["use-network"] = "true" if self.options.use_network else "false"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        # Builds the two generated artifacts of the project:
        #   skeletonmm.tar.{gz,xz}  archive of the skeleton binding module
        #   libstdc++.tag           copied from the source tree (offline mode)
        meson.build()
        # Upstream defines no test targets (no `meson test` suite, no tests/
        # directory in the tarball), so the project's own outputs and the
        # generated helper commands are verified instead.
        self._verify_build_outputs()

    def _verify_build_outputs(self):
        import glob
        import subprocess
        import sys
        import tarfile

        skeletons = glob.glob(os.path.join(self.build_folder, "skeletonmm.tar*"))
        if not skeletons:
            raise ConanException("skeletonmm.tar.* was not generated")
        with tarfile.open(skeletons[0]) as archive:
            members = archive.getnames()
        required = ("skeletonmm/meson.build", "skeletonmm/skeleton/src/skeleton.hg")
        missing = [name for name in required if name not in members]
        if missing:
            raise ConanException(f"incomplete {os.path.basename(skeletons[0])}: missing {missing}")

        tag_file = os.path.join(self.build_folder, "libstdc++.tag")
        if not os.path.isfile(tag_file) or os.path.getsize(tag_file) < 4096:
            raise ConanException("libstdc++.tag is missing or truncated")

        get_script = os.path.join(self.build_folder, MM_COMMON_GET)
        expected = f"{MM_COMMON_GET} {self.version}"
        result = subprocess.run([sys.executable, get_script, "--version"],
                                capture_output=True, text=True)
        if result.returncode != 0 or expected not in result.stdout:
            raise ConanException(f"{MM_COMMON_GET} --version failed (rc={result.returncode}): "
                                 f"{result.stdout}{result.stderr}")
        self.output.info(f"[ok] verified {os.path.basename(skeletons[0])} "
                         f"({len(members)} entries), libstdc++.tag and '{expected}'")

    def package(self):
        meson = Meson(self)
        meson.install()
        self._relocate_pkg_config_files()

    def _relocate_pkg_config_files(self):
        """Point the installed .pc files at the package folder, not at the staging root.

        Conan configures Meson with ``--prefix=/`` and installs with DESTDIR, so
        the generated .pc files start with ``prefix=/`` and every variable they
        export (pkgdatadir, doctooldir, doxytagfile) would resolve below
        ``/share``. ``${pcfiledir}`` keeps them correct wherever the package is
        unpacked (Conan cache, worker, user tree).
        """

        pkgconfig_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        for name in ("mm-common-util.pc", "mm-common-libstdc++.pc"):
            pc_file = os.path.join(pkgconfig_dir, name)
            if not os.path.isfile(pc_file):
                self.output.warning(f"{name} was not installed by Meson")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            if "prefix=/" not in content:
                self.output.warning(f"{name} does not use the DESTDIR staging prefix; left as is")
                continue
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(content.replace("prefix=/", "prefix=${pcfiledir}/../.."))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        # Autotools consumers need the installed m4 macros on ACLOCAL_PATH;
        # this mirrors the NOTICE mm-common prints at install time.
        self.buildenv_info.append_path(
            "ACLOCAL_PATH", os.path.join(self.package_folder, "share", "aclocal"))
