#!/usr/bin/env python3
"""Conan recipe — cairo-dock 3.5.0 (CMake; GTK3 dock / panel / desklet).

cairo-dock ("GLDI") is a GTK3 + Cairo/OpenGL desktop dock.  Upstream ships
both the `cairo-dock` executable and `libgldi` (the public C API consumed by
the separate cairo-dock-plug-ins project), therefore the Conan package also
publishes include/, lib/ and a pkg-config file.

OHOS (aarch64 / musl / clang 15) adaptation notes
-------------------------------------------------
* GL is a HARD requirement of the upstream build system::

      set (packages_required "glib-2.0 gthread-2.0 cairo librsvg-2.0 dbus-1
                              dbus-glib-1 libxml-2.0 gl glu libcurl")
      pkg_check_modules ("PACKAGE" REQUIRED "${packages_required_semicolon}")

  so the pkg-config modules `gl` and `glu` must resolve.  OHOS has no desktop
  ``libGL.so``: the registry ``mesa/24.3.4.1`` package (the revision that
  ``glu/9.0.3`` pins) ships ``libOSMesa.so`` — the desktop-GL entry points
  implemented by the softpipe software rasteriser, no X11/Wayland/DRM — next
  to the desktop GL headers.  ``_provide_gl_pc()`` republishes mesa's own
  ``osmesa.pc`` under the module name ``gl`` (prefix rewritten to the real
  package folder), which is the same manoeuvre glu/9.0.3 performs for the
  ``osmesa`` module.
* X11 / Wayland / EGL are OPTIONAL backends upstream (their
  ``pkg_check_modules()`` calls carry no REQUIRED).  OHOS has neither an X
  server nor a Wayland compositor, and the OHOS ``gtk/3.24.38.1`` package is
  built broadway-only (``x11_backend=false``), so all three are switched off
  explicitly instead of relying on "not found" fallbacks.
* ``gtk/3.24.38.1`` (broadway backend) provides ``gtk+-3.0.pc``; pango, cairo,
  gdk-pixbuf, atk, harfbuzz, ... arrive through it.
* ``glib/2.84.0.1`` is consumed through PkgConfigDeps, which emits the full
  component set including ``gthread-2.0.pc`` (verified in the build's
  generators folder).  ``_ensure_gthread_pc()`` is therefore a defensive
  no-op kept for consistency with archives/a/abiword-plugin-*/3.0.8 where the
  aggregate-only variant really did omit it.
* Upstream's GUI test suite (``tests/*.py``) is not wired into CMake (no
  ``enable_testing()`` / ``add_test()`` anywhere) and needs a running dock on
  an X display plus xdotool/python-dbus/pygobject; moreover the 3.5.0 release
  tarball does not ship the ``CairoDock`` module those tests import.  The
  per-item inventory and the reasons each item cannot run are recorded in
  notes.md / test_package/MANIFEST.yml (R51).
* ``cmake_minimum_required (VERSION 2.6)`` is rejected by CMake >= 4 (the
  worker provides 4.1.2); patch 0001 raises it to the oldest policy level
  CMake 4 still accepts.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, save)
from conan.tools.gnu import PkgConfigDeps


class CairoDockConan(ConanFile):
    name = "cairo-dock"
    version = "3.5.0"
    description = ("Cairo-Dock (GLDI) — a pretty and convenient interface to your "
                   "desktop: dock, panel, desklet (GTK3 + Cairo/OpenGL)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Cairo-Dock/cairo-dock-core"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The upstream build always produces SHARED libgldi (+ the dock binary),
    # so the package is a shared library that also exposes an executable.
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    #: pkg-config modules upstream's CMakeLists demands (REQUIRED).
    _required_modules = ("glib-2.0 gthread-2.0 cairo librsvg-2.0 dbus-1 "
                         "dbus-glib-1 libxml-2.0 gl glu libcurl gtk+-3.0").split()

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GTK3 stack (broadway backend on OHOS).  cairo-dock includes gtk/gdk
        # headers directly and links the whole GTK3 closure.
        #
        # Version choice: gtk/3.24.38.1 + librsvg/2.62.3 is the only published
        # OHOS pairing of the two whose pins do not clash - gtk/3.24.43 pins
        # cairo-gobject/1.18.4.2 while every published librsvg 2.62.3.x pins
        # cairo-gobject/1.18.4.3, and resolving that either way changes the
        # package_id of the other package (both are header/embed dependencies),
        # which would force a full gtk or Rust-based librsvg rebuild from source
        # inside CI.  gtk/3.24.38.1 and librsvg/2.62.3 agree on
        # cairo-gobject/1.18.4, pango/1.56.4 and gdk-pixbuf/2.44.6, so every
        # binary is taken from the registry (verified with `conan graph info`:
        # every node reports Download/Cache, never Build/Missing).
        self.requires("gtk/3.24.38.1", transitive_headers=True, transitive_libs=True)
        # librsvg-2.0 (SVG icon rendering) and libxml-2.0 (themes/config).
        self.requires("librsvg/2.62.3", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)
        # dbus-1 + dbus-glib-1 (the whole dock API is exported over D-Bus).
        self.requires("dbus-glib/0.114.1", transitive_headers=True, transitive_libs=True)
        # dbus-glib/0.114.1 pins dbus/1.14.10; unify on 1.14.10.1, which is the
        # last 1.14.10 revision without the optional glib/2.88.3 dependency
        # (1.14.10.2+ enable DBUS_WITH_GLIB and would conflict with the GTK
        # tree's glib/2.84.0.1).  Same pairing as dbustest/19.04.0.1.
        self.requires("dbus/1.14.10.1", override=True)
        # libcurl (theme server / update checks).  The pkg-config module is
        # "libcurl" (archives/c/curl/8.15.0.1 declares pkg_config_name=libcurl).
        self.requires("curl/8.15.0.1", transitive_headers=True, transitive_libs=True)
        # Desktop-GL provider: mesa's OSMesa (GL entry points + GL headers).
        self.requires("mesa/24.3.4.1")
        self.requires("glu/9.0.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cairo-dock/3.5.0 is packaged for Linux/OHOS only (os={self.settings.os})")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # generate()
    # ------------------------------------------------------------------ #
    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        self._provide_gl_pc()
        self._ensure_gthread_pc()
        self._ensure_dbus1_pc()
        self._ensure_glib_intl_libs()

        env = Environment()
        # po/: `find_program (MSGFMT_EXECUTABLE msgfmt)` — the gettext tools
        # are not on the conan build PATH (only /data/service/hnp/bin is),
        # but msgfmt/xgettext/msgmerge live in the SDK gettext tree.
        for gdir in sorted(glob.glob("/data/service/hnp/gettext.org/*/bin"), reverse=True):
            if os.path.isdir(gdir):
                env.prepend_path("PATH", gdir)
                env.prepend_path("LD_LIBRARY_PATH", gdir)
                break
        if self.settings.os == "OHOS":
            # hnp cmake/clang need libc++_shared.so from /system/lib64.
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self).save_script("cairo_dock_buildenv")

        tc = CMakeToolchain(self)
        # CMake has no OHOS platform module and this is a native build
        # (build == host); same choice as pan/0.165 and 460+ other recipes.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
        # upstream: cmake_minimum_required (VERSION 2.6) — CMake >= 4 refuses to
        # configure projects whose minimum is below 3.5.  The supported knob
        # (used by 600+ recipes in this repository) keeps the upstream policy
        # level at 3.5 instead of patching the source.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # src/*.c define glibc's *internal* feature macro __USE_POSIX before
        # including the system headers in order to get localtime_r(); musl's
        # features.h does not honour it, and the project's own `-std=c99`
        # (strict ANSI) hides every POSIX declaration, so
        # src/gldit/cairo-dock-themes-manager.c fails with
        #   error: call to undeclared function 'localtime_r'
        # (upstream turns that into an error via -Werror-implicit-function-declaration).
        # Expose POSIX.1-2008 for the whole build (the "add-cflags / feature test
        # macro" class, knowledge E032); the source uses no GNU/BSD-only function
        # (checked: no strcasestr/memmem/strsep/asprintf/vasprintf/strndup).
        tc.preprocessor_definitions["_POSIX_C_SOURCE"] = "200809L"
        # Optional display backends: OHOS has no X server / Wayland
        # compositor and the OHOS gtk3 is broadway-only.
        tc.variables["enable-x11-support"] = False
        tc.variables["enable-wayland-support"] = False
        tc.variables["enable-egl-support"] = False
        # Upstream's `po/` target shells out to msgfmt for every .po file;
        # keep the translations (they are installed data) but do not let a
        # missing/broken gettext tool abort an otherwise valid build.
        tc.variables["force-icon-in-menus"] = True
        tc.generate()

    def _provide_gl_pc(self):
        """Publish mesa's OSMesa as the pkg-config module ``gl``.

        Upstream requires the module ``gl``; OHOS ships no libGL.so.  mesa's
        OSMesa exports the full desktop-GL entry points, so re-expose its
        ``osmesa.pc`` under the name ``gl`` with the prefix rewritten to the
        actual package folder (the in-package copy carries ``prefix=/``).
        """
        gens = self.generators_folder
        dst = os.path.join(gens, "gl.pc")
        if os.path.exists(dst):
            return
        if "mesa" not in self.dependencies:
            self.output.warning("mesa dependency missing: cannot provide the 'gl' pkg-config module")
            return
        mesa_pf = self.dependencies["mesa"].package_folder
        src = os.path.join(mesa_pf, "lib", "pkgconfig", "osmesa.pc")
        if not os.path.isfile(src):
            raise ConanInvalidConfiguration(f"mesa package does not ship osmesa.pc: {src}")
        with open(src, encoding="utf-8") as handle:
            text = handle.read()
        text = text.replace("prefix=/", f"prefix={mesa_pf}", 1)
        text = text.replace("Name: osmesa", "Name: gl", 1)
        text = text.replace("Description: Mesa Off-screen Rendering Library",
                            "Description: Mesa desktop OpenGL (OSMesa/softpipe) provided as 'gl' for OHOS", 1)
        text = re.sub(r"(?m)^Version:.*$", f"Version: {self.dependencies['mesa'].ref.version}", text)
        save(self, dst, text)
        self.output.info(f"provided gl.pc -> {mesa_pf}/lib/libOSMesa.so")

    def _ensure_dbus1_pc(self):
        """Provide the ``dbus-1`` pkg-config module that upstream asks for.

        dbus/1.14.10.1 does not declare ``pkg_config_name``, so PkgConfigDeps
        emits ``dbus.pc`` while upstream dbus - and cairo-dock's own
        ``packages_required`` list - use the upstream module name ``dbus-1``.
        Publish a forwarding alias (the "alias .pc" pattern already used by
        gdk-pixbuf/pango in this repository): the alias carries no flags of its
        own and resolves to the Conan-generated ``dbus.pc`` through Requires.
        """
        gens = self.generators_folder
        dst = os.path.join(gens, "dbus-1.pc")
        if os.path.exists(dst):
            return
        if "dbus" not in self.dependencies:
            self.output.warning("dbus dependency missing: cannot provide the 'dbus-1' module")
            return
        dep = self.dependencies["dbus"]
        save(self, dst,
             "Name: dbus-1\n"
             "Description: alias for the Conan 'dbus' package (upstream module name)\n"
             f"Version: {dep.ref.version}\n"
             "Requires: dbus\n")
        self.output.info("provided dbus-1.pc (alias -> dbus.pc)")

    def _ensure_gthread_pc(self):
        """Write gthread-2.0.pc if PkgConfigDeps did not emit it.

        Observation in this graph: glib/2.84.0.1 publishes Conan *components*
        (glib-2.0, gobject-2.0, gthread-2.0, gio-2.0, gmodule-2.0) under the
        aggregate pkg-config name ``glib-2.0-unofficial``, so PkgConfigDeps
        does emit gthread-2.0.pc and this helper is a no-op (verified in the
        build's generators folder: "Name: gthread-2.0 / Description: Conan
        component: gthread-2.0").  It is kept as a fallback because other glib
        revisions in this repository declare a single aggregate pkg_config_name
        ("glib-2.0") with no components, in which case the ``gthread-2.0``
        module upstream requires would be missing (the same gap the
        abiword-plugin-*/3.0.8 recipes fill by hand).
        """
        gens = self.generators_folder
        dst = os.path.join(gens, "gthread-2.0.pc")
        if os.path.exists(dst):
            return
        if "glib" not in self.dependencies:
            self.output.warning("glib dependency missing: cannot provide gthread-2.0.pc")
            return
        dep = self.dependencies["glib"]
        prefix = dep.package_folder
        inc_main = os.path.join(prefix, "include", "glib-2.0")
        inc_derived = os.path.join(prefix, "lib", "glib-2.0", "include")
        if not os.path.isdir(inc_main) or not os.path.isdir(inc_derived):
            raise ConanInvalidConfiguration(
                f"glib package layout unexpected: {inc_main} / {inc_derived}")
        version = str(dep.ref.version)
        # The upstream glib version (2.84.0) minus the conan revision suffix,
        # so dependants comparing against `glib-2.0 >= x` keep working.
        version = ".".join(version.split(".")[:3])
        save(self, dst,
             "prefix={prefix}\n"
             "libdir=${{prefix}}/lib\n"
             "includedir=${{prefix}}/include\n"
             "\n"
             "Name: gthread-2.0\n"
             "Description: Thread support for GLib (Conan package: glib)\n"
             "Version: {version}\n"
             "Requires: glib-2.0\n"
             "Libs: -L${{libdir}} -lgthread-2.0 -pthread\n"
             "Cflags: -I{inc_main} -I{inc_derived} -pthread\n"
             "".format(prefix=prefix, version=version,
                       inc_main=inc_main, inc_derived=inc_derived))
        self.output.info(f"provided gthread-2.0.pc -> {prefix}/lib/libgthread-2.0.so")

    def _ensure_glib_intl_libs(self):
        """Re-add ``-lintl`` to the generated ``glib-2.0.pc``.

        glib/2.84.0.1 is built with the Windows-style *proxy* ``<libintl.h>``:
        that header lives in the glib package (``include/libintl.h``) and
        ``#define``s ``gettext``/``dgettext``/... to ``g_libintl_*``; the very
        same package ships ``lib/libintl.so.8`` which defines those
        ``g_libintl_*`` symbols.  (``glib/gi18n.h`` includes ``<libintl.h>``
        and expands ``_()`` to ``gettext()``, so every cairo-dock source that
        uses translations passes through that header.)

        Upstream's own ``glib-2.0.pc`` carries ``-lintl`` in ``Libs``, but
        ``PkgConfigDeps`` rebuilds the .pc from the glib recipe's ``cpp_info``,
        which declares neither the ``intl`` library nor the dependency, so the
        generated .pc emits only ``-lglib-2.0 -lm -lpthread -ldl``.  Upstream's
        own CMake guard, ``check_library_exists(intl libintl_gettext ...)``
        (CMakeLists.txt:193), also fails here: glib's libintl.so exports
        ``g_libintl_*``, not ``libintl_gettext``, so ``LIBINTL_LIBRARIES``
        stays empty.  Result: ``ld.lld: error: undefined symbol:
        g_libintl_gettext`` when linking the executable and libgldi.so.

        Appending ``-lintl`` to the generated ``glib-2.0.pc`` ``Libs`` line
        makes pkg-config pull it into ``PACKAGE_LIBRARIES`` / ``GTK_LIBRARIES``
        (which all targets - gldi, cd-Help and the dock executable - link),
        with the glib package's ``-L`` already on the link line.  Same fix as
        at-spi2-core/2.60.5 and ayatana-ido/0.10.4 ("对 .pc 追加 -lintl").
        """
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as handle:
            content = handle.read()
        if re.search(r"(?m)^Libs:.*(?:\s)-lintl(?:\s|$)", content):
            return
        if "glib" not in self.dependencies:
            self.output.warning("glib dependency missing: cannot re-add -lintl to glib-2.0.pc")
            return
        glib_lib = os.path.join(self.dependencies["glib"].package_folder, "lib")
        if not os.path.isfile(os.path.join(glib_lib, "libintl.so")):
            # glib built without the proxy libintl: nothing to add.
            self.output.warning(f"glib ships no libintl.so under {glib_lib}: leaving glib-2.0.pc as-is")
            return
        content = re.sub(r"(?m)^(Libs:.*)$", r"\1 -lintl", content, count=1)
        save(self, pc, content)
        self.output.info(f"appended -lintl to glib-2.0.pc (g_libintl_* provider: {glib_lib}/libintl.so)")

    # ------------------------------------------------------------------ #
    # build() / package()
    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            if "/system/lib64" not in cur:
                os.environ["LD_LIBRARY_PATH"] = ("/system/lib64:" + cur) if cur else "/system/lib64"
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships no CMake-registered test suite (see notes.md): the
        # tests/ directory holds 12 Python GUI scripts that are not part of
        # the build graph, so ctest would report "No tests were found".  The
        # executable verification lives in test_package/.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        for lic in ("LICENSE", "LGPL-2", "copyright"):
            if os.path.isfile(os.path.join(self.source_folder, lic)):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_ohos_elfs()

    def _sign_ohos_elfs(self):
        """Sign the shipped executable and shared objects for the OHOS loader."""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(f"Required OHOS ELF signing tool missing: {tool}")
        targets = []
        exe = os.path.join(self.package_folder, "bin", "cairo-dock")
        if os.path.isfile(exe):
            targets.append(exe)
        for pattern in ("*.so", "*.so.*"):
            targets.extend(p for p in glob.glob(os.path.join(self.package_folder, "lib", pattern))
                           if os.path.isfile(p) and not os.path.islink(p))
        for target in sorted(set(targets)):
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"', ignore_errors=True)
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')
            os.chmod(target, 0o755)
        self.output.info(f"signed {len(set(targets))} OHOS ELF file(s)")

    def package_info(self):
        # The dock executable plus the shared GLDI library and its headers.
        self.cpp_info.libs = ["gldi"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/cairo-dock"]
        self.cpp_info.set_property("pkg_config_name", "gldi")
        self.cpp_info.set_property("cmake_file_name", "gldi")
        self.cpp_info.set_property("cmake_target_name", "gldi::gldi")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
