#!/usr/bin/env python3
"""Conan recipe for lksctp-tools 1.0.21 (SCTP user-space library + tools).

- Autotools build (configure + make).
- OHOS adaptation: E091 guard for linux/socket.h vs musl sys/socket.h
  sockaddr_storage redefinition (patch 0012), and upstream func_tests
  include fixes (0001-0011).
- GitHub archive tarball ships no `configure`, so build() runs
  `autoreconf -fi` (via Autotools.autoreconf) when needed; the build host
  lacks automake/aclocal/libtoolize, so they are pulled in as tool_requires
  (same approach as argp-standalone). E114: drop `umask 077` from the
  generated configure (HMDFS UID mapping makes 0700 tmp dirs unwritable).
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LksctpToolsConan(ConanFile):
    name = "lksctp-tools"
    version = "1.0.21"
    description = "lksctp-tools 1.0.21: SCTP user-space tools and libsctp"
    license = "LGPL-2.1-or-later"
    homepage = "http://www.sctp.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # GitHub archive tarball ships no configure -> autoreconf 自举。
        # tool_requires 用 **build profile** 解析（同 argp-standalone）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess 不认识 HarmonyOS（uname -s=HarmonyOS 猜不出 build type），
        # 必须显式指定 build/host triplet（同 argp-standalone / abiword 系列）。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # libsctp 库本身不依赖内核 SCTP 可用性；func_tests 需内核 SCTP
        # 模块（OHOS 无则 Protocol not supported），且产物目标是库，
        # 故关闭测试编译，测试由 test_package 消费者验证承载。
        tc.configure_args.append("--disable-tests")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub archive tarball 从不含 configure（configure 是 autoreconf
        # 产物、不进版本库），此时必须先自举。
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # E114: umask 077 -> 022（HMDFS UID 映射导致 0700 临时目录不可写）；
        # 必须放在 autoreconf 之后，否则自举会覆盖改动。
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sctp"]