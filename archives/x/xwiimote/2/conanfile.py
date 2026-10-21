#!/usr/bin/env python3
"""Conan recipe for xwiimote 2 — Nintendo Wii Remote (wiimote) 访问库与工具.

上游源码包只提供 configure.ac / Makefile.am（无预生成 configure），
因此 build() 先 `mkdir -p m4 && autoreconf -i` 生成 configure，再走 autotools 流程
（不经上游 autogen.sh：它会自行执行 ./configure --enable-debug，与 Conan 参数冲突）。

configure 生成后按 E129 用 sed 把 `umask 077` 放宽为 `umask 022`：HMDFS 对新建目录
强制 setgid，autoconf 的 077 会让 config.status 的临时目录不可写。此处改动对象是
本次现场生成的 configure（非上游产物），属已登记的 R6 例外，可复现。

适配要点：
  - UDEV_* / NCURSES_*：上游 configure.ac 用 PKG_CHECK_MODULES 探测 libudev 与
    ncurses。libudev-zero 的 Conan 包名与其 .pc 模块名（libudev）不一致，ncurses
    也不保证导出模块，故 generate() 按依赖 cpp_info 直接生成 libudev.pc /
    ncurses.pc 写入 generators_folder——AutotoolsToolchain 已把该目录前置进
    PKG_CONFIG_PATH，pkg-config 探测即命中，无需改动上游构建脚本。
  - R33：编译/链接参数全部来自 Conan 依赖信息，不引用裸 shell 变量。
  - R9：make 固定 -j1（沙箱与 CI 上并行 fork 易触发资源限制失败）。

版本号说明：上游 AC_INIT 与 git tag（xwiimote-2）都是单字符版本 "2"，而 Conan 2
的 RecipeReference 模式要求版本至少 2 个字符（`Invalid package version '2'`）。
按仓内既有先例（archives/c/cutmp3/4）做法：任务卡目录保持 `2` 不变，由
set_version() 把产物版本规范为上游主版本的等值点号形式 `2.0`。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _dep_info(dep):
    """取依赖聚合后的 CppInfo（兼容不同 Conan 2.x 小版本）。"""
    aggregated = getattr(dep.cpp_info, "aggregated_components", None)
    return aggregated() if aggregated is not None else dep.cpp_info


def _write_dep_pc(conanfile, module, dep):
    """按依赖 cpp_info 生成 pkg-config 文件（上游 configure.ac 走 PKG_CHECK_MODULES）。

    libudev-zero 的包名与其 pkg-config 模块名（libudev）不一致，ncurses 亦不保证
    导出模块，故此处直接据 cpp_info 生成同名 .pc。写入 generators_folder 后依据
    AutotoolsToolchain 前置的 PKG_CONFIG_PATH 被 pkg-config 找到。
    """
    info = _dep_info(dep)
    cflags = " ".join("-I" + path for path in info.includedirs)
    libdirs = " ".join("-L" + path for path in getattr(info, "libdirs", []))
    libs = " ".join("-l" + lib for lib in info.libs)
    content = "\n".join([
        "prefix={}".format(dep.package_folder or ""),
        "Name: {}".format(module),
        "Description: {} provided by Conan dependency {}".format(module, dep.ref),
        "Version: {}".format(dep.ref.version),
        "Cflags: {}".format(cflags),
        "Libs: {}".format(" ".join(filter(None, [libdirs, libs]))),
        "",
    ])
    save(conanfile, os.path.join(conanfile.generators_folder, module + ".pc"), content)


class XwiimoteConan(ConanFile):
    name = "xwiimote"
    description = "Library and tools for Nintendo Wii Remote (wiimote) devices"
    license = "MIT"
    homepage = "https://github.com/xwiimote/xwiimote"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def set_version(self):
        # 上游版本 "2" 短于 Conan 版本模式最小长度 → 等值规范为主版本点号形式
        self.version = "2.0"

    def _build_triplet(self):
        """构建机三元组（HarmonyOS 上 config.guess 失效，需显式指定）。"""
        arch = {"armv8": "aarch64", "armv7": "arm", "x86_64": "x86_64",
                "x86": "i686"}.get(str(self.settings.arch), "aarch64")
        return "{}-unknown-linux-ohos".format(arch)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # R26/R4：ncurses 与系统同名，必须静态（防止下游 override 成 shared 后污染 /lib）
        self.options["ncurses"].shared = False

    def build_requirements(self):
        # 上游发行包无预生成 configure，build() 需 autoreconf/libtoolize；CI worker
        # 的 PATH 里没有 aclocal/libtoolize，必须由 Conan 注入（手装工具不可见）。
        # autoconf 不声明（OHOS SDK 已提供，声明会拉 OHOS 版 perl 冲突）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # pkgconf 提供 share/aclocal/pkg.m4：上游 configure.ac 用 PKG_CHECK_MODULES，
        # 缺 pkg.m4 时该宏不展开（R33：不靠手装 aclocal 路径）
        self.tool_requires("pkgconf/3.0.6")

    def requirements(self):
        self.requires("libudev-zero/1.0.4")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args += ["--enable-shared", "--disable-static"]
        else:
            tc.configure_args += ["--disable-shared", "--enable-static"]
        if self.settings.os == "OHOS":
            # config.guess 无法识别 HarmonyOS 内核（cannot guess build type），
            # 显式给出构建机三元组；config.sub 已支持 *-linux-ohos 形态
            tc.configure_args.append("--build=" + self._build_triplet())
        for module, dep in (("libudev", self.dependencies["libudev-zero"]),
                            ("ncurses", self.dependencies["ncurses"])):
            _write_dep_pc(self, module, dep)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # 上游发行包未包含预生成 configure，需在源码目录先 autoreconf 生成构建文件
        # （不经 autogen.sh：它会顺带执行 ./configure --enable-debug，与 Conan 参数冲突）
        self.run("mkdir -p m4 && autoreconf -i", cwd=self.source_folder)
        # E129：HMDFS 对新目录强制 setgid，autoconf 的 umask 077 会让 config.status
        # 的临时目录连属主都不可写（subs1.awk: Permission denied）→ 放宽为 022
        self.run("sed -i 's/umask 077/umask 022/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # .la 记录构建机绝对路径与依赖展开信息，属中间产物，不入包
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.settings.os == "OHOS":
            # OHOS 内核只加载带 .codesign 段的 ELF，未签名产物在真机不可用；
            # PR 校验不跑流水线签名，故配方内自签（与仓内 pan/0.165 同范式）
            self._sign_ohos_artifacts()

    @staticmethod
    def _is_elf(path):
        """按魔数判定实体文件是否为 ELF（静态构建下的 lib/*.a 非 ELF，须跳过）。"""
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_artifacts(self):
        """对包内 ELF（bin/* 与 lib/*.so）逐个自签名，缺工具/失败即报错。"""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration(
                "Required OHOS signing tools are missing (binary-sign-tool / readelf)")
        signed = 0
        for subdir in ("bin", "lib"):
            base = os.path.join(self.package_folder, subdir)
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                path = os.path.join(base, name)
                # 符号链接（libxwiimote.so → .so.2 → .so.2.0.0）只签实体文件
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                # 仅签 ELF：静态构建时 lib/ 下是 libxwiimote.a（ar 归档），
                # 送签会失败；与 test_package 的 ELF 判定同款（魔数 0x7fELF）
                if not self._is_elf(path):
                    continue
                self._sign_ohos_elf(path, signer, readelf)
                signed += 1
        if signed == 0:
            raise ConanInvalidConfiguration(
                "no ELF artifact found to sign under bin/ and lib/")

    @staticmethod
    def _sign_ohos_elf(path, signer, readelf):
        output = path + ".signed"
        # 签名工具的输出是新文件（受 umask 影响，实测 0660），os.replace() 会用它的
        # 权限覆盖 install 出来的 0770 原文件——若不恢复，bin/xwiishow 与
        # lib/libxwiimote.so.2.0.0 都会丢可执行位，门禁 L2 报 `no executables`。
        # 先记录签名前权限，替换后显式恢复（设备实测：不恢复即 0660）。
        mode = os.stat(path).st_mode & 0o7777
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, capture_output=True, text=True)
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True).stdout
        if sections.count(".codesign") != 1:
            raise ConanInvalidConfiguration(
                "Signed ELF {} has invalid .codesign count".format(path))
        os.replace(output, path)
        os.chmod(path, mode)

    def package_info(self):
        self.cpp_info.libs = ["xwiimote"]
        # 产物同时包含库与命令行工具 xwiishow（commands.json 已按 tool 声明）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "xwiimote")
        self.cpp_info.set_property("cmake_target_name", "xwiimote::xwiimote")
        self.cpp_info.set_property("pkg_config_name", "libxwiimote")
