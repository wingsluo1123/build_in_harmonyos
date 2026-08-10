#!/usr/bin/env python3
"""Conan recipe — valgrind 3.24.0 (Autotools, 内存调试工具).

OHOS (aarch64) 适配要点:
- config.guess/config.sub: HarmonyOS 平台识别 (E007) + linux-ohos 内核组合
- configure: OHOS 用户态 libc 为 musl 变体，走 musl 分支 (原报 "requires glibc 2.2+")
- config.guess/config.status: HMDFS 临时目录 mkdir 修复 (E114)
- vgdb.c: OHOS 无 pthread_cancel 符号，__OHOS__ 守卫 (E085)
- --enable-only64bit: OHOS 工具链仅支持 aarch64，跳过 32 位 guest 汇编 (armv6t2)
- 测试程序 index/rindex/pthread_cancel/_res/mq 等 musl 缺失符号已加 __OHOS__ 守卫
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ValgrindConan(ConanFile):
    name = "valgrind"
    version = "3.24.0"
    description = "Valgrind - dynamic binary instrumentation framework / memory debugger"
    license = "GPL-2.0-or-later"
    homepage = "https://valgrind.org/"
    url = "https://sourceware.org/pub/valgrind/valgrind-3.24.0.tar.bz2"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        import os
        import subprocess

        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # OHOS 工具链仅支持 aarch64，跳过 32 位 guest 编译（armv6t2 汇编不支持）
        tc.configure_args.append("--enable-only64bit")
        # OHOS: clang 工具链无 libgcc.a（valgrind 链接 -lgcc 需要），
        # 用 libclang_rt.builtins.a 创建符号链接并提供 -L 搜索路径（工具链目录只读，不可直接放置）
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or "clang"
            rt = subprocess.check_output([cc, "-print-file-name=libclang_rt.builtins.a"], text=True).strip()
            if rt and os.path.isfile(rt):
                link_dir = os.path.join(self.build_folder, "ohos-gcc-rt")
                os.makedirs(link_dir, exist_ok=True)
                link = os.path.join(link_dir, "libgcc.a")
                if not os.path.exists(link):
                    os.symlink(rt, link)
                tc.extra_ldflags.append(f"-L{link_dir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # W3 本地 CI 模拟超时 600s：valgrind 干净重建耗时较长，用 -j4 并行加速
        autotools.make(args=["-j4"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # valgrind 为命令行工具（bin/valgrind 及 libexec/valgrind/ 下各工具），
        # 同时提供头文件与静态库供下游开发（include/valgrind/*.h、lib/valgrind/*.a）
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
