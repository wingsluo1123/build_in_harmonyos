#!/usr/bin/env python3
"""Conan test_package for gnome-desktop 44.1.

消费者侧验证（R34：必须实质调用被测包 API）：
  - CMake 侧 find_package(gnome-desktop-3.0) + 链接 gnome-desktop-3.0 目标
  - 运行 test_gnome_desktop：版本 API / locale 解析 / GnomeWallClock /
    GnomeXkbInfo 共 6 项断言（见 src/test_gnome_desktop.c）

运行环境准备（OHOS 专有约束）：
  - 制品仓 gsettings-desktop-schemas 只带 XML schema，无 gschemas.compiled；
    GnomeWallClock 的 g_settings_new("org.gnome.desktop.interface") 需要已编译
    schema → 此处用 glib 包内的 glib-compile-schemas 现场编译到构建目录。
  - 制品仓 GLib 工具为 ELF，HarmonyOS 上执行需签名 → 复制到构建目录后
    binary-sign-tool 自签名。
  - GnomeXkbInfo 通过 XKB_CONFIG_ROOT 环境变量定位 XKB 规则数据，
    指向 xkeyboard-config 依赖包的 share/X11/xkb。
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment

SIGNER = "/data/service/hnp/bin/binary-sign-tool"


class GnomeDesktopTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明数据类依赖：否则 conan 把它当“可跳过的二进制”
        # （Skipped binaries），package_folder 为 None，测试无法定位
        # XKB 规则数据目录。
        self.requires("xkeyboard-config/2.48")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        exe = os.path.join(self.cpp.build.bindirs[0], "test_gnome_desktop")
        self._sign(exe)
        self._compile_schemas()

    def _dep_env(self):
        """依赖运行时环境：库搜索路径 + glib 工具 PATH。

        glib-compile-schemas 等 ELF 工具需要 LD_LIBRARY_PATH 找到包内
        libglib-2.0.so；被测程序同样需要全部依赖库与自身包内库。
        """
        env = Environment()
        paths = []
        for dep in self.dependencies.values():
            folder = dep.package_folder
            if not folder:
                continue
            for libdir in dep.cpp_info.libdirs or []:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    folder, libdir)
                if os.path.isdir(path):
                    paths.append(path)
        glib_folder = self.dependencies["glib"].package_folder
        paths.append(os.path.join(glib_folder, "lib"))
        for path in paths:
            env.prepend_path("LD_LIBRARY_PATH", path)
        env.prepend_path("PATH", os.path.join(glib_folder, "bin"))
        return env

    def _sign(self, binary):
        if self.settings.os != "OHOS":
            return
        if not os.path.isfile(SIGNER):
            self.output.warning(f"signer missing, skip signing {binary}")
            return
        self.run(shlex.join([SIGNER, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))

    def _signed_tool(self, name):
        """复制 glib 包内的 ELF 工具到构建目录并签名后返回路径。"""
        source = os.path.join(self.dependencies["glib"].package_folder, "bin",
                              name)
        if not os.path.isfile(source):
            return None
        out_dir = os.path.join(self.build_folder, "tools")
        os.makedirs(out_dir, exist_ok=True)
        target = os.path.join(out_dir, name)
        shutil.copyfile(source, target)
        os.chmod(target, 0o755)
        self._sign(target)
        return target

    def _compile_schemas(self):
        """把 gsettings-desktop-schemas 的 XML 编译成本地 gschemas.compiled。"""
        package = self.dependencies["gsettings-desktop-schemas"].package_folder
        source = os.path.join(package, "share", "glib-2.0", "schemas")
        out_dir = os.path.join(self.build_folder, "schemas")
        os.makedirs(out_dir, exist_ok=True)
        compiled = os.path.join(out_dir, "gschemas.compiled")
        if os.path.isfile(compiled):
            return
        if not os.path.isdir(source):
            self.output.warning(f"schemas dir missing: {source}")
            return
        for xml in glob.glob(os.path.join(source, "*.xml")):
            shutil.copy2(xml, os.path.join(out_dir, os.path.basename(xml)))
        tool = self._signed_tool("glib-compile-schemas")
        if tool is None:
            self.output.warning("glib-compile-schemas missing; "
                                "wall-clock assertions may fail")
            return
        with self._dep_env().vars(self).apply():
            self.run(f"{shlex.quote(tool)} {shlex.quote(out_dir)}")

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_gnome_desktop")
        env = self._dep_env()
        env.define_path("GSETTINGS_SCHEMA_DIR",
                        os.path.join(self.build_folder, "schemas"))
        kb_config = self.dependencies["xkeyboard-config"].package_folder
        # 规则数据真实目录是 share/xkeyboard-config-2；包内 share/X11/xkb
        # 是指向 /share/xkeyboard-config-2 的绝对软链（脱离包前缀不可用）。
        kb_data = os.path.join(kb_config, "share", "xkeyboard-config-2")
        if not os.path.isdir(kb_data):
            kb_data = os.path.join(kb_config, "share", "X11", "xkb")
        env.define_path("XKB_CONFIG_ROOT", kb_data)
        env.prepend_path("PATH",
                         os.path.join(self.dependencies["glib"].package_folder,
                                      "bin"))
        with env.vars(self).apply():
            self.run(exe, env="conanrun")
