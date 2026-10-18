#!/usr/bin/env python3
"""Conan recipe for qt5-qtscript 5.15.2 on OpenHarmony PC.

QtScript is the deprecated-but-still-shipped Qt5 module providing the
Qt Script engine (QScriptEngine/QScriptValue API backed by an in-tree
copy of JavaScriptCore). It produces two shared libraries:

  * libQt5Script      — the script engine itself (depends on Qt5Core)
  * libQt5ScriptTools — the debugging widgets (depends on Qt5Core/Gui/Widgets)

It is built with qmake taken from the qt5-qtbase Conan package
(qtscript.pro, -spec linux-clang) and requires qt5-qtbase 5.15.2.2
(Core/Gui/Widgets), matching the qt5 family dependency line
(qt5-qtdeclarative / qt5-qtcharts both pin qt5-qtbase/5.15.2.2).
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout


class Qt5QtscriptConan(ConanFile):
    name = "qt5-qtscript"
    version = "5.15.2"
    description = "Qt5 Script module (QScriptEngine + JavaScriptCore, QtScriptTools debugger) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    # Matches both the `.conan2/p/b/<pkg>/b` and the `.cache/conan2/p/b/<pkg>/b`
    # conan build-dir layouts (both shapes appear across cache versions/paths).
    # Kept in sync with the qt5-qtcharts pattern so the .pri rewriting never
    # leaves stale build-directory paths in the qtbase module files.
    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
    )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # No patches shipped with this recipe (manifest.yaml: patches: none);
        # kept as the standard recipe shape so a future genuine upstream patch
        # declared in conandata.yml is exported automatically.
        export_conandata_patches(self)

    def requirements(self):
        # qmake 工具与 Qt5 Core/Gui/Widgets 基础库由 qt5-qtbase 提供。
        # qt5 线依赖包名固定为 qt5-qtbase/5.15.2.2（与 qt5-qtdeclarative、
        # qt5-qtcharts 一致；勿用 qtbase/6.x 或 qtbase-opensource-src）。
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256", ""),
                    strip_root=True)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration(
            "Unable to download qtscript source from all mirrors"
        )

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability)."""
        # Fix qt.conf
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    f"[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )

        # Fix .pri files that reference the build directory
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = self._BUILD_DIR_PATTERN.sub(qtbase_pkg, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def build(self):
        # No-op unless conandata.yml declares patches (it declares none).
        apply_conandata_patches(self)

        qtbase = self.dependencies["qt5-qtbase"]
        qtbase_pkg = qtbase.package_folder

        # Fix qt5-qtbase paths (qt.conf and .pri files point to build dir)
        self._fix_qtbase_paths(qtbase_pkg)

        qmake = os.path.join(qtbase_pkg, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )

        build_env = Environment()
        build_env.define("QTDIR", qtbase_pkg)
        build_env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))

        with build_env.vars(self).apply():
            # Configure with qmake (qtscript.pro drives src/script +
            # src/scripttools via qtHaveModule(widgets))
            self.run(
                f'cd "{self.source_folder}" && '
                f'{shlex.quote(qmake)} qtscript.pro -spec linux-clang'
            )

            # Build (prevent stripping - OHOS loader rejects stripped ELF).
            # 并发固定 -j1（qt5-qtwebchannel 先例）：CI worker 高负载时
            # make 并行子进程触发 "/bin/sh: can't fork"（Resource
            # temporarily unavailable），且 make jobserver 在 HMDFS 上
            # mkfifo 报 Operation not permitted（降并发可同时规避两者）。
            # 本地如需提速可用 QTSCRIPT_JOBS 环境变量覆盖。
            jobs = 1
            if os.environ.get("QTSCRIPT_JOBS", "").strip().isdigit():
                jobs = int(os.environ["QTSCRIPT_JOBS"])
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        src = self.source_folder

        # Copy libraries (unstripped)
        lib_dir = os.path.join(src, "lib")
        copy(self, "*.so*", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.la", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pc", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Ensure library symlinks exist (HMDFS may not preserve them during
        # copy); dynamic discovery — no hardcoded .so.5.15.2 names.
        pkg_lib = os.path.join(self.package_folder, "lib")
        for lib_base in ("libQt5Script.so", "libQt5ScriptTools.so"):
            if not os.path.isdir(pkg_lib):
                break
            real_so = None
            for name in sorted(os.listdir(pkg_lib)):
                if (name.startswith(lib_base)
                        and not name.endswith((".prl", ".la", ".pc"))):
                    real_so = name
                    break
            if not real_so:
                continue
            so_path = os.path.join(pkg_lib, real_so)
            stem = lib_base[len("lib"):].split(".so")[0]  # Qt5Script / Qt5ScriptTools
            for link_name in (lib_base, f"{lib_base}.5", f"{lib_base}.5.15"):
                link_path = os.path.join(pkg_lib, link_name)
                if link_path == so_path:
                    continue
                if not os.path.exists(link_path) and os.path.exists(so_path):
                    try:
                        os.symlink(real_so, link_path)
                    except OSError:
                        shutil.copy2(so_path, link_path)

        # Copy headers (Qt forwarding headers live in include/)
        include_dir = os.path.join(src, "include")
        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir,
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)

        # Copy source headers (Qt forwarding headers reference src/)
        copy(self, "*.h", src=os.path.join(src, "src"),
             dst=os.path.join(self.package_folder, "src"), keep_path=True)

        # Copy plugins
        plugins_dir = os.path.join(src, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

        # Copy mkspecs modules (qt_script.pri / qt_scripttools.pri)
        mkspecs_dir = os.path.join(src, "mkspecs")
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy cmake configs (Qt5Script/Qt5ScriptTools Config files)
        cmake_dir = os.path.join(lib_dir, "cmake")
        if os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"),
                 keep_path=True)

        # Anti-leak guard: package must not embed our build directory.
        build_root = os.path.abspath(self.build_folder)
        leaked = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                if build_root in text:
                    leaked.append(os.path.relpath(path, self.package_folder))
        if leaked:
            raise ConanException(
                "package still references Qt build directories (pruned after "
                f"build): {sorted(leaked)}"
            )

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        # Qt5Script: the script engine (links Qt5Core)
        qt5script = self.cpp_info.components["Qt5Script"]
        qt5script.libs = ["Qt5Script"]
        qt5script.includedirs = ["include", "include/QtScript"]
        qt5script.requires = ["qt5-qtbase::Qt5Core"]
        qt5script.set_property("cmake_file_name", "Qt5Script")
        qt5script.set_property("cmake_target_name", "Qt5::Script")

        # Qt5ScriptTools: debugging widgets (links Qt5Core/Gui/Widgets)
        qt5scripttools = self.cpp_info.components["Qt5ScriptTools"]
        qt5scripttools.libs = ["Qt5ScriptTools"]
        qt5scripttools.includedirs = ["include", "include/QtScriptTools"]
        qt5scripttools.requires = [
            "qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui",
            "qt5-qtbase::Qt5Widgets",
        ]
        qt5scripttools.set_property("cmake_file_name", "Qt5ScriptTools")
        qt5scripttools.set_property("cmake_target_name", "Qt5::ScriptTools")
