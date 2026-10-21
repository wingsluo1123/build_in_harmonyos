#!/usr/bin/env python3
"""Conan recipe for libwraster 0.96.0 (WindowMaker wrlib).

libwraster is the image manipulation/conversion library of Window Maker
(source tree `wrlib/` of WindowMaker-0.96.0).  It is a hard dependency of
the Window Maker dockapps (wmglobe, wmjupiter, ...).

Build strategy:
  * The full Window Maker release is one autotools project; only `wrlib/`
    is needed here.  `configure` runs at the top level to generate
    `config.h` (wraster.h is derived from wraster.h.in by
    replace-ac-keywords.sh which needs config.h), then the build is
    restricted to the wrlib subdirectory.
  * All optional image-format backends (png/jpeg/gif/tiff/webp/magick)
    are disabled: wmglobe/wmjupiter load embedded XPM maps only, and the
    core API (RCreateImage / RScaleImage / RPutPixel / RGetPixel /
    RGetImageFromXPMData / RConvertImage / RCreateXImage / RPutXImage /
    RReleaseImage / RClearImage / RMessageForError) does not require them.
    XPM support stays enabled (needs libxpm) because RGetImageFromXPMData
    is a hard requirement of the downstream dockapps.
  * libxmu is NOT required: the only Xmu call (XmuLookupStandardColormap
    in context.c) is guarded by #ifdef HAVE_LIBXMU.
  * config.guess / config.sub are patched to recognize HarmonyOS
    (aarch64-unknown-linux-ohos); the patches were round-trip verified.
"""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


_VARIABLE_REFERENCE = re.compile(r"\$[({]([A-Za-z_][A-Za-z0-9_]*)[)}]")


def _makefile_variables(makefile, names=("prefix", "datarootdir", "datadir",
                                        "localedir", "pixmapdir", "pkgconfdir",
                                        "PACKAGE_TARNAME")):
    """Resolve plain `VAR = value` assignments of a generated Makefile.

    Returned values have ${VAR} / $(VAR) references expanded recursively, so
    `${datarootdir}/locale` style definitions come back as concrete paths.
    """
    if not makefile.is_file():
        return {}
    raw = {}
    for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:+]?=\s*(\S.*)$", line)
        if match:
            raw.setdefault(match.group(1), match.group(2).rstrip())
    resolved = {}

    def resolve(name, seen=()):
        if name in resolved:
            return resolved[name]
        if name in seen:
            return ""
        value = raw.get(name, "")
        resolved[name] = ""  # guards against cyclic definitions
        value = _VARIABLE_REFERENCE.sub(
            lambda match: resolve(match.group(1), seen + (name,)), value)
        resolved[name] = value
        return value

    for name in names:
        resolve(name)
    return {name: resolved.get(name, "") for name in names}


class LibwrasterConan(ConanFile):
    name = "libwraster"
    version = "0.96.0"
    description = "Window Maker raster graphics (image manipulation) library"
    license = "LGPL-2.0-or-later"
    homepage = "https://www.windowmaker.org/"
    url = "https://github.com/window-maker/wmaker"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxpm/3.5.17",
            transitive_headers=True,
            transitive_libs=True,
        )
        # The top-level configure (a generated file of the full Window Maker
        # project) probes for Xft through PKG_CHECK_MODULES even though that
        # probe only serves WINGs, which is not built here: the wrlib sources
        # never include Xft headers and wrlib/Makefile.am links only
        # @GFXLIBS@ @MAGICKLIBS@ @XLIBS@ @LIBXMU@ -lm.  pkg.m4 honours pre-set
        # XFT_CFLAGS/XFT_LIBS and then skips the pkg-config lookup entirely
        # (see _build_environment), so no libxft requirement is needed.  This
        # matters for consumers: a real libxft requirement would be published
        # in cpp_info.requires and drag a shared libXft.so.2/fontconfig link
        # requirement into every dependent binary (R26).

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libwraster supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        self._prepare_linker_view()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        # E490: restore known autotools script modes (some adaptation paths
        # preserve source content without executable bits).
        for script in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "ltmain.sh"):
            path = Path(self.source_folder, script)
            if path.is_file():
                path.chmod(0o755)
        environment = self._build_environment()
        with environment.vars(self).apply():
            # config.h ends with #include "config-paths.h" (AH_BOTTOM in
            # configure.ac), but the generating rule lives only in the
            # top-level Makefile (BUILT_SOURCES).  wrlib's own Makefile has
            # no rule for it, so it must be produced from the top level
            # before descending into wrlib.
            if str(self.settings.os) == "OHOS":
                self._generate_ohos_configure()
                self._configure_ohos()
                self._generate_config_paths()
                self._run_ohos("make -j1 -C wrlib")
            else:
                self._configure()
                self.run("make -j1 config-paths.h", env="conanbuild")
                self.run("make -j1 -C wrlib", env="conanbuild")

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 -C wrlib install DESTDIR={destination}")
            else:
                self.run(
                    f"make -j1 -C wrlib install DESTDIR={shlex.quote(self.package_folder)}",
                    env="conanbuild",
                )
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._drop_build_rpath()
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "wrlib"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["wraster"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "libxpm::libxpm",
        ]
        self.cpp_info.set_property("cmake_file_name", "libwraster")
        self.cpp_info.set_property("cmake_target_name", "libwraster::libwraster")
        self.cpp_info.set_property("pkg_config_name", "wrlib")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ------------------------------------------------------------------
    # configure
    # ------------------------------------------------------------------

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--without-font",
                "--without-examples",
                "--disable-debug",
                "--disable-pango",
                "--disable-magick",
                "--disable-png",
                "--disable-jpeg",
                "--disable-gif",
                "--disable-tiff",
                "--disable-webp",
                "--enable-xpm",
                "--disable-animations",
                "--disable-mwm-hints",
                "--disable-boehm-gc",
                "--disable-xdnd",
                "--disable-wmreplace",
                "--disable-res",
                "--disable-shm",
                "--disable-xinerama",
                "--disable-randr",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
                f"LDFLAGS=-L{self._linker_view.as_posix()}",
            ]
        )
        return toolchain

    def _configure(self):
        args = self._autotools_toolchain().configure_args
        configure = os.path.join(self.source_folder, "configure")
        self.run(f"{shlex.quote(configure)} " + " ".join(shlex.quote(a) for a in args),
                 env="conanbuild")

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        arguments = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *self._autotools_toolchain().configure_args,
        ]
        command = " ".join(shlex.quote(argument) for argument in arguments)
        self._run_ohos(f'"{shell}" "{self._ohos_configure_path()}" {command}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        content = upstream.read_text(encoding="utf-8")
        if content.count("umask 077") != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace("umask 077", "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _generate_config_paths(self):
        """Produce config-paths.h, preferring the upstream top-level rule.

        config.h ends with #include "config-paths.h" and the generating rule
        lives only in the top-level Makefile.  Configuration on a worker whose
        posix_spawn fails can stop mid-way, leaving that Makefile without the
        rule, so fall back to writing the file from the Makefile's own
        variables instead of failing the build.
        """
        target = Path(self.build_folder, "config-paths.h")
        try:
            self._run_ohos("make -j1 config-paths.h")
        except ConanException:
            pass
        if target.exists():
            return
        variables = _makefile_variables(Path(self.build_folder, "Makefile"))
        required = ("localedir", "pixmapdir", "datadir", "pkgconfdir")
        if not all(variables.get(name) for name in required):
            raise ConanException("config-paths.h could not be produced")
        package_tarname = variables.get("PACKAGE_TARNAME") or "WindowMaker"
        lines = [
            "/* this is a generated file - do not edit */",
            "",
            "/* define where the translations are stored */",
            f'#define LOCALEDIR "{variables["localedir"]}"',
            "",
            "/* define an extra path for pixmaps */",
            f'#define PIXMAPDIR "{variables["pixmapdir"]}"',
            "",
            "/* where shared data is stored */",
            f'#define PKGDATADIR "{variables["datadir"]}/{package_tarname}"',
            "",
            "/* where the global defaults are stored */",
            f'#define PKGCONFDIR "{variables["pkgconfdir"]}"',
            "",
            "/* where the user data root is located */",
            '#define GSUSER_SUBDIR "GNUstep"',
            "",
            "/* where the user defaults are stored */",
            '#define DEFAULTS_SUBDIR "Defaults"',
            "",
            "/* where the user data are stored */",
            '#define USERDATA_SUBDIR "Library"',
            "",
        ]
        target.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    # ------------------------------------------------------------------
    # environment / linker view (same pattern as libdockapp 0.7.3)
    # ------------------------------------------------------------------

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define("MKDIR_P", "/system/bin/mkdir -p")
        # Satisfy the configure-time Xft probe without depending on libxft:
        # pkg.m4 keeps the pre-set values when both variables are non-empty
        # and never calls pkg-config for "xft".  Nothing built here consumes
        # XFT_CFLAGS/XFT_LIBS (configure does not fold them into XLIBS), so the
        # values only have to be non-empty and harmless.
        environment.define("XFT_CFLAGS", "-I/usr/include")
        environment.define("XFT_LIBS", "-lX11")
        environment.prepend_path("LD_LIBRARY_PATH", str(self._linker_view))

        linker = Path("/data/service/hnp/bin/ld.lld")
        if linker.exists():
            sdk_lib = linker.resolve().parent.parent / "lib"
            if sdk_lib.is_dir():
                environment.prepend_path("LD_LIBRARY_PATH", str(sdk_lib))

        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                path = Path(libdir)
                if not path.is_absolute():
                    path = Path(dependency.package_folder, libdir)
                if path.is_dir():
                    environment.prepend_path("LD_LIBRARY_PATH", str(path))
        return environment

    def _prepare_linker_view(self):
        """Provide libtool with relocatable copies of dependency metadata."""
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
                relocated = []
                for token in shlex.split(match.group(1)):
                    if token.startswith("-L"):
                        continue
                    if token.endswith(".la"):
                        name = os.path.basename(token)
                        if not name.startswith("lib"):
                            raise ConanException(f"unexpected libtool archive: {token}")
                        token = "-l" + name[3:-3]
                    relocated.append(token)
                line = "dependency_libs='-L%s %s'" % (view, " ".join(relocated))
            lines.append(line)
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # packaging
    # ------------------------------------------------------------------

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "wrlib.pc")
        if pc_path.is_file():
            lines = pc_path.read_text(encoding="utf-8").splitlines()
            variables = ("prefix=", "exec_prefix=", "libdir=", "includedir=")
            payload = []
            for line in lines:
                if line.startswith(variables):
                    continue
                if line.startswith("Libs:"):
                    line = "Libs: -L${libdir} -lwraster"
                elif line.startswith("Cflags:"):
                    line = "Cflags: -I${includedir}"
                payload.append(line)
            pc_path.write_text(
                "\n".join(
                    [
                        "prefix=${pcfiledir}/../..",
                        "exec_prefix=${prefix}",
                        "libdir=${prefix}/lib",
                        "includedir=${prefix}/include",
                        *payload,
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
        libtool_archive = Path(self.package_folder, "lib", "libwraster.la")
        if libtool_archive.is_file():
            libtool_archive.unlink()

    def _drop_build_rpath(self):
        """Remove the task-local linker view from the published ELF."""
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(patchelf) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration("OHOS packaging requires patchelf and llvm-readelf")
        for library in Path(self.package_folder, "lib").glob("libwraster.so*"):
            if not library.is_file():
                continue
            dynamic = subprocess.run(
                [readelf, "-d", str(library)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
            if "(RPATH)" in dynamic or "(RUNPATH)" in dynamic:
                if str(self._linker_view) not in dynamic:
                    raise ConanException("libwraster carries an unexpected runtime search path")
                subprocess.run(
                    [patchelf, "--remove-rpath", str(library)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
