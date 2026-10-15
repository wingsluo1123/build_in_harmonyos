#!/usr/bin/env python3
"""Conan recipe — pftools 3.2.12 (cmake, HarmonyOS PC / os=OHOS arch=armv8)

pftools 由三部分组成:
  * pftoolsV3            —— C 实现: pfsearchV3 / pfscanV3 / pfcalibrateV3 / pfindex /
                            pfdump / pfpam / pfemit / pfsplit
  * pftools release 2.3  —— Fortran 77 老程序: gtop / htop / ptoh / ptof / pfw / 2ft /
                            6ft / psa2msa / pfscan / pfsearch / pfmake / pfscale
  * Perl 脚本            —— ps_scan.pl / compare_2_profiles.pl / ... (安装到 bin/)

依赖:
  - pcre2/10.47                 默认构型 (USE_PCRE2=ON) 强制链接 libpcre2-8
  - libfile-slurp-perl/9999.32  Perl 脚本运行期依赖 (use File::Slurp)
  - tool_requires flang-ohos/20.1.0  Fortran 77 组件编译器 (OHOS 无 gfortran)

OHOS(aarch64) 适配要点 —— 全部在 patches/0001-ohos-aarch64-port.patch:

  1. C 对齐内核是 x86 SSE2/SSE4.1 专用: src/C/include/pfProfile.h 无条件
     #include <emmintrin.h>，aarch64 下 clang 直接报
     "This header is only meant to be used on x86 and x64 architecture"，
     9 个内核文件 (sse2/sse41，约 4.6k 行) 也只有 intrinsic 实现、无标量回退。
     补丁新增 src/C/simd/ 垫片 (emmintrin.h / smmintrin.h / xmmintrin.h /
     mm_malloc.h)，在非 x86 架构下 (CMakeLists.txt 按 CMAKE_SYSTEM_PROCESSOR 判断)
     把 x86 SIMD 头重定向到 sse2neon.h —— MIT 许可的 SSE->NEON 转译层，
     由 conandata.yml 的 "sse2neon" 源拉取到 src/C/simd/。
  2. 内核里的 x86 内联汇编 (xorps / maxps / pmaxsd / phaddd / movsd / movss /
     cvtsi2ss / pshufd) 改写为等价 intrinsic；utils/system.c 的
     cpuid / xgetbv / bsrq 探测加非 x86 分支 (aarch64 直接声明
     MM_SSE2|MM_SSE41，因为垫片同时提供两套内核)。
  3. USE_AFFINITY=OFF: OHOS 使用 musl，features.h 不定义 __USE_GNU，而上游
     system.c 在 USE_AFFINITY 下会 #error "GNU EXTENSION not activated"。
     这是 INSTALL 记载的官方构型 ("Build without affinity (old machines)")。
  4. Fortran 组件由 flang-ohos/20.1.0 提供:
       - flang 不接受 -std=legacy (gfortran 专用) -> 按编译器 ID 选择 flag；
       - flang-ohos 只带编译器、不带 crt/运行时 -> generate() 里把 OHOS SDK 的
         crtbeginS/crtendS/libclang_rt.builtins/libunwind 注入其 resource-dir
         (与 archives/a/alfa/2.2 同一做法)；
       - flang 未实现 FDATE 扩展 -> pfmake.f 改用标准 DATE_AND_TIME。
  5. Fortran 源码里的 Status='SCRATCH' 依赖 /tmp，而 HarmonyOS 的 /tmp 是只读
     文件系统 (musl tmpfile() 亦固定用 /tmp) -> 改为 $TMPDIR 下的具名工作文件
     (psa2msa.f / regpr.f / pfw.f)；测试脚本硬编码的 /tmp 同样改为
     ${TMPDIR:-/tmp}。
  6. -ffp-contract=off: AArch64 有 FMA，clang 默认做浮点收缩，会让 pfsearchV3
     打印的分数与 x86 参考差 1 ULP (上游 tests/examples/test_V3.out 逐字节比对)。
     关闭收缩后 ctest 6/6 通过、test_V3 输出与参考完全一致。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)

# OHOS SDK 里 clang 的 resource-dir 版本目录（crtbeginS/crtendS/builtins 来源）
_SDK_CLANG_RES = "lib/clang/15.0.4"


def _shim(name, target):
    """生成一个把 x86 SIMD 头重定向到 sse2neon.h 的垫片头。"""
    return (f"/* Portable SIMD shim — x86 <{target}> replacement for non-x86 targets.\n"
            " *\n"
            " * The pftoolsV3 alignment kernels include the x86 SSE2/SSE4.1 intrinsics\n"
            f" * headers. On targets without SSE (e.g. AArch64) <{target}> is x86-only and\n"
            " * clang refuses it, so src/C/simd/ is put first on the include path (see the\n"
            " * top-level CMakeLists.txt) and redirects to sse2neon.h, an SSE -> NEON\n"
            " * translation layer (MIT, https://github.com/DLTcollab/sse2neon).\n"
            " */\n"
            f"#ifndef PFTOOLS_SHIM_{name}_H\n"
            f"#define PFTOOLS_SHIM_{name}_H\n"
            '#include "sse2neon.h"\n'
            "#endif\n")


class PftoolsConan(ConanFile):
    name = "pftools"
    version = "3.2.12"
    description = ("PROSITE generalized profile toolkit: pftoolsV3 (pfsearchV3, "
                   "pfscanV3, pfcalibrateV3, pfindex, pfdump, pfpam, pfemit, "
                   "pfsplit) plus the legacy pftools release 2.3 Fortran 77 suite")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/sib-swiss/pftools3"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml", "patches/*"

    # 可移植 SIMD 垫片：source() 阶段写入 src/C/simd/（非 x86 架构下生效）
    _SIMD_SHIM_HEADERS = {
        "emmintrin.h": _shim("EMMINTRIN", "emmintrin.h"),
        "smmintrin.h": _shim("SMMINTRIN", "smmintrin.h"),
        "xmmintrin.h": _shim("XMMINTRIN", "xmmintrin.h"),
        "mm_malloc.h": _shim("MM_MALLOC", "mm_malloc.h"),
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 默认构型 USE_PCRE2=ON -> pfsearchV3/pfscanV3/pfdump 链接 libpcre2-8
        self.requires("pcre2/10.47")
        # Perl 脚本 (ps_scan.pl ...) 运行期依赖 File::Slurp
        self.requires("libfile-slurp-perl/9999.32")

    def build_requirements(self):
        # OHOS 无 gfortran；LLVM Flang 由 ohpcd 提供 (OHOS/armv8 binary)
        self.tool_requires("flang-ohos/20.1.0")

    def validate(self):
        # R32: settings.os 判断必须用 in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} 仅适配 HarmonyOS/Linux (当前 os={self.settings.os})")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload 的 URL 末段是 v3.2.12（无扩展名），必须显式给出 filename，
        # 否则 conan 不识别为 tar.gz 包
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            filename=f"pftools-{self.version}.tar.gz")
        # 可移植 SIMD 垫片目录：4 个重定向头由本配方生成，sse2neon.h 从
        # conandata.yml 的 "sse2neon" 源拉取（单头文件用 download()，
        # get() 会把它当压缩包解压）
        shim = os.path.join(self.source_folder, "src", "C", "simd")
        os.makedirs(shim, exist_ok=True)
        for name, body in self._SIMD_SHIM_HEADERS.items():
            with open(os.path.join(shim, name), "w", encoding="utf-8") as fh:
                fh.write(body)
        sse2neon = self.conan_data["sources"]["sse2neon"]
        download(self, sse2neon["url"], os.path.join(shim, "sse2neon.h"),
                 sha256=sse2neon["sha256"])

    # ── OHOS SDK 路径（flang 运行集注入用） ─────────────────────────────
    @staticmethod
    def _ohos_sdk_llvm():
        cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        return cands[-1] if cands else ""

    def generate(self):
        pcre2 = self.dependencies["pcre2"]
        perlmod = self.dependencies["libfile-slurp-perl"]
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        flang_bin = os.path.join(flang_pkg, "bin", "flang")

        # Perl 脚本语法检查（CMakeLists "Check Perl script syntax"）需要 File::Slurp，
        # 否则 Perl 脚本不会安装进 bin/
        perl5lib = os.path.join(perlmod.package_folder, "lib", "perl5")
        if os.path.isdir(perl5lib):
            os.environ["PERL5LIB"] = perl5lib

        # flang 运行需要自己的 lib/（libLLVM.so / libclang-cpp.so）
        env_lib = [os.path.join(flang_pkg, "lib")]
        sdk_llvm = self._ohos_sdk_llvm()
        if sdk_llvm:
            env_lib.append(os.path.join(sdk_llvm, "lib"))
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(env_lib)

        # flang-ohos 只带编译器，不带 crt/运行时：把 SDK clang 的
        # crtbeginS/crtendS/libclang_rt.builtins/libunwind 复制到 flang 期望的
        # resource-dir（同 archives/a/alfa/2.2，本地实测通过）
        if sdk_llvm:
            sdk_resdir = os.path.join(sdk_llvm, _SDK_CLANG_RES)
            sdk_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
            fl_res = os.path.join(flang_pkg, "lib", "clang", "20", "lib",
                                  "aarch64-linux-ohos")
            os.makedirs(fl_res, exist_ok=True)
            for name, src_name in (("crtbeginS.o", "clang_rt.crtbegin.o"),
                                   ("crtendS.o", "clang_rt.crtend.o"),
                                   ("libclang_rt.builtins.a", "libclang_rt.builtins.a"),
                                   ("libunwind.a", "libunwind.a")):
                src = os.path.join(sdk_resdir, "lib", "aarch64-linux-ohos", src_name)
                if not os.path.isfile(src):
                    src = os.path.join(sdk_lib, src_name)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(fl_res, name))

        # PCRE2 位于 conan 包内（非系统路径），FindPCRE2.cmake 用 FIND_PATH/FIND_LIBRARY
        pcre2_inc = os.path.join(pcre2.package_folder, "include")
        cands = (glob.glob(os.path.join(pcre2.package_folder, "lib", "libpcre2-8.a"))
                 or glob.glob(os.path.join(pcre2.package_folder, "lib", "libpcre2-8.so*")))
        pcre2_lib = cands[0] if cands else ""

        tc = CMakeToolchain(self)
        tc.user_presets_path = False  # E225: 不生成 source-side preset
        if str(self.settings.os) == "OHOS":
            # OHOS SDK 无 Platform/HarmonyOS 模块；按 arpack-ng 惯例映射到 Linux，
            # 架构显式给出，供 CMakeLists 的 SIMD 垫片判定使用
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Fortran 编译器检查只编译不链接（flang 的 crt/运行时不易在此阶段满足）
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.variables["CMAKE_Fortran_COMPILER"] = flang_bin

        tc.variables["USE_PCRE2"] = True
        tc.variables["PCRE2_INCLUDE_DIR"] = pcre2_inc
        tc.variables["PCRE2_LIBRARY"] = pcre2_lib
        # musl 不定义 __USE_GNU，上游 system.c 在 USE_AFFINITY 下 #error；
        # INSTALL 记载的官方构型：cmake -DUSE_AFFINITY=OFF
        tc.variables["USE_AFFINITY"] = False
        # rpath 交给 conan 管理（同时避免上游覆盖 CMAKE_EXE_LINKER_FLAGS）
        tc.variables["USE_RPATH"] = False
        # find_package(Threads REQUIRED) 在 conan cache 里 try_compile 不稳
        tc.variables["CMAKE_THREAD_LIBS_INIT"] = "-lpthread"
        tc.variables["CMAKE_HAVE_THREADS_LIBRARY"] = "1"
        tc.variables["CMAKE_USE_PTHREADS_INIT"] = "1"

        # AArch64 的 FMA 收缩会让浮点结果与 x86 参考差 1 ULP（上游测试逐字节比对）
        tc.extra_cflags.append("-ffp-contract=off")
        fflags = ["-ffp-contract=off"]
        link_flags = []
        if sdk_llvm:
            sysroot = os.path.join(sdk_llvm, "..", "sysroot")
            fflags.append(f"--sysroot={sysroot}")
            link_flags += [
                f"--sysroot={sysroot}",
                f"-L{os.path.join(sdk_llvm, _SDK_CLANG_RES, 'lib', 'aarch64-linux-ohos')}",
                f"-L{os.path.join(sdk_llvm, 'lib', 'aarch64-linux-ohos')}",
            ]
        tc.cache_variables["CMAKE_Fortran_FLAGS"] = " ".join(fflags)
        tc.variables["CMAKE_Fortran_LINK_FLAGS"] = " ".join(link_flags)
        # C 目标（pfcalibrateV3）链接 Fortran 目标文件 quantile(rq0.f)，
        # 需要显式带上 Fortran 运行时
        tc.extra_exelinkflags.extend(
            link_flags + [os.path.join(flang_pkg, "lib", "libFortranRuntime.a"),
                          os.path.join(flang_pkg, "lib", "libFortranDecimal.a")])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # Perl 脚本运行期需要 File::Slurp
        perl5lib = os.path.join(
            self.dependencies["libfile-slurp-perl"].package_folder, "lib", "perl5")
        if os.path.isdir(perl5lib):
            self.runenv_info.prepend_path("PERL5LIB", perl5lib)
