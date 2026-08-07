#!/usr/bin/env python3
"""Conan recipe for the iftop 1.0pre4 terminal application."""

import os
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IftopConan(ConanFile):
    name = "iftop"
    version = "1.0_pre4"
    description = "Display bandwidth usage on an interface by host"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ex-parrot.com/pdw/iftop/"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _has_pthread_cancel(self):
        """Feature probe for pthread_cancel() (musl/OHOS lacks it).

        R8 compliance: instead of keying the sources off a platform macro, we
        probe whether ``pthread_cancel`` is actually usable and expose the result
        as the feature macro ``HAVE_PTHREAD_CANCEL``. The patched sources branch
        on that macro, matching the stk recipe's ``check_symbol_exists`` approach.
        """
        if self.settings.os == "OHOS":
            # musl-based OHOS libc does not implement pthread_cancel().
            return False
        cc = os.environ.get("CC") or "clang"
        src = (
            "#include <pthread.h>\n"
            "int main(void){ return (int)(long)(void*)pthread_cancel; }\n"
        )
        fd, path = tempfile.mkstemp(suffix=".c")
        try:
            os.write(fd, src.encode())
        finally:
            os.close(fd)
        out = path + ".o"
        try:
            proc = subprocess.run(
                [cc, "-c", path, "-o", out],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
            )
            return proc.returncode == 0
        except Exception:
            # Non-OHOS platforms normally provide pthread_cancel; assume present.
            return True
        finally:
            for p in (path, out):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # 不再硬编码 --build：0001/0002 补丁已让 config.guess 直接输出
        # aarch64-unknown-linux-ohos，config.sub 也不会再把它归一化成
        # linux-gnu-ohos，因此让 autoconf 自行探测真实三元组即可。
        # iftop 的 configure 只在 /usr /usr/local /opt /software 这几个固定
        # 前缀下搜索 pcap.h，必须显式指向 conan 提供的 libpcap 安装根目录，
        # 否则会以 "can't find pcap.h" 终止。
        tc.configure_args.append(
            "--with-libpcap={}".format(self.dependencies["libpcap"].package_folder)
        )
        # R8: 用特性探测结果 (而非平台宏) 控制 pthread_cancel 分支。
        tc.extra_defines.append(
            "HAVE_PTHREAD_CANCEL={}".format(1 if self._has_pthread_cancel() else 0)
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
# OHOS-CI-trigger: re-run build @ 2026-08-02 21:12 (no functional change)
