#!/usr/bin/env python3
"""Conan recipe for rna-star 2.7.11b — Spliced Transcripts Alignment to a Reference (Makefile, C++).

STAR（alexdobin/STAR，GPL-3.0）是 RNA-seq 剪接比对工具，上游以纯 `make`
（source/ 下 GNU Makefile）构建，产物为单个命令行可执行文件 `STAR`。自带
htslib 子目录（lib-static 静态构建进 STAR）与可移植 SIMD opal 比对模块。

构建策略（OHOS aarch64，clang 15 + libc++）：
- 上游 Makefile 硬编码 `CXX ?= g++`（`CXXFLAGS ?= -pipe -Wall -Wextra`）；
  经自测 .o 编译规则用裸 `$(CXXFLAGS)`，因此命令行传 `CXX`/`CC`/`CXXFLAGS`
  即完全接管编译（R33 取自 conan conf）。
- E130：OHOS 自定义 libc++-ohos 头要求 C++17 最低，上游默认 `-std=c++11`
  会报 nullptr_t/__abi_tag__ 错误；`.o` 规则用纯 `$(CXXFLAGS)`，传
  `-std=c++17` 即覆盖；链接处 STAR 目标 `CXXFLAGS := ... $(CXXFLAGS)`
  最后出现也以 `-std=c++17` 胜出；opal 规则 `-std=c++11 $(CXXFLAGS)` 同理。
- C++17 移除 `register` 存储类：`SuffixArrayFuns.cpp` 的 7 处
  `register <type> var` 在 clang -std=c++17 下是硬错误，经 conandata 补丁
  移除（0001 补丁，纯 portability，无平台宏）。
- OpenMP：STAR 的 `CXXFLAGS_common` 无条件含 `-fopenmp`（无法关掉），且
  CLI 必须被直接执行。按 knowledge 同款工具链结论，链接给
  `-fopenmp -static-openmp` 让 libomp 静态并入，产出 `DT_NEEDED` 收敛到
  libc/libz 的自包含二进制，规避 clang 默认 RUNPATH 写宿主 resource dir
  导致 `Error loading shared library libomp.so` 启动失败。
- 架构标志：`CXXFLAGS_SIMD ?= -mavx2` 是 x86 专属，aarch64 上传它会直接
  报 unknown target；opal 用 simde_avx2.h（SIMDe 可移植实现）在 aarch64 上
  软件兜底，故命令行传 `CXXFLAGS_SIMD=` 清空该标志即可（无需删 SIMDe）。
- htslib 内嵌（source/htslib，lib-static 静态链进 STAR），需要 zlib.h 与
  `-lz`，故声明 conan 依赖 zlib，并把 zlib include/lib 注入 CPPFLAGS/LDFLAGS
  （STAR own 代码不直接用 zlib，仅 htslib 用）。
- `xxd`：上游 `parametersDefault.xxd: xxd -i parametersDefault`，而 OHOS
  /usr/bin/xxd 是 toybox 实现，`-i` 只输出裸 hex 体、缺 `unsigned char
  parametersDefault[]` 声明与 `parametersDefault_len` 变量（STAR.cpp /
  Parameters.cpp 都 `#include "parametersDefault.xxd"` 并引用这两个符号，
  toybox 输出必编译失败）。因此在 build() 预生成符合 vim-xxd 契约的
  `parametersDefault.xxd`（先于 make 落盘且比 parametersDefault 新，make
  不会触发玩具 xxd 规则）。metaeuk 同款坑。
- 可执行 ELF 需 binary-sign-tool 自签（E077/E082，否则 OHOS 内核拒绝执行），
  package() 逐 bin 自签 + 兜底容错。

上游测试：STAR 无正式测试套件（无 make check/ctest/gtest/测试目录，CI
.travis 仅 `make STAR`）。消费测试真实驱动 STAR --version（exit 0，输出
2.7.11b）与 usage（输出 STAR version=2.7.11b），见 test_package。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RnaStarConan(ConanFile):
    name = "rna-star"
    version = "2.7.11b"
    description = "rna-star — Spliced Transcripts Alignment to a Reference (STAR), RNA-seq aligner"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/alexdobin/STAR"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # 上游为纯 make（source/ 下 GNU Makefile），直接 make；no_copy_source +
    # basic_layout 让 build() 原地在 source_folder 构建产出 STAR（augustus
    # 同款 makefile 打包模式，避免 makefile 就地产物在 build/source 两份之间
    # 的归属歧义）。
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 内嵌 htslib 静态构建需要 zlib.h + -lz（见类级注释）。
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rna-star only supports Linux/OHOS, got {self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"rna-star/2.7.11b is adapted and validated for armv8 only, "
                f"got {self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def generate(self):
        """把 conan 聚合环境脚本的「反激活前导块」切换为函数形态。

        conan 默认（tools.env:deactivation_mode 未设）在 conanbuildenv-<id>.sh
        顶部生成一段**在 source 时立即执行**的反激活前导块：

            for v in LD_LIBRARY_PATH PATH SHELL CONFIG_SHELL
            do
               value=$(printenv $v) || is_defined="" || true   # 每个变量 fork 一个 printenv + 命令替换子 shell
               ...
            done

        这段仅为生成一个本配方从不使用的 deactivate_*.sh，却会在
        `self.run(env="conanbuild")` 展开的 `. conanbuildenv-*.sh` 里对每个
        变量 fork 一次 printenv 与子 shell。真机 worker 进程/内存受限时，
        mksh 在执行到该循环末尾（脚本第 13 行 `done`）即返回 EAGAIN：

            /system/bin/sh: .../conanbuildenv-release-armv8.sh[13]: can't fork - try again

        构建在 conan 环境脚本激活阶段即失败，早于 make 任何一次编译。
        设为 "function" 后，前导块被改写为只**定义**一个反激活函数（source
        时不执行、零 fork），仍完整导出 LD_LIBRARY_PATH/PATH/SHELL/
        CONFIG_SHELL（lld 依赖 LD_LIBRARY_PATH 找 libxml2.so.16，不可用
        env=None 跳过整个 env 文件）。conf 用 define 注入，generate() 在
        conan 自动生成 VirtualBuildEnv 之前运行，故生效。
        """
        self.conf.define("tools.env:deactivation_mode", "function")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _star_src_dir(self):
        """STAR 上游把全部可构建源码（Makefile / *.cpp / parametersDefault /
        htslib 内嵌）放在仓库的 source/ 子目录；strip_root=True 解包后该
        子目录在 source_folder 下（即 <source_folder>/source）。make 与
        parametersDefault 生成、打包都要以此为根，而非 source_folder 根。
        """
        return os.path.join(self.source_folder, "source")

    def _gen_compilation_info_header(self):
        """STAR 上游把 COMPILATION_TIME_PLACE / GIT_BRANCH_COMMIT_DIFF 两个字符串
        宏放在 CXXFLAGS_common，只在链接目标应用；.o 编译规则用裸 $(CXXFLAGS)
        从不带 CXXFLAGS_common，故需在配方 CXXFLAGS 里补一个信息宏。

        但经命令行 `-D'NAME="value"'` 传字符串宏时，外层 self.run 命令串与
        make→shell 的引号层层嵌套，真机 clang 实际收到的 `-D` 值会丢引号
        （得到 `#define COMPILATION_TIME_PLACE harmonyos`，源码里当字符串字面量
        引用即报 undeclared identifier）。为彻底避开引号转义，这里生成一个
        force-include 头文件，用 `-include <abs path>` 把两个宏以 `#define`
        字面量形式固定注入（纯信息输出，固定值即可）。
        """
        header_path = os.path.join(self._star_src_dir(), ".hmbs_compilation_info.h")
        content = (
            "#ifndef HMBS_COMPILATION_INFO_H\n"
            "#define HMBS_COMPILATION_INFO_H\n"
            '#define COMPILATION_TIME_PLACE "harmonyos"\n'
            '#define GIT_BRANCH_COMMIT_DIFF "none"\n'
            "#endif\n"
        )
        with open(header_path, "w", encoding="ascii") as f:
            f.write(content)
        self.output.info(
            f"generated force-include {os.path.relpath(header_path, self._star_src_dir())} "
            f"(avoid shell-quoting of string -D macros)")
        return header_path

    def _gen_parameters_default_xxd(self):
        """上游 `xxd -i parametersDefault > parametersDefault.xxd` 依赖 vim-xxd
        的输出契约（`unsigned char parametersDefault[]` + `parametersDefault_len`），
        OHOS toybox xxd 只产裸 hex 体。此处用 Python 生成 vim-xxd 等价头文件，
        先于 make 落盘（mtime 晚于 parametersDefault，make 视其最新不触发玩具
        xxd 规则）。STAR.cpp / Parameters.cpp 都 include 该头并引用这两个符号。
        """
        src = self._star_src_dir()
        data_path = os.path.join(src, "parametersDefault")
        if not os.path.isfile(data_path):
            raise OSError(f"parametersDefault not found at {data_path}")
        with open(data_path, "rb") as f:
            data = f.read()
        lines = []
        for i in range(0, len(data), 12):
            lines.append("  " + ", ".join("0x%02x" % b for b in data[i:i + 12]) + ",")
        xxd = "unsigned char parametersDefault[] = {\n" + "\n".join(lines) + "\n};\n"
        xxd += "unsigned int parametersDefault_len = %d;\n" % len(data)
        out_path = os.path.join(src, "parametersDefault.xxd")
        with open(out_path, "w", encoding="ascii") as f:
            f.write(xxd)
        self.output.info(
            f"generated {os.path.relpath(out_path, src)} (vim-xxd contract, "
            f"{len(data)} bytes, toybox-xxd workaround)")

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "/data/service/hnp/bin/clang")
        cxx = compilers.get("cpp", "/data/service/hnp/bin/clang++")

        stdlib = "-stdlib=libc++" if str(self.settings.compiler.libcxx) == "libc++" else ""

        # zlib include/lib 来自 conan 依赖（htslib 需要 zlib.h，STAR 链接 -lz）。
        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_inc = " ".join(f"-I{d}" for d in zlib_info.includedirs)
        zlib_lib = " ".join(f"-L{d}" for d in zlib_info.libdirs)

        # OHOS 无 /bin/sh（mksh 不能执行 ELF），make 内部 shell 用 hnp bash。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # 先于 make 生成 vim-xxd 契约的 parametersDefault.xxd（toybox xxd 坑）。
        self._gen_parameters_default_xxd()

        # 生成 force-include 头，把 COMPILATION_TIME_PLACE / GIT_BRANCH_COMMIT_DIFF
        # 两个字符串信息宏以 #define 字面量注入（避开经 make→shell 传 `-D'N="v"'`
        # 时引号被剥、clang 收到裸标识符导致的 undeclared identifier）。
        compilation_header = self._gen_compilation_info_header()

        # .o 编译规则用裸 $(CXXFLAGS)（覆盖上游 ?= -pipe -Wall -Wextra），
        # 故在此完整携带上游等价开关 + E130 的 c++17 + hnp 缺省头路径的
        # -stdlib=libc++ + OpenMP。CXXFLAGS_SIMD 清空以去掉 x86 专属 -mavx2。
        #
        # 上游 Makefile 把 COMPILATION_TIME_PLACE / GIT_BRANCH_COMMIT_DIFF 两个
        # 信息宏放在 CXXFLAGS_common，仅在链接目标（STAR）里应用；但 .o 编译规则
        # 是裸 $(CXXFLAGS)，从不带 CXXFLAGS_common，导致 STAR.cpp / Parameters.cpp
        # 在 .o 阶段报“未声明”。因此这里用 -include 强制注入（而非 -D 字符串宏，
        # 后者经引号层层嵌套在真机 clang 会丢引号）。
        cxxflags = " ".join(f for f in [
            f"-include {compilation_header}",
            "-O3", "-std=c++17", stdlib, "-fopenmp", "-static-openmp", "-Wall",
        ] if f)
        ldflags = " ".join(f for f in [stdlib, zlib_lib] if f)

        # zlib include 必须通过「环境变量」而非 make 命令行变量注入：STAR 顶层
        # make 通过 $(MAKE) -C htslib 递归构建内嵌 htslib，其 Makefile 用
        # `CPPFLAGS += -I. -DSAMTOOLS=1` 补自己的头路径；若把 CPPFLAGS 作为
        # make 命令行变量传入，GNU Make 会忽略子 makefile 的 `+=`（命令行变量
        # 覆盖一切），导致 htslib 编译缺 `-I.` 而报 `cram/sam_header.h not found`。
        # 改为 `CPPFLAGS="..." make ...` 的 env 前缀形式后，子 makefile 的
        # `+=` 正常叠加，得到 `<zlib_inc> -I. -DSAMTOOLS=1`。
        #
        # LDFLAGS 同理必须走 env 前缀而非 make 命令行变量：上游 Makefile 的
        # `STAR: LDFLAGS := $(LDFLAGSextra) $(LDFLAGS_shared) $(LDFLAGS)` 靠
        # target-specific 赋值把 `-Lhtslib -Bstatic -lhts -Bdynamic -lz` 并入
        # 链接；但 GNU Make 规定「target-specific 变量值不覆盖命令行变量」，
        # 一旦 LDFLAGS 作为 make 命令行变量传入，该 target-specific 赋值被整条
        # 丢弃，链接只剩本配方的 LDFLAGS（-stdlib=libc++ -L<zlib>），缺 -lhts，
        # 导致 ld.lld 报大量 bgzf_*/bam_*（htslib）未定义。改为 env 前缀后，
        # target-specific 赋值正常覆盖 env 值，链接得到
        # `-pthread -Lhtslib -Bstatic -lhts -Bdynamic -lz -stdlib=libc++ -L<zlib>`。
        #
        # Depend.list 是上游 Makefile 的「头文件依赖清单」，由一条规则一次性把
        # 全部 ~190 个源文件喂给单个 `$(CXX) -MM` 生成：
        #   Depend.list: $(SOURCES) parametersDefault.xxd htslib
        #       $(CXX) $(CXXFLAGS_common) -MM $^ >> Depend.list
        # clang 处理多输入时会为每个源文件 fork 一个 `-cc1` 子进程，真机 worker
        # 进程/内存受限，成批 posix_spawn 直接返回 EAGAIN：
        #   clang-15: error: unable to execute command: posix_spawn failed:
        #             Resource temporarily unavailable
        # 规则失败 → make 删除半成品 Depend.list → 后续 `include Depend.list`
        # 报 `Makefile:138: Depend.list: No such file or directory` 并 Error 1。
        # Depend.list 只服务增量重编译，全新构建并不需要它；用 `-o Depend.list`
        # 告诉 make 把该目标当作「已是最新、不要重建」（GNU make 对缺失但可重建的
        # include 文件在有 -o 时静默跳过，不报错），从而彻底绕开这条高 fork 规则。
        #
        # 代价：Depend.list 同时也是 htslib 的唯一触发点
        # （`Depend.list: ... htslib`），跳过它后内嵌 htslib 不会自动构建，链接
        # 会缺 `-lhts`；故显式追加 `htslib` 作为 make 目标，先构建 libhts.a。
        self.run(
            f'CPPFLAGS="{zlib_inc}" LDFLAGS="{ldflags}" '
            f'make -j1 -o Depend.list htslib all '
            f'SHELL="{bash}" CC="{cc}" CXX="{cxx}" '
            f'CXXFLAGS="{cxxflags}" CFLAGS="-O3" '
            f'CXXFLAGS_SIMD=',
            cwd=self._star_src_dir(),
            env=["conanbuild"],
        )

    def package(self):
        # 打包 STAR 可执行文件（上游无 install 目标，直接打包产物。
        # STAR 由 source/ 子目录的 make 产出，故从其构建目录拷贝）。
        copy(self, "STAR", src=self._star_src_dir(),
             dst=os.path.join(self.package_folder, "bin"))
        # 许可证文件（位于仓库根，source_folder 根下）
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # OHOS 内核要求可执行 ELF 含有效 .codesign 段（E077/E082），否则
        # test_package 执行 bin/STAR 报 Operation not permitted。工具缺失则
        # 跳过签名（preflight worker 工具链缺件场景，CI worker 具备时正常签名）。
        if str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            sign_available = os.path.isfile(sign_tool) and os.path.isfile(objcopy)
            bin_dir = os.path.join(self.package_folder, "bin")
            for name in os.listdir(bin_dir):
                bin_path = os.path.join(bin_dir, name)
                if not os.path.isfile(bin_path):
                    continue
                try:
                    os.chmod(bin_path, 0o755)
                except OSError:
                    pass
                if not sign_available:
                    self.output.info(
                        f"binary-sign-tool not found, skipping ELF signing for {name}")
                    continue
                tmp_signed = bin_path + ".signed"
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{bin_path}" 2>/dev/null || true',
                    quiet=True)
                self.run(
                    f'"{sign_tool}" sign -inFile "{bin_path}" -outFile "{tmp_signed}" '
                    f'-selfSign 1',
                    quiet=True)
                os.replace(tmp_signed, bin_path)
                os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
