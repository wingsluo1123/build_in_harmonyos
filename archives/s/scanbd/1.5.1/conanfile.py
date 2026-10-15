#!/usr/bin/env python3
"""Conan recipe for scanbd — scanner button daemon on OpenHarmony.

scanbd watches SANE scanners through libsane and runs the action scripts
configured in scanbd.conf when a scanner button is pressed.  The recipe builds
the upstream 1.5.1 release tarball with its bundled Autoconf build system.
"""

import os
import re
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ScanbdConan(ConanFile):
    name = "scanbd"
    version = "1.5.1"
    description = "Scanner button daemon: watches SANE scanners and runs actions on button events"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/scanbd/"
    url = "https://sourceforge.net/projects/scanbd/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libconfuse/3.3")
        self.requires("sane-backends/1.2.1")
        self.requires("dbus/1.14.10")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("scanbd only builds for Linux/OHOS targets")

    def layout(self):
        basic_layout(self)

    def source(self):
        # filename= 显式指定：URL 带 ?viasf=1 查询串，conan 无法从 URL 推断
        # 压缩格式（CI #84839 实证：Cannot deduce file name from the url）。
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="scanbd-1.5.1.tgz")
        # The upstream tarball packs its tree as "./1.5.1/...", so a single
        # strip_root pass only removes the "./" component and leaves one extra
        # directory behind.  Flatten it so that the sources sit at the root of
        # the source folder, as the rest of the build expects.
        nested = os.path.join(self.source_folder, "1.5.1")
        if os.path.isdir(nested):
            for entry in os.listdir(nested):
                shutil.move(os.path.join(nested, entry), self.source_folder)
            os.rmdir(nested)

    def _stage_libtool_archives(self):
        """Copy dependency libtool archives into a relocatable staging directory.

        Dependency packages ship *.la files that still record absolute paths from
        the machine that built them ("libdir='//lib'",
        "dependency_libs='-L/.../lib //lib/libpng16.la -lsane'").  Libtool
        follows those paths while linking and aborts with "cannot find the
        library '//lib/libpng16.la'".  The Conan cache is not ours to rewrite, so
        every archive is copied into a staging directory instead:

        * libdir is repointed at the real package lib directory;
        * dependency_libs entries naming a *.la file are replaced by the staged
          copy, or by "-L<dir> -l<name>" when only the shared library exists;
          entries we cannot resolve anywhere are dropped, since the packages are
          shared libraries whose own DT_NEEDED entries carry their dependencies.

        The link line has to search the staging directory first, which is set up
        by _prepend_lib_search_path().
        """
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                path = Path(libdir)
                if path.is_dir():
                    libdirs.append(path)

        archives = {}
        library_dirs = {}
        for libdir in libdirs:
            for entry in sorted(libdir.iterdir()):
                name = entry.name
                if name.endswith(".la"):
                    archives.setdefault(name, (entry, libdir))
                elif ".so" in name:
                    library_dirs.setdefault(name.split(".so")[0], libdir)
                elif name.endswith(".a"):
                    library_dirs.setdefault(name[:-2], libdir)

        stage = Path(self.generators_folder) / "ohos-la-stage"
        stage.mkdir(parents=True, exist_ok=True)
        for name, (archive, libdir) in archives.items():
            text = archive.read_text(errors="replace")
            text = re.sub(r"^libdir='.*'", "libdir='%s'" % libdir, text, flags=re.M)

            def rewrite(match):
                tokens = []
                for token in match.group(1).split():
                    if not token.endswith(".la"):
                        tokens.append(token)
                        continue
                    base = os.path.basename(token)
                    if base in archives:
                        tokens.append(str(stage / base))
                        continue
                    stem = base[:-3]
                    directory = library_dirs.get(stem)
                    if directory is not None:
                        tokens.extend(["-L%s" % directory, "-l%s" % stem[len("lib"):]])
                return "dependency_libs='%s'" % " ".join(tokens)

            text = re.sub(r"^dependency_libs='(.*)'$", rewrite, text, flags=re.M)
            (stage / name).write_text(text)
        return stage

    @staticmethod
    def _prepend_lib_search_path(pc_dir, stage):
        """Search the libtool staging directory before the dependency lib dirs.

        Autoconf bakes the pkg-config --libs output into the generated Makefile,
        so the -L order of the link line is fixed at configure time: prepending
        the staging directory to every module's Libs makes libtool pick the
        sanitized archives instead of the broken ones inside the dependencies.
        """
        for module in sorted(Path(pc_dir).glob("*.pc")):
            text = module.read_text(encoding="utf-8")
            text = re.sub(r"^(Libs(?:\.private)?:)", r"\1 -L%s" % stage, text, flags=re.M)
            module.write_text(text, encoding="utf-8")

    def generate(self):
        PkgConfigDeps(self).generate()

        # The Conan dbus recipe exports its pkg-config module as "dbus", while
        # upstream dbus installs "dbus-1" and scanbd's configure.ac probes the
        # upstream name.  Publish an alias module so the mandatory DBUS check
        # resolves against the Conan package instead of a host dbus.
        pc_dir = Path(self.generators_folder)
        if (pc_dir / "dbus.pc").is_file() and not (pc_dir / "dbus-1.pc").exists():
            (pc_dir / "dbus-1.pc").write_text(
                "Name: dbus-1\n"
                "Description: dbus-1 alias for the Conan 'dbus' pkg-config module\n"
                f"Version: {self.dependencies['dbus'].ref.version}\n"
                "Requires: dbus\n",
                encoding="utf-8",
            )

        # Dependency packages carry libtool archives whose libdir/dependency_libs
        # still point at their build machine; stage sanitized copies and make the
        # link line resolve them before the packages' own copies.
        stage = self._stage_libtool_archives()
        self._prepend_lib_search_path(pc_dir, stage)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # The bundled Autoconf snapshot predates HarmonyOS; patches/0001
            # teaches config.sub the linux-ohos triplet.
            "--build=aarch64-linux-gnu",
            "--host=aarch64-linux-ohos",
            # systemd units have no meaning inside a Conan package
            "--with-systemdsystemunitdir=no",
            # OHOS provides neither libudev nor HAL; upstream then falls back to
            # its SIGHUP based scanner polling path
            "--disable-udev",
            "--disable-hal",
            # AC_FUNC_MALLOC answers its probe by running a test program, which
            # cannot work while cross-compiling: Autoconf then assumes a broken
            # malloc and redirects every call to gnulib's rpl_malloc(), a symbol
            # OHOS does not provide.  Answer the probe explicitly instead.
            "ac_cv_func_malloc_0_nonnull=yes",
        ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
