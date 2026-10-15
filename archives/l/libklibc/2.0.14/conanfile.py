#!/usr/bin/env python3
"""Conan recipe for klibc 2.0.14 — 最小化 libc 子集（initramfs 用），HarmonyOS PC aarch64。

klibc 是面向 Linux initramfs 早期用户空间的最小 C 库实现（libc 本体，零外部库依赖）。
适配要点：
- 上游构建系统是 kernel-style kbuild（自定义 Makefile，非 autotools/cmake），
  通过 ``KLIBCARCH`` 与 ``CC``/``AR``/``LD`` 等变量交叉编译。
- 构建硬依赖 Linux UAPI 头（``KLIBCKERNELSRC``）；OHOS SDK sysroot 提供 ``linux/`` 与
  ``asm-generic/`` 头，但 asm 头位于 ``aarch64-linux-ohos/asm``（非标准 ``asm-arm64``）。
  patch 0001 通过 ``KLIBCASMDIR`` 变量适配该布局，并把符号链接改为 ``cp -rf`` 复制
  （规避 HMDFS 符号链接限制，同时物化 asm 头供 package 打包）。
- 构建还需 perl（syscalls.pl/makeerrlist.pl 生成 syscall 桩与 errlist）与 HOSTCC
  （编译 fixdep/sha1hash 主机工具）；HarmonyOS 无 gcc/ar，改用 clang/llvm-*。
- 用 Conan copy 手动打包，不用 ``make install``（HarmonyOS 无 GNU install，见知识库 E098）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class KlibcConan(ConanFile):
    name = "libklibc"
    version = "2.0.14"
    description = "libklibc — the klibc minimal C library for HarmonyOS PC"
    license = "MIT AND BSD-3-Clause AND GPL-2.0-only"
    homepage = "https://www.kernel.org/pub/linux/libs/klibc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # klibc 核心产物是静态库（libc.a + crt0.o），也构建共享库；用 static-library
    # 避免 Conan 2.x 对 library 强制要求 shared option。
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    # conan arch -> klibc KLIBCARCH
    _ARCH_MAP = {
        "armv8": "arm64",
        "armv7": "arm",
        "armv6": "arm",
        "x86_64": "x86_64",
        "x86": "i386",
        "ppc64le": "ppc64",
        "ppc64": "ppc64",
        "riscv64": "riscv64",
    }

    # KLIBCARCH -> OHOS asm 头目录名（相对 sysroot/usr/include）
    _ASM_DIR_MAP = {
        "arm64": "aarch64-linux-ohos/asm",
        "arm": "arm-linux-ohos/asm",
        "x86_64": "x86_64-linux-ohos/asm",
        "i386": "i686-linux-ohos/asm",
    }

    def _klibc_arch(self):
        return self._ARCH_MAP.get(str(self.settings.arch), str(self.settings.arch))

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # klibc 是 libc 本体，零外部库依赖（仅构建期依赖内核 UAPI 头 + 工具链 + perl）。
        pass

    def layout(self):
        basic_layout(self)
        # klibc 在源码树内构建（kernel-style kbuild 产物输出到源码树）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- 工具链与 sysroot 探测 ----

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return {
            "cc": compilers.get("c", "clang"),
            "cxx": compilers.get("cpp", "clang++"),
        }

    def _tool(self, cc, name):
        """Prefer LLVM tools beside CC; fall back to PATH for brew-installed tools."""
        cc_dir = os.path.dirname(cc)
        if cc_dir:
            candidate = os.path.join(cc_dir, name)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(name) or name

    def _find_sysroot(self, cc):
        """探测 OHOS sysroot。

        OHOS clang 不支持 ``--print-sysroot``，故优先用 ``--print-resource-dir`` 推导：
        resource dir 形如 ``.../native/llvm/lib/clang/<ver>``，向上 4 级到 ``native``，
        再取 ``native/sysroot``。其余方式作为回退。
        """
        # 1) --print-resource-dir
        try:
            rd = subprocess.check_output(
                [cc, "--print-resource-dir"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if rd:
                d = os.path.normpath(rd)
                for _ in range(4):
                    d = os.path.dirname(d)
                sr = os.path.join(d, "sysroot")
                if os.path.isdir(os.path.join(sr, "usr", "include")):
                    return sr
        except Exception:
            pass
        # 2) --print-sysroot（部分 clang 支持）
        try:
            out = subprocess.check_output(
                [cc, "--print-sysroot"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if out and os.path.isdir(os.path.join(out, "usr", "include")):
                return out
        except Exception:
            pass
        # 3) 从 clang 路径推导常见布局
        cc_dir = os.path.dirname(os.path.abspath(cc))
        for rel in (("..", "sysroot"), ("..", "..", "sysroot")):
            c = os.path.normpath(os.path.join(cc_dir, *rel))
            if os.path.isdir(os.path.join(c, "usr", "include")):
                return c
        return None

    def _find_asm_dir(self, sysroot, arch):
        """探测 asm 头目录（相对 sysroot/usr/include）。"""
        inc = os.path.join(sysroot, "usr", "include")
        preferred = self._ASM_DIR_MAP.get(arch)
        if preferred and os.path.isdir(os.path.join(inc, preferred)):
            return preferred
        for name in ("aarch64-linux-ohos/asm", "asm-arm64", "asm"):
            if os.path.isdir(os.path.join(inc, name)):
                return name
        return None

    def build(self):
        apply_conandata_patches(self)
        arch = self._klibc_arch()
        cc = self._compilers()["cc"]
        tools = {
            "ar": self._tool(cc, "llvm-ar"),
            "ranlib": self._tool(cc, "llvm-ranlib"),
            "strip": self._tool(cc, "llvm-strip"),
            "nm": self._tool(cc, "llvm-nm"),
            "objcopy": self._tool(cc, "llvm-objcopy"),
            "objdump": self._tool(cc, "llvm-objdump"),
            "readelf": self._tool(cc, "llvm-readelf"),
            "ld": self._tool(cc, "ld.lld"),
            "perl": self._tool(cc, "perl"),
        }
        sysroot = self._find_sysroot(cc)
        if not sysroot:
            raise ConanInvalidConfiguration(
                "OHOS sysroot not found; cannot satisfy klibc KLIBCKERNELSRC "
                "(Linux UAPI headers) dependency"
            )
        asmdir = self._find_asm_dir(sysroot, arch)
        if not asmdir:
            raise ConanInvalidConfiguration(
                f"OHOS asm UAPI headers not found under {sysroot}/usr/include"
            )

        # 创建干净的 UAPI 头目录：只含 linux/asm/asm-generic，排除 OHOS musl 头
        # （sysroot 的 stdarg.h/stdlib.h 依赖 bits/alltypes.h，若直接 -I sysroot/include
        #  会通过 #include_next 误 include musl 头导致污染）。
        kh = os.path.join(self.build_folder, "kernel-headers")
        kh_inc = os.path.join(kh, "include")
        os.makedirs(kh_inc, exist_ok=True)
        inc_root = os.path.join(sysroot, "usr", "include")
        shutil.copytree(os.path.join(inc_root, "linux"), os.path.join(kh_inc, "linux"))
        shutil.copytree(os.path.join(inc_root, "asm-generic"),
                        os.path.join(kh_inc, "asm-generic"))
        # asm 头（OHOS 布局 aarch64-linux-ohos/asm），复制为 asm/ 供 <asm/*.h> 使用
        shutil.copytree(os.path.join(inc_root, asmdir), os.path.join(kh_inc, "asm"))
        # 同时物化到源码树 usr/include/asm（顶层 make 不触发 usr/include 的 always 目标）
        asm_dst = os.path.join(self.source_folder, "usr", "include", "asm")
        if os.path.isdir(asm_dst):
            shutil.rmtree(asm_dst)
        shutil.copytree(os.path.join(kh_inc, "asm"), asm_dst)
        # 物化 asm-generic（asm 头会 #include <asm-generic/xxx.h>，package 需一并打包）
        ag_dst = os.path.join(self.source_folder, "usr", "include", "asm-generic")
        if os.path.isdir(ag_dst):
            shutil.rmtree(ag_dst)
        shutil.copytree(os.path.join(kh_inc, "asm-generic"), ag_dst)
        # 物化 linux（klibc 头会 #include <linux/xxx.h>，package 需一并打包）
        linux_dst = os.path.join(self.source_folder, "usr", "include", "linux")
        if os.path.isdir(linux_dst):
            shutil.rmtree(linux_dst)
        shutil.copytree(os.path.join(kh_inc, "linux"), linux_dst)

        # KLIBCKERNELSRC 指向干净目录（其下有 include/linux、include/asm-generic、include/asm）。
        kernelsrc = kh

        # arm64 交叉链接：clang 编译需显式 target；ld.lld 直接链接需 emulation。
        # （kbuild 已探测 LD_IS_LLD 自动切换 --image-base/-Ttext-segment。）
        extra_cflags = ""
        extra_ldflags = ""
        if arch == "arm64":
            extra_cflags = "--target=aarch64-linux-ohos"
            extra_ldflags = "-m aarch64linux"
        elif arch == "x86_64":
            extra_cflags = "--target=x86_64-linux-ohos"
            extra_ldflags = "-m elf_x86_64"
        elif arch == "i386":
            extra_cflags = "--target=i686-linux-ohos"
            extra_ldflags = "-m elf_i386"

        make_vars = (
            f'KLIBCARCH={arch} '
            f'KLIBCKERNELSRC="{kernelsrc}" '
            f'KLIBCASMDIR="{asmdir}" '
            f'CC="{cc}" HOSTCC="{cc}" '
            f'AR="{tools["ar"]}" RANLIB="{tools["ranlib"]}" '
            f'STRIP="{tools["strip"]}" NM="{tools["nm"]}" '
            f'OBJCOPY="{tools["objcopy"]}" OBJDUMP="{tools["objdump"]}" '
            f'LD="{tools["ld"]}" PERL="{tools["perl"]}" '
            f'EXTRA_KLIBCCFLAGS="{extra_cflags}" '
            f'EXTRA_KLIBCLDFLAGS="{extra_ldflags}" '
        )
        # HarmonyOS 的 HMDFS 不允许 GNU make 创建 jobserver FIFO。清除外层
        # MAKEFLAGS 并强制单 job，避免递归 Kbuild 在 jobserver 不可用时失控地
        # 并发启动 /bin/sh、cut 和 clang 子进程。
        # 只构建 klcc + libc 本体（all 目标）；usr/dash、usr/gzip、usr/kinit、usr/utils
        # 是额外工具，不属于 libc 本体，避免引入多余构建复杂度。
        self.run(f"MAKEFLAGS= make {make_vars} -j1", env="conanbuild")
        # Clang 的 malloc/calloc builtins 会改写 zero-size / overflow 边界测试，
        # 使上游测试观测到编译器假设而非 klibc 实现；只对测试目标关闭这两个 builtin。
        test_make_vars = make_vars.replace(
            f'EXTRA_KLIBCCFLAGS="{extra_cflags}"',
            f'EXTRA_KLIBCCFLAGS="{extra_cflags} -fno-builtin-malloc -fno-builtin-calloc"',
        )
        if test_make_vars == make_vars:
            raise ConanException("failed to add malloc/calloc test compiler flags")
        # 构建上游测试程序（usr/klibc/tests，static + shared 版本）。
        self.run(f"MAKEFLAGS= make {test_make_vars} -j1 test", env="conanbuild")
        self._run_upstream_tests(cc, tools, arch)

    def _relink_test_elf(self, cc, tools, arch, testdir, name):
        """Link a Kbuild test object through OHOS clang so the ELF has .codesign.

        klibc's Kbuild invokes ld.lld directly, which omits the codesign section
        emitted by the HarmonyOS clang driver. Re-link the same upstream object,
        crt0.o and libc.a with clang; this keeps the upstream test logic intact.
        """
        target = {
            "arm64": "--target=aarch64-linux-ohos",
            "x86_64": "--target=x86_64-linux-ohos",
            "i386": "--target=i686-linux-ohos",
        }.get(arch, "")
        libsrc = os.path.join(self.source_folder, "usr", "klibc")
        testobj = os.path.join(testdir, f"{name}.o")
        crt0 = os.path.join(libsrc, "arch", arch, "crt0.o")
        libc = os.path.join(libsrc, "libc.a")
        linked = os.path.join(testdir, f"{name}.clang")
        for path in (testobj, crt0, libc):
            if not os.path.isfile(path):
                raise ConanException(f"cannot re-link upstream test; missing {path}")
        builtins = subprocess.check_output(
            [cc, *([target] if target else []), "-print-libgcc-file-name"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        if not builtins or not os.path.isfile(builtins):
            raise ConanException("clang compiler-rt builtins archive not found")
        self.run(
            f'"{cc}" {target} -nostdlib -nostdinc -static -no-pie '
            f'-Wl,-e,_start -o "{linked}" "{crt0}" "{testobj}" '
            f'-Wl,--start-group "{libc}" "{builtins}" -Wl,--end-group',
            env="conanbuild",
        )
        sections = subprocess.check_output(
            [tools["readelf"], "-S", linked], text=True, stderr=subprocess.STDOUT
        )
        if ".codesign" not in sections:
            raise ConanException(f"OHOS clang did not add .codesign to {name}")
        os.replace(linked, os.path.join(testdir, name))

    def _run_upstream_tests(self, cc, tools, arch):
        """运行 usr/klibc/tests 下全部 39 个静态程序并强制要求 39/39。

        测试程序是 klibc 静态链接的 ELF（Linux syscall ABI）；Kbuild 直接调用 ld.lld，
        因此用 OHOS clang driver 重链同一组 upstream object/crt0/libc 以加入 .codesign。
        make test 编译时关闭 malloc/calloc compiler builtins，防止 Clang 改写库实现边界测试。
        testrand48 是输出向量程序，按其确定性输出校验
        （上游源码故意返回 1）；其余测试必须返回 0，任何跳过或未构建均阻断出包。
        """
        testdir = os.path.join(self.source_folder, "usr", "klibc", "tests")
        if not os.path.isdir(testdir):
            raise ConanException(f"upstream test directory missing: {testdir}")
        names = sorted(
            os.path.splitext(f)[0] for f in os.listdir(testdir) if f.endswith(".c")
        )
        if len(names) != 39:
            raise ConanException(
                f"expected 39 upstream test programs, found {len(names)}"
            )
        outdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(outdir, exist_ok=True)
        # 需要命令行参数的测试（上游无 runtests 脚本，参数需手动传）：
        # - fnmatch：pattern/string/flags 三参数（不传则 argv[1]=NULL 崩溃）
        # - mmaptest：test_file 可写路径（默认硬编码 /tmp，OHOS /tmp 只读 EROFS）
        test_args = {
            "fnmatch": '"*.c" "foo.c" 0',
            "mmaptest": f'"{os.path.join(outdir, "mmaptest.tmp")}"',
        }
        passed, failed, not_built = [], [], []
        expected_nonzero = []
        for name in names:
            prog = os.path.join(testdir, name)
            if not os.path.isfile(prog):
                not_built.append(name)
                continue
            self._relink_test_elf(cc, tools, arch, testdir, name)
            args = test_args.get(name, "")
            capture = os.path.join(outdir, f"{name}.output")
            r = self.run(
                f'timeout 15 "{prog}" {args} > "{capture}" 2>&1',
                cwd=outdir, env="conanbuild",
                ignore_errors=True,
            )
            if name == "testrand48":
                # This upstream vector printer deliberately exits 1; treat it as a
                # pass only when both POSIX rand48 outputs and the saved seed match.
                try:
                    with open(capture, "rb") as stream:
                        output = stream.read().decode("ascii", errors="replace").splitlines()
                except OSError:
                    output = []
                expected = [
                    "Initial seed: 0x0000 0x0000 0x0000",
                    "lrand48() = 615467189",
                    "mrand48() = 1230934378",
                ]
                if r == 1 and output == expected:
                    passed.append(name)
                    expected_nonzero.append(name)
                else:
                    failed.append(name)
            else:
                (passed if r == 0 else failed).append(name)
        self.output.info(
            f"upstream tests: {len(passed)} passed, {len(failed)} failed, "
            f"{len(not_built)} not-built, skipped=0"
        )
        if failed:
            self.output.warning(f"failed tests: {' '.join(failed)}")
        if not_built:
            self.output.warning(f"not-built tests: {' '.join(not_built)}")
        summary = os.path.join(self.build_folder, "upstream-tests-summary.txt")
        with open(summary, "w") as f:
            f.write(f"passed={len(passed)}\nfailed={len(failed)}\n"
                    f"not_built={len(not_built)}\n")
            if failed:
                f.write("failed_list=" + " ".join(failed) + "\n")
            if not_built:
                f.write("not_built_list=" + " ".join(not_built) + "\n")
            f.write(f"expected_nonzero={len(expected_nonzero)}\n")
            if expected_nonzero:
                f.write("expected_nonzero_list=" + " ".join(expected_nonzero) + "\n")
            f.write("skipped=0\n")
        if failed or not_built or len(passed) != len(names):
            raise ConanException(
                "upstream suite must pass all 39 tests with no skips; "
                f"passed={len(passed)}/{len(names)}, failed={failed}, "
                f"not_built={not_built}"
            )

    def package(self):
        arch = self._klibc_arch()
        src = self.source_folder
        libsrc = os.path.join(src, "usr", "klibc")
        inc_src = os.path.join(src, "usr", "include")
        inc_dst = os.path.join(self.package_folder, "include")
        lib_dst = os.path.join(self.package_folder, "lib")
        bin_dst = os.path.join(self.package_folder, "bin")
        lic_dst = os.path.join(self.package_folder, "licenses")

        # 头文件（usr/include 下所有 *.h，含 arch/arpa/bits/net/sys 等子目录；
        # asm 已由 patch 0001 物化为真实目录）。
        copy(self, "*.h", inc_src, inc_dst, keep_path=True)
        # 静态库：libc.a 重命名为 libklibc.a，避免与系统 musl libc（-lc）混淆。
        copy(self, "libc.a", libsrc, lib_dst)
        os.rename(os.path.join(lib_dst, "libc.a"), os.path.join(lib_dst, "libklibc.a"))
        # 启动对象 + 共享 stub（消费者 -nostdlib 链接所需）。
        copy(self, "crt0.o", os.path.join(libsrc, "arch", arch), lib_dst)
        copy(self, "shared-stub.o", libsrc, lib_dst)
        # 共享库（libc.so + 带 soname 的 klibc-<hash>.so；arm64 KLIBCSHAREDFLAGS 非空）。
        copy(self, "libc.so", libsrc, lib_dst)
        copy(self, "klibc-*.so", libsrc, lib_dst)
        # klcc 编译器包装器。
        copy(self, "klcc", os.path.join(src, "klcc"), bin_dst)
        # 许可证（klibc 本体 BSD/MIT + Linux 派生 GPL + gzip 工具 GPL）。
        copy(self, "LICENSE", libsrc, lic_dst)
        copy(self, "COPYING", os.path.join(src, "usr", "gzip"), lic_dst)

    def package_info(self):
        arch = self._klibc_arch()
        # klibc 头文件布局：通用头在 include/，架构相关头在 include/arch/<arch>/klibc/，
        # 位数头在 include/bits64/（arm64 为 64 位）。消费者需全部加入 include 路径。
        self.cpp_info.includedirs = ["include", f"include/arch/{arch}", "include/bits64"]
        self.cpp_info.libdirs = ["lib"]
        # klibc 是 libc 本体，消费方式特殊：需 -nostdlib + crt0.o + libklibc.a
        # （见 test_package），故只声明库名，消费者按完整路径链接。
        self.cpp_info.libs = ["klibc"]
