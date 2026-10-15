#!/usr/bin/env python3
"""Conan recipe for libxfce4util 4.20.1 — XFCE core utility library.

Build system: meson (XFCE 4.20 起 meson 为主构建系统，tarball 同时携带
autotools 文件但本配方走 meson，与 4.20.0 的 autotools 配方区分).
Dependencies: glib/2.84.0.1 (glib-2.0 / gobject-2.0 / gio-2.0 组件).

OHOS adaptation notes (无源码补丁):
- gettext/i18n: OHOS sysroot 的 libintl.h 是空 stub（无 gettext 族声明），
  glib 制品自带 proxy-libintl（include/libintl.h 把 gettext 宏映射到
  g_libintl_*，lib/libintl.so 提供 SONAME libintl.so.8 的符号）。
  meson dependency() 的 cflags 把 glib include 目录置于 sysroot 之前，
  代理头生效（appstream/at-spi2-core 同款机制，无需复制头文件）。
- 链接: lld 默认 --no-allow-shlib-undefined，消费 glib 共享库的可执行文件
  需要在链接行上显式见到 -lintl（g_libintl_* 符号提供者）；conan
  PkgConfigDeps 生成的 glib-2.0.pc 不含 -lintl，构建前增强 .pc 的 Libs
  行（accountsservice 26.27.3 同款手法）。
- xdt-gen-visibility: 源码根目录的 python3 脚本，meson find_program()
  优先搜索源码目录；shebang /usr/bin/env python3 由构建环境 PATH 解析。
- introspection / vala / gtk-doc 关闭（制品仓无 gobject-introspection，
  OHOS 无 vapigen，gtk-doc 默认即 false）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Libxfce4UtilConan(ConanFile):
    name = "libxfce4util"
    version = "4.20.1"
    description = "XFCE core utility library (libxfce4util): GObject helpers, i18n, resource lookup, kiosk, string/utf8/file utils"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.xfce.org/xfce/libxfce4util"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        # meson.build: dependency('glib-2.0'/'gobject-2.0'/'gio-2.0', >= 2.72)
        # glib 制品导出 glib-2.0/gobject-2.0/gio-2.0 组件 .pc + proxy-libintl
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def _augment_glib_pc_intl(self):
        # conan(PkgConfigDeps) 生成的 glib-2.0.pc 不列 -lintl；OHOS lld 以
        # --no-allow-shlib-undefined 链接，任何消费 libglib-2.0.so（其自身有
        # 未定义 g_libintl_*）的目标都需要 -lintl（glib 包内 proxy-libintl，
        # SONAME libintl.so.8）出现在链接行上（accountsservice 26.27.3 同款）。
        for pc_name in ("glib-2.0", "gobject-2.0", "gio-2.0"):
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(
                    f"libxfce4util: {pc_name}.pc not generated, skip -lintl augment"
                )
                continue
            with open(pc_file, encoding="utf-8") as fh:
                content = fh.read()
            libs_line = next(
                (ln for ln in content.splitlines() if ln.startswith("Libs:")), None
            )
            if libs_line is not None and "-lintl" not in libs_line.split():
                content = content.replace(libs_line, libs_line + " -lintl", 1)
                with open(pc_file, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(content)
                self.output.info(
                    f"libxfce4util: augmented {pc_name}.pc Libs with -lintl"
                )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pc_intl()
        tc = MesonToolchain(self)
        # gobject-introspection 制品仓无货；OHOS 无 vapigen；gtk-doc 默认关
        tc.project_options["introspection"] = False
        tc.project_options["vala"] = "disabled"
        tc.project_options["gtk-doc"] = False
        # meson 裸名探测 ar：CI worker 上 llvm-ar ENOENT（wayland/glib 先例），
        # 显式注入绝对路径
        ar_path = "/data/service/hnp/bin/ar"
        if not os.path.isfile(ar_path):
            ar_path = shutil.which("ar") or ""
        if ar_path:
            tc.ar = ar_path
        # pkg-config 二进制：显式落定，避免 meson "Found pkg-config: NO"
        pc_bin = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pc_bin or not os.path.isfile(str(pc_bin)):
            pc_bin = "/data/service/hnp/bin/pkg-config"
        if os.path.isfile(str(pc_bin)):
            tc.pkgconfig = pc_bin
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_env(self):
        # TMPDIR 落到构建目录（OHOS /tmp 只读，accountsservice 先例）
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        return env

    def build(self):
        # 上游 4.20.1 无 test() 声明（tarball 实测无 tests/ 目录），
        # 测试覆盖由 test_package 消费者冒烟承担（见 test_package/MANIFEST.yml）
        with self._build_env().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_env().vars(self).apply():
            Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x7fELF"

    def _sign_installed_elfs(self):
        # meson install 重写 ELF（剥离构建目录 RUNPATH 等），链接器自签的
        # .codesign 段失效 → OHOS 加载器拒绝加载（"Error loading shared
        # library ... (needed by ...)"，errno 为空；实测构建目录原件可加载、
        # 安装副本 127）。install 后重签（glib 2.84.0.1 / accountsservice
        # 26.27.3 同款：llvm-objcopy 删旧段 + binary-sign-tool selfSign）。
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"libxfce4util: required OHOS signing tool not found: {tool}"
                )
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for subdir in ("bin", "sbin", "libexec"):
            binary_dir = os.path.join(self.package_folder, subdir)
            if os.path.isdir(binary_dir):
                for name in os.listdir(binary_dir):
                    path = os.path.join(binary_dir, name)
                    if (
                        os.path.isfile(path)
                        and not os.path.islink(path)
                        and self._is_elf(path)
                    ):
                        targets.append(path)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(
                f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1'
            )
        self.output.info(
            f"libxfce4util: re-signed {len(targets)} installed ELF(s) after meson install"
        )

    def package_info(self):
        # 下游 XFCE 组件（libxfce4ui/libxfce4panel 等）经 pkg-config 查
        # libxfce4util-1.0；头文件安装于 include/xfce4/libxfce4util/
        self.cpp_info.set_property("pkg_config_name", "libxfce4util-1.0")
        self.cpp_info.libs = ["xfce4util"]
        self.cpp_info.includedirs = ["include/xfce4"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
