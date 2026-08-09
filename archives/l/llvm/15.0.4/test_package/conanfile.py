import os
from conan import ConanFile

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 后续验收入口（R8 仅 scaffold，不执行）：
        # 1. 检查 LLVMConfig/LLVMExports/ClangTargets 导出存在
        # 2. 检查静态归档 libLLVM*.a / libclang*.a 实际存在（首项 libLLVMDemangle.a）
        # 3. 用 ar/readelf 抽查归档成员 ELF machine=AArch64、triple=aarch64-unknown-linux-ohos
        # 4. 编译最小消费者：链接 LLVM 组件并校验
        dep = self.dependencies["llvm"].cpp_info
        libdir = dep.libdirs[0]
        llvm_cmake = os.path.join(libdir, "cmake", "llvm", "LLVMConfig.cmake")
        clang_cmake = os.path.join(libdir, "cmake", "clang", "ClangTargets.cmake")
        demangle = os.path.join(libdir, "libLLVMDemangle.a")
        checks = {
            "LLVMConfig.cmake": os.path.isfile(llvm_cmake),
            "ClangTargets.cmake": os.path.isfile(clang_cmake),
            "libLLVMDemangle.a": os.path.isfile(demangle),
        }
        for name, ok in checks.items():
            self.output.info(f"verify {name}: {'OK' if ok else 'MISSING'}")
        missing = [n for n, ok in checks.items() if not ok]
        if missing:
            raise RuntimeError(f"static package verification failed: {missing}")

    def test(self):
        # 后续验收：确认导出引用可满足、ABI 为 AArch64、AdaptiveCpp 消费者编译范围。
        # R8 未执行；获批构建后按 manifest 的 test_package_tests 执行。
        self.output.info("llvm/15.0.4 static package test_package entry prepared (not executed in R8)")
