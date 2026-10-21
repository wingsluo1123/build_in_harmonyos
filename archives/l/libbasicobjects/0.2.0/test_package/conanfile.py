from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
import os
import shutil


class LibBasicobjectsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # OHOS 真机/CI Worker 的 make 执行 /bin/sh 受限,强制 Ninja 生成器
        # (conf 必须在 CMakeToolchain 构造前定义才生效)。
        self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")
        tc = CMakeToolchain(self)
        # E092:CMake 不识别 HarmonyOS 平台(无 Platform/OHOS module),configure
        # 阶段编译器探测失败。OHOS 基于 Linux 内核,按 E092 rec_approach 以
        # Linux 平台生成(aarch64 由 profile 传递)。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "8"])

    def test(self):
        # 消费者探针:链接安装后的 libbasicobjects,断言 simplebuffer 全公开 API。
        # 无 layout() 时 build_folder 即 test_package 源目录,用绝对路径执行。
        self.run(os.path.join(self.build_folder, "basicobjects_probe"), env="conanrun")
        # 上游官方单测复跑(vendored 源码与安装库链接,消费者口径)。
        self.run(os.path.join(self.build_folder, "simplebuffer_ut"), env="conanrun")
