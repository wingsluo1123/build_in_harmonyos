#!/usr/bin/env python3
"""Conan test_package for lttng-ust 2.12.10 (OHOS consumer probe).

编译并运行 test_lttng_ust.c + tp.c：验证公共头、liblttng-ust /
liblttng-ust-tracepoint 的链接与运行期加载、tracef/tracelog 宏以及真实
TRACEPOINT_EVENT 注册路径。断言 5 条（鸿蒙侧消费者用例，单列不进上游分母）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class LttngUstTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        incs, libdirs, deps_libs = [], [], []
        for _ref, dep in self.dependencies.items():
            incs += dep.cpp_info.includedirs
            libdirs += dep.cpp_info.libdirs
            deps_libs += dep.cpp_info.libs
        inc = " ".join("-I" + p for p in dict.fromkeys(incs))
        # 本目录既是源码目录也是 `#include "probe_tp.h"` 的解析基准，而
        # <lttng/tracepoint-event.h> 里的 `#include TRACEPOINT_INCLUDE`（值为
        # "./probe_tp.h"）是相对**该头文件所在目录**解析的 ⇒ 必须把本目录加进
        # 搜索路径，否则报 `'./probe_tp.h' file not found`（conan create 实测）。
        src = self.source_folder.replace("\\", "/")
        src_inc = f'-I"{src}" -I.'
        # liburcu/0.15.6 在 ohpcd 是静态包（只有 .a），消费者必须显式链接
        # 依赖的库名；库名直接取自依赖 cpp_info.libs（不写死）。
        libs = ["-llttng-ust", "-llttng-ust-tracepoint"]
        libs += ["-l" + name for name in dict.fromkeys(deps_libs)]
        link = " ".join(["-L" + p for p in dict.fromkeys(libdirs)]
                        + libs
                        # OHOS sysroot 的 libc.so 桩未导出 pthread_cancel /
                        # pthread_setcancelstate（真机 libc 里有），lld 的
                        # --no-allow-shlib-undefined 会对 liblttng-ust-tracepoint.so
                        # 的这两个 UND 符号误报未定义 ⇒ 必须显式放行。
                        + ["-Wl,--allow-shlib-undefined"]
                        + ["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        cc = "clang"
        for cand in ("clang", os.environ.get("CC", "")):
            if cand and shutil.which(cand):
                cc = cand
                break
        # OHOS musl 头需 _GNU_SOURCE 才声明 clock_gettime 等（urcu generic.h 用）
        self.run(f'{cc} -std=c11 -D_GNU_SOURCE {src_inc} '
                 f'"{src}/test_lttng_ust.c" "{src}/tp.c" '
                 f'-o test_lttng_ust_probe {inc} {link}')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: only verifying compile+link")
            return
        self.run("./test_lttng_ust_probe", env="conanrun")
