#!/usr/bin/env python3
"""Conan recipe — spek 0.8.5 (Autotools, headless CLI build)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
import os


class SpekConan(ConanFile):
    name = "spek"
    version = "0.8.5"
    description = "Spek - Acoustic spectrum analyser (headless CLI build)"
    license = "GPL-3.0"
    homepage = "https://www.spek.cc/"
    url = "https://github.com/alexkay/spek"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Headless build: skip wxWidgets GUI
        tc.configure_args.append("--disable-gui")
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # R33: PKG_CONFIG_PATH 必须从环境读取, 不能硬编码本机绝对路径.
        # 系统 FFmpeg 装在 $DEFAULT_PREFIX (CI profile 注入), 其 .pc 文件在
        # $DEFAULT_PREFIX/lib/pkgconfig. 通过 AutotoolsToolchain 的 env 注入,
        # 这样 configure 调用时自动生效 (Conan 2.x 会 source tc.generate()
        # 产生的 conanbuild 脚本).
        default_prefix = os.environ.get("DEFAULT_PREFIX", "")
        if default_prefix:
            pc_dir = os.path.join(default_prefix, "lib", "pkgconfig")
            tc.environment.prepend_path("PKG_CONFIG_PATH", pc_dir)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Regenerate configure from patched configure.ac (patch adds --disable-gui)
        # Use autoconf instead of autoreconf -fi (autopoint not available on CI worker)
        self.run("autoconf", cwd=self.source_folder)
        # E046: HMDFS does not preserve +x on autoconf-generated configure,
        # causing "Permission denied" (exit 126) when Autotools.exec() runs it.
        # chmod every configure we can find in source/build folders.
        import glob
        for pattern in (
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.build_folder, "configure"),
            os.path.join(os.path.dirname(self.build_folder), "configure"),
        ):
            if os.path.exists(pattern):
                os.chmod(pattern, 0o755)
        autotools = Autotools(self)
        # PKG_CONFIG_PATH 已在 generate() 通过 Environment 注入 (R33),
        # 这里只需调用 configure, 不再硬编码本机路径.
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]