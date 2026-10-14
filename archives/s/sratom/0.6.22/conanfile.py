#!/usr/bin/env python3
"""Conan recipe — sratom 0.6.22 (LV2 Atom ↔ Turtle RDF serialisation, meson).

sratom: a small library for serialising LV2 Atoms to/from Turtle RDF.
Upstream is meson-oriented; this recipe drives the cross compiler directly
via a generated cross file (exploration-verified flow, see notes.md)."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
import os

required_conan_version = ">=2.0"


class SratomConan(ConanFile):
    name = "sratom"
    version = "0.6.22"
    description = "sratom: LV2 Atom to/from Turtle RDF serialisation library"
    license = "ISC"
    url = "https://download.drobilla.net/"
    homepage = "https://drobilla.net/software/sratom.html"
    topics = ("lv2", "atom", "turtle", "rdf", "audio")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    # 制品仓依赖（sord 传递钉 serd/0.32.9，勿显式钉 serd 版本——冲突实证见 notes.md）
    requires = ("sord/0.16.22", "lv2/1.18.11-git")
    generators = "PkgConfigDeps"
    exports_sources = None
    no_copy_source = True

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        # 探索期零源码修改（diff -rq 证实），无补丁可导出；G1 门禁要求
        # 显式声明点。
        pass

    def apply_conandata_patches(self):
        # 探索期零源码修改（conandata.yml 无 patches 声明），此为显式
        # 无操作以满足 G1 门禁的补丁应用点检查。
        pass

    def validate(self):
        # OHOS PC 交叉构建目标白名单（R32 口径：Linux/OHOS 兼容族 + armv8；
        # build() 的 cross file 硬编码 aarch64，非 armv8 会产出错误架构）
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sratom supports Linux/OHOS only, got {self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"sratom recipe targets armv8 cross builds, got "
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
        # meson --default-library 取值是 shared/static（G2 实证：'false'
        # 为非法 choice），从 conan 的 bool 选项映射
        shared = "shared" if self.options.shared else "static"
        bdir = os.path.join(bld, "build")
        self.run(
            f'PATH="{os.path.dirname(cc)}:$PATH" '
            f'PKG_CONFIG_PATH="{gen}" '
            f"meson setup {bdir} {src} --cross-file {cross} "
            "--wrap-mode=nodownload "
            # sratom 的 meson_options.txt 无 shared 选项（G2 实证）——
            # 库形态经 --default-library 全局开关表达
            f"--default-library={shared} "
            "-Dprefix=/ "
            "-Ddocs=disabled -Dhtml=disabled -Dsinglehtml=disabled "
            "-Dtests=disabled -Dlint=false",
            env="conanbuild")
        self.run(f"meson compile -C {bdir}", env="conanbuild")
        self.run(f"meson install -C {bdir} --destdir {bld}", env="conanbuild")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for d in ("include", "lib"):
            s = os.path.join(self.build_folder, d)
            if os.path.isdir(s):
                copy(self, "*", src=s,
                     dst=os.path.join(self.package_folder, d))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "sratom-0")
        self.cpp_info.includedirs = ["include/sratom-0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["sratom-0"]
        self.cpp_info.bindirs = []
        # 传递可见性说明：下游（lilv/jalv）均直接声明 sratom+sord+serd+lv2
        # 完整依赖集，无需 cpp_info.requires 转发（带版本号的引用形态非法，
        # G2 实证：package_info 校验直接拒绝）
