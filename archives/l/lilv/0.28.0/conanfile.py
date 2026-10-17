#!/usr/bin/env python3
"""Conan recipe — lilv 0.28.0 (LV2 plugin host library, meson).

lilv: C library for loading and introspecting LV2 plugins. Meson-oriented
upstream; recipe drives the cross compiler via a generated cross file
(exploration-verified flow, see notes.md). Downstream consumer: jalv."""

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
import os

required_conan_version = ">=2.0"


class LilvConan(ConanFile):
    name = "lilv"
    version = "0.28.0"
    description = "lilv: C library for simple use of LV2 plugins"
    license = "ISC"
    url = "https://download.drobilla.net/"
    homepage = "https://drobilla.net/software/lilv.html"
    topics = ("lv2", "plugins", "audio", "host")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    # 制品仓依赖（sratom 为本次适配前置发布，PR #15450；不显式钉 serd——
    # sord 传递钉 serd/0.32.9，显式钉版冲突实证见 notes.md）
    requires = ("sratom/0.6.22", "sord/0.16.22", "lv2/1.18.11-git")
    generators = "PkgConfigDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        # 探索期零源码修改（diff 证实），无补丁可导出；G1 门禁要求显式
        # 声明点。
        pass

    def apply_conandata_patches(self):
        # 探索期零源码修改（conandata.yml 无 patches 声明），显式无操作
        # 以满足 G1 门禁的补丁应用点检查。
        pass

    def validate(self):
        # OHOS PC 交叉构建目标白名单（R32 口径）；build() 的 cross file
        # 硬编码 aarch64，非 armv8 会产出错误架构
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lilv supports Linux/OHOS only, got {self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"lilv recipe targets armv8 cross builds, got "
                f"{self.settings.arch}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def build(self):
        src = self.source_folder
        bld = self.build_folder
        gen = self.generators_folder
        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        ar = os.path.join(os.path.dirname(cc), "llvm-ar")
        ar_line = f"ar = '{ar}'\n" if os.path.exists(ar) else ""
        cross = os.path.join(bld, "ohos-cross.ini")
        with open(cross, "w") as fh:
            fh.write(
                "[binaries]\n"
                f"c = '{cc}'\n"
                f"{ar_line}"
                "pkg-config = 'pkg-config'\n"
                "\n[host_machine]\n"
                "system = 'linux'\n"
                "cpu_family = 'aarch64'\n"
                "cpu = 'aarch64'\n"
                "endian = 'little'\n"
                "\n[properties]\n"
                "needs_exe_wrapper = true\n")
        # meson --default-library 取值是 shared/static（sratom G2 实证：
        # true/false 为非法 choice）
        libtype = "shared" if self.options.shared else "static"
        bdir = os.path.join(bld, "build")
        # PATH 前置仅当编译器带目录时追加（W4 P3：防空目录拼接侵入）
        cc_dir = os.path.dirname(cc)
        path_prefix = f'PATH="{cc_dir}:$PATH" ' if cc_dir else ""
        self.run(
            f"{path_prefix}"
            f'PKG_CONFIG_PATH="{gen}" '
            f"meson setup {bdir} {src} --cross-file {cross} "
            "--wrap-mode=nodownload "
            f"--default-library={libtype} "
            "-Dprefix=/ "
            "-Dbindings_py=disabled -Dbindings_cpp=disabled "
            "-Ddocs=disabled -Dhtml=disabled -Dsinglehtml=disabled "
            "-Dtests=disabled -Dlint=false -Dtools=disabled "
            "-Ddynmanifest=disabled",
            env="conanbuild")
        # CI worker 资源紧张时 ninja 首个 spawn 即 EAGAIN（posix_spawn:
        # Resource temporarily unavailable，跨 4 个 worker 同签名实证），
        # 与源码无关；按 -j 4→2→1 逐级限流重试缓解。最终仍失败则原样
        # 抛出最后一次错误——不掩盖真实编译失败。
        last_err = None
        for jobs in (4, 2, 1):
            try:
                self.run(f"meson compile -C {bdir} -j {jobs}", env="conanbuild")
                last_err = None
                break
            except ConanException as exc:
                last_err = exc
                self.output.warning(
                    f"meson compile -j {jobs} failed; retrying with lower "
                    f"parallelism (worker spawn pressure): {exc}")
        if last_err is not None:
            raise last_err
        self.run(f"meson install -C {bdir} --destdir {bld}", env="conanbuild")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # destdir 层级：meson install --destdir 保持 prefix 结构，取最深层
        # 的 include/lib
        for d in ("include", "lib"):
            s = os.path.join(self.build_folder, d)
            if not os.path.isdir(s):
                # 逐级下探 destdir 嵌套（install --destdir 保持相对布局）
                cur = self.build_folder
                for _ in range(5):
                    parts = [p for p in os.listdir(cur)
                             if os.path.isdir(os.path.join(cur, p))
                             and p not in ("build",)]
                    nxt = None
                    for p in parts:
                        cand = os.path.join(cur, p, d)
                        if os.path.isdir(cand):
                            nxt = cand
                            break
                    if nxt:
                        s = nxt
                        break
                    # 深入唯一子目录
                    if len(parts) == 1:
                        cur = os.path.join(cur, parts[0])
                    else:
                        break
            if not os.path.isdir(s):
                # W4 审计 P2：destdir 下探失败必须硬失败，禁止静默空包
                raise ConanException(
                    f"meson destdir layout not resolved: '{d}' not found "
                    f"under {self.build_folder}")
            copy(self, "*", src=s,
                 dst=os.path.join(self.package_folder, d))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lilv-0")
        self.cpp_info.includedirs = ["include/lilv-0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["lilv-0"]
        self.cpp_info.bindirs = []
        # cpp_info 级依赖转发（W4 审计 P2：pkg-config 之外的通道如
        # CMakeDeps 静态链下游需经此拿到 sratom/sord/serd 符号）。
        # 条目必须写成 dep::dep：裸包名会被 conan 当作「本包内部 component」
        # 校验，而本配方未定义 components，package_info() 直接报错
        # （CI #93033 实证）；无 components 的依赖用 dep::dep 引用。
        self.cpp_info.requires = ["sratom::sratom", "sord::sord", "lv2::lv2"]
