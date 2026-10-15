#!/usr/bin/env python3
"""Conan recipe for libXaw 1.0.14 (X Athena Widgets library).

One configure/build produces TWO shared libraries from the same sources:

  * libXaw6 - ``-DOLDXAW``, ``-version-info 6:1:0`` -> libXaw6.so.6.0.1
  * libXaw7 - ``-DXAW7``,   ``-version-info 7:0:0`` -> libXaw7.so.7.0.0

The upstream configure runs ``PKG_CHECK_MODULES(XAW6, xproto x11 xext
xextproto xt xmu)`` and ``PKG_CHECK_MODULES(XAW7, ... xt xmu xpm)``; the
installed xaw6.pc / xaw7.pc are ``Requires: xproto xt`` with
``Requires.private`` on the runtime libraries.  xproto/xextproto are
header-only modules shipped by xorgproto.  Headers live in
``include/X11/Xaw/*.h`` and are shared by both ABIs.

Dependency track: libXaw needs libxmu (XAW6 + XAW7) and libxpm (XAW7 only),
and those two currently sit on different libx11 tracks in this repository.
libxmu/1.3.1.1 pins ``libx11/1.8.13 force=True`` and synthesizes the
libX11.la shadow that libxt needs, so this recipe follows that track.
libxpm/3.5.17 pins ``libx11/6.4.0 force=True``; the two force pins do not
collide, the graph root's 1.8.13 wins (verified with ``conan graph info``:
``Overrides: libx11/6.4.0: ['libx11/1.8.13']``).  The cost is that the
published binaries of libxext/6.4.0.1 and libxpm/3.5.17 no longer match the
resulting package_id, so both are rebuilt from source - their recipes carry
their own linker-view / ``.la`` relocation precisely for that.

OHOS build notes (same platform contract as libxpm / libxmu):

  * configure runs in CROSS mode (``--build=aarch64-unknown-linux-gnu
    --host=aarch64-linux-ohos``) so autoconf never tries to *run* a conftest
    binary on the worker.  The config.sub shipped in the 1.0.14 tarball
    (2020-06-20) does not know the linux-ohos OS, hence
    ``patches/0001-config.sub.patch``.
  * a build-local relocatable linker view keeps libtool's stale
    ``dependency_libs`` paths (libxcb.la and friends) from failing the link
    or leaking into the published metadata.
  * ``configure`` is executed by /system/bin/sh with ``umask 077`` rewritten
    to ``022``: config.status creates its ``./confXXXXXX`` scratch directory
    with mode 0700, which the OHOS/HMDFS volume refuses to write into.
"""

import os
import posixpath
import re
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibxawConan(ConanFile):
    name = "libxaw"
    version = "1.0.14"
    description = "X Athena Widgets library (libXaw6 + libXaw7)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxaw"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxaw"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxaw supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Align with libxmu/1.3.1.1 (libx11/1.8.13 force + libxext/6.4.0.1):
        # libxmu is the dependency that actually needs the .la-preserving
        # 1.8.13 track, because libxt synthesizes libX11.la from it.
        self.requires(
            "libx11/1.8.13",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxt/1.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        self._prepare_linker_view()
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxext", "pkg_config_name", "xext")
        pkg_config.set_property("libxpm", "pkg_config_name", "xpm")
        # libxmu/1.3.1.1 exposes its component PC as "libxmu", but libXaw's
        # configure does PKG_CHECK_MODULES(XAW*, ... xmu) and expects the
        # upstream X11 module name "xmu" (the same convention libxt uses for
        # "xt").  Rename the component PC at the consumer so the published
        # libxmu/1.3.1.1 package needs no re-cut.
        pkg_config.set_property("libxmu::xmu", "pkg_config_name", "xmu")
        pkg_config.generate()
        AutotoolsDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Upstream installs libXaw6.so.6.0.1 (SONAME libXaw.so.6) and
        # libXaw7.so.7.0.0 (SONAME libXaw.so.7); install-exec-hook also links
        # the unversioned libXaw.so -> libXaw7.so.  Headers are shared.
        # NOTE: AutotoolsDeps puts every dependency library into LIBS, so the
        # libXaw6 link also records DT_NEEDED libXpm.so.4 / libXmuu.so.1 even
        # though the xaw6 component below (correctly, per upstream
        # XAW6_LIBS = xproto x11 xext xextproto xt xmu) does not require
        # libxpm.  This mirrors the other X11 recipes in this repository and
        # does not affect consumers, because libxpm stays a package-level
        # requirement of libxaw.
        self.cpp_info.components["xaw7"].libs = ["Xaw7"]
        self.cpp_info.components["xaw7"].requires = [
            "libxt::libxt",
            "libxmu::libxmu",
            "libxext::libxext",
            "libx11::libx11",
            "libxpm::libxpm",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.components["xaw7"].set_property(
            "cmake_target_name", "libxaw::xaw7"
        )
        self.cpp_info.components["xaw7"].set_property("pkg_config_name", "xaw7")

        self.cpp_info.components["xaw6"].libs = ["Xaw6"]
        self.cpp_info.components["xaw6"].requires = [
            "libxt::libxt",
            "libxmu::libxmu",
            "libxext::libxext",
            "libx11::libx11",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.components["xaw6"].set_property(
            "cmake_target_name", "libxaw::xaw6"
        )
        self.cpp_info.components["xaw6"].set_property("pkg_config_name", "xaw6")

        self.cpp_info.set_property("cmake_file_name", "libxaw")
        self.cpp_info.set_property("cmake_target_name", "libxaw::libxaw")
        self.cpp_info.set_property("cmake_target_aliases", ["libxaw::Xaw7"])
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if hasattr(self, "_linker_view"):
            environment.define("LD_LIBRARY_PATH", str(self._linker_view))
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _prepare_linker_view(self):
        """Create a private linker view with relocatable libtool metadata."""
        linker_view = Path(self.build_folder, "linker-view")
        linker_view.mkdir(parents=True, exist_ok=True)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for source in source_dir.iterdir():
                    if source.suffix not in (".a", ".la", ".so") or not source.is_file():
                        continue
                    destination = linker_view / source.name
                    if source.suffix == ".la":
                        content = source.read_text(encoding="utf-8")
                        destination.write_text(
                            self._relocate_libtool_archive(content, linker_view),
                            encoding="utf-8",
                            newline="\n",
                        )
                    else:
                        shutil.copyfile(source, destination)
        self._linker_view = linker_view

    @staticmethod
    def _relocate_libtool_archive(content, linker_view):
        view = linker_view.as_posix()
        lines = []
        for line in content.splitlines():
            if line.startswith("libdir="):
                line = f"libdir='{view}'"
            elif line.startswith("dependency_libs="):
                match = re.match(r"dependency_libs='(.*)'$", line)
                if not match:
                    raise ConanException("unexpected libtool dependency_libs format")
                tokens = shlex.split(match.group(1))
                relocated = []
                for token in tokens:
                    if token.startswith("-L"):
                        continue
                    if token.endswith(".la"):
                        name = posixpath.basename(token)
                        if not name.startswith("lib"):
                            raise ConanException(f"unexpected libtool archive: {token}")
                        token = "-l" + name[3:-3]
                    relocated.append(token)
                line = "dependency_libs='-L%s %s'" % (view, " ".join(relocated))
            lines.append(line)
        return "\n".join(lines) + "\n"

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        library_args = (
            ("--enable-shared", "--disable-static")
            if self.options.shared
            else ("--disable-shared", "--enable-static")
        )
        toolchain.configure_args.extend(
            argument
            for argument in library_args
            if argument not in toolchain.configure_args
        )
        toolchain.configure_args.extend(
            [
                "--disable-docs",
                "--disable-specs",
                "--without-xmlto",
                "--without-fop",
                "--without-xsltproc",
            ]
        )
        flag = f"LDFLAGS=-L{self._linker_view.as_posix()}"
        if flag not in toolchain.configure_args:
            toolchain.configure_args.append(flag)
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            # Explicit cross build: autoconf must not try to RUN a conftest
            # binary on the OHOS worker.
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-linux-ohos",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(shlex.quote(argument) for argument in configure_args)
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        generated = self._ohos_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _relocate_metadata(self):
        lib_dir = Path(self.package_folder, "lib")
        for pc_name in ("xaw6.pc", "xaw7.pc"):
            pc_path = lib_dir / "pkgconfig" / pc_name
            if not pc_path.is_file():
                raise ConanException(f"installed {pc_name} is missing")
            pc_content = pc_path.read_text(encoding="utf-8")
            pc_content, count = re.subn(
                r"^prefix=.*$",
                "prefix=${pcfiledir}/../..",
                pc_content,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ConanException(f"{pc_name} has no unique prefix field")
            pc_path.write_text(pc_content, encoding="utf-8")

        for la_name in ("libXaw6.la", "libXaw7.la"):
            la_path = lib_dir / la_name
            if la_path.is_file():
                la_path.unlink()
