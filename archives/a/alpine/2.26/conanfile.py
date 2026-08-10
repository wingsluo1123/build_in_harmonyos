#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AlpineConan(ConanFile):
    name = "alpine"
    version = "2.26"
    description = "Alpine 邮件客户端（pico 风格终端邮件程序，pico/pilot 工具的继任者）"
    license = "Apache-2.0"
    homepage = "https://alpineapp.email"
    url = "https://alpineapp.email/alpine/release/src/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    # 导出 patches/ 目录（本配方暂无补丁，保留声明以便后续添加）
    exports_sources = "patches/*"

    def requirements(self):
        # alpine 终端界面依赖 wide-char ncurses（ncursesw）；
        # 邮件加密/SSL 依赖 openssl（官方要求 OpenSSL 1.0.0c+）
        self.requires("ncurses/6.4")
        self.requires("openssl/1.1.1w")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        # alpine 的 config.guess 可能无法识别 HarmonyOS，指定 --build/--host 三元组；
        # --disable-shared --enable-static：单二进制可运行（drill 等工具先例）
        tc.configure_args.extend(
            ["--disable-shared", "--enable-static",
             f"--build={triplet}", f"--host={triplet}"])
        tc.generate()
        # 依赖包（ncurses/openssl）的 pkg-config 路径
        from conan.tools.env import Environment
        env = Environment()
        for dep in ("ncurses", "openssl"):
            if dep in self.dependencies:
                env.append_path(
                    "PKG_CONFIG_PATH",
                    os.path.join(self.dependencies[dep].package_folder, "lib", "pkgconfig"),
                )
        env.vars(self).save_script("conanbuild_pkgconfig")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # OHOS 沙箱 umask 077 创建的 0700 目录不可写（config.status 等），
        # 构建前改 umask 022（librrd 先例）
        old = os.umask(0o022)
        try:
            autotools = Autotools(self)
            autotools.configure()
            # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
            autotools.make(args=["-j1"])
        finally:
            os.umask(old)

    def package(self):
        old = os.umask(0o022)
        try:
            autotools = Autotools(self)
            autotools.install()
        finally:
            os.umask(old)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]

    def _machine(self, arch):
        return {"armv8": "aarch64"}.get(str(arch), str(arch))
