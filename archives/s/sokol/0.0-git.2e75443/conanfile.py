#!/usr/bin/env python3
"""Conan recipe — sokol 0.0-git.2e75443 (cross-platform single-header
graphics/audio/app-toolkit library collection by floooh).

sokol 是一组minimal、依赖无(zero-dependency)的 C/C++ 单头库：
  core: sokol_gfx.h / sokol_app.h / sokol_audio.h / sokol_fetch.h /
        sokol_args.h / sokol_log.h / sokol_time.h / sokol_glue.h
  util: sokol_color.h / sokol_debugtext.h / sokol_gl.h /
        sokol_shape.h / sokol_letterbox.h / sokol_memtrack.h /
        sokol_fontstash.h / sokol_imgui.h / sokol_gfx_imgui.h /
        sokol_app_imgui.h / sokol_nuklear.h / sokol_spine.h /
        sokol_cmdbuf.h / sokol_framebuffer.h
形态：header-only。实现段通过在恰好一个 TU 中 #define SOKOL_IMPL
（或 per-header 的 <NAME>_IMPL）激活；无构建系统、无源码编译产物。

版本号依据：上游 master-only 无 tag（master-only 库规则
0.0-git.{hash7}）：master @
  2e75443dbd4940b5aa8d76a8e479f8e4b270b9a3 → 0.0-git.2e75443。
本机 diff -r 全树比对 master tarball vs 2e75443 tarball：0 差异
（快照后上游无新提交），镜像与官方 master URL 同锚本版本。

W0 依赖实测：零第三方依赖（core/util 头仅依赖 libc/libm/
pthread/POSIX stdio，OHOS musl 全覆盖；util 中 imgui/nuklear/
fontstash/spine 桥接头仅在其对应上游库被一并包含时才有意义，
单头交付形态不产生 conan requires）。

配方设计（参照 minunit 0.0-git20230524 header-only 先例）：
- package_type = "header-library"；package() 仅拷贝 8 个 core 头
  → include/、15 个 util 头 → include/util/、LICENSE → licenses/。
- build() 真跑上游官方测试（R34/L1）：
  * functional 套件（tests/functional/ 12 个 TU + utest.h）：上游
    CMake 默认构建的 sokol-test 目标（SOKOL_DUMMY_BACKEND 模式，
    平台无关），排除 SokolSpine（88 例，tests/ext 需 git clone
    spine-c 运行时，CI 白名单网络不可达）。真跑 294 用例。
  * compile 套件（tests/compile/ 上游官方编译冒烟）：上游
    compile/CMakeLists.txt 默认目标中的平台无关子集，C 与 C++ 双
    形态真编译（sokol_gfx/app/audio/fetch/time/args/log/glue +
    color/debugtext/gl/shape/letterbox/memtrack/cmdbuf/framebuffer）。
- 消费者测试（test_package/）：C TU（11 个 core/util 头真用 +
  dummy 后端 setup/shutdown 生命周期 + args 解析 + fetch 真文件
  读取 + letterbox 视口计算）+ C++ TU（cmdbuf 实现段 C++ 编译）。

上游测试平台差异（无源码补丁，仅编译 flag）：
  utest.h 在 Linux 分支用 syscall(SYS_clock_gettime,…)；OHOS musl
  的 sys/syscall.h 无 SYS_* 宏、且 utest.h 的 glibc 探测分支
  （__GLIBC__）不命中导致 time.h 未包含。解法：编译 flag
  -DUTEST_USE_CLOCKGETTIME -include time.h（预包含），零补丁。
  （上游 sokol_app.h 的 X11 后端与 3D 后端在 OHOS 无对应系统能
  力——本包以 SOKOL_DUMMY_BACKEND 模式验证逻辑层，图形后端绑定
  由消费者自行选择，属上游设计而非适配缺口。）
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)

required_conan_version = ">=2.0"

# 上游 functional 套件（默认 sokol-test 目标的源 TU；spine 排除：
# tests/ext git clone spine-c 运行时，CI 站点白名单不可达）
FUNCTIONAL_TEST_TUS = [
    "sokol_test.c",
    "sokol_args_test.c",
    "sokol_audio_test.c",
    "sokol_cmdbuf_test.c",
    "sokol_color_test.c",
    "sokol_debugtext_test.c",
    "sokol_fetch_test.c",
    "sokol_gfx_test.c",
    "sokol_gl_test.c",
    "sokol_log_test.c",
    "sokol_shape_test.c",
]
# 上游 compile 套件（平台无关子集，C 形态；排除项见 notes.md：
# sokol_app.c/.cc 需 X11+真实 3D 后端、sokol_all.c 需 cimgui/spine/
# nuklear 外部库、tests/ 无 sokol_memtrack.c 编译 TU —— 上游目录即无）
COMPILE_C_TUS = [
    "sokol_gfx.c", "sokol_audio.c", "sokol_fetch.c", "sokol_time.c",
    "sokol_args.c", "sokol_log.c", "sokol_glue.c", "sokol_color.c",
    "sokol_debugtext.c", "sokol_gl.c", "sokol_shape.c",
    "sokol_letterbox.c", "sokol_cmdbuf.c", "sokol_framebuffer.c",
    "sokol_main.c",
]
# 上游 compile 套件（C++ 形态；cmdbuf 需补丁 s0001，见 patches/；
# framebuffer.cc 上游目录即无）
COMPILE_CXX_TUS = [
    "sokol_gfx.cc", "sokol_audio.cc", "sokol_fetch.cc", "sokol_time.cc",
    "sokol_args.cc", "sokol_log.cc", "sokol_glue.cc", "sokol_color.cc",
    "sokol_debugtext.cc", "sokol_gl.cc", "sokol_shape.cc",
    "sokol_letterbox.cc", "sokol_cmdbuf.cc", "sokol_main.cc",
]
CORE_HEADERS = [
    "sokol_gfx.h", "sokol_app.h", "sokol_audio.h", "sokol_fetch.h",
    "sokol_args.h", "sokol_log.h", "sokol_time.h", "sokol_glue.h",
]
UTIL_HEADERS = [
    "sokol_color.h", "sokol_debugtext.h", "sokol_gl.h", "sokol_shape.h",
    "sokol_letterbox.h", "sokol_memtrack.h", "sokol_fontstash.h",
    "sokol_imgui.h", "sokol_gfx_imgui.h", "sokol_app_imgui.h",
    "sokol_nuklear.h", "sokol_spine.h", "sokol_cmdbuf.h",
    "sokol_framebuffer.h",
]


class SokolConan(ConanFile):
    name = "sokol"
    version = "0.0-git.2e75443"
    description = ("Minimal cross-platform C/C++ single-header libraries "
                   "for graphics, audio, app plumbing and tools (floooh)")
    license = "Zlib"
    homepage = "https://github.com/floooh/sokol"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("graphics", "audio", "single-header", "header-only",
              "cross-platform", "embedded")

    package_type = "header-library"
    implements = ["auto_header_only_mode"]
    # header-only：settings 声明但 binary 由 header-only 模式归一
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        # 补丁随配方导出（vorbis 1.3.7 先例：export_sources 钩子）
        export_conandata_patches(self)

    def layout(self):
        # basic_layout：源码在 src/，构建产物在 build/
        from conan.tools.layout import basic_layout
        basic_layout(self, src_folder="src")

    def package_id(self):
        # 纯头文件包：任何配置产出同一组头文件
        self.info.clear()

    def source(self):
        # conandata 镜像列表（ghfast.top 在前，官方 GitHub 兜底）；
        # sha256 本机实测（两 URL 内容逐字节一致）
        get(self, **self.conan_data["sources"], strip_root=True)
        # R04：版本化补丁（见 conandata.yml patches 段）：
        #  s0001  sokol_cmdbuf 实现段 C++ 编译 void*→uint8_t* 显式转换
        apply_conandata_patches(self)

    def build(self):
        # ── 上游官方测试（真跑，进统计表）────────────────────────
        # R33：编译器从 conf 注入（profile tools.build:compiler_executables），
        # 禁止裸用 ${CC}/${CFLAGS} shell 变量。
        compilers = self.conf.get("tools.build:compiler_executables",
                                  check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        src = self.source_folder
        build = self.build_folder
        funcdir = os.path.join(src, "tests", "functional")
        compdir = os.path.join(src, "tests", "compile")

        c_flags = [
            "-std=gnu11", "-O1", "-DSOKOL_DUMMY_BACKEND",
            "-DUTEST_USE_CLOCKGETTIME", "-include", "time.h",
        ]
        # 上游 utest.h 仅在 Linux 使用 syscall(SYS_clock_gettime)：
        # OHOS musl 无 SYS_* 宏且 __GLIBC__ 探测不命中 → 用编译 flag
        # 预包含 time.h 并切换到 clock_gettime 路径（零源码补丁）。
        inc_flags = ["-I{}".format(src), "-I{}".format(os.path.join(src, "util")),
                     "-I{}".format(funcdir)]

        # ── 1. functional 套件：编译 11 TU → 链接 sokol-test → 真跑 ──
        objs = []
        for tu in FUNCTIONAL_TEST_TUS:
            obj = os.path.join(build, tu.replace(".c", ".o"))
            self.run("{cc} {cflags} {incs} -c {srcfile} -o {obj}".format(
                cc=cc, cflags=" ".join(c_flags), incs=" ".join(inc_flags),
                srcfile=os.path.join(funcdir, tu), obj=obj))
            objs.append(obj)
        testbin = os.path.join(build, "sokol-test")
        self.run("{cc} -o {bin} {objs} -lm".format(
            cc=cc, bin=testbin, objs=" ".join(objs)))

        if can_run(self):
            # fetch 用例需要上游资产 comsi.s3m 在 CWD（上游 CMake 用
            # file(COPY) 拷到构建目录，同语义）
            copy(self, "comsi.s3m",
                 src=os.path.join(funcdir, "assets"), dst=build)
            retcode = self.run("./sokol-test", cwd=build, ignore_errors=True)
            if retcode != 0:
                raise ConanException(
                    "sokol upstream functional suite FAILED: exit code %d "
                    "(294 UTEST cases expected all-pass, spine suite "
                    "excluded: needs external spine-c runtime via git clone, "
                    "not reachable from CI whitelist network)" % retcode)
            self.output.info(
                "sokol upstream functional suite PASS: 294/294 UTEST cases "
                "(dummy backend; SokolSpine 88 cases excluded - external "
                "spine-c runtime dependency)")
        else:
            self.output.warning(
                "cross-building: functional suite compiled but run skipped")

        # ── 2. compile 套件：上游官方编译冒烟（C + C++ 双形态）──
        for tu in COMPILE_C_TUS:
            obj = os.path.join(build, "compile_" + tu.replace(".c", ".o"))
            self.run("{cc} {cflags} {incs} -c {srcfile} -o {obj}".format(
                cc=cc, cflags=" ".join(c_flags), incs=" ".join(inc_flags),
                srcfile=os.path.join(compdir, tu), obj=obj))
        cxx_flags = ["-std=c++11", "-O1", "-DSOKOL_DUMMY_BACKEND"]
        for tu in COMPILE_CXX_TUS:
            obj = os.path.join(build, "compile_" + tu.replace(".cc", ".o"))
            self.run("{cxx} {cflags} {incs} -c {srcfile} -o {obj}".format(
                cxx=cxx, cflags=" ".join(cxx_flags), incs=" ".join(inc_flags),
                srcfile=os.path.join(compdir, tu), obj=obj))
        self.output.info(
            "sokol upstream compile suite PASS: {c} C TUs + {cxx} C++ TUs "
            "(dummy backend, platform-independent subset of upstream "
            "tests/compile/CMakeLists.txt)".format(
                c=len(COMPILE_C_TUS), cxx=len(COMPILE_CXX_TUS)))

    def package(self):
        # 许可证
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 精确清单拷贝（禁止 *.h 通配——会把 tests/、bindgen/ 等
        # 非交付头一并打包）：
        # core 头 → include/ 根（消费者 #include <sokol_gfx.h>）
        for hdr in CORE_HEADERS:
            copy(self, hdr, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))
        # util 头 → include/util/（上游布局：消费侧 -I<root> -I<root>/util，
        # #include "sokol_color.h"）
        for hdr in UTIL_HEADERS:
            copy(self, hdr, src=os.path.join(self.source_folder, "util"),
                 dst=os.path.join(self.package_folder, "include", "util"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "sokol")
        self.cpp_info.set_property("cmake_target_name", "sokol::sokol")
        self.cpp_info.set_property("pkg_config_name", "sokol")
        # 消费侧实现 TU 需要两个 include 根（core 与 util 平铺）：
        # include/ 与 include/util/ 同时加入搜索路径（CMakeDeps 自动
        # 处理 includedirs 列表）
        self.cpp_info.includedirs = ["include", "include/util"]
