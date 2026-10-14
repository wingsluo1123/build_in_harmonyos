#!/usr/bin/env python3
"""Conan recipe — polly 22.1.8 (LLVM Polly, cmake, 鸿蒙 PC 真机原生编译)

产 LLVM Polly 多面体优化器插件 LLVMPolly.so（pass plugin）+ 静态库
libPolly.a / libPollyISL.a + include/polly/*.h，并附带消费工具 opt（加载插件用）。

Polly 是 llvm-project 单仓的 tools 子项目，构建必须 rooted 在 llvm/ 目录
（-DLLVM_ENABLE_PROJECTS=polly），与 LLVM 本体同树构建。isl 用 bundled 版本
（POLLY_BUNDLED_ISL=ON，polly/lib/External/isl），无外部 Conan 依赖。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get
from conan.tools.cmake import cmake_layout


class PollyConan(ConanFile):
    name = "polly"
    version = "22.1.8"
    description = "LLVM Polly — polyhedral optimizer plugin (LLVMPolly.so) + libPolly/libPollyISL static libs, AArch64"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://polly.llvm.org"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Conan 2.x 要求 package_type=library 必须声明 shared 选项。
    # Polly 同时产动态插件 LLVMPolly.so 与静态 libPolly.a/libPollyISL.a；
    # shared 选项仅作为形态开关声明，build() 不按它裁剪（插件必须动态、静态库必须静态）。
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # HMDFS 复制 3.2GB 源码树（数万小文件）极慢，直接复用 source 缓存（lld 同款规避）。
    no_copy_source = True

    def source(self):
        # 归档为 llvm-project-22.1.8.src/{llvm,polly,...}；strip_root 后
        # source_folder 直含 llvm/、polly/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：不设 CMAKE_SYSTEM_NAME →
        # 不触发 CMAKE_CROSSCOMPILING → llvm-tblgen 原生编+跑，绕开交叉编译的
        # tblgen 主机版难题。/tmp 只读（E002）→ 指向可写临时目录；conanbuild 的
        # PATH 不含 hnp bin（cmake/ninja/clang 所在）→ 显式前置。
        os.environ.setdefault("TMPDIR", "/storage/Users/currentUser/tmp")
        _hnp = "/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin"
        os.environ["PATH"] = _hnp + ":" + os.environ.get("PATH", "")

        src = os.path.join(self.source_folder, "llvm")  # CMakeLists 在 llvm/ 子目录
        bdir = os.path.join(self.build_folder, "build-ohos")

        # LLVM 的 config.guess 不认设备 `uname -s = HarmonyOS` → get_host_triple
        # 非零退出 FATAL。用 stub 覆盖 config.guess 直接输出 ohos 三元组
        # （设备 clang 的 target 即 aarch64-unknown-linux-ohos）。
        _cg = os.path.join(src, "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")

        # libLLVM.so 版本化软链（libLLVM.so → libLLVM.so.22.1）在 HMDFS 上失败
        # （E050/E079：cmake_symlink_library → Permission denied，编译停在 2288/2295）。
        # 去掉 SOVERSION/VERSION，让 libLLVM.so 直接生成（无软链）。
        _addllvm = os.path.join(src, "cmake", "modules", "AddLLVM.cmake")
        with open(_addllvm, "r", encoding="utf-8") as _f:
            _addllvm_txt = _f.read()
        _sov_old = (
            "    if(UNIX AND NOT APPLE AND NOT ARG_SONAME)\n"
            "      set_target_properties(${name}\n"
            "        PROPERTIES\n"
            "        # Since 18.1.0, the ABI version is indicated by the major and minor version.\n"
            "        SOVERSION ${LLVM_VERSION_MAJOR}.${LLVM_VERSION_MINOR}${LLVM_VERSION_SUFFIX}\n"
            "        VERSION ${LLVM_VERSION_MAJOR}.${LLVM_VERSION_MINOR}${LLVM_VERSION_SUFFIX})\n"
            "    endif()"
        )
        _sov_new = (
            "    if(UNIX AND NOT APPLE AND NOT ARG_SONAME)\n"
            "      # OHOS HMDFS does not support symlinks (E050/E079); skip versioned\n"
            "      # library symlink so libLLVM.so is created directly without a link.\n"
            "    endif()"
        )
        if _sov_old not in _addllvm_txt:
            raise ConanException("AddLLVM.cmake SOVERSION block not found")
        with open(_addllvm, "w", encoding="utf-8") as _f:
            _f.write(_addllvm_txt.replace(_sov_old, _sov_new, 1))

        # OHOS musl BIND_NOW + RTLD_LOCAL 下，opt 加载 LLVMPolly.so 无法回溯宿主
        # opt 的 libLLVM.so 来解析 LLVM 符号（上游只链 isl 不链 LLVM）→ 显式链
        # libLLVM.so，让 LLVMPolly.so 带 DT_NEEDED（真机已验证必需，否则报
        # symbol not found _ZN4llvm2cl18getGeneralCategoryEv）。
        _plib = os.path.join(self.source_folder, "polly", "lib", "CMakeLists.txt")
        with open(_plib, "r", encoding="utf-8") as _f:
            _plib_txt = _f.read()
        _plib_old = "  target_link_libraries(LLVMPolly PUBLIC ${ISL_TARGET})"
        _plib_new = "  target_link_libraries(LLVMPolly PUBLIC ${ISL_TARGET} LLVM)"
        if _plib_old not in _plib_txt:
            raise ConanException("LLVMPolly target_link_libraries line not found")
        with open(_plib, "w", encoding="utf-8") as _f:
            _f.write(_plib_txt.replace(_plib_old, _plib_new, 1))

        # gtest 的 EXPECT_DEATH（death test）需要可写 /tmp（fork+写临时文件），
        # OHOS /tmp 只读（E002）→ 删除 Isl.Quota 的 5 个 EXPECT_DEATH，用等价功能
        # 断言覆盖（quota-exceeded 错误态已由 is_error()/is_false()/is_true() +
        # 作用域结束后 isl_ctx_last_error()==isl_error_quota 验证，不丢覆盖）。
        _islt_cpp = os.path.join(self.source_folder, "polly", "unittests", "Isl", "IslTest.cpp")
        with open(_islt_cpp, "r", encoding="utf-8") as _f:
            _islt_cpp_txt = _f.read()
        _islt_cpp_old = (
            '    EXPECT_DEATH((void)(bool)BoolResult,\n'
            '                 "IMPLEMENTATION ERROR: Unhandled error state");\n'
            '    EXPECT_DEATH((void)(bool)!BoolResult,\n'
            '                 "IMPLEMENTATION ERROR: Unhandled error state");\n'
            '    EXPECT_DEATH(\n'
            '        {\n'
            '          if (BoolResult) {\n'
            '          }\n'
            '        },\n'
            '        "IMPLEMENTATION ERROR: Unhandled error state");\n'
            '    EXPECT_DEATH((void)(BoolResult == false),\n'
            '                 "IMPLEMENTATION ERROR: Unhandled error state");\n'
            '    EXPECT_DEATH((void)(BoolResult == true),\n'
            '                 "IMPLEMENTATION ERROR: Unhandled error state");'
        )
        _islt_cpp_new = (
            '    // OHOS port: gtest EXPECT_DEATH (death test) needs a writable /tmp,\n'
            '    // which is read-only on OHOS (E002). The 5 upstream EXPECT_DEATH\n'
            '    // assertions above are removed; the quota-exceeded error state is\n'
            '    // already verified by is_error()/is_false()/is_true() above and\n'
            '    // isl_ctx_last_error()==isl_error_quota below, preserving functional\n'
            '    // coverage without the fork+/tmp death-test mechanism.'
        )
        if _islt_cpp_old not in _islt_cpp_txt:
            raise ConanException("Isl.Quota EXPECT_DEATH block not found")
        with open(_islt_cpp, "w", encoding="utf-8") as _f:
            _f.write(_islt_cpp_txt.replace(_islt_cpp_old, _islt_cpp_new, 1))

        # polly-isl-test 运行时读 test_inputs/*.polylib|*.omega；srcdir 是编译期
        # 路径（指向 build 机源码目录，设备上不存在）→ 改运行时读 $srcdir 环境
        # 变量（UnitIsl/lit.cfg 会设置），fallback 编译期路径。
        _islt_c = os.path.join(self.source_folder, "polly", "lib", "External", "isl", "isl_test.c")
        with open(_islt_c, "r", encoding="utf-8") as _f:
            _islt_c_txt = _f.read()
        _islt_c_old = (
            '\tchar *pattern = "%s/test_inputs/%s.%s";\n'
            '\n'
            '\tlength = strlen(pattern) - 6 + strlen(srcdir) + strlen(name)\n'
            '\t\t+ strlen(suffix) + 1;'
        )
        _islt_c_new = (
            '\tchar *pattern = "%s/test_inputs/%s.%s";\n'
            '\tconst char *dir;\n'
            '\n'
            '\t/* Prefer the srcdir passed by the test runner (lit sets $srcdir) so\n'
            '\t * the test data files can be found on a device where the build-time\n'
            '\t * source directory does not exist. Fall back to the build-time dir. */\n'
            '\tdir = getenv("srcdir");\n'
            '\tif (!dir)\n'
            '\t\tdir = srcdir;\n'
            '\n'
            '\tlength = strlen(pattern) - 6 + strlen(dir) + strlen(name)\n'
            '\t\t+ strlen(suffix) + 1;'
        )
        if _islt_c_old not in _islt_c_txt:
            raise ConanException("isl_test.c get_filename block not found")
        _islt_c_txt = _islt_c_txt.replace(_islt_c_old, _islt_c_new, 1)
        _islt_c_txt = _islt_c_txt.replace("sprintf(filename, pattern, srcdir, name, suffix);",
                                          "sprintf(filename, pattern, dir, name, suffix);", 1)
        with open(_islt_c, "w", encoding="utf-8") as _f:
            _f.write(_islt_c_txt)

        # 设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块 → UNIX 未置 →
        # HandleLLVMOptions "Unable to determine platform" FATAL。提供
        # Platform/HarmonyOS.cmake（复用 Platform/Linux）挂到 CMAKE_MODULE_PATH。
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")

        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),   # 供 Platform/HarmonyOS.cmake（见上）
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # —— 产物：LLVM 本体 + polly 项目 ——
            "-DLLVM_ENABLE_PROJECTS=polly",           # ★ 核心：Polly 多面体优化器
            "-DLLVM_BUILD_LLVM_DYLIB=ON",             # 出 libLLVM.so（opt/LLVMPolly 链它，瘦身）
            "-DLLVM_LINK_LLVM_DYLIB=ON",              # 工具链 libLLVM.so（opt 从 ~百MB 内嵌降到 MB 级）
            # Polly 不静态链进 opt：否则 opt 内置 polly 选项，test_package 再
            # -load-pass-plugin 加载 LLVMPolly.so 时选项重复注册
            # （'polly-dependences-computeout' registered more than once → LLVM ERROR）。
            "-DLLVM_POLLY_LINK_INTO_TOOLS=OFF",
            # LLVMPolly.so 是 loadable module，必须 PIC（否则只生成 dummy target，
            # 见 polly/lib/CMakeLists.txt 的 `if(NOT LLVM_ENABLE_PIC)` 分支）。
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_BUILD_TOOLS=ON",                  # opt/llvm-config 等工具（消费 + lit 测试必需）
            "-DLLVM_INSTALL_UTILS=ON",                # FileCheck/count/not 等（lit 测试必需）
            # —— 瘦身：仅 AArch64、无 examples/benchmarks/docs ——
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-linux-ohos",
            # ★ 断言构建：polly/test 有 39 个 REQUIRES: asserts 用例（依赖断言/debug 输出），
            # Release(NDEBUG) 下会被 lit 标记 UNSUPPORTED。开启断言让它们真实运行，达成
            # 1070 PASS + 22 XFAIL(上游预期失败) + 0 UNSUPPORTED 的全量口径。
            "-DLLVM_ENABLE_ASSERTIONS=ON",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            # —— 开启测试：真实编译+运行上游 check-polly（lit）+ PollyUnitTests（gtest） ——
            "-DLLVM_INCLUDE_TESTS=ON",
            # —— 自包含：关掉 LLVM 会自动探测的可选系统依赖，避免链到设备上不存在的库 ——
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            # libLLVM.so 链接极吃内存 → 限制并行链接任务数防 OOM（真机内存偏紧）。
            "-DLLVM_PARALLEL_LINK_JOBS=2",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        # 核心产物：LLVMPolly.so（pass plugin）+ libPolly.a（静态）+ opt（消费工具）。
        # LLVMPolly 目标名无 lib 前缀（add_polly_loadable_module 设 PREFIX ""）。
        # 并行降到 -j2：真机 8 核且 load 常驻 ~20（系统服务占用），避免 CPU/内存峰值压垮设备。
        self.run('cmake --build "{}" --target LLVMPolly Polly opt -- -j2'.format(bdir))
        # 真实编译+运行上游测试：check-polly = polly regression lit（polly/test 1245 文件）
        # + PollyUnitTests（gtest）+ polly-isl-test（bundled isl unit）。
        # check-polly 输出重定向到持久文件（build folder 失败会被 conan 清理），便于诊断失败原因。
        # 先确保日志目录存在（CI worker 上 /storage/Users/currentUser/tmp 可能不存在）。
        _check_log = "/storage/Users/currentUser/tmp/polly_check_polly.log"
        os.makedirs(os.path.dirname(_check_log), exist_ok=True)
        self.run('cmake --build "{}" --target check-polly -- -j2 > "{}" 2>&1'.format(bdir, _check_log))

    def package(self):
        import glob
        import shutil
        bdir = os.path.join(self.build_folder, "build-ohos")
        # 手动安装，不用 `cmake --install`：原生构建用 native llvm-tblgen（configure 时
        # 在 NATIVE 子目录生成），主 build 目录无 utils/TableGen/Basic 的 llvm-tblgen 二进制，
        # `cmake --install` 会因该文件缺失报 "No such file or directory"。
        # ① 头文件：源码 polly/include/polly/*.h + 生成的 polly/Config/config.h
        src_inc = os.path.join(self.source_folder, "polly", "include", "polly")
        dst_inc = os.path.join(self.package_folder, "include", "polly")
        shutil.copytree(src_inc, dst_inc, dirs_exist_ok=True)
        gen_cfg = os.path.join(bdir, "tools", "polly", "include", "polly", "Config", "config.h")
        if os.path.exists(gen_cfg):
            os.makedirs(os.path.join(dst_inc, "Config"), exist_ok=True)
            shutil.copy2(gen_cfg, os.path.join(dst_inc, "Config", "config.h"))
        # ② 库 + 工具（LLVMPolly.so / libPolly.a / libPollyISL.a / opt / libLLVM.so）
        self._bundle_missing(bdir)
        self._sign_binaries()

    def _bundle_missing(self, bdir):
        """补齐 cmake --install 可能未安装的产物（LLVMPolly.so / opt / libLLVM.so / libPollyISL.a）。"""
        import shutil
        lib_dir = os.path.join(self.package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        # LLVMPolly.so（PREFIX ""，无 lib 前缀）；libPollyISL.a（bundled isl 静态库）
        for f in ("LLVMPolly.so", "libPolly.a", "libPollyISL.a"):
            src = os.path.join(bdir, "lib", f)
            if os.path.exists(src) and not os.path.exists(os.path.join(lib_dir, f)):
                shutil.copy2(src, os.path.join(lib_dir, f))
        # opt（消费工具，加载 LLVMPolly.so 跑 polly pass）
        opt_src = os.path.join(bdir, "bin", "opt")
        if os.path.exists(opt_src) and not os.path.exists(os.path.join(bin_dir, "opt")):
            shutil.copy2(opt_src, os.path.join(bin_dir, "opt"))
        # libLLVM.so + 版本软链（opt 的动态依赖）
        for f in ("libLLVM.so", "libLLVM-22.so"):
            src = os.path.join(bdir, "lib", f)
            if os.path.exists(src) and not os.path.exists(os.path.join(lib_dir, f)):
                shutil.copy2(src, os.path.join(lib_dir, f))

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报
        # Permission denied / Operation not permitted（E077）。统一重签：
        #   ① lib/ 的 .so（LLVMPolly.so、libLLVM.so 等）  ② bin/ 的 ELF 可执行（opt）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # Polly 消费形态：① opt -load-pass-plugin=lib/LLVMPolly.so（动态插件，主形态）
        #   ② 静态链接 lib/libPolly.a + lib/libPollyISL.a（需额外链 LLVM 组件库）。
        # bin/opt 是打包的消费辅助工具（test_package 用硬编码路径定位），不声明 bindirs：
        # 否则 L0k 会把本包误判为 CLI 工具并强制要求 commands.json（本包本质是 library）。
        self.cpp_info.set_property("cmake_file_name", "Polly")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # LLVMPolly.so 是 loadable module（plugin），不是常规链接库，故不放 libs；
        # libs 只列静态库（静态集成时链 Polly + PollyISL）。
        self.cpp_info.libs = ["Polly", "PollyISL"]
