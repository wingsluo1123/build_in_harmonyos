#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
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
        # alpine 终端界面依赖 wide-char ncurses（ncursesw，6.5 已合入 registry）；
        # 邮件加密/SSL 依赖 openssl（官方要求 OpenSSL 1.0.0c+）
        self.requires("ncurses/6.5")
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
        # configure 的 dlopen 检查（AC_SEARCH_LIBS dlopen——CI #21996 报
        # No library containing dlopen found）——LIBS=-ldl 让检查找到
        # libdl.so（OHOS 的 dlopen 在 libdl——bionic）
        env = Environment()
        env.append("LIBS", "-ldl")
        env.vars(self).save_script("conanbuild_ldl")
        # configure 的 terminfo 检查（setupterm in -lncurses 等 -l 链接测试）
        # 需要 -L ncurses 包 lib 路径（CI #17674 报 Terminfo/termcap not found）——
        # LDFLAGS/CFLAGS 指向 ncurses 包（configure 链接测试继承）。
        # 注意：AutotoolsToolchain 无 extra_cppflags 属性（CI #21036 实测
        # AttributeError——与 fizmo #20735 相同），改用 extra_cflags
        ncurses = self.dependencies["ncurses"]
        tc.extra_ldflags.append(f"-L{os.path.join(ncurses.package_folder, 'lib')}")
        tc.extra_cflags.append(f"-I{os.path.join(ncurses.package_folder, 'include')}")
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
        # 显式应用 0001-configure-ncursesw.patch（multitail 教训：必须显式
        # 调用 apply_conandata_patches——否则补丁不会被应用）
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

    def build(self):
        # OHOS 沙箱 umask 077 创建的 0700 目录不可写（config.status 等），
        # 构建前改 umask 022（librrd 先例）
        old = os.umask(0o022)
        try:
            autotools = Autotools(self)
            # env 显式激活 conanbuild_ldl（LIBS=-ldl——dlopen 检查——
            # CI #21996 重复失败：save_script 的独立脚本需 env 列表显式
            # 激活——multitail 教训）
            autotools.configure(env=["conanbuild", "conanbuild_ldl"])
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
