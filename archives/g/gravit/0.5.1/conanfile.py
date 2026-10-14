#!/usr/bin/env python3
"""Conan recipe for Gravit 0.5.1 — a gravity simulator (GPL-2.0-or-later).

HarmonyOS PC (aarch64) adaptation.

Upstream 0.5.1 (2014) is an autotools/GNU-make tree that renders a full 3D
scene through the OpenGL fixed-function pipeline (``glBegin``/``glEnd``,
``gluPerspective``, point-sprites) and presents it on an SDL 1.2 window
created with ``SDL_SetVideoMode(..., SDL_OPENGL)``.

HarmonyOS PC has no window system (X11/Wayland/EGL) and therefore no
window-system OpenGL, and the published OHOS Mesa package is OSMesa-only
(``libOSMesa.so``, ``softpipe``, no ``libGL``/``libEGL``).  The SDL surface is
consequently turned into a plain software surface and the GL context comes
from OSMesa; every finished frame is copied onto that surface, which replaces
``SDL_GL_SwapBuffers()``.  The build macro names the capability, not the
platform (R8).

The remaining changes are portability fixes, see ``patches/`` and notes.md:

* ``src/gravit.h`` — ``sys/timeb.h`` does not exist in musl.
* ``configure.in`` — drop ``AC_FUNC_MALLOC``/``AC_FUNC_REALLOC`` (they rewrite
  ``malloc``/``realloc`` to ``rpl_malloc``/``rpl_realloc`` and the tree ships no
  gnulib replacement module; upstream removed both again on the develop branch
  for the same reason) and the hardcoded ``/usr/local`` include/lib paths.
* ``src/tool.c`` — resolve the compile-time absolute DATA_DIR/SYSCONFDIR roots
  relative to the running executable, because the package is installed under an
  arbitrary prefix on the device.

SDL comes from ``sdl12-compat`` rather than ``sdl/1.2.15``: the published
``sdl_image``/``sdl_ttf`` packages link against it, so using a second SDL
implementation would put two SDL runtimes in one process.

Upstream ships no test suite at all (see test_package/MANIFEST.yml for the
counting evidence); the complemented consumer tests are in ``test_package/``.

R26: this package is an application, no system-library collision concerns.
R32: ``settings.os`` is never compared against a single-value ``"Linux"``.
R33: compilers/flags come from the Conan profile, never from bare shell vars.
R38: the package installs ``bin/gravit``, hence commands.json exists.
"""
import os
import shlex
import stat
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GravitConan(ConanFile):
    name = "gravit"
    version = "0.5.1"
    description = ("Gravit — a visually stunning gravity simulator "
                   "(SDL 1.2 + OpenGL, OSMesa offscreen rendering on HarmonyOS PC)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/gak/gravit"
    url = "https://github.com/gak/gravit"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Environment variables exported by the Perl/autoconf/automake tool
    # packages.  They describe that package's own interpreter and data
    # directories; the bootstrap clears them so that no two installations are
    # mixed (see _bootstrap_autotools).
    _TOOL_ENV_VARS = (
        "PERL", "PERL5LIB", "M4",
        "AUTOMAKE", "ACLOCAL", "ACLOCAL_PATH",
        "AUTOM4TE", "AUTOCONF", "AUTOHEADER", "AUTORECONF", "AUTOSCAN",
        "AUTOUPDATE", "IFNAMES",
        "autom4te_perllibdir", "AC_MACRODIR", "trailer_m4",
        "autom4te_buildauxdir",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL 1.2 API through sdl12-compat: the SDL 1.2 add-on libraries below
        # link against it, and libSDL-1.2.so is the SDL the whole process uses.
        self.requires("sdl12-compat/1.2.68")
        self.requires("sdl-image/1.2.12")
        self.requires("sdl_ttf/2.0.11")
        # In-game scripting (spawn scripts are Lua).
        self.requires("lua/5.2.4")
        # PNG screenshots.
        self.requires("libpng/1.6.58")
        # OpenGL: there is no libGL on OHOS, the GL context and the fixed
        # function pipeline come from OSMesa; glu/9.0.3 is built against it.
        self.requires("glu/9.0.3")
        self.requires("mesa/24.3.4.1")

    def build_requirements(self):
        # The 0.5.1 tarball only carries configure.in/Makefile.am, so the build
        # system has to be generated; automake is not part of the base
        # toolchain and therefore comes from its tool package.
        self.tool_requires("automake/1.18")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        # The tree builds in-source: configure writes Makefile and src/config.h
        # into the source folder and Makefile.in has no VPATH support.
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        # The capability this build needs (R8: named after the capability, not
        # the platform): OSMesa supplies the GL context.
        deps.environment.append("CPPFLAGS", ["-DOSMESA_RENDER"])
        # sdl_image/sdl_ttf install their headers under include/SDL but declare
        # includedirs = ["include"], so AutotoolsDeps cannot know about the
        # extra level; their own .pc files advertise include/SDL.
        deps.environment.append("CPPFLAGS", self._sdl_family_include_flags())
        deps.generate()

        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.generate()
        self._provide_gl_pc()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        # HMDFS does not always preserve the executable bit of the freshly
        # generated helper scripts, so configure would not be able to run
        # config.sub.
        self._restore_helper_modes(
            self.source_folder,
            ("configure", "config.guess", "config.sub", "install-sh", "missing",
             "depcomp", "compile"),
        )

        sdl_config = self._write_sdl_config()
        environment = self._configure_environment(sdl_config)
        configure = os.path.join(self.source_folder, "configure")
        self.run(
            f"{environment} {shlex.join(['sh', configure, *self._configure_args()])}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        # -j1: serial builds are the repository policy and the OHOS sandbox has
        # no make jobserver FIFOs.
        self.run(f"{environment} make -j1", cwd=self.source_folder, env="conanbuild")
        # The generated Makefile has automake's `check` target, but this tree
        # compiles no test program, so it registers zero cases.  It is driven
        # anyway so that the conan/CI log carries the upstream test entry point
        # instead of silently skipping it (L1c).
        self.run(f"{environment} make check", cwd=self.source_folder, env="conanbuild")

    def package(self):
        environment = self._configure_environment(
            os.path.join(self.build_folder, "sdl-config")
        )
        self.run(
            f"{environment} make -j1 install DESTDIR={shlex.quote(self.package_folder)}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        for license_file in ("COPYING", "README"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "gravit")
        self.cpp_info.set_property("cmake_target_name", "gravit::gravit")
        self.cpp_info.requires = [
            "sdl12-compat::sdl12-compat",
            "sdl-image::sdl-image",
            "sdl_ttf::sdl_ttf",
            "lua::lua",
            "libpng::libpng",
            "glu::glu",
            "mesa::mesa",
        ]

    # ── helpers ─────────────────────────────────────────────────────────────

    def _configure_args(self):
        return [
            # Install into the package folder; every path is derived from it.
            "--prefix=/",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            # agar (the optional alternative GUI, 1.4.1+) is not published in
            # the OHOS artifact repository; upstream supports building without
            # it and falls back to its built-in console UI.
            "--without-agar",
            # The pkg-config modules of the dependencies live in the
            # generators folder.
            f"PKG_CONFIG_PATH={self.generators_folder}",
        ]

    def _run_bootstrap_step(self, command, description):
        """Run one autotools bootstrap step with a bounded timeout + retries.

        A loaded CI worker can transiently refuse to fork (``sh: can't fork -
        try again``, i.e. fork() EAGAIN / RLIMIT_NPROC).  With the stock
        /system/bin/sh that leaves autom4te waiting on the orphaned child, so
        the whole ``conan create`` hangs until the CI build timeout kills the
        job — observed twice on gravit 0.5.1 (3600 s timeout right after
        ``autom4te: error: need GNU m4 1.4 or later: m4``).  Bounding every
        step with GNU ``timeout`` and retrying turns a transient process-limit
        hit into a bounded retry instead of a 3600 s hang.
        """
        attempts = 3
        limit = 600
        for attempt in range(1, attempts + 1):
            try:
                self.run(f"timeout {limit} {command}",
                         cwd=self.source_folder, env="conanbuild")
                return
            except ConanException as exc:
                if attempt == attempts:
                    raise
                self.output.warning(
                    f"autotools bootstrap step '{description}' failed "
                    f"(attempt {attempt}/{attempts}): {exc}"
                )
                time.sleep(10)

    def _bootstrap_autotools(self):
        """Regenerate ``configure``/``Makefile.in`` (upstream's autogen.sh).

        The 0.5.1 release tarball only carries ``configure.in``/``Makefile.am``,
        so the build system has to be generated first.

        automake/aclocal come from the Conan tool package, whose generated
        launchers carry the *builder's* Perl in their shebang, while the Perl
        package exports ``PERL5LIB`` and autoconf package variables for its own
        (differently configured) Perl.  Letting those two mix makes the XS
        modules fail to relocate (``Error relocating .../auto/Cwd/Cwd.so:
        Perl_my_cxt_init: symbol not found``) and leaves the relocated autoconf
        launchers with an unusable ``@INC``.  The tool-package environment is
        therefore cleared for the bootstrap, so that one self-consistent
        toolchain is used throughout: the compiler-side autoconf/autoheader/m4
        of the environment (PATH order) plus the automake package's own scripts
        driven through one interpreter with their module directory on ``-I``.
        """
        automake_root = self.dependencies.build["automake"].package_folder
        automake_share = os.path.join(automake_root, "share", "automake-1.18")
        perl = ["perl", "-I", automake_share]
        clean_env = "env " + " ".join(f"-u {name}" for name in self._TOOL_ENV_VARS)

        self._run_bootstrap_step(
            f"{clean_env} " + shlex.join(
                perl + [
                    os.path.join(automake_root, "bin", ".aclocal-real"),
                    "--automake-acdir=" + os.path.join(automake_root, "share", "aclocal-1.18"),
                    "--system-acdir=" + os.path.join(automake_root, "share", "aclocal"),
                    "--force",
                    "-I", "acinclude",
                ]
            ),
            "aclocal",
        )
        self._run_bootstrap_step(f"{clean_env} autoheader --force", "autoheader")
        self._run_bootstrap_step(
            f"{clean_env} " + shlex.join(
                perl + [
                    os.path.join(automake_root, "bin", ".automake-real"),
                    "--libdir=" + automake_share,
                    "--foreign",
                    "--include-deps",
                    "--add-missing",
                    "--copy",
                    "--force-missing",
                ]
            ),
            "automake",
        )
        self._run_bootstrap_step(f"{clean_env} autoconf --force", "autoconf")
        self._make_config_status_tmp_writable(
            os.path.join(self.source_folder, "configure")
        )

    @staticmethod
    def _make_config_status_tmp_writable(configure):
        """Create config.status' scratch directory with the ambient umask.

        The template autoconf embeds into ``configure``/``config.status``
        creates that directory with ``umask 077``.  On the setgid HMDFS volume
        the on-disk owner is not the build UID, so the resulting 0700 directory
        is not writable even by its creator and config.status dies with
        "can't create ./confXXXXXX/subs1.awk: Permission denied".  Creating the
        directory with the ambient umask (022) yields 0755 and works.  The
        template last changed with autoconf 2.72; failing loudly keeps a future
        autoconf from silently reintroducing the bug.
        """
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        patched = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            'mkdir "$tmp"',
        )
        if patched == content:
            raise ConanException(
                "autoconf's config.status temporary-directory template changed"
            )
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(patched)

    def _sdl_family_include_flags(self):
        """``-I<pkg>/include/SDL`` for the SDL 1.2 add-on libraries.

        Their headers are installed under ``include/SDL`` (which is what their
        own .pc files advertise) while ``cpp_info.includedirs`` stays at the
        default ``include``, so AutotoolsDeps cannot know about that extra
        level and ``#include <SDL_image.h>`` would not be found.
        """
        flags = []
        for name in ("sdl-image", "sdl_ttf"):
            flags.append(
                "-I" + os.path.join(self.dependencies[name].package_folder,
                                    "include", "SDL")
            )
        return flags

    def _provide_gl_pc(self):
        """Publish a ``gl.pc`` for the OSMesa-backed OpenGL provider.

        configure.ac probes ``PKG_CHECK_EXISTS([gl])``/``[glu]`` to decide
        whether it can use pkg-config for OpenGL; PkgConfigDeps generates
        ``glu.pc``/``mesa.pc`` from the packages, but nothing named ``gl``
        exists, which would send configure down its ``-lGL -lGLU`` fallback and
        the build would fail to link (no libGL on OHOS).  The file only has to
        describe the OSMesa provider correctly, which is exactly what the
        installed ``osmesa.pc`` does.
        """
        destination = os.path.join(self.generators_folder, "gl.pc")
        if os.path.exists(destination):
            return
        package_folder = self.dependencies["mesa"].package_folder
        save(
            self,
            destination,
            f"""prefix={package_folder}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: gl
Description: Mesa offscreen OpenGL (OSMesa) for HarmonyOS PC
Version: 3.3
Libs: -L${{libdir}} -lOSMesa
Cflags: -I${{includedir}}
""",
        )

    def _write_sdl_config(self):
        """Write the ``sdl-config`` shell that configure.ac's AM_PATH_SDL calls.

        The published sdl12-compat package ships a real sdl-config, but it is
        not guaranteed to be on PATH inside the Conan build environment, so the
        values are pinned explicitly here (same approach as sdl_image/1.2.12).
        """
        dependency = self.dependencies.host["sdl12-compat"]
        include_dir = os.path.join(dependency.package_folder, "include", "SDL")
        lib_dir = os.path.join(dependency.package_folder, "lib")
        path = os.path.join(self.build_folder, "sdl-config")
        save(
            self,
            path,
            f"""#!/bin/sh
case "$1" in
  --version) printf '%s\\n' '1.2.68' ;;
  --prefix|--exec-prefix) printf '%s\\n' '{dependency.package_folder}' ;;
  --cflags) printf '%s\\n' '-I{include_dir}' ;;
  --libs|--static-libs) printf '%s\\n' '-L{lib_dir} -lSDL-1.2' ;;
  *) exit 1 ;;
esac
""",
        )
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.chmod(path, os.stat(path).st_mode | executable_bits)
        return path

    def _configure_environment(self, sdl_config):
        """Environment prefix for configure/make: SDL_CONFIG plus the library
        search path the AC_TRY_RUN SDL version probe needs."""
        lib_dirs = [
            os.path.join(dependency.package_folder, "lib")
            for dependency in self.dependencies.host.values()
        ]
        assignments = [
            "CONFIG_SHELL=/bin/sh",
            "SHELL=/bin/sh",
            f"SDL_CONFIG={shlex.quote(sdl_config)}",
            f"LD_LIBRARY_PATH={':'.join(lib_dirs)}:$LD_LIBRARY_PATH",
        ]
        return " ".join(assignments)

    @staticmethod
    def _restore_helper_modes(root, names):
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | executable_bits)
