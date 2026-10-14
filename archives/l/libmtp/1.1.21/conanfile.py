#!/usr/bin/env python3
"""Conan recipe — libmtp 1.1.21 (Library for accessing MTP devices).

W0b 历史核验（2026-09-30）：archives/l/libmtp/1.1.21 旧格式条目（hints/notes）
记录了 2026-05-26 真机整链成功的适配经验，本配方按现行 Conan 框架重建：

  * 依赖唯一：libusb-1.0（configure.ac:116 PKG_CHECK_MODULES(LIBUSB,
    libusb-1.0 >= 1.0.0)）。归档配方 l/libusb/1.0.27 已定义
    pkg_config_name="libusb-1.0"（conanfile.py:209），PkgConfigDeps 可直接
    生成 libusb-1.0.pc → configure 的 pkg-config 探测能真实解析。
  * 可选依赖 libgcrypt 仅服务 MTPZ（Zune 设备），--disable-mtpz 显式关闭
    （termrec curl/--disable-mad 同款降级先例）。
  * configure.ac 无 AC_CANONICAL_HOST，但 libtool 在 configure:4676 无条件调
    config.guess，2021 版不认 uname=HarmonyOS（真机首验 D4：cannot guess
    build type）→ 显式 --build/--host=aarch64-unknown-linux-gnu
    （termrec §12.1 同款）。
  * USE_LINUX 由编译期探测 __linux__ 判定（configure.ac:86-96，OHOS clang
    定义 __linux__ → true）→ udev 规则/mtp-probe 会被构建并安装到绝对路径
    @UDEV@（默认 /usr/lib/udev，旧条目实机记录"只读文件系统安装失败"）。
    用 --with-udev="${prefix}/lib/udev" 重定向进包内（make 展开 ${prefix}
    为安装前缀，零补丁解决）。
  * E011: configure:18485 ``(umask 077 && mktemp -d "./confXXXXXX")`` ——
    HMDFS 上 077 去掉 group 写位后目录不可写（libfuse/termrec 同类），
    build() 内联 sed umask 077→022。
  * E386: SHELL=/bin/sh + unset CONFIG_SHELL（termrec §12.38① 先例）。
  * 唯一真补丁：examples/pathutils.c:138 rindex()——musl/OHOS 无此 legacy
    函数（旧条目 0003 补丁同问题，本补丁直接改用标准 strrchr）。
    旧条目 0001/0002（config.guess/sub 更新）由显式三元组绕开，不再需要；
    0004（.pc 修正）/0005（gphoto2-endian 注释）在 Conan 流程下由
    configure 自动生成/前缀替换覆盖，不再需要（见 notes.md）。
  * 上游零测试（全部 Makefile.am 无 check_PROGRAMS/TESTS）→ 依
    TEST_QUALITY_SPEC 由 test_package 补充消费者测试。
  * R9: make -j1（Autotools.make 默认非并行）。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibmtpConan(ConanFile):
    name = "libmtp"
    version = "1.1.21"
    description = "Library for accessing MTP (Media Transfer Protocol) devices"
    license = "LGPL-2.1-or-later"
    homepage = "https://libmtp.sourceforge.io"
    url = "https://github.com/libmtp/libmtp"
    topics = ("mtp", "usb", "media-transfer", "android")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # configure.ac:116 PKG_CHECK_MODULES(LIBUSB, libusb-1.0 >= 1.0.0)
        self.requires("libusb/1.0.27")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported (libusb-1.0 backend needs Linux-compatible USB stack)")
        libusb_version = str(self.dependencies["libusb"].ref.version)
        if not libusb_version.startswith("1.0"):
            raise ConanInvalidConfiguration(
                f"libmtp 1.1.21 needs libusb-1.0 backend (>= 1.0.0), got {libusb_version}")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        # 链接闭包：聚合 libusb 及其传递依赖
        AutotoolsDeps(self).generate()
        # libusb-1.0.pc：libusb 配方 pkg_config_name 属性自动生成
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # R1 参数最少化；MTPZ 仅服务 Zune 设备，显式关闭避免引入 libgcrypt
        tc.configure_args.append("--disable-mtpz")
        # 库形态（libusb/1.0.27 同款参数）
        tc.configure_args.append(
            "--enable-shared" if self.options.shared else "--disable-shared")
        tc.configure_args.append(
            "--disable-static" if self.options.shared else "--enable-static")
        # udev 规则与 mtp-probe 默认装到绝对路径 /usr/lib/udev（旧条目实机
        # 记录只读文件系统失败）——重定向进安装前缀，make 展开 ${prefix}
        tc.configure_args.append('--with-udev=${prefix}/lib/udev')
        # PKG_CHECK_MODULES 需要 pkg-config 真实解析 libusb-1.0 模块
        # （mtpfs 先例：conanbuild 不会自动注入 PKG_CONFIG_PATH）
        tc.configure_args.append(f"PKG_CONFIG_PATH={self.generators_folder}")
        # D4（真机首验）：libtool 在 configure:4676 无条件调 config.guess，
        # 2021 版不认 uname=HarmonyOS → 显式三元组（termrec §12.1 同款；
        # 交付目标 OHOS aarch64）
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        env = tc.environment()
        # E386 (termrec §12.38①)：SDK bash getcwd 在 HMDFS 构建目录失败
        env.unset("CONFIG_SHELL")
        env.define("SHELL", "/bin/sh")
        # D3（真机首验）：OHOS musl 忽略 DT_RUNPATH，configure 的 conftest
        # 运行期找不到 libusb-1.0.so.0（errno 127 伪装成 "cannot run C
        # compiled programs"）→ 依赖包 libdirs 注入 LD_LIBRARY_PATH
        # （termrec §12.38③ 同款）
        for _, dep in self.dependencies.host.items():
            for d in dep.cpp_info.libdirs:
                path = d if os.path.isabs(d) else os.path.join(
                    dep.package_folder, d)
                env.prepend_path("LD_LIBRARY_PATH", path)
        tc.generate(env=env)

    def build(self):
        # E011: configure:18485 "umask 077 && mktemp -d" 在 HMDFS 产生
        # 不可写临时目录；sed 成 022（libfuse/mtpfs 同款内联先例）
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            replace_in_file(self, configure, "umask 077", "umask 022",
                            strict=False)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()  # R9: -j1

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool .la 不参与 conan 消费（下游走 cpp_info/AutotoolsDeps）
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        # OHOS 共享库需自签名才能被加载（libusb/1.0.27 同款）
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.warning("binary-sign-tool not found, skip signing")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            subprocess.run([objcopy, "--remove-section", ".codesign", so],
                           check=False)
            signed = so + ".signed"
            subprocess.run([signer, "sign", "-inFile", so, "-outFile", signed,
                            "-selfSign", "1"], check=True)
            os.replace(signed, so)

    def package_info(self):
        self.cpp_info.libs = ["mtp"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # examples/ 17 个 mtp-* CLI 工具随上游默认安装（bin_PROGRAMS）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libmtp")
        # libmtp 无 pthread 依赖（configure.ac 无 ACX_PTHREAD，源码单线程）
