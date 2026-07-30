#!/usr/bin/env python3
"""Conan recipe — zstd 1.5.6 (cmake)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class ZstdConan(ConanFile):
    name = "zstd"
    version = "1.5.6"
    description = "Zstandard - fast real-time compression algorithm"
    license = "BSD-3-Clause AND GPL-2.0-or-later"
    homepage = "https://github.com/facebook/zstd"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _ohos_toolchain(self):
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]")

    def build(self):
        import os
        apply_conandata_patches(self)
        self._patch_gnu_qsort_r()
        toolchain = self._ohos_toolchain()
        cml_dir = os.path.join(self.source_folder, "build", "cmake")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",  # ohos.toolchain.cmake 的目标架构；与 1.5.7 一致，OHOS PC 当前仅 arm64
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DZSTD_BUILD_SHARED=ON",
            "-DZSTD_BUILD_STATIC=OFF",
            "-DZSTD_BUILD_PROGRAMS=OFF",
            "-DZSTD_BUILD_TESTS=OFF",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, cml_dir, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def _patch_gnu_qsort_r(self):
        # R8 偏离说明（详见 notes.md「R8 平台条件编译宏偏离记录」）：
        # OHOS 用 musl libc，不提供 GNU 风格的 qsort_r。zstd 的 cover.c / zstd_deps.h 在
        # __linux__ 下自动 #define _GNU_SOURCE → 走 glibc qsort_r → 链接报 undefined symbol: qsort_r。
        # 上游本就为 __ANDROID__（注释 "NDK doesn't ship qsort_r()"）开了同样例外；OHOS 同理，
        # 给两处守卫追加 && !defined(__OHOS__) 例外（真机 __OHOS__=1），令其走 C90 fallback
        # （全局 ctx + 普通 qsort）——这是有实质逻辑的平台分支适配（非空壳 stub），符合 R8。
        # 此方案与已发布的 zstd/1.5.7 recipe 完全对齐。
        import os
        old = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__)"
        new = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__) && !defined(__OHOS__)"
        for rel in ("lib/dictBuilder/cover.c", "lib/common/zstd_deps.h"):
            p = os.path.join(self.source_folder, rel)
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            if old in txt:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(txt.replace(old, new))

    def package(self):
        import os
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        explicit_libs = ['zstd']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "zstd")
        self.cpp_info.set_property("cmake_target_name", "zstd::libzstd")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]