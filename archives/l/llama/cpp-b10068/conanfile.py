#!/usr/bin/env python3
"""Conan recipe for llama.cpp cpp-b10068 (LLM inference engine), built with CMake."""

import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LlamaConan(ConanFile):
    name = "llama"
    version = "cpp-b10068"
    description = "llama.cpp LLM inference engine with bundled ggml tensor backend"
    license = "MIT"
    homepage = "https://github.com/ggml-org/llama.cpp"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tools": [True, False],
        "with_server": [True, False],
        "with_app": [True, False],
        "with_tests": [True, False],
        "with_server_ui": [True, False],
        "openssl": [True, False],
        # GGML_CPU_ARM_ARCH, e.g. "armv8.2-a+dotprod+fp16"; 未设置 = 编译器基线
        "cpu_arch": "ANY",
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tools": True,
        "with_server": True,
        "with_app": True,
        "with_tests": True,
        "with_server_ui": True,
        "openssl": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Conan 2:ANY 选项声明后必须有值才能算包 ID;未显式指定时移除
        # (generate() 里 get_safe 返回 None → 留编译器基线)
        if not self.options.get_safe("cpu_arch"):
            self.options.rm_safe("cpu_arch")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["LLAMA_BUILD_COMMON"] = True
        tc.variables["LLAMA_BUILD_TOOLS"] = bool(self.options.with_tools)
        tc.variables["LLAMA_BUILD_SERVER"] = bool(self.options.with_server)
        tc.variables["LLAMA_BUILD_APP"] = bool(self.options.with_app)
        tc.variables["LLAMA_BUILD_TESTS"] = bool(self.options.with_tests)
        tc.variables["LLAMA_BUILD_EXAMPLES"] = False
        tc.variables["LLAMA_BUILD_UI"] = bool(self.options.with_server_ui)
        # 禁止构建期从 HuggingFace 下载预编译 WebUI(离线确定性;
        # 关闭后上游脚本优雅降级为内嵌空 UI,仅 WARNING)
        tc.variables["LLAMA_USE_PREBUILT_UI"] = False
        tc.variables["LLAMA_OPENSSL"] = bool(self.options.openssl)
        tc.variables["LLAMA_LLGUIDANCE"] = False
        tc.variables["GGML_BUILD_EXAMPLES"] = False
        tc.variables["GGML_BUILD_TESTS"] = False
        tc.variables["GGML_CCACHE"] = False
        # ggml 0.17.0.1 归档配方同款:OpenMP 默认关闭。SDK 的 libomp.so 不可
        # 随包分发(下游设备无 SDK,运行时 __kmpc_* 符号全部解析失败,实测
        # test_package 报 "Error loading shared library libomp.so"),
        # 关闭后 ggml 使用自带线程池
        tc.variables["GGML_OPENMP"] = False
        # 上游警告集对编译器 ID 敏感,split C/C++ 编译器 profile 下会混入
        # Clang 专属旗标(ggml 0.17.0.1 同款处理)
        tc.variables["GGML_ALL_WARNINGS"] = False
        # 可复现性硬约束:GGML_NATIVE 默认走 -mcpu=native 探测,会把构建机
        # CPU 特性烧进产物(knowledge: fasttextembed native-cpu-flag-gate /
        # ascon-c REL_FLAGS)。关闭后用 GGML_CPU_ARM_ARCH 或编译器基线。
        tc.variables["GGML_NATIVE"] = False
        cpu_arch = self.options.get_safe("cpu_arch")
        if cpu_arch:
            tc.variables["GGML_CPU_ARM_ARCH"] = str(cpu_arch)
        tc.generate()

        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        if self.options.shared:
            # 对外声明的 5 个库 + 包内其余 .so(libmtmd 与 8 个工具 impl 库)
            # 全部补 SONAME:CI 的 L5a 门禁对 lib/ 下任何缺 SONAME 的 .so 报错,
            # 且它们随包分发,统一 SONAME=文件名 与无版本号实体一致
            self._set_soname_and_resign(
                [
                    "libllama.so",
                    "libllama-common.so",
                    "libggml.so",
                    "libggml-base.so",
                    "libggml-cpu.so",
                    "libmtmd.so",
                    "libllama-batched-bench-impl.so",
                    "libllama-bench-impl.so",
                    "libllama-cli-impl.so",
                    "libllama-completion-impl.so",
                    "libllama-fit-params-impl.so",
                    "libllama-perplexity-impl.so",
                    "libllama-quantize-impl.so",
                    "libllama-server-impl.so",
                ]
            )

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上 SONAME、归一化 DT_NEEDED 并**重新签名**。

        为何补 SONAME:本包产物无 DT_SONAME。后果不在本包,而在**下游**——
        CMake 默认按完整路径链接无 SONAME 的库,于是把构建机的 conan cache
        绝对路径写进下游的 DT_NEEDED,换机器即无法加载。
        制品仓已实测到三个因此损坏的包(fontconfig / poppler / tbb),
        ggml 0.17.0.1 同款处理。

        为何归一化 DT_NEEDED:包内库的链接发生在**构建树**,依赖库当时无
        SONAME,链接器把 "../bin/libggml.so" 这类**相对路径**写进包内库的
        DT_NEEDED(ggml 自身配方无此问题:其库在构建树同目录,记录的是裸
        文件名;llama.cpp 的库分跨 bin/ 与 src/,路径必带 ../)。打包后相对
        路径按进程 CWD 解析,在任何消费者目录下都必然加载失败(实测
        test_package 报 "Error loading shared library ../bin/libggml.so")。
        统一改写为裸文件名(即第 1 步设的 SONAME),加载器经
        LD_LIBRARY_PATH/$ORIGIN 即可解析。

        为何必须重签:改动 ELF 会破坏链接器自签,鸿蒙 PC 的 XPM 会拒绝加载
        (报 Permission denied / Operation not permitted)。
        顺序必须是 patchelf → 剥旧签名段 → 自签。
        """
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")

        # 第 1 步:给对外 .so 补 SONAME(裸文件名,与无版本号实体一致)
        for name in sonames:
            f = os.path.join(lib_dir, name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME:找不到 %s,跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            self.output.info("已设 SONAME=%s" % name)

        # 第 2 步:归一化所有打包 ELF(lib/*.so 与 bin/*)的 DT_NEEDED:
        # 带路径的条目(../bin/... 等)一律改写为其文件名(裸 SONAME)
        resign = set()
        for name in sonames:
            f = os.path.join(lib_dir, name)
            if os.path.isfile(f) and not os.path.islink(f):
                resign.add(f)
        for d in (lib_dir, bin_dir):
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                f = os.path.join(d, name)
                if os.path.islink(f) or not os.path.isfile(f):
                    continue
                probe = subprocess.run(
                    [patchelf, "--print-needed", f], capture_output=True, text=True)
                if probe.returncode != 0:
                    continue  # patchelf 不识别的文件(非 ELF),原样保留
                for needed in probe.stdout.split():
                    if "/" not in needed:
                        continue
                    bare = needed.rsplit("/", 1)[-1]
                    self.run('{pe} --replace-needed "{o}" "{n}" "{f}"'.format(
                        pe=patchelf, o=needed, n=bare, f=f))
                    self.output.info("DT_NEEDED 归一化:%s: %s -> %s" % (name, needed, bare))
                    resign.add(f)

        # 第 3 步:对所有被改写的 ELF 重签(补 SONAME 的与归一化 DT_NEEDED 的)
        for f in sorted(resign):
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))
            self.output.info("已重签 %s" % os.path.relpath(f, self.package_folder))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "llama")
        self.cpp_info.set_property("cmake_target_name", "llama::llama")
        self.cpp_info.set_property("pkg_config_name", "llama")
        self.cpp_info.libs = ["llama", "llama-common", "ggml", "ggml-base", "ggml-cpu"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
