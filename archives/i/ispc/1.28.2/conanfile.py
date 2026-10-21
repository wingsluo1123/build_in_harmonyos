#!/usr/bin/env python3
"""Conan recipe — ispc 1.28.2 (cmake, 鸿蒙 PC 真机原生编译)

ISPC（Intel Implicit SPMD Program Compiler）= 自带 SPMD 语言前端 + LLVM 后端的编译器：
本平台产出 aarch64/NEON 向量与内联汇编级 codegen。

依赖（硬）：**同一个包内同时提供 LLVM 与 Clang 前端库**的 llvm-project 包。
  ISPC 1.28.2 的 CMakeLists.txt 无条件链接 CLANG_LIBRARY_LIST =
  clangFrontend clangBasic clangEdit clangLex clangSupport clangASTMatchers
  （源码 src/preprocessor.cpp、src/module.cpp、src/binary_composite.cpp 直接 #include <clang/...>），
  且 FindLLVM.cmake 要求 clang/clang++/llvm-as/FileCheck 位于 llvm-config 同目录（NO_DEFAULT_PATH）。
  支持区间 LLVM 18.1–21.1（src/ispc_version.h: LATEST_SUPPORTED_LLVM / #error 守卫）。

依赖形态要求（`llvm-config --targets-built` 必须同时含 AArch64、ARM、X86）：
  * AArch64：本平台主机架构目标；
  * ARM：FindLLVM.cmake 只在 `--targets-built` **同时**含 AArch64 与 ARM 时才置
    `LLVM_SUPPORTS_ARM=ON`；否则 `ARM_ENABLED` 默认 OFF，而 aarch64 宿主上 `X86_HOST=OFF`
    ⇒ `CMakeLists.txt:357` 直接 `FATAL_ERROR "Either X86, ARM, WASM or XE targets need to be enabled."`；
  * X86：上游 lit 套件有 167 个用例带 `REQUIRES: X86_ENABLED`（只做 codegen，不执行 x86 机器码），
    缺后端即被判 UNSUPPORTED，通过率结构性达不到 90%。
  该断言在 generate() 里显式做掉（fail fast），避免把依赖形态问题拖到 configure 深处。

为什么不是 ohpcd 的 llvm/20.1.0：该包只含 LLVM（无 Clang 前端、无 lib/cmake/clang），
  且 `--targets-built` 仅 AArch64 —— 无法满足上面的 clang 链接面与 ARM/X86 后端要求。
  详见 notes.md「依赖缺口」。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import cmake_layout

# 依赖包的 conan 引用（依赖任务发布后如包名/版本不同，改这里）
LLVM_PROJECT_REF = "llvm-project/20.1.8"
LLVM_PROJECT_NAME = "llvm-project"

# 依赖包必须提供的 LLVM 后端（理由见模块 docstring）
REQUIRED_LLVM_TARGETS = ("AArch64", "ARM", "X86")

# ISPC 无条件链接的 clang 前端组件（CMakeLists.txt:411）
CLANG_LIBRARY_LIST = ("clangFrontend", "clangBasic", "clangEdit",
                      "clangLex", "clangSupport", "clangASTMatchers")


def _sdk_bash() -> str:
    """设备 shebang/驱动统一用 HNP bash；不存在时退回 /bin/sh（CI worker 同镜像）。"""
    for cand in ("/data/service/hnp/bin/bash", "/bin/sh"):
        if os.path.exists(cand):
            return cand
    return "sh"


class IspcConan(ConanFile):
    name = "ispc"
    version = "1.28.2"
    description = "Intel Implicit SPMD Program Compiler（SPMD 前端 + LLVM 后端，aarch64/NEON codegen）"
    license = "BSD-3-Clause"
    homepage = "https://ispc.github.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        # 在 build() 中真实运行上游测试套件（lit check-all + run_tests.py func-tests）并打印
        # 四分项（PASS/FAIL/SKIP/NOT_RUN）与通过率；结果以日志为准，不由构建成功与否改写。
        "with_upstream_tests": [True, False],
    }
    default_options = {"with_upstream_tests": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(LLVM_PROJECT_REF)

    def source(self):
        # GitHub tag 归档：ispc-1.28.2/ 顶层；strip_root 后 source_folder 直接是仓库根
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    # ── 依赖定位 ────────────────────────────────────────────────────────────
    def _dep_root(self) -> str:
        dep = self.dependencies[LLVM_PROJECT_NAME]
        root = dep.package_folder
        if not root or not os.path.isdir(root):
            raise ConanException("dependency {} package_folder missing".format(LLVM_PROJECT_REF))
        return root

    @staticmethod
    def _first(pattern: str, what: str) -> str:
        # recursive=True 必需：`**` 在非递归 glob 下等同单个 `*`，会漏掉
        # `<pkg>/bin/llvm-config` 这种零层深度的命中。
        hits = sorted(glob.glob(pattern, recursive=True))
        if not hits:
            raise ConanException(
                "{} not found (pattern {}). The {} package must ship LLVM+Clang dev files "
                "(lib/cmake/llvm, lib/cmake/clang, clang component libs, bin/llvm-config, bin/FileCheck).".format(
                    what, pattern, LLVM_PROJECT_REF
                )
            )
        return hits[-1]

    def _dep_paths(self):
        root = self._dep_root()
        paths = {
            "root": root,
            "llvm_config": self._first(os.path.join(root, "**", "bin", "llvm-config"), "llvm-config"),
        }
        paths["bin"] = os.path.dirname(paths["llvm_config"])
        paths["llvm_dir"] = self._first(os.path.join(root, "**", "lib", "cmake", "llvm"), "LLVM cmake dir")
        # 依赖契约的其余面直接断言（fail fast，把「包不完整」挡在 configure 之前）：
        #   1) FindLLVM.cmake 用 NO_DEFAULT_PATH 在 llvm-config 同目录找这四个工具；
        #   2) ISPC 用 find_library(NAMES libclangX.a clang-cpp HINTS <llvm-config --libdir>)
        #      定位 6 个 clang 组件（CMakeLists.txt:411/813-826），静态库或 libclang-cpp 均可。
        tools = ("clang", "clang++", "llvm-as", "FileCheck")
        missing_tools = [t for t in tools if not os.path.exists(os.path.join(paths["bin"], t))]
        libdirs = [d for d in glob.glob(os.path.join(root, "**", "lib"), recursive=True) if os.path.isdir(d)]
        libs = []
        for d in libdirs:
            libs.extend(os.path.basename(p) for p in glob.glob(os.path.join(d, "*")))
        cpp_shared = any(n.startswith("libclang-cpp.so") for n in libs)
        missing_clang = []
        if not cpp_shared:
            missing_clang = [
                c for c in CLANG_LIBRARY_LIST
                if not any(n.startswith("lib" + c + ".") for n in libs)
            ]
        if missing_tools or missing_clang:
            raise ConanException(
                "{} is incomplete: missing tools {} (expected next to llvm-config at {}); "
                "missing clang component libs {} (expected under {}/lib). ISPC needs the clang "
                "frontend (CMakeLists.txt:411 CLANG_LIBRARY_LIST) and the tools FindLLVM.cmake "
                "resolves with NO_DEFAULT_PATH.".format(
                    LLVM_PROJECT_REF, missing_tools, paths["bin"], missing_clang, root
                )
            )
        return paths

    def _targets_built(self, llvm_config: str) -> str:
        # 绝对路径调用 llvm-config（设备 Python 裸命令名不搜 PATH，见 notes/device-facts §一.14）
        out = subprocess.check_output([llvm_config, "--targets-built"], text=True)
        return out.strip()

    @staticmethod
    def _host_c_include_dirs():
        """问询宿主 clang，取它自己的 C 头文件搜索目录（排除 clang 自带 resource-dir）。

        用途：cmake/GenerateBuiltins.cmake 编译 builtins-c++ 时写死
        `-isystem/usr/<debian_triple>/include`（Debian/Ubuntu multiarch 交叉 sysroot），
        OHOS 上该路径不存在。这里不改上游源码，改为把宿主工具链真实的 C 头目录补进去。
        """
        cc = "/data/service/hnp/bin/clang"
        if not os.path.exists(cc):
            return []
        try:
            proc = subprocess.run([cc, "-E", "-x", "c", "-v", os.devnull],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        except OSError:
            return []
        dirs, inside = [], False
        for line in (proc.stderr or "").splitlines():
            s = line.strip()
            if "#include <...> search starts here:" in s:
                inside = True
                continue
            if s.startswith("End of search list"):
                inside = False
                continue
            if inside and os.path.isdir(s) and "/lib/clang/" not in s:
                dirs.append(s)
        return dirs

    def _builtins_cpp_wrapper(self, clangpp: str):
        """生成注入宿主 C 头目录的 clang++ 包装脚本，返回可传给 -DCLANGPP_EXECUTABLE 的值。

        背景（设备实测，属**上游构建缺陷**）：builtins-c-cpu.cpp 的编译命令是
            clang++ --target=<triple> -isystem/usr/<debian_triple>/include ... -o - | llvm-as -o out.bc
        OHOS 上没有 /usr/<debian_triple>/include ⇒ clang++ 报
        `builtins-c-cpu.cpp:42:10: fatal error: 'unistd.h' file not found`；而管道只取
        `llvm-as` 的退出码 ⇒ 失败被静默吞掉，llvm-as 对空输入产出**空模块**
        （1304 字节、0 符号）。后果：ispc 编出的程序在链接期报
        `ld.lld: error: undefined symbol: __do_print`（func-tests 21 个 print/asin 用例失败）。
        """
        host_incs = self._host_c_include_dirs()
        if not host_incs:
            self.output.warning("host C include dirs not detected; builtins-c++ compilation may "
                                "silently produce EMPTY bitcode -> print() will not link")
            return None
        tools_dir = os.path.join(self.build_folder, "_host_tools")
        os.makedirs(tools_dir, exist_ok=True)
        wrapper = os.path.join(tools_dir, "clang++")
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexec \"{}\" {}\"$@\"\n".format(
                clangpp, "".join('-isystem "{}" '.format(d) for d in host_incs)))
        os.chmod(wrapper, 0o755)
        self.output.info("builtins-c++ clang++ wrapper: {} (+isystem {})".format(
            wrapper, ":".join(host_incs)))
        return wrapper

    @staticmethod
    def _check_builtins_cpp_not_empty(bdir: str):
        """硬校验 builtins-c++ 位码非空：空模块会让 print()/__do_print 在链接期才暴露。"""
        bc_dir = os.path.join(bdir, "share", "ispc")
        bad = []
        for name in sorted(os.listdir(bc_dir)) if os.path.isdir(bc_dir) else []:
            if not (name.startswith("builtins_cpp_") and name.endswith(".bc")):
                continue
            p = os.path.join(bc_dir, name)
            size = os.path.getsize(p)
            if size < 8192:
                bad.append("{} ({} bytes)".format(name, size))
        if bad:
            raise ConanException(
                "builtins-c++ bitcode is EMPTY: {}. This is the silent-failure mode of "
                "cmake/GenerateBuiltins.cmake (`clang++ ... -o - | llvm-as -o out.bc` — the pipe "
                "returns llvm-as' exit status, so a clang++ header error yields an empty module). "
                "Check the clang++ wrapper injection (CLANGPP_EXECUTABLE) and the host C include "
                "dirs; without this, ispc output fails to link with "
                "'undefined symbol: __do_print'.".format(", ".join(bad)))


    def generate(self):
        """依赖形态断言（fail fast）：AArch64 + ARM + X86 三个后端必须齐备。"""
        targets = self._targets_built(self._dep_paths()["llvm_config"]).split()
        missing = [t for t in REQUIRED_LLVM_TARGETS if t not in targets]
        self.output.info(
            "dependency {}: llvm-config --targets-built = {}".format(LLVM_PROJECT_REF, " ".join(targets))
        )
        if missing:
            raise ConanException(
                "{} must be built with LLVM_TARGETS_TO_BUILD including {} (missing: {}; "
                "llvm-config --targets-built = {!r}). AArch64 = host arch target; ARM = ISPC "
                "FindLLVM.cmake only sets LLVM_SUPPORTS_ARM when both AArch64 and ARM exist "
                "(otherwise ARM_ENABLED=OFF and CMakeLists.txt:357 FATAL_ERRORs on aarch64 hosts "
                "because X86_HOST=OFF); X86 = required by 167 lit cases guarded with "
                "REQUIRES: X86_ENABLED.".format(
                    LLVM_PROJECT_REF, " ".join(REQUIRED_LLVM_TARGETS),
                    " ".join(missing), " ".join(targets),
                )
            )

    def build(self):
        apply_conandata_patches(self)
        paths = self._dep_paths()
        targets = self._targets_built(paths["llvm_config"]).split()
        x86_enabled = "X86" in targets
        arm_enabled = "ARM" in targets
        aarch64_enabled = "AArch64" in targets
        if not (aarch64_enabled or x86_enabled):
            raise ConanException("dependency LLVM has neither X86 nor AArch64 backend: {}".format(targets))

        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")

        # 设备 uname -s = HarmonyOS，CMake 无 Platform/HarmonyOS 模块 ⇒ UNIX 未置 ⇒ 平台判定 FATAL。
        # 提供 Platform/HarmonyOS.cmake（复用 Platform/Linux）挂到 CMAKE_MODULE_PATH。
        # 与本仓 llvm/20.1.0、clang/22.1.8 同族策略：保持 native（不设 CMAKE_SYSTEM_NAME），
        # 使 ispc 构建期需要运行的 llvm-tblgen/ispc 生成步骤原生化。
        moddir = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(moddir, "Platform"), exist_ok=True)
        with open(os.path.join(moddir, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as f:
            f.write("include(Platform/Linux)\n")

        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
        # builtins-c++ 的 clang++ 需要宿主 C 头目录（详见 _builtins_cpp_wrapper 的说明）
        ccpp_wrapper = self._builtins_cpp_wrapper(os.path.join(paths["bin"], "clang++"))
        defs = [
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(moddir),
            '-DCMAKE_C_COMPILER="/data/service/hnp/bin/clang"',
            '-DCMAKE_CXX_COMPILER="/data/service/hnp/bin/clang++"',
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # FindLLVM.cmake 用 find_program(... NO_DEFAULT_PATH) 定位 llvm-config 与同目录的
            # clang/clang++/llvm-as/FileCheck。依赖包 package_type=library ⇒ bindirs 不进 PATH，
            # 必须显式给出，否则 FATAL "Failed to find llvm-config"。
            '-DLLVM_CONFIG_EXECUTABLE="{}"'.format(paths["llvm_config"]),
            # LLVM_DIR 只被 FindLLVM.cmake 打印/记录（ISPC 不调用 find_package(LLVM)）；给出它
            # 让 configure 日志直接显示依赖来源。Clang 组件库不经 find_package(Clang)，而是
            # `find_library(... NAMES libclangX.a clang-cpp HINTS ${LLVM_LIBRARY_DIRS})`
            # （CMakeLists.txt:813-826，LLVM_LIBRARY_DIRS 来自 `llvm-config --libdir`），
            # 依赖包 6 个 .a 与 libclang-cpp.so 都在 lib/ 下 ⇒ 无需 -DClang_DIR。
            '-DLLVM_DIR="{}"'.format(paths["llvm_dir"]),
            # 目标面全部由依赖包 `llvm-config --targets-built` 自适应（不硬编码，
            # 避免为不存在的后端约束引入源码/配置改动）：
            #   X86 —— 覆盖 167 个 REQUIRES: X86_ENABLED 的 lit 用例（只 codegen 不执行）；
            #   ARM —— FindLLVM.cmake 要求 AArch64 与 ARM 同时存在才开 ARM_ENABLED。
            "-DX86_ENABLED={}".format("ON" if x86_enabled else "OFF"),
            "-DARM_ENABLED={}".format("ON" if arm_enabled else "OFF"),
            "-DWASM_ENABLED=OFF",
            "-DXE_ENABLED=OFF",
            # 上游测试目标 check-all（lit）；测试实际运行由 with_upstream_tests 控制
            "-DISPC_INCLUDE_TESTS=ON",
            "-DISPC_INCLUDE_BENCHMARKS=OFF",
            "-DISPC_INCLUDE_EXAMPLES=OFF",
            "-DISPC_INCLUDE_RT=OFF",
            "-DISPC_LIBRARY=OFF",
            # 与 ISPC_LIBRARY=OFF 保持一致：本包按 application 交付，不构建 libispc；
            # ISPC_LIBRARY_JIT 是「把 ISPC 作为带 JIT 的库构建」，库不存在时该开关无意义。
            # 上游 lit 用 `REQUIRES: ISPC_LIBRARY_JIT` 守卫 ispc-library-jit.cpp /
            # ispc-jit-error-handling.cpp，置 OFF 后这两个用例按上游机制判 UNSUPPORTED（SKIP），
            # 而不是因 `-lispc` 缺失报 FAIL（其中 ispc-jit-error-handling.cpp 另受 OHOS musl
            # `extern FILE *const stderr;` 限制——该用例会 `stderr = tmpfile()` 赋值给 const 指针）。
            "-DISPC_LIBRARY_JIT=OFF",
            # CI 红修复（build#89756）：**关闭上游发布打包路径 ISPC_PREPARE_PACKAGE**。
            # ON 时 CMakeLists.txt:1181-1209 会 `ExternalProject_Add(ispc_web)`——在**构建期**
            # `git clone https://github.com/ispc/ispc.github.com.git`（文档站仓库，仅用于把
            # faq.html/ispc.html/perfguide.html/css/ 拷进安装树）。CI worker 无法直连 github
            # （r3 build#89756：901/932 步 ispc_web-download `Failed to connect to github.com
            # port 443`，重试 3 次后 CMake Error `Failed to clone repository` ⇒ ninja 停止）。
            # 置 OFF 后 ispc_web 目标根本不存在，构建完全离线；随之失去的静态文件
            # （LICENSE.txt/third-party-programs.txt/ReleaseNotes.txt/contrib/ examples/）由
            # package() 从源码目录补齐（见 package()），仅 web HTML 文档不再随包——它们是
            # ispc.github.io 网站内容，不参与编译/链接/运行，test_package 与下游消费均不引用。
            "-DISPC_PREPARE_PACKAGE=OFF",
            # 关键（否则 ispc 一启动即 `std::bad_cast` 崩溃）：
            # ISPC_PREPARE_PACKAGE=ON 会把 ISPC_STATIC_LINK 默认为 ON（CMakeLists.txt:292-296），
            # 于是 CMakeLists.txt:794-799
            # 给链接器加 `-static-libgcc -static-libstdc++`。在 OHOS 的 clang 上这会让可执行文件
            # **静态链入 libc++**（`-static-libstdc++` 对 libc++ 语义同样生效），而依赖包
            # libLLVM.so.20.1 是动态链接 libc++_shared.so 的共享库 ⇒ 同一进程内出现两份 libc++，
            # 首个 iostream/locale 使用即 `libc++abi: terminating due to uncaught exception of type
            # std::bad_cast`。最小复现（设备实测，3 行程序）：
            #   clang++ t.cpp -static-libstdc++ -lLLVM-20  → rc=134 std::bad_cast
            #   clang++ t.cpp                -lLLVM-20  → OK（双方共用 libc++_shared.so）
            # 故显式关闭静态 libc++/libgcc，使 ispc 与 libLLVM.so 使用同一份 libc++_shared.so。
            # 注意：ISPC_STATIC_LINK 在 ISPC 源码里只用于加这两个链接选项（无其它语义）。
            "-DISPC_STATIC_LINK=OFF",
            "-DISPC_STATIC_STDCXX_LINK=OFF",
        ]
        if ccpp_wrapper:
            # find_program(CLANGPP_EXECUTABLE ...) 对已在缓存里的值不再覆盖，故此处生效；
            # 该变量仅被 GenerateBuiltins.cmake 的 dispatch 与 builtins-c++ 两处编译使用。
            defs.append('-DCLANGPP_EXECUTABLE="{}"'.format(ccpp_wrapper))
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}" -- -j{}'.format(bdir, jobs))
        self._check_builtins_cpp_not_empty(bdir)

        if self.options.with_upstream_tests:
            self._run_upstream_tests(src, bdir)

    def _install_host_cc_wrappers(self, bin_dir: str) -> None:
        """把**宿主** C/C++ 编译器以薄包装脚本形式放进 <build>/bin，供 lit 的 %{cc}/%{cxx} 使用。

        原因（设备实测）：tests/CMakeLists.txt 依次追加
            --path=${CMAKE_RUNTIME_OUTPUT_DIRECTORY}   # = <build>/bin
            --path=${LLVM_TOOLS_BINARY_DIR}            # = 依赖包 llvm-project 的 bin
        而 lit 把这两个目录**按给定顺序前置**到测试 PATH（LitConfig.py:
        `PATH = os.pathsep.join(litConfig.path + [os.environ['PATH']])`）。依赖包 bin/ 里自带
        一整套 clang/clang++（target `aarch64-unknown-linux-ohos`，不带 OHOS sysroot），于是
        lit 里所有 `clang`/`clang++` 步骤都拿到它，报 `'stdio.h' file not found` 与
        `ld.lld: error: unable to find library -lc`（22 个 lit FAIL 中 16 个由此产生）。
        <build>/bin 排在依赖包 bin 之前，因此只在这一个目录里覆盖 %{cc}/%{cxx} 两个名字即可；
        FileCheck / llvm-as 等仍按依赖包 bin 解析（保持与所链接 LLVM 20 同版本）。
        """
        host_bin = "/data/service/hnp/bin"
        os.makedirs(bin_dir, exist_ok=True)
        for name in ("clang", "clang++"):
            tool = os.path.join(host_bin, name)
            if not os.path.exists(tool):
                self.output.warning("host compiler {} missing; lit %{{cc}}/{{cxx}} will fall back "
                                    "to the dependency package's clang".format(tool))
                continue
            wrapper = os.path.join(bin_dir, name)
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write('#!/bin/sh\nexec "{}" "$@"\n'.format(tool))
            os.chmod(wrapper, 0o755)

    # ── 上游测试（R51 / AGENTS §3.5：真实运行 + 逐类归因）────────────────────
    def _run_upstream_tests(self, src: str, bdir: str):
        """运行 lit(check-all) 与 run_tests.py(func-tests)，打印四分项与通过率。

        口径：TOTAL = PASS + FAIL + SKIP + NOT_RUN（lit 的 Unsupported 计入 SKIP）。
        未执行/跳过/失败一律如实打印，不写 PASS。

        日志落点：默认 `self.build_folder`；若设置 `ISPC_TEST_EVIDENCE_DIR` 则落该目录，
        便于 conan create 的临时 build 目录被回收后仍可复算（设备轮与 W4 复算用）。
        """
        bin_dir = os.path.join(bdir, "bin")
        evd = os.environ.get("ISPC_TEST_EVIDENCE_DIR") or self.build_folder
        os.makedirs(evd, exist_ok=True)
        lit_log = os.path.join(evd, "lit.log")
        run_log = os.path.join(evd, "run_tests.log")
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)

        self._install_host_cc_wrappers(bin_dir)

        # 1) lit（tests/lit-tests，647 个用例；上游 CMake 目标 check-all）
        lit_rc = self.run(
            'cmake --build "{}" --target check-all > "{}" 2>&1'.format(bdir, lit_log),
            ignore_errors=True,
        )
        self.output.info("lit check-all rc={} (log: {})".format(lit_rc, lit_log))

        # 2) run_tests.py（tests/func-tests，1576 个用例；上游 aarch64 CI 的测试路径）
        #    ⚠ 必须从**源码根**运行：get_test_files() 用 `./tests/func-tests/*ispc` 相对 CWD 取用例，
        #    在别处运行会得到空列表并以 `ValueError: max() iterable argument is empty` 退出。
        run_cmd = (
            'cd "{cwd}" && ISPC_HOME="{bin}" PATH="{bin}:$PATH" '
            '{py} "{src}/scripts/run_tests.py" -t neon-i32x4 -a aarch64 -o O2 '
            '-c clang++ -j {jobs} --non-interactive --time '
            '--fail_db "{src}/tests/fail_db.txt" > "{log}" 2>&1'
        ).format(cwd=src, bin=bin_dir, py="python3",
                 src=src, jobs=jobs, log=run_log)
        run_rc = self.run(run_cmd, ignore_errors=True)
        self.output.info("run_tests.py rc={} (log: {})".format(run_rc, run_log))

        # 3) 四分项汇总（原始日志保留在 evd，供 W3/W4 复算）
        #    汇总本身失败不得让已完成构建的包失败：捕获后如实告警。
        try:
            self._report_upstream_results(lit_log, run_log, lit_rc, run_rc)
        except Exception as exc:  # noqa: BLE001 - 汇总失败不应毁掉构建产物
            self.output.warning("upstream test summary failed ({}); read {} and {} manually"
                                .format(exc, lit_log, run_log))

    @staticmethod
    def _report_upstream_results(lit_log: str, run_log: str, lit_rc, run_rc) -> None:
        import re

        def read(p):
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    return f.read()
            except OSError:
                return ""

        def grab(text, label):
            m = re.search(r"^\s*%s\s*:\s*(\d+)\s*$" % re.escape(label), text, re.M)
            return int(m.group(1)) if m else 0

        lt, rt = read(lit_log), read(run_log)
        lit = {k: grab(lt, k) for k in ("Passed", "Failed", "Unsupported", "Expectedly Failed", "Timed Out")}
        lit_total = sum(lit.values())
        m = re.search(r"^(\d+) / (\d+) tests PASSED", rt, re.M)
        rt_pass = int(m.group(1)) if m else 0
        rt_total = int(m.group(2)) if m else 0
        m = re.search(r"^(\d+) / \d+ tests FAILED compilation", rt, re.M)
        rt_compfail = int(m.group(1)) if m else 0
        m = re.search(r"^(\d+) / \d+ tests FAILED execution", rt, re.M)
        rt_runfail = int(m.group(1)) if m else 0
        m = re.search(r"^(\d+) / \d+ tests SKIPPED", rt, re.M)
        rt_skip = int(m.group(1)) if m else 0

        total = lit_total + rt_total
        passed = lit["Passed"] + rt_pass
        failed = lit["Failed"] + lit["Timed Out"] + rt_compfail + rt_runfail
        skipped = lit["Unsupported"] + lit["Expectedly Failed"] + rt_skip
        not_run = total - (passed + failed + skipped)
        rate = (passed / total * 100.0) if total else 0.0
        print("UPSTREAM_TEST_SUMMARY " + str({
            "lit_rc": lit_rc, "run_tests_rc": run_rc,
            "lit": lit, "lit_total": lit_total,
            "run_tests": {"PASSED": rt_pass, "FAILED_compilation": rt_compfail,
                          "FAILED_execution": rt_runfail, "SKIPPED": rt_skip, "TOTAL": rt_total},
            "PASS": passed, "FAIL": failed, "SKIP": skipped, "NOT_RUN": not_run,
            "TOTAL": total, "pass_rate_pct": round(rate, 2),
            "hard_gate_90pct": (rate >= 90.0) if total else None,
        }))
        if total and rate < 90.0:
            print("WARNING: upstream pass rate {:.2f}% < 90% hard gate "
                  "(PASS={} FAIL={} SKIP={} NOT_RUN={} TOTAL={}); every non-PASS case must be "
                  "attributed in reports/test-report.md — FAIL/SKIP are never rewritten into PASS."
                  .format(rate, passed, failed, skipped, not_run, total))
        if lit_rc not in (0, None) or run_rc not in (0, None):
            print("NOTE: lit rc={} run_tests rc={} (non-zero is expected when any case "
                  "fails or is skipped); per-case attribution goes to reports/test-report.md."
                  .format(lit_rc, run_rc))

    # ── 打包 ────────────────────────────────────────────────────────────────
    def _is_elf(self, path: str) -> bool:
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS 要求被 exec 的 ELF 带 .codesign，否则 EPERM/EACCES（与本仓 llvm/clang 同族）
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.exists(objcopy) and os.path.exists(signer)):
            self.output.warning("binary-sign-tool/llvm-objcopy missing; skip re-signing")
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in sorted(os.listdir(bindir)):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        for f in targets:
            if os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._package_upstream_static_files()
        self._sign_binaries()

    def _package_upstream_static_files(self):
        """CI 红修复（build#89756）：ISPC_PREPARE_PACKAGE=OFF 后从**源码目录**补齐上游随包静态文件。

        上游 ON 发布路径（CMakeLists.txt:1178-1209）随包安装：examples/（排除 xpu）、contrib/、
        LICENSE.txt、third-party-programs.txt、docs/ReleaseNotes.txt，以及 ispc_web 克隆来的
        web HTML（faq.html/ispc.html/perfguide.html/css/）。置 OFF 后这些 install 规则全部消失，
        但前五项都是**源码树内静态文件**，无需网络即可拷贝，故在此补齐以保持产物面等价。
        唯一不随包的是 web HTML——它是 ispc.github.io 网站内容（构建期 git clone github，
        CI worker 不可达，见 build() 注释），不参与编译/链接/运行，test_package 与下游不引用。

        另：OFF 时上游会额外 `install(TARGETS check_isa DESTINATION bin)`（CMakeLists.txt:130-132，
        ON 时装但不安装）；旧包不含它，为保持产物面等价在此移除。
        """
        src = self.source_folder
        dst = self.package_folder
        copy(self, "LICENSE.txt", src=src, dst=dst)
        copy(self, "third-party-programs.txt", src=src, dst=dst)
        copy(self, "ReleaseNotes.txt", src=os.path.join(src, "docs"), dst=dst)
        copy(self, "*", src=os.path.join(src, "contrib"), dst=os.path.join(dst, "contrib"))
        # 上游：install(DIRECTORY examples/ DESTINATION examples PATTERN "xpu" EXCLUDE)
        for sub in ("common", "cpu"):
            copy(self, "*", src=os.path.join(src, "examples", sub),
                 dst=os.path.join(dst, "examples", sub))
        chk = os.path.join(dst, "bin", "check_isa")
        if os.path.exists(chk):
            os.remove(chk)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
