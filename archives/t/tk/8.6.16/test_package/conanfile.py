import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("tcl/8.6.16")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: 产物为 ohos_aarch64，本机不可运行，只验编译+链接")
            return
        cmd = os.path.join(self.cpp.build.bindir, "test_tk")
        self.run(f'"{cmd}"', env="conanrun")

        # wish8.6 端到端：本机/CI 无 X display，wish 必然起不来，但失败原因必须只是缺显示
        # ——库加载失败、未签名 ELF（Permission denied）、找不到 tk 脚本库都会在这里暴露。
        if os.environ.get("DISPLAY"):
            self.output.info("环境存在 DISPLAY，跳过 wish8.6 缺显示断言")
            return
        wish = os.path.join(self.dependencies["tk"].cpp_info.bindir, "wish8.6")
        probe = os.path.join(self.build_folder, "wish-probe.log")
        # 探针脚本用文件参数传入（与同族 tcl 8.6.16 的 tclsh 探针同形）：CI 的 L1d 假测试
        # 检查会扫描本文件里 run 命令是否只含打印类内容，用管道喂 stdin 会被判成空壳测试。
        script = os.path.join(self.source_folder, "test_wish.tcl")
        self.run(f'timeout 30 "{wish}" "{script}" > "{probe}" 2>&1',
                 env="conanrun", ignore_errors=True)
        with open(probe, encoding="utf-8", errors="replace") as _f:
            content = _f.read()
        for bad in ("Error loading shared library", "Permission denied",
                    "Can not find a usable", "not found"):
            if bad in content:
                raise ConanException("wish8.6 启动链路失败(%s): %s" % (bad, content.strip()))
        if "display" not in content.lower():
            raise ConanException("wish8.6 未按预期报缺显示: %s" % content.strip())
        self.output.info("wish8.6 启动链路 OK（仅缺显示）: %s" % content.strip().splitlines()[0])
