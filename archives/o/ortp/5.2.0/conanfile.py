#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ortp/5.2.0 — oRTP 实时传输协议库（OpenHarmony PC / aarch64 适配配方）

上游:    https://gitlab.linphone.org/BC/public/ortp
镜像:    https://github.com/BelledonneCommunications/ortp（官方 GitHub
         镜像，tag 归档与 gitlab 字节一致，sha256 相同）

包内容: libortp（RFC 3550 RTP 协议栈：会话/ payload/ jitter buffer/
         事件/ 统计，ORTP_PUBLIC API）

适配要点（完整说明见 notes.md 与父目录 README「OHOS 适配」）:
  1. CMake 版本：上游 cmake_minimum_required 3.1 与 CMake 4.x 不兼容
     → patches/0001 提升 3.5（沿用 2026-05 真机预构建已验证的补丁）。
  2. CMSG_NXTHDR：rtpsession_inet.c 触发 clang 类型比较告警，STRICT
     下 -Werror 失败 → 0001 补丁追加 -Wno-error=sign-compare，同时
     ENABLE_STRICT=OFF 双保险。
  3. 测试程序：src/tests 为 rtp 收发工具（mrtpsend/mrtprecv 等，依赖
     网络/设备），ENABLE_TESTS=OFF 不构建。独立 tester/ 有 1 个
     FEC 用例，启用完整 ortp_tester 并通过已发布的
     bctoolbox-tester/BCUnit 框架执行，消费测试另计。
  4. 文档：ENABLE_DOC=OFF（无 doxygen）。
  5. bctoolbox：find_package(bctoolbox 0.2.0 REQUIRED)，由 registry
     已发布的 bctoolbox/5.3.115 满足（5.3.115 >= 0.2.0，CMake
     config-version AnyNewerVersion 兼容）。
"""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rmdir)

import os
import shlex

required_conan_version = ">=2.0"


class OrtpConan(ConanFile):
    name = "ortp"
    version = "5.2.0"
    description = ("oRTP: RTP protocol library (RFC 3550) - sessions, "
                   "payloads, jitter buffer, events and statistics")
    license = "AGPL-3.0-or-commercial"
    homepage = "https://www.linphone.org/technical-corner/ortp"
    url = "https://gitlab.linphone.org/BC/public/ortp"
    topics = ("rtp", "rtc", "multimedia", "linphone")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/**"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # 上游 CMakeLists: find_package(bctoolbox 0.2.0 REQUIRED)
        self.requires("bctoolbox/5.3.115")

    def build_requirements(self):
        self.test_requires("bcunit/5.3.113")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # 上游 find_package(bctoolbox 0.2.0 REQUIRED) 会被 Conan 默认的
        # SameNewerVersion 兼容策略拒绝（5.3.115 的 major 与 0.2.0 不同，
        # 真机实测报 "not compatible with requested version 0.2.0"）。
        # bctoolbox 的 Conan 配方对 BCUnit 用同一修法，此处对等处理。
        deps.set_property("bctoolbox", "cmake_config_version_compat", "AnyNewerVersion")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["ENABLE_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["ENABLE_DOC"] = "OFF"
        # src/tests 为 RTP 收发工具；tester/ 另有 1 个 FEC 用例。
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_UNIT_TESTS"] = "ON"
        dep = self.dependencies["bctoolbox"]
        tester_library = None
        for libdir in dep.cpp_info.libdirs:
            for suffix in (".a", ".so"):
                candidate = os.path.join(dep.package_folder, libdir, "libbctoolbox-tester" + suffix)
                if os.path.isfile(candidate):
                    tester_library = candidate
                    break
            if tester_library:
                break
        if not tester_library:
            raise ConanInvalidConfiguration("Published bctoolbox package lacks its tester library")
        tc.variables["BCTOOLBOX_TESTER_LIBRARY"] = tester_library
        tc.variables["BCTOOLBOX_TESTER_INCLUDE_DIRS"] = ";".join(
            os.path.join(dep.package_folder, path) for path in dep.cpp_info.includedirs
        )
        # CMSG_NXTHDR 告警双保险（0001 补丁已加 -Wno-error=sign-compare）
        tc.variables["ENABLE_STRICT"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        tester = os.path.join(self.build_folder, "tester", "ortp_tester")
        if not os.path.isfile(tester):
            raise ConanInvalidConfiguration("The original upstream ortp_tester was not built")
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "src"))
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, libdir))
        with env.vars(self).apply():
            self.run(shlex.quote(tester), cwd=os.path.dirname(tester))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The upstream tester is executed in build(), not a public CLI.
        rmdir(self, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ortp")
        self.cpp_info.set_property("cmake_target_name", "ortp::ortp")
        self.cpp_info.set_property("pkg_config_name", "ortp")
        self.cpp_info.libs = ["ortp"]
        self.cpp_info.requires = ["bctoolbox::bctoolbox"]
