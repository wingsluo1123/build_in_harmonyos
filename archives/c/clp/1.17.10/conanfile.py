#!/usr/bin/env python3
"""Conan recipe — Clp (COIN-OR Linear Programming) 1.17.10.

Autotools project. 上游 Depends on coinutils and osi，但两者未发布到制品仓，
本配方不声明依赖（同 klystrack 删 sdl2_image 逻辑），构建时需自带或 CI worker 预装。
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ClpConan(ConanFile):
    name = "clp"
    version = "1.17.10"
    description = "COIN-OR Linear Programming solver"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Clp"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # coinutils/osi 未发布到制品仓，不声明依赖（CI worker 预装或自带源码）
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static; respect the shared option
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.extra_cflags.append("-fPIC")
        tc.extra_cxxflags.append("-fPIC")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E072: autotools 项目需要替换 config.sub/config.guess 以支持 ohos 三元组
        for name in ("config.guess", "config.sub"):
            for root, dirs, files in os.walk(self.source_folder):
                if name in files:
                    path = os.path.join(root, name)
                    replace_in_file(self, path,
                        'Linux|GNU|K\*BSD|NetBSD|OpenBSD|DragonFly|FreeBSD',
                        'Linux|GNU|K\*BSD|NetBSD|OpenBSD|DragonFly|FreeBSD|OHOS')
                    self.output.info(f"patched {name}: {path}")
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp="${TMPDIR:-/tmp}/conan-cs-$$"')
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["Clp"]
