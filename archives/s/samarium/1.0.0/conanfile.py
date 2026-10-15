#!/usr/bin/env python3
"""samarium 1.0.0 —— OpenHarmony PC (OHOS aarch64) 的 Conan 2 配方。

上游：https://github.com/strangeQuark1041/samarium（C++20 二维物理仿真库，CMake + Boost.UT）

**适配范围（partial）**：交付 `math` / `physics` / `geometry` / `graphics`(非 SFML 部分) /
`util` 全部核心模块；`app`（SFML RenderWindow 应用循环）与 `gui`（SFML 键盘/鼠标输入）
两个模块**不交付** —— 它们硬依赖 SFML 的 **Window + Graphics**，而本制品仓的
`sfml/2.6.1.1` 只提供 `System`/`Network`（见 `archives/s/sfml/2.6.1.1/manifest.yaml`
的 `modules_disabled`），其头文件目录已被上游配方裁掉。裁剪范围、理由与上游测试
执行情况见 `manifest.yaml` 的 `modules_disabled` / `notes.md`。

上游的 conan 1 形态 `conanfile.py` 只作依赖线索（fmt/8.1.1、sfml/2.5.1、range-v3/0.12.0）；
本配方按仓库规范重写为 conan 2，并通过 `patches/` 让它消费 conan 2 的 CMake 包配置。
"""
import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, rm, rmdir)


class SamariumConan(ConanFile):
    name = "samarium"
    version = "1.0.0"
    description = ("2-D physics simulation library written in modern C++ "
                   "(OHOS core build: math/physics/geometry/graphics/util)")
    license = "MIT"
    homepage = "https://strangequark1041.github.io/samarium/"
    url = "https://github.com/strangeQuark1041/samarium"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # 上游 conanfile.py 声明的依赖：sfml 被裁掉（见模块说明），保留 fmt 与 range-v3。
    requires = "fmt/8.1.1", "range-v3/0.12.0"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 不在 CMake 的已知平台表里 ⇒ CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG 未定义，
        # 生成的共享库会缺 DT_SONAME（L5 门禁拦），同时版本化符号链接在 HMDFS 上不可靠。
        # 显式补 SONAME 标志并关闭版本化 soname（先例 archives/h/hidapi/0.15.0）。
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _upstream_test_ld_path(self):
        """构建树的 samarium_tests 需要 libsamarium.so 与依赖的 libfmt.so。

        OHOS 不在 CMake 的已知平台表里 ⇒ CMake 不会给可执行文件写 RPATH/RUNPATH，
        构建树里的测试二进制因此找不到这两个库（CI 实证：
        `Error loading shared library libsamarium.so: (needed by .../test/samarium_tests)`
        与同文案的 libfmt.so.8）。显式把它们注入 LD_LIBRARY_PATH
        （仓库同类先例：libtrng 4.28 的 ctest、castxml 0.7.0 的 Environment()）。
        """
        libdirs = [os.path.join(self.build_folder, "src")]  # 构建树里的 libsamarium.so
        for name in ("fmt", "range-v3"):
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir) and dependency.package_folder:
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    libdirs.append(libdir)
        libdirs.append("$LD_LIBRARY_PATH")
        return os.pathsep.join(libdirs)

    def _run_upstream_tests(self):
        """真跑上游 Boost.UT 套件（patches/0004 让它真的执行）。

        CI 的 host/build profile 同为 ohos-aarch64 ⇒ 原生构建，测试二进制在
        worker 上可直接执行（构建树里的 ELF 不受"安装态 ELF 不可 execve"限制）。
        """
        if cross_building(self) or not can_run(self):
            self.output.warning(
                "samarium: cross build, upstream ctest suite not executed on this host")
            return
        self.run('LD_LIBRARY_PATH="{}" ctest --test-dir {} -V --output-on-failure'.format(
            self._upstream_test_ld_path(), shlex.quote(self.build_folder)))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 许可原文必须进包（MIT，文件名为 LICENSE.md）
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 裁掉未交付模块的公共头，保证安装头集合的包含闭包自洽（umbrella 已同补丁修好）
        include_dir = os.path.join(self.package_folder, "include", "samarium")
        for header in ("app.hpp", "gui.hpp"):
            rm(self, header, include_dir)
        rmdir(self, os.path.join(include_dir, "app"))
        rmdir(self, os.path.join(include_dir, "gui"))
        if self.options.shared:
            self._sign_shared_libs()

    # ── OHOS：交付的 .so 必须自签名，否则加载器拒载（E135/E517） ──────────
    def _sign_shared_libs(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = sorted(set(
            glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True) +
            glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)))
        if not shared_objects:
            raise ConanInvalidConfiguration(
                "samarium: shared build produced no .so in {}".format(libdir))
        objcopy = os.environ.get("OHOS_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("OHOS_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration("llvm-objcopy not found: {}".format(objcopy))
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool not found: {}".format(signer))
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self._remove_codesign_section(objcopy, shared_object)
            # 必须写另一个输出文件：inFile == outFile 时签名工具会"自报成功但没签上"
            signed = shared_object + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", shared_object, "-outFile", signed, "-selfSign", "1"],
                capture_output=True, text=True, check=False)
            for stream in (result.stdout, result.stderr):  # stderr 绝不丢弃
                if stream and stream.strip():
                    self.output.info(stream.strip())
            if result.returncode != 0 or not os.path.isfile(signed) or os.path.getsize(signed) == 0:
                raise ConanInvalidConfiguration(
                    "samarium: binary-sign-tool failed for {} (rc={})".format(
                        shared_object, result.returncode))
            os.replace(signed, shared_object)
            os.chmod(shared_object, 0o755)
            # 真判据：重新读一遍 .codesign 段，而不是看 os.access(X_OK)
            if not self._has_codesign_section(objcopy, shared_object):
                raise ConanInvalidConfiguration(
                    "samarium: .codesign section missing after signing: {}".format(shared_object))
            self.output.info("samarium: signed {}".format(os.path.basename(shared_object)))

    @staticmethod
    def _remove_codesign_section(objcopy, shared_object):
        result = subprocess.run([objcopy, "--remove-section", ".codesign", shared_object],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            output = ((result.stderr or "") + (result.stdout or "")).lower()
            if "does not exist" not in output and "not found" not in output:
                raise ConanInvalidConfiguration(
                    "samarium: cannot inspect {}: {}".format(shared_object, output.strip()))

    @staticmethod
    def _has_codesign_section(objcopy, shared_object):
        result = subprocess.run(
            [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
            capture_output=True, text=True, check=False)
        return result.returncode == 0

    def package_info(self):
        # 单一组件形态：CMakeDeps 只在**组件**层面展开 requires（实测无组件的
        # 包级 cpp_info.requires 会被静默丢弃 ⇒ 消费者的 range/v3 头找不到）。
        self.cpp_info.set_property("cmake_file_name", "samarium")
        self.cpp_info.set_property("pkg_config_name", "samarium")
        samarium = self.cpp_info.components["samarium"]
        samarium.set_property("cmake_target_name", "samarium::samarium")
        samarium.libs = ["samarium"]
        # 公共头使用 C++20（concepts / std::span / std::numbers），语言标准必须传给消费者
        samarium.cxxflags = ["-std=c++20"]
        # samarium 的公共头包含 range/v3 与 fmt 头 ⇒ 依赖必须传播到消费者
        samarium.requires = ["fmt::fmt", "range-v3::range-v3"]
        if str(self.settings.os) in ("OHOS", "HarmonyOS", "Linux"):
            samarium.system_libs = ["pthread", "m"]
