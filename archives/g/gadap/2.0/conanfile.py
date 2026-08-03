#!/usr/bin/env python3
"""Conan recipe for gadap 2.0 — GADAP (Generic Adaptable Data Parser).

GrADS Client Interface for accessing OPeNDAP in-situ data (station data).
Build system: autotools (configure + make). Depends on libdap, libxml2,
curl and libtirpc (libdap's XDR dependency).

License: GPL-2.0-or-later
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GadapConan(ConanFile):
    name = "gadap"
    version = "2.0"
    description = "GADAP: GrADS Client Interface for OPeNDAP in-situ data"
    license = "GPL-2.0-or-later"
    homepage = "http://cola.gmu.edu/grads/"
    url = "https://salsa.debian.org/science-team/gadap"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libdap/curl/libtirpc 未发布到制品仓（无 conan 配方），由系统预编译包
        # 提供（cmd-pkgs，安装于 ~/usr/local）；仅 libxml2 已发布。
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: platform check uses in ("Linux", "OHOS"), never == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gadap requires Linux or OHOS, got {self.settings.os}")

    def source(self):
        # strip_root 对带 "./gadap-2.0/" 前缀的 tar 条目不生效（OHOS conan 2.29），
        # 手动剥离顶层目录，使源码直接落在 source_folder，补丁路径才能命中。
        get(self, **self.conan_data["sources"])
        import os
        import shutil
        src = self.source_folder
        sub = os.path.join(src, "gadap-2.0")
        if os.path.isdir(sub):
            for f in os.listdir(sub):
                shutil.move(os.path.join(sub, f), os.path.join(src, f))
            os.rmdir(sub)

    def generate(self):
        import os
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # libdap/curl/libtirpc 由系统预编译包提供（cmd-pkgs → ~/usr/local）
        pkg_prefix = os.path.expanduser("~/usr/local")
        tc.extra_cppflags = [f"-I{pkg_prefix}/include/tirpc"]
        tc.extra_cflags = [f"-I{pkg_prefix}/include/libxml2"]
        tc.extra_cxxflags = [f"-I{pkg_prefix}/include/libxml2"]
        tc.generate()
        # 让 configure 的 dap-config/pkg-config 找到系统预编译包
        self.output.info(f"PKG_CONFIG_PATH={pkg_prefix}/lib/pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gadap"]
        self.cpp_info.requires = ["libxml2::libxml2"]
        # libdap/curl/libtirpc 无 conan 配方，由系统预编译包提供（cmd-pkgs → ~/usr/local）
        import os
        prefix = os.path.expanduser("~/usr/local")
        self.cpp_info.system_libs = ["dap", "dapserver", "dapclient", "curl", "tirpc"]
        link_flags = [f"-L{prefix}/lib64", f"-L{prefix}/lib"]
        self.cpp_info.exelinkflags = link_flags
        self.cpp_info.sharedlinkflags = link_flags
        # 运行期：系统预编译包位于 ~/usr/local/lib，需加入 LD_LIBRARY_PATH
        for libdir in ("lib64", "lib"):
            p = os.path.join(prefix, libdir)
            if os.path.isdir(p):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", p)
