#!/usr/bin/env python3
"""Conan recipe for wlrobs 1.2 — Meson.

OBS Studio 插件：在 wlroots 系 Wayland 合成器上做屏幕采集（screencopy 与
export-dmabuf 两个后端），构建产物为单个共享库插件 libwlrobs.so，安装到
lib/obs-plugins/，由 OBS 运行时 dlopen 加载，不参与消费者链接。

上游：https://hg.sr.ht/~scoopta/wlrobs（Mercurial，v1.2 tarball）

依赖消费（全部经制品仓 conan download 验证）：
  - obs/32.1.2      → meson.build: dependency('libobs')（pkg-config 名 libobs）
  - wayland/1.24.0  → meson.build: dependency('wayland-client')

OHOS 适配要点（无源码补丁，全部在 generate() 层解决）：
  1. libobs.pc / wayland-client.pc 的 prefix 指向陈旧构建目录或 '/'（E429
     同族问题），复制进 fixed_pkgconfig 并重写 prefix，置于 PKG_CONFIG_PATH
     最前；libobs.pc Cflags 内的 -Werror 一并剥离（禁止传染消费者编译）。
     .pc 不允许重复 Cflags/Libs 关键字行——只做单行内替换，不追加行。
  2. libobs.pc 的 -I${prefix}/include 恰为 wlrobs '#include <obs/...>' 所需
     的父目录（obs 包头文件布局 include/obs/）。
  3. meson.build 的 cc.find_library('dl'/'rt')：OHOS NDK sysroot
     usr/lib/aarch64-linux-ohos/ 提供 libdl.a/librt.a 静态桩，无需修改。
  4. OHOS sandbox meson 找不到 llvm-ar → native 文件注入 ar 行
     （wayland/1.24.0 同款）。

上游测试（R51 申报，详见 test_package/MANIFEST.yml）：上游无自动化测试
（无 tests/ 目录，meson.build 无 test() 声明，0/0）；鸿蒙侧新增 dlopen
闭包探针消费者用例验证插件 ABI 可加载（RTLD_NOW 全符号解析 + dlsym
obs_module_load），为适配后新增的本平台测试用例。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WlrobsConan(ConanFile):
    name = "wlrobs"
    version = "1.2"
    description = "OBS Studio plugin for screen capture on wlroots Wayland compositors"
    license = "GPL-3.0-only"
    homepage = "https://hg.sr.ht/~scoopta/wlrobs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_scpy": [True, False],
        "with_dmabuf": [True, False],
    }
    default_options = {
        "shared": True,
        "with_scpy": True,
        "with_dmabuf": True,
    }

    def export_sources(self):
        export_conandata_patches(self)  # 无补丁时 no-op（G1 骨架要求）
        copy(self, "COPYING.md", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # meson.build: dependency('wayland-client') + dependency('libobs')
        self.requires("wayland/1.24.0")
        self.requires("obs/32.1.2")
        # 版本收敛：wayland/1.24.0 配方钉 expat/2.8.2（精确），而 obs 经
        # ffmpeg→fontconfig/2.18.1.1 需要 expat/2.8.2.1（精确）——两侧精确
        # 钉版硬冲突。顶层 force=True 收敛到 2.8.2.1：wayland 已发布二进制
        # 的依赖闭包记录为 expat/2.8.Z（2.8.x 任意补丁），package_id 仍命中，
        # 无需重建 wayland（R36 不受影响）。
        self.requires("expat/2.8.2.1", force=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def _fix_pc(self, dep, pc_name, extra_includes=None, strip_werror=False,
                strip_requires_private=False):
        """复制依赖自带的 .pc 到 fixed_pkgconfig 并重写 prefix。

        E429 同族：依赖包内 .pc 的 prefix 指向构建目录或 '/'，而真实安装
        位于包目录。单行内修改（.pc 不允许重复 Cflags 行），可选剥离
        -Werror（上游 .pc 把自己仓库的告警策略传染给消费者）。
        """
        base = dep.package_folder
        pc_src = os.path.join(base, "lib", "pkgconfig", pc_name)
        if not os.path.isfile(pc_src):
            return None
        fixed_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_dir, exist_ok=True)
        with open(pc_src, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
        if extra_includes:
            # obs 的 sse-intrin.h #include <simde/x86/sse2.h>（obs 侧
            # simde transitive_headers=True），但其 libobs.pc 的 Cflags 不含
            # simde include——追加进同一 Cflags 行（.pc 禁止重复 Cflags 行）
            content = re.sub(
                r"(?m)^(Cflags:.*)$",
                lambda m: m.group(1) + " " + " ".join(
                    "-I" + d for d in extra_includes),
                content)
        if strip_werror:
            # 仅当 Cflags 行内出现时剥离，单行内替换
            content = re.sub(
                r"(?m)^(Cflags:.*)\s-Werror\s*", r"\1 ", content)
            content = re.sub(r"(?m)^(Cflags:.*?)\s+-Werror$", r"\1", content)
        if strip_requires_private:
            # 动态链接场景 Requires.private 的静态闭包不参与链接；且被
            # Requires.private 引用的包（如 libffi）作为 shared 依赖的静态
            # 传递依赖会被 Conan skip（package_folder=None），其 .pc 在
            # conan 包内不存在 → pkg-config 解析 wayland-client 直接失败。
            # 剥离该行，保留本包自身的 -I/-L/-l（wayland-client.pc 原行）。
            content = re.sub(r"(?m)^Requires\.private:.*$\n?", "", content)
            content = re.sub(r"(?m)^Libs\.private:.*$\n?", "", content)
        out = os.path.join(fixed_dir, pc_name)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info(f"wlrobs: fixed {pc_name} prefix -> {base}")
        return out

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["use_scpy"] = bool(self.options.with_scpy)
        tc.project_options["use_dmabuf"] = bool(self.options.with_dmabuf)

        # fixed_pkgconfig 置于 PKG_CONFIG_PATH 最前：meson dependency() 经
        # pkg-config 解析 libobs / wayland-client，重写后的 pc 优先命中
        pc_paths = []
        fixed_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        simde = self.dependencies["simde"]
        if self._fix_pc(self.dependencies["obs"], "libobs.pc",
                        extra_includes=list(simde.cpp_info.includedirs),
                        strip_werror=True):
            pc_paths.append(fixed_dir)
        if self._fix_pc(self.dependencies["wayland"], "wayland-client.pc",
                        strip_requires_private=True):
            if fixed_dir not in pc_paths:
                pc_paths.append(fixed_dir)
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue  # build/tool 上下文依赖无 host 包目录
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                pc_paths.append(pc)
        if pc_paths:
            tc.pkg_config_path = os.pathsep.join(
                [tc.pkg_config_path] + pc_paths)
        tc.generate()

        # OHOS sandbox：meson 找不到 llvm-ar → native 文件注入 ar 行
        # （wayland/1.24.0 先例）
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =", f"[binaries]\nar = '{ar_path}'\nc =")
        with open(native_file, "w") as f:
            f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # 无补丁时 no-op（G1 骨架要求）
        meson = Meson(self)
        meson.configure()
        meson.build()
        # R51 上游测试申报：上游无自动化测试（源码树无 tests/ 目录、
        # meson.build 无 test() 声明、meson_options.txt 仅 use_scpy/
        # use_dmabuf 两个构建选项），故无 meson test 步骤；清点证据见
        # test_package/MANIFEST.yml 与 reports/test-report.md。

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 插件 so（lib/obs-plugins/libwlrobs.so）由 OBS 运行时 dlopen 加载，
        # 不参与消费者链接：cpp_info.libs 置空，libdirs 指向插件目录。
        self.cpp_info.libdirs = ["lib/obs-plugins"]
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
