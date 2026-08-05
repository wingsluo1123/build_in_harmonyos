#!/usr/bin/env python3
"""Conan recipe for gadap 2.0 — GADAP (Generic Adaptable Data Parser).

GrADS Client Interface for accessing OPeNDAP in-situ data (station data).
Build system: autotools (configure + make). Depends on libdap, libxml2,
curl and libtirpc (libdap's XDR dependency).

License: GPL-2.0-or-later
"""
import io
import os
import ssl
import tarfile
import urllib.request

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
        import shutil
        src = self.source_folder
        sub = os.path.join(src, "gadap-2.0")
        if os.path.isdir(sub):
            for f in os.listdir(sub):
                shutil.move(os.path.join(sub, f), os.path.join(src, f))
            os.rmdir(sub)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        # R33: 编译器必须从 Conan conf 获取，显式传给 configure（CI 环境
        # AutotoolsToolchain 不会自动注入 CC/CXX/CXXFLAGS 到 configure 命令）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        if compilers.get("c"):
            tc.configure_args.append(f"CC={compilers['c']}")
        if compilers.get("cpp"):
            tc.configure_args.append(f"CXX={compilers['cpp']}")
        # CI 上 CXXFLAGS 环境变量未生效，显式注入编译器选项
        cxxflags = []
        if str(self.settings.compiler.libcxx):
            cxxflags.append(f"-stdlib={self.settings.compiler.libcxx}")
        if str(self.settings.compiler.cppstd):
            cxxflags.append(f"-std=c++{self.settings.compiler.cppstd}")
        cxxflags.append(f"-O{'3' if self.settings.build_type == 'Release' else '0'}")
        if cxxflags:
            tc.configure_args.append(f"CXXFLAGS={' '.join(cxxflags)}")
        # libdap/curl/libtirpc 由系统预编译包提供（cmd-pkgs → ~/usr/local）
        pkg_prefix = os.path.expanduser("~/usr/local")
        tirpc_inc = f"-I{pkg_prefix}/include/tirpc"
        xml2_inc = f"-I{pkg_prefix}/include/libxml2"
        tc.extra_cppflags = [tirpc_inc, xml2_inc]
        tc.extra_cflags = [tirpc_inc, xml2_inc]
        tc.extra_cxxflags = [tirpc_inc, xml2_inc]
        tc.generate()
        # 实际设置 PKG_CONFIG_PATH，让 configure 的 dap-config/pkg-config 找到系统预编译包
        self.buildenv_info.prepend_path("PKG_CONFIG_PATH",
                                         f"{pkg_prefix}/lib/pkgconfig")
        self.output.info(f"PKG_CONFIG_PATH={pkg_prefix}/lib/pkgconfig")
        # E002: /tmp 只读 — configure 编译测试程序时 clang 需可写 TMPDIR，
        # CI 干净环境下 TMPDIR 指向只读路径会导致
        # "clang: error: unable to make temporary file: Read-only file system"
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.buildenv_info.define("TMPDIR", tmpdir)
        self.output.info(f"TMPDIR={tmpdir}")

    def _ensure_system_deps(self):
        """Install missing system libraries from cmd-pkgs.

        libdap/curl/libtirpc 无 conan 配方，由 cmd-pkgs 预编译包提供
        （https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs）。CI worker 是
        干净环境，需在此自动安装，否则 configure 报 Cannot find libdap。

        下载完整性由 HTTPS 证书验证（ssl.create_default_context()）保障，
        禁用 TLS 验证会导致供应链投毒风险（P1 已修复）。
        """
        import hashlib
        prefix = os.path.expanduser("~/usr/local")
        bin_dir = os.path.join(prefix, "bin")
        inc_dir = os.path.join(prefix, "include")

        # (probe_file, cmd_pkgs_name, cmd_pkgs_version)
        deps = [
            (os.path.join(bin_dir, "dap-config"), "libdap", "3.21.1"),
            (os.path.join(inc_dir, "tirpc", "rpc", "types.h"), "libtirpc", "1.3.3"),
            (os.path.join(inc_dir, "curl", "curl.h"), "curl", "8.19.0"),
            (os.path.join(inc_dir, "libxml2", "libxml", "xmlwriter.h"), "libxml2", "2.15.3"),
        ]

        def _present(probe):
            return os.path.exists(probe) or os.path.islink(probe)

        missing = [(pkg, ver) for probe, pkg, ver in deps if not _present(probe)]
        if not missing:
            self.output.info("All system dependencies present")
            return

        ctx = ssl.create_default_context()

        for pkg, ver in missing:
            self.output.info(f"Installing {pkg} {ver} from cmd-pkgs...")
            url = (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                f"download/pkgs/{pkg}-{ver}-ohos-aarch64.tar.gz"
            )
            try:
                req = urllib.request.urlopen(url, context=ctx, timeout=120)
                try:
                    data = req.read()
                    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
                    tf.extractall(prefix)
                    tf.close()
                finally:
                    req.close()
                self.output.info(f"  Installed {pkg} {ver} from cmd-pkgs")
            except Exception as e:
                # P2: 依赖安装失败必须终止构建，静默继续会掩盖根因
                raise ConanInvalidConfiguration(
                    f"Failed to install system dependency {pkg} {ver} from cmd-pkgs: {e}")

    def build(self):
        # E002: /tmp 只读 — configure 编译测试程序时 clang 需可写 TMPDIR，
        # CI 干净环境下 TMPDIR 指向只读路径会报
        # "clang: error: unable to make temporary file: Read-only file system"
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        # CI worker 干净环境无 libdap/curl/libtirpc 预编译包，先自动安装
        self._ensure_system_deps()
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
