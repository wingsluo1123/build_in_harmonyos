#!/usr/bin/env python3
"""Conan test_package — intel-oneapi-dpcpp 2026.0.0_220 (candidate nightly snapshot).

验证目标：
- 包内存在 DPC++ clang++（构建产物，非系统 Clang）
- 包内存在 libsycl.so
- 使用包内 clang++ 以 -fsycl -fsycl-targets=spir64 编译最小 SYCL 程序（device 阶段）
"""
import os

from conan import ConanFile
from conan.tools.files import load


class InteloneapiDpcppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        clangxx = os.path.join(pkg, "bin", "clang++")
        libsycl = os.path.join(pkg, "lib", "libsycl.so")
        assert os.path.exists(clangxx), f"clang++ 缺失: {clangxx}"
        assert os.path.exists(libsycl), f"libsycl.so 缺失: {libsycl}"
        ver = self.run(f"{clangxx} --version", env="conanrun")
        self.output.info(f"clang++ --version rc={ver}")
        # device-only 编译冒烟（不依赖 GPU/runtime）
        src = os.path.join(self.source_folder, "test_sycl.cpp")
        with open(src, "w", encoding="utf-8") as f:
            f.write("#include <sycl/sycl.hpp>\nint main(){ sycl::queue q; return 0; }\n")
        rc = self.run(
            f"{clangxx} -fsycl -fsycl-targets=spir64 -std=c++17 "
            f"-isystem {os.path.join(pkg, 'include')} "
            f"-isystem /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1 "
            f"-isystem /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos "
            f"-isystem /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include "
            f"-fsycl-device-only {src} -o {os.path.join(self.build_folder, 'test_sycl.bc')}",
            env="conanrun",
        )
        self.output.info(f"-fsycl-device-only rc={rc}")
        assert rc == 0, "SYCL device-only 编译失败"
