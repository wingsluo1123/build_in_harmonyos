#!/usr/bin/env python3
"""Conan recipe — wmauda 0.9 (Audacious remote-control dockapp).

wmauda is a WindowMaker/Fluxbox dockapp that controls Audacious via D-Bus.
Single-file C project with a trivial Makefile (no configure script).

Upstream: http://ftp.debian.org/debian/pool/main/w/wmauda/wmauda_0.9.orig.tar.gz
Homepage: https://www.netswarm.net/
License:  GPL-2.0-or-later

Key adaptation points:
  1. The Makefile gathers CFLAGS/LIBS with `$(shell pkg-config audacious
     dbus-1 audclient gtk+-2.0 ...)`, which cannot resolve cross-compiled .pc
     files on OHOS.  All four pkg-config lines are rewritten with explicit
     -I/-L/-l flags collected from the dependency graph instead.
  2. Dependency dir/lib collection walks `self.dependencies` (all host
     dependencies, transitive included) and also reads CppInfo *components*:
     glib declares its libraries as components, so its top-level
     `cpp_info.libs` is empty and only the component libs make the link
     succeed.  Nothing is resolved from a conan cache path — the recipe must
     behave identically on the CI worker, where CONAN_HOME is `~/.conan2`.
  3. The audacious/dbus.h and audacious/audctrl.h headers come from the
     libaudclient package (Audacious D-Bus client stub library).
  4. PIXMAP_DIR is derived from PREFIX in the Makefile; passing PREFIX to
     make ensures the baked-in pixmap path matches the install layout.
  5. Builds an executable (package_type = "application"), not a library.
  6. Upstream has no automated test suite (hand-written Makefile with only
     all/clean/install, no check target).  test_package/test.sh verifies the
     built binary and its runtime dependency chain.

Dependency graph alignment overrides:
  - gtk2/2.24.33 pins glib/2.84.0.1 (GTK3 stack)
  - dbus-glib/0.114 pins glib/2.88.0 → override to 0.114.1 (glib/2.84.0.1)
  - libaudclient/3.5-rc2 hard-requires glib/2.88.0 + dbus-glib/0.114, so it
    cannot share this graph; the dependency lines fixes this and is consumed
    as libaudclient/3.5-rc2.1 (dbus-glib/0.114.1 + glib/2.84.0.1)
  - libjpeg-turbo provides libjpeg → override to avoid provide conflict
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save


class WmaudaConan(ConanFile):
    name = "wmauda"
    version = "0.9"
    description = "wmauda — remote-control dockapp for Audacious media player"
    license = "GPL-2.0-or-later"
    homepage = "https://www.netswarm.net/"
    url = "http://ftp.debian.org/debian/pool/main/w/wmauda"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Match libaudclient/3.5-rc2.1 binary expectations exactly:
        #   dbus-glib/0.114.1 + glib/2.84.0.1
        # 3.5-rc2.1 (not 3.5-rc2) is required on purpose: its recipe is
        # pinned to glib/2.84.0.1 + dbus-glib/0.114.1, so the package_id it
        # computes inside this graph (glib override → 2.84.0.1) equals the
        # one already published in the registry and the binary is downloaded
        # instead of being rebuilt from source on the CI worker.
        self.requires("glib/2.84.0.1", override=True)
        self.requires("dbus-glib/0.114.1", override=True)
        self.requires("expat/2.8.2.1", override=True)
        self.requires("libjpeg-turbo/3.2.0", force=True)
        self.requires("gtk2/2.24.33")
        self.requires("libaudclient/3.5-rc2.1")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    @staticmethod
    def _dep_libs(dep):
        """依赖的库名列表，含其 CppInfo 组件（components）。

        部分配方——glib（因而所有 GTK+2 消费者）即是——把库声明在
        ``cpp_info`` 的 **组件** 里而非顶层 ``cpp_info.libs``。只读顶层会静默
        得到空列表，链接期即以 ``g_*`` 未定义符号失败，因此必须一并收集
        组件库名。
        """
        libs = list(dep.cpp_info.libs or [])
        try:
            for comp in dep.cpp_info.components.values():
                libs.extend(comp.libs or [])
        except Exception:
            pass
        return libs

    def build(self):
        # Profile stores tools.build:compiler_executables as a JSON string;
        # parse it directly instead of using dotted sub-keys (which Conan
        # does not expand for nested dict confs).
        cc = ar = ranlib = None
        ce_raw = self.conf.get("tools.build:compiler_executables")
        if ce_raw:
            try:
                ce = json.loads(ce_raw) if isinstance(ce_raw, str) else ce_raw
                cc = ce.get("c")
                ar = ce.get("ar") or ce.get("cpp")  # may be absent
                ranlib = ce.get("ranlib")
            except Exception:
                pass
        # Fallback to OHOS SDK paths when conf is not available
        cc = cc or os.environ.get("CC", "/data/service/hnp/bin/clang")
        ar = ar or os.environ.get("AR", "/data/service/hnp/bin/llvm-ar")
        ranlib = ranlib or os.environ.get("RANLIB", "/data/service/hnp/bin/llvm-ranlib")

        # Collect include dirs, lib dirs, and lib names from dependencies
        include_dirs = []
        lib_dirs = []
        lib_names = []
        seen_dirs = set()
        seen_libs = set()
        for req, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            pkg_inc = os.path.join(dep.package_folder, "include")
            for inc_dir in (dep.cpp_info.includedirs or []):
                full = os.path.join(dep.package_folder, inc_dir)
                if full not in seen_dirs and os.path.isdir(full):
                    seen_dirs.add(full)
                    include_dirs.append(full)
            # Auto-detect ALL subdirs under include/ (glib-2.0, harfbuzz,
            # freetype2, atk-1.0, gdk-2.0, cairo, dbus-1.0, etc.)
            if os.path.isdir(pkg_inc):
                try:
                    for entry in os.listdir(pkg_inc):
                        sub = os.path.join(pkg_inc, entry)
                        if os.path.isdir(sub) and sub not in seen_dirs:
                            seen_dirs.add(sub)
                            include_dirs.append(sub)
                except OSError:
                    pass
            # Auto-detect lib/*-2.0/include (glibconfig.h lives here)
            pkg_lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(pkg_lib):
                try:
                    for entry in os.listdir(pkg_lib):
                        sub = os.path.join(pkg_lib, entry, "include")
                        if os.path.isdir(sub) and sub not in seen_dirs:
                            if "-" in entry and any(c.isdigit() for c in entry):
                                seen_dirs.add(sub)
                                include_dirs.append(sub)
                except OSError:
                    pass
            for lib_dir in (dep.cpp_info.libdirs or []):
                full = os.path.join(dep.package_folder, lib_dir)
                if full not in seen_dirs and os.path.isdir(full):
                    seen_dirs.add(full)
                    lib_dirs.append(full)
            # Panel CppInfo components: glib (pulled in transitively via gtk2)
            # declares its libraries as components, so its top-level
            # cpp_info.libs is empty and the libs must come from the
            # components instead.
            for lib in self._dep_libs(dep):
                if lib not in seen_libs:
                    seen_libs.add(lib)
                    lib_names.append(lib)

        # Patch Makefile: replace $(shell pkg-config ...) lines and add
        # PIXMAP_DIR.  This avoids the OHOS pkg-config problem and the
        # shell-escaping nightmare of embedding paths in CFLAGS.
        makefile = os.path.join(self.source_folder, "Makefile")
        mf = load(self, makefile)

        pixmap_dir = os.path.join(self.package_folder, "share", "pixmaps")
        # PIXMAP_DIR must be a C string literal: "\"<path>\""
        pixmap_cstr = pixmap_dir.replace("\\", "\\\\").replace('"', '\\"')
        pixmap_line = f'CFLAGS += -DPIXMAP_DIR=\\\\"{pixmap_cstr}\\\\"'

        # Build the replacement lines
        inc_flags = " ".join(f"-I{d}" for d in include_dirs)
        lib_flags = " ".join(f"-L{d}" for d in lib_dirs)
        lib_flags += " " + " ".join(f"-l{l}" for l in lib_names)

        new_cflags = f"CFLAGS = -g -pipe {inc_flags}"
        new_libs = f"LIBS = {lib_flags}"

        # Replace pkg-config lines in Makefile
        # Line: CFLAGS += $(shell pkg-config audacious --cflags) $(shell pkg-config dbus-1 --cflags) -DPIXMAP_DIR="\"$(PIXMAP_DIR)\""
        mf = re.sub(
            r'CFLAGS\s*\+=\s*\$\(shell pkg-config audacious.*',
            new_cflags,
            mf,
        )
        # Line: LIBS := $(shell pkg-config audacious --libs) $(shell pkg-config audclient --libs)  $(shell pkg-config dbus-1 --libs)
        mf = re.sub(
            r'LIBS\s*:=\s*\$\(shell pkg-config audacious.*',
            new_libs,
            mf,
        )
        # Line: CFLAGS += $(shell pkg-config gtk+-2.0 --cflags)
        mf = re.sub(
            r'CFLAGS\s*\+=\s*\$\(shell pkg-config gtk\+-2\.0.*',
            new_cflags,
            mf,
        )
        # Line: LIBS += $(shell pkg-config gtk+-2.0 --libs)
        mf = re.sub(
            r'LIBS\s*\+=\s*\$\(shell pkg-config gtk\+-2\.0.*',
            new_libs,
            mf,
        )
        # Add PIXMAP_DIR after the first CFLAGS line
        mf = mf.replace(new_cflags, new_cflags + "\n" + pixmap_line, 1)

        save(self, makefile, mf)

        self.run(
            f"make -j1 "
            f"CC={cc} AR={ar} RANLIB={ranlib} "
            f"PREFIX={self.package_folder}"
        )

    def package(self):
        self.run(f"make install PREFIX={self.package_folder}")
        # Also install dock-master.xpm (upstream Makefile omits it)
        pixmap_dir = os.path.join(self.package_folder, "share", "pixmaps")
        import shutil
        for xpm in ("wmauda.xpm", "dock-master.xpm"):
            src = os.path.join(self.source_folder, xpm)
            dst = os.path.join(pixmap_dir, xpm)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
