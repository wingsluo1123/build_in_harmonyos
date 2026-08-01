#!/usr/bin/env python3
"""Conan recipe — ncurses 6.4 (Autotools, static lib for OHOS)."""
import os
import tempfile
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
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
    generators = "AutotoolsToolchain"
    no_copy_source = True

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

    def source(self):
        # 显式按版本取 sources，避免 ** 解包把版本号当 kwarg
        src = self.conan_data["sources"][str(self.version)]
        get(self, **src, strip_root=True)

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
        apply_conandata_patches(self)
        # HMDFS 不允许 cwd 写临时文件，给 configure 提供 TMPDIR
        with tempfile.TemporaryDirectory() as tmpdir:
            bash = os.environ.get("CONFIG_SHELL", "bash")
            configure = os.path.join(self.source_folder, "configure")
            ret = self.run(f"TMPDIR={tmpdir} {bash} {configure} --prefix={self.package_folder}",
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
