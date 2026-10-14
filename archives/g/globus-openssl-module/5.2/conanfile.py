#!/usr/bin/env python3
"""Conan recipe — globus-openssl-module 5.2 (Grid Community Toolkit).

Globus OpenSSL 模块包装库：globus_module_activate(GLOBUS_OPENSSL_MODULE)
时初始化 OpenSSL 并注册 GSI 代理证书相关 OID 与 X509V3 扩展方法
（PROXYCERTINFO / OLD PROXYCERTINFO / 四个代理策略 OID），供 GSI 链上层
库使用。

Build system: autotools (pkg-config based)
Source: Debian pool orig tarball (globus-openssl-module_5.2.orig.tar.gz)

Rules compliance:
  R1:  Minimal configure args (--prefix handled by AutotoolsToolchain)
  R27: 依赖 = configure.ac 闭包：globus-common/18.15 +
       globus-gsi-openssl-error/4.4 + globus-gsi-proxy-ssl/6.6（同链先发包）
       + openssl/3.5.6（仓内主流钉版）
  R32: settings.os validated with in ("Linux", "OHOS")
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, collect_libs, copy, get
from conan.tools.files import export_conandata_patches, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GlobusOpensslModuleConan(ConanFile):
    name = "globus-openssl-module"
    version = "5.2"
    package_type = "library"
    license = "Apache-2.0"
    homepage = "https://github.com/gridcf/gct"
    url = ""  # CI fills this
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # R27: configure.ac 依赖闭包（逐项实核，单 flavor，无 thr/nothr
        # 变体；LT_INIT 仅 [dlopen win32-dll]，无静态 ltdl）：
        #   PACKAGE_DEPS = "globus-common >= 14, globus-gsi-proxy-ssl >= 4,
        #                  globus-gsi-openssl-error >= 2"
        #   PKG_CHECK_MODULES([OPENSSL], [openssl >= 1.0])
        # 源码 include globus_error_openssl.h（gsi-openssl-error）与
        # proxycertinfo.h（gsi-proxy-ssl），与闭包一致。
        self.requires("globus-common/18.15")
        self.requires("globus-gsi-openssl-error/4.4")
        self.requires("globus-gsi-proxy-ssl/6.6")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"globus-openssl-module only supports Linux/OHOS, "
                f"got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )

    @staticmethod
    def _ohos_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }.get(str(arch))
        if triplet is None:
            raise ConanInvalidConfiguration("Unsupported OHOS architecture")
        return triplet

    @staticmethod
    def _build_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }.get(str(arch))
        if triplet is None:
            raise ConanInvalidConfiguration("Unsupported build architecture")
        return triplet

    def generate(self):
        # PkgConfigDeps: 生成 globus-common.pc / globus-gsi-openssl-error.pc /
        # globus-gsi-proxy-ssl.pc / openssl.pc（configure 的 PKG_CHECK_MODULES
        # 对 PACKAGE_DEP 三模块一次解析，需 .pc 进 PKG_CONFIG_PATH）
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Keep build and host distinct（同 globus-common/globus-callout/
            # globus-gsi-openssl-error 先例）
            tc.configure_args.extend(
                [
                    "--build={}".format(
                        self._build_triplet(self.settings_build.arch)
                    ),
                    "--host={}".format(self._ohos_triplet(self.settings.arch)),
                ]
            )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # libtool 2.4.2 .la 陷阱（同 globus-callout 4.3 /
        # globus-gsi-openssl-error 4.4 先例，扩展到三个 globus 依赖）：
        # configure 经 pkg-config 把 -lglobus_common / -lglobus_proxy_ssl /
        # -lglobus_openssl_error 展开进 library/Makefile 的 LIBADD（本包
        # SUBDIRS 仅 library，无 test/ 目标）。-l 形式经 libtool 解析依赖包
        # lib/ 下 .la（dependency_libs 记录无效 libdir）会链接失败——必须在
        # make 之前（Makefile 由 configure 生成后）把三个 globus token 逐一
        # 替换为对应包内 .so 绝对路径，让 libtool 直接链接 .so。openssl 无
        # .la，-lssl/-lcrypto 不动。注意 -lglobus_openssl_error 以
        # -lglobus_openssl 为前缀，按完整 token 替换互不污染。
        _repl = []
        for _dep, _token, _so in (
            ("globus-common", "-lglobus_common", "libglobus_common.so"),
            ("globus-gsi-proxy-ssl", "-lglobus_proxy_ssl",
             "libglobus_proxy_ssl.so"),
            ("globus-gsi-openssl-error", "-lglobus_openssl_error",
             "libglobus_openssl_error.so"),
        ):
            _d = self.dependencies.get(_dep)
            if _d and _d.package_folder:
                _repl.append(
                    (_token, os.path.join(_d.package_folder, "lib", _so)))
        _mf = os.path.join(self.build_folder, "library", "Makefile")
        if os.path.isfile(_mf):
            _c = open(_mf).read()
            for _token, _so_path in _repl:
                _c = _c.replace(_token, _so_path)
            open(_mf, "w").write(_c)
        autotools.make()

    def package(self):
        copy(self, "GLOBUS_LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = [
            lib for lib in libs if "globus_openssl" in lib
        ] or ["globus_openssl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "GlobusOpensslModule")
        self.cpp_info.set_property("cmake_target_name",
                                   "Globus::OpensslModule")
        self.cpp_info.set_property("pkg_config_name",
                                   "globus-openssl-module")
        # 向消费者传递依赖 traits（headers/libs/run）：下游 test_package/
        # 消费者才能继续拿到 globus-common / gsi-openssl-error /
        # gsi-proxy-ssl / openssl 的头文件与库（否则这些依赖在下游图中被
        # 跳过，package_folder 为 None）。格式 pkg::pkg，同
        # globus-gsi-openssl-error 4.4 先例。缺失任一项都会让下游断依赖。
        self.cpp_info.requires = [
            "globus-common::globus-common",
            "globus-gsi-openssl-error::globus-gsi-openssl-error",
            "globus-gsi-proxy-ssl::globus-gsi-proxy-ssl",
            "openssl::openssl",
        ]
        if str(self.settings.os) in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.extend(["pthread", "dl"])
