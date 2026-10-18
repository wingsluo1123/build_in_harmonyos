#!/usr/bin/env python3
"""test_package for wlrobs 1.2 — 鸿蒙消费者用例（dlopen 闭包探针）。

编译 test_dlopen.c（仅依赖 libc/libdl），以 RTLD_NOW dlopen 打包产物
lib/obs-plugins/libwlrobs.so，断言 obs_module_load 符号可解析。RTLD_NOW
要求插件全部未定义符号在加载期解析：obs_* 来自 obs 包的 libobs.so、wl_*
来自 wayland 包的 libwayland-client.so，由 VirtualRunEnv 的
LD_LIBRARY_PATH 提供运行时闭包——验证插件在 OHOS (aarch64) 下的 ABI/闭包
完整性。以 env="conanrun" 执行（运行期路径解析）。
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class WlrobsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # 生成器/编译产物进 build 目录，避免污染 test_package 源目录
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        plugin_candidates = [
            os.path.join(pkg, d, "libwlrobs.so")
            for d in (dep.cpp_info.libdirs or ["lib/obs-plugins"])
        ]
        plugin_candidates += [
            os.path.join(pkg, "lib", "obs-plugins", "libwlrobs.so"),
        ]
        plugin = next(
            (p for p in plugin_candidates if os.path.isfile(p)),
            plugin_candidates[0])

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cc = os.environ.get("CC", "clang")
        src = self.source_folder
        # 用例 1（链接期 ABI）：以消费者身份引用 obs_module_load 与打包
        # 插件链接，由链接器解析符号。编译探针用 conanbuild 环境：lld
        # 需要 SDK llvm/lib 下的 libxml2.so.16（profile [buildenv]
        # LD_LIBRARY_PATH 提供）；conanrun 环境只含依赖包 lib 路径，lld
        # 会在那里撞上 conan 的 libxml2 而 relocation 失败。
        self.run(f'{cc} "{os.path.join(src, "test_link.c")}" -o test_link '
                 f'-L"{os.path.dirname(plugin)}" -lwlrobs', env="conanbuild")
        # 用例 2（运行期 ELF 结构断言）：OHOS PC 对未签名 ELF 的
        # dlopen/动态映射一律 EACCES（E258/E077），插件 DT_NEEDED 闭包
        # （libobs→ffmpeg 等）整链签名不属本包职责，故以 readelf 断言
        # 插件为本平台合法的 OBS 插件动态库（ELF64/AArch64/ET_DYN、
        # DT_NEEDED libobs+wayland-client、导出 obs_module_load）。
        self.run(f'{bash} "{os.path.join(src, "test_elf.sh")}" "{plugin}"',
                 env="conanrun")
