#!/usr/bin/env python3
"""Conan recipe — ncurses 6.4 (Autotools, static lib for OHOS)."""
import os
import tempfile
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.4"
    license = "X11"
    author = "Thomas E. Dickey"
    url = "https://invisible-island.net/ncurses/"
    homepage = "https://invisible-island.net/ncurses/"
    description = "System V release 4.0 curses emulation library"
    topics = ("curses", "terminal", "tui")
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "widec": [True, False]}
    default_options = {"shared": False, "fPIC": True, "widec": True}
    # AutotoolsToolchain 不放 generators attribute（generate() 内实例化，conan 2.x 不允许两者并存）
    # 不设 no_copy_source: patches 目录需拷到 source cache 让 apply_conandata_patches 找到

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def validate(self):
        # R32 平台兼容性检查（统模式：先 OS 后 arch）
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(f"ncurses {self.version} only supports OHOS, got os={self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(f"ncurses {self.version} only supports armv8, got arch={self.settings.arch}")
        # 必须静态编译，共享库会劫持系统 libncursesw.so.6 导致 zsh 崩溃
        if self.options.shared:
            raise ConanInvalidConfiguration("ncurses must be static (--without-shared), shared lib hijacks system libncursesw.so.6")
        if not self.options.widec:
            raise ConanInvalidConfiguration("ncurses must compile with widec=True for OHOS (readline/bash require wide character support)")

    def source(self):
        # 显式按版本取 sources，避免 ** 解包把版本号当 kwarg
        src = self.conan_data["sources"][str(self.version)]
        get(self, **src, strip_root=True)
        # 手动把 patches/ 从 recipe folder 拷到 source folder（绕 conan 2.x patches 怪异）
        patches_src = os.path.join(self.recipe_folder, "patches")
        patches_dst = os.path.join(self.source_folder, "patches")
        os.makedirs(patches_dst, exist_ok=True)
        if os.path.isdir(patches_src):
            for pf in os.listdir(patches_src):
                copy(self, pf, src=patches_src, dst=patches_dst)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS 适配 configure options（按 archives/n/ncurses/6.4/manifest.yaml）
        tc.configure_args.append("--without-shared")
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--without-debug")
        tc.configure_args.append("--without-ada")
        tc.configure_args.append("--without-manpages")
        tc.configure_args.append("--without-tests")
        tc.configure_args.append("--without-cxx-binding")
        if self.options.widec:
            tc.configure_args.append("--enable-widec")
        # 头文件安装到顶层 include/ 而非 include/ncursesw/（aamath/catgirl 同实践）
        tc.configure_args.append("--enable-overwrite")
        tc.generate()

    def build(self):
        # 手动应用 patch（绕 conan 2.x apply_conandata_patches cache 查找问题）
        patch_file = os.path.join(self.source_folder, "patches", "0001-port-for-ohos.patch")
        if os.path.exists(patch_file):
            ret = self.run(f"patch -p1 < \"{patch_file}\"", cwd=self.source_folder, shell=True)
            if ret != 0:
                raise ConanException(f"patch 0001-port-for-ohos failed with exit code {ret}")
        # HMDFS 不允许 cwd 写临时文件，给 configure 提供 TMPDIR
        with tempfile.TemporaryDirectory() as tmpdir:
            bash = os.environ.get("CONFIG_SHELL", "bash")
            configure = os.path.join(self.source_folder, "configure")
            # ncurses 6.4 老 autotools (2022 config.guess) �猜不出 OHOS aarch64，显式传 build/host
            ret = self.run(f"TMPDIR={tmpdir} {bash} {configure} --prefix={self.package_folder} --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu",
                         cwd=self.source_folder, shell=True)
            if ret != 0:
                raise ConanException(f"configure failed with exit code {ret}")
            ret = self.run(f"make -j$(nproc) TMPDIR={tmpdir}", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"make failed with exit code {ret}")

    def package(self):
        ret = self.run(f"make install DESTDIR= TMPDIR=/tmp", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"make install failed with exit code {ret}")
        # 确认 4 个静态库已安装
        for lib in ("libncursesw.a", "libpanelw.a", "libmenuw.a", "libformw.a"):
            if not os.path.exists(os.path.join(self.package_folder, "lib", lib)):
                raise ConanException(f"expected static lib {lib} not found in package")

    def package_info(self):
        # 上游提供 4 个静态库，主库是 libncursesw（widec 版本）
        self.cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
