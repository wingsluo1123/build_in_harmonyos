#!/usr/bin/env python3
"""Conan recipe template — CMake projects.

Usage: Replace Aptpkg, apt-pkg, 2.7.14, apt-pkg 2.7.14, MIT,
       Fill in requires() and cpp_info.libs as needed.

This template enforces R26: BUILD_SHARED_LIBS=OFF for system-name libraries.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps


def _find_ohos_native_sdk():
    """Locate the OHOS native SDK root that ships the libc++ headers/libs.

    The OHOS clang (aarch64-unknown-linux-ohos) uses a sysroot without the
    C++ standard library headers, so CXXFLAGS need
      -isystem <sdk>/include/libcxx-ohos/include/c++/v1
    and the linker needs
      -L<sdk>/lib/aarch64-linux-ohos
    to resolve the libc++ runtime.  Same convention as libffado.
    """
    candidates = []
    for var in ("OHOS_NATIVE_SDK", "OHOS_SDK_ROOT", "OHOS_NDK_HOME", "OHOS_SDK"):
        if os.environ.get(var):
            candidates.append(os.path.join(os.environ[var], "native"))
    candidates.append("/storage/Users/currentUser/ohos-sdk")
    candidates.extend(sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native")))
    for c in candidates:
        # 兼容两种 SDK 布局：扁平（<sdk>/include/libcxx-ohos/...，本地）与
        # CI worker 的 llvm 嵌套（<sdk>/llvm/include/libcxx-ohos/...）。
        for sdk in (c, os.path.join(c, "llvm")):
            if os.path.isdir(os.path.join(sdk, "include", "libcxx-ohos", "include", "c++", "v1")):
                return sdk
    return None


class AptpkgConan(ConanFile):
    name = "apt-pkg"
    version = "2.7.14"
    description = "apt-pkg 2.7.14"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libdb/5.3.35")
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")
        self.requires("liblzma/5.8.1")
        self.requires("lz4/1.9.4")
        self.requires("libgcrypt/1.11.0")
        self.requires("xxhash/0.8.2")
        self.requires("libzstd/1.5.7")
        self.requires("gnutls/3.8.10")
        self.requires("systemd/261")
        self.requires("libseccomp/2.5.5")
        self.requires("eudev/3.2.14")

    def build_requirements(self):
        # apt CMake 硬性 find_program(TRIEHASH) / find_package(Perl)，
        # 构建期工具放 tool_requires（不入运行期依赖图）
        self.tool_requires("triehash/0.3.1")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # apt 的 CMake/Find*.cmake 全部走 pkg_check_modules(liblzma/libzstd/
        # libsystemd/libseccomp/libgcrypt/libxxhash/libudev/libgcrypt...)，
        # 必须生成 conan 依赖的 .pc 并注入 PKG_CONFIG_PATH
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS/musl 无 gettext/libintl（ohpcd 未发布 gettext），apt 的
        # NLS 仅影响 po/ 翻译消息，对静态库运行期无影响。关闭可避免
        # find_package(Intl REQUIRED) 找不到 libintl 而 configure 失败。
        tc.variables["USE_NLS"] = "OFF"
        # OHOS 无 docbook-xsl 样式表（host 侧工具），且文档对库运行期无用；
        # WITH_DOC=OFF 会经 cmake_dependent_option 级联关闭 manpages/guides/
        # doxygen/examples，避免 doc/CMakeLists 引入 Documentation.cmake 后
        # 因找不到 docbook xsl 而 FATAL_ERROR。
        tc.variables["WITH_DOC"] = "OFF"
        # Add project-specific CMake variables here:
        # tc.variables["ENABLE_FOO"] = "ON"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        tc.variables["WITH_TESTS"] = "OFF"

        # OHOS libc++ SDK: 头文件与运行库不在编译器 sysroot，必须显式注入。
        sdk = _find_ohos_native_sdk()
        if not sdk:
            raise ConanInvalidConfiguration(
                "OHOS native SDK (libcxx-ohos headers) not found; set "
                "OHOS_NATIVE_SDK/OHOS_SDK_ROOT or install the SDK (see notes.md)")
        cxx_inc = os.path.join(sdk, "include", "libcxx-ohos", "include", "c++", "v1")
        sdk_lib = os.path.join(sdk, "lib", "aarch64-linux-ohos")
        tc.extra_cxxflags.append(f"-isystem {cxx_inc}")
        tc.extra_sharedlinkflags.append(f"-L{sdk_lib}")
        tc.extra_exelinkflags.append(f"-L{sdk_lib}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["apt-pkg"]
