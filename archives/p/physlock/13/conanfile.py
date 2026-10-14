#!/usr/bin/env python3
"""Conan recipe — physlock 13 on HarmonyOS PC (aarch64-linux-ohos).

physlock 是用 PAM 认证的轻量级 Linux 控制台锁屏工具（等价于 `vlock -an`），
只允许前台 VT 的会话用户或 root 解锁。上游为单一 C 可执行文件工程，构建系统
是**手写 GNU Makefile**（非 autotools/cmake/meson）。

第三方依赖（与上游默认构型 `HAVE_SYSTEMD=1` 及 Debian Build-Depends 一致）：
  * linux-pam/1.7.2 : `-lpam -lpam_misc`
      Makefile ldlibs；`<security/pam_appl.h>`(physlock.h) / `<security/pam_misc.h>`(main.c)
  * systemd/261     : `-lsystemd`（libsystemd 客户端库）
      Makefile `HAVE_SYSTEMD=1 -> ldlibs 含 -lsystemd`；Debian `Build-Depends: libsystemd-dev`

OHOS 适配（真实、最小）：
  1. **OHOS 无 `cc`/`gcc`**：Makefile 的 `$(CC)` 默认 `cc` 在 OHOS 上不存在
     （`cc: not found`），必须显式传 `CC=<OHOS clang>`（R33：从 Conan conf 获取，
     非裸 shell 变量）。本配方 build() 从 `tools.build:compiler_executables` 读取。
  2. **依赖注入走私有目录**：PAM/systemd 的头/库通过 `CPPFLAGS`/`LDFLAGS` 指向各自
     Conan 包目录（R49：不使用共享 `/usr/local`）。
  3. **上游 install 需 root**：Makefile `install` 目标用
     `install -m 4755 -o root -g root`（README 明确说 install 需要 root），
     非 root/沙箱环境直接失败。本配方 build() 只做 `make`，package() 手工落
     `bin/physlock` 与渲染后的 `share/man/man1/physlock.1`（与上游 install 结果等价，
     不依赖 root，也不修改上游源码）。

平台无关语义保持：默认编译路径不定义 `-DHAVE_SYSTEMD`（上游亦然），
`session.c` 的 `#if HAVE_SYSTEMD` 分支不参与编译（构建的 `-lsystemd` 仅出现在链接行）。
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PhyslockConan(ConanFile):
    name = "physlock"
    version = "13"
    description = ("Lightweight Linux/OHOS console locking tool "
                   "(PAM-authenticated, equivalent to `vlock -an`)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xyb3rt/physlock"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 本配方无补丁（上游 v13 零改动），保留钩子以符合配方结构约定
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "physlock locks Linux/OHOS virtual consoles and requires PAM")

    def requirements(self):
        # 与上游默认构型（Makefile HAVE_SYSTEMD=1）及 Debian Build-Depends 一致
        self.requires("linux-pam/1.7.2")
        self.requires("systemd/261")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS 只提供 hnp 版 bash（无 /bin/bash）；与 ci/conan/profiles/ohos-aarch64 的
        # [buildenv] 对齐，显式声明 CONFIG_SHELL/SHELL 作为兜底（make 的 recipe 行本身
        # 固定用 /bin/sh，不受 SHELL 环境变量影响）。
        env = Environment()
        env.define("CONFIG_SHELL", os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash"))
        env.define("SHELL", os.environ.get("SHELL", "/data/service/hnp/bin/bash"))
        env.vars(self).save_script("physlock-build-env")

    def _dep_flags(self):
        """从依赖包私有目录收集 -I/-L（R49：不使用共享系统前缀）。"""
        cppflags, ldflags = [], []
        for dep in ("linux-pam", "systemd"):
            cpp_info = self.dependencies[dep].cpp_info
            cppflags += [f"-I{d}" for d in cpp_info.includedirs]
            ldflags += [f"-L{d}" for d in cpp_info.libdirs]
        return cppflags, ldflags

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict).get("c") or "clang"
        cppflags, ldflags = self._dep_flags()
        command = " ".join([
            f"CC={shlex.quote(cc)}",
            f"CFLAGS={shlex.quote('-fPIC -O2')}",
            f"CPPFLAGS={shlex.quote(' '.join(cppflags))}",
            f"LDFLAGS={shlex.quote(' '.join(ldflags))}",
            "make -j1",
        ])
        self.output.info(f"physlock build: {command}")
        self.run(command, cwd=self.source_folder)

    def package(self):
        # 不调用 `make install`：上游 install 目标硬编码 `-o root -g root`，非 root 失败。
        copy(self, "physlock", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 等价上游 `make install` 对 man1 的处理：sed "s/VERSION/<version>/g" physlock.1
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(man_dir, exist_ok=True)
        with open(os.path.join(self.source_folder, "physlock.1"), encoding="utf-8") as src, \
                open(os.path.join(man_dir, "physlock.1"), "w", encoding="utf-8") as dst:
            dst.write(src.read().replace("VERSION", str(self.version)))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
