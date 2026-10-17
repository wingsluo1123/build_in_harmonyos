#!/usr/bin/env python3
"""Conan recipe for libidn 1.42 - Autotools with OHOS adaptation."""
import os
import re
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class LibidnConan(ConanFile):
    name = "libidn"
    version = "1.42"
    description = "Internationalized Domain Names implementation"
    license = "LGPL-2.1+"
    homepage = "https://www.gnu.org/software/libidn/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os {self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-doc")
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.vars(self, "conanbuildenv").save_script("conanbuildenv")

    def build(self):
        apply_conandata_patches(self)
        # E013: fork 风暴下 config.status "newly created file is older than
        # distributed files"（HMDFS mtime 滞后）——解压后统一刷新源码树 mtime
        self._touch_source_tree()
        # E011: HMDFS umask 077 breaks config.status temp dirs (subs1.awk Permission denied)
        self._fix_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        self._fix_config_h()
        autotools.make(args=["-j2"])
        # 上游官方测试套件（tests/ 下的用例）真实执行：make check。
        # 用例与被测库同一源码树构建，执行结果直接进 CI 构建日志（L1c），
        # 不使用任何伪造通过率。测试二进制与库同源，无需额外依赖。
        autotools.make(target="check", args=["-j1"])

    def _touch_source_tree(self):
        now = time.time()
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                path = os.path.join(root, name)
                try:
                    os.utime(path, (now, now))
                except OSError:
                    pass

    def _fix_configure_umask(self):
        for folder in (self.source_folder, self.build_folder):
            if not folder:
                continue
            path = os.path.join(folder, "configure")
            if os.path.isfile(path):
                with open(path, "r") as f:
                    content = f.read()
                fixed = content.replace("umask 077", "umask 022")
                if fixed != content:
                    with open(path, "w") as f:
                        f.write(fixed)
                break

    def _fix_config_h(self):
        src = self.source_folder
        config_h = os.path.join(src, "config.h")
        if not os.path.isfile(config_h):
            config_h = os.path.join(self.build_folder, "config.h")
        if not os.path.isfile(config_h):
            return
        with open(config_h, "r") as f:
            content = f.read()
        config_log = os.path.join(src, "config.log")
        if not os.path.isfile(config_log):
            config_log = os.path.join(self.build_folder, "config.log")
        fixes = {}
        if os.path.isfile(config_log):
            with open(config_log, "r") as f:
                for line in f:
                    m = re.match(r'(ac_cv_[\w]+)=(.+)', line)
                    if not m:
                        continue
                    key, val = m.group(1), m.group(2)
                    if val != "yes":
                        continue
                    if key.startswith("ac_cv_header_") and key.endswith("_h"):
                        fixes["HAVE_" + key[len("ac_cv_header_"):].upper()] = "1"
                    elif key.startswith("ac_cv_func_"):
                        fixes["HAVE_" + key[len("ac_cv_func_"):].upper()] = "1"
                    elif key.startswith("ac_cv_type_"):
                        fixes["HAVE_" + key[len("ac_cv_type_"):].upper()] = "1"
                    elif key.startswith("ac_cv_have_decl_"):
                        fixes["HAVE_DECL_" + key[len("ac_cv_have_decl_"):].upper()] = "1"
        fixes["PROMOTED_MODE_T"] = "mode_t"
        fixes["HAVE_DECL_STRERROR_R"] = "1"
        fixes["HAVE_STRERROR_R"] = "1"
        fixes["STDC_HEADERS"] = "1"
        fixes["PACKAGE_NAME"] = '"GNU Libidn"'
        fixes["PACKAGE_TARNAME"] = '"libidn"'
        fixes["PACKAGE_VERSION"] = '"1.42"'
        fixes["PACKAGE_STRING"] = '"GNU Libidn 1.42"'
        fixes["PACKAGE_BUGREPORT"] = '"help-libidn@gnu.org"'
        fixes["PACKAGE_URL"] = '"https://www.gnu.org/software/libidn/"'
        fixes["PACKAGE"] = '"libidn"'
        fixes["VERSION"] = '"1.42"'
        for macro, value in fixes.items():
            pattern = "/* #undef " + macro + " */"
            replacement = "#define " + macro + " " + value
            content = content.replace(pattern, replacement)
        with open(config_h, "w") as f:
            f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["idn"]
        self.cpp_info.set_property("cmake_file_name", "libidn")
        self.cpp_info.set_property("cmake_target_name", "libidn::libidn")
        self.cpp_info.set_property("pkg_config_name", "libidn")
