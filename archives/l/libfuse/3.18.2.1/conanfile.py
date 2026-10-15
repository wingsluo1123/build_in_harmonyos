#!/usr/bin/env python3
"""Conan recipe for libfuse (fuse3) 3.18.2 — OHOS-ready.

Build system: Meson
Upstream: https://github.com/libfuse/libfuse
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
import os


class LibfuseConan(ConanFile):
    name = "libfuse"
    # ★ 本版本**只为发布 shared 变体**而存在：上游源码、补丁与 3.18.2 完全相同，
    #   唯一差别是 default_options.shared=True。原因：ohpcd 上 3.18.2 已发布的
    #   制品只有**静态**变体（package_id 21b17f8b…，shared=False），而 saunafs
    #   需要 shared=True 的 0726937e…；conan 的兼容性回退只放宽 settings、**不放宽
    #   options**，所以这个变体只能由一个新版本号带出来（R37 亦要求换版本号）。
    #   详见 notes.md 与 PR 正文。
    version = "3.18.2.1"
    description = "libfuse — Filesystem in Userspace (fuse3)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libfuse/libfuse"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # 与 3.18.2 的唯一差异：默认产出**动态库**（消费方如 saunafs 要求 shared=True）
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os not in ("Linux", "FreeBSD", "OHOS"):
            raise ConanInvalidConfiguration("libfuse supports only Linux, FreeBSD and OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Disable examples, utils, tests, and useroot for OHOS compat
        tc.project_options["examples"] = False
        tc.project_options["utils"] = False
        tc.project_options["tests"] = False
        tc.project_options["useroot"] = False
        tc.generate()

        # ★ 限制构建并行度：conan 默认按核数给 meson compile -j20，在长期高负载
        #   的 CI 机器上（loadavg ~21-22、MemFree ~1GB）ninja 大量并发 spawn 时
        #   撞上 "posix_spawn: Resource temporarily unavailable"（#15754 首轮
        #   实测；同款也曾打断 saunafs 的构建）。本包只有 1 个构建目标，低并行
        #   几乎不增加墙钟时间，却显著降低 fork/spawn 压力。
        self.conf.define("tools.build:jobs", 4)

        # Set AR explicitly for meson's early archiver detection.
        # CI profile's buildenv PATH may not flow to the meson subprocess.
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/ar")
        envvars = env.vars(self)
        envvars.save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["fuse3"]
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs.extend(["dl", "rt"])
        elif self.settings.os in ("OHOS",):
            # dl/rt are part of libc on OHOS, no extra linking needed
            pass
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "fuse3")
