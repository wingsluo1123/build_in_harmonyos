#!/usr/bin/env python3
"""Conan recipe — lsp-r3d-glx-lib 1.0.31 (lsp-plugins GLX 3D 渲染后端).

上游自研 make 构建系统（make config → make → make install）。上游依赖链
（modules.mk pin，*_TYPE 均为 src）：lsp-common-lib 1.0.49、lsp-r3d-iface
1.0.31、lsp-r3d-base-lib 1.0.31（生产）+ lsp-test-fw 1.0.35（测试），四者
由 src/Makefile 的 $(ARTIFACT_DEPS) 规则以 -D<NAME>_BUILTIN 内嵌编译进
本包产物；源码由 conandata.yml 预置到 modules/（替代上游 `make fetch` 的
git clone，构建期离线可复现）。上游系统依赖 LIBX11/LIBGL 为 pkg 型，OHOS
上不存在，本 OHOS 后端不依赖它们。

OpenHarmony 适配（路径 A：新写独立平台后端，上游文件零改动）：
  * ohos/backend.cpp（随配方导出，source() 拷入 src/ohos/）实现与上游
    src/main/backend.cpp 同一组 glx::backend_t 虚表函数，用 EGL pbuffer
    替换 X11/GLX；GL 入口一律经 eglGetProcAddress 运行时解析（OHOS 直连
    的 GL 符号是调度空桩），因此链接只需 -lEGL。
  * patches/0001：公共头 X11/GLX include 用 __has_include 条件化，公共头
    不引入平台宏（R8）。
  * patches/0002：src/Makefile 按 make 命令行变量 PLATFORM_OHOS=1 选择编译
    src/ohos/*.cpp；平台标识只经 make 变量注入，源码里不裸用平台宏（R8）。
  * PLATFORM=Linux：上游 make 按 uname -s 探测平台，OHOS PC 返回
    "HarmonyOS"（上游不识别，落入 Unknown 分支），显式按 Linux 语义配置；
    OHOS aarch64 与上游 Linux 路径一致。

平台能力边界（README/notes 有完整声明，不得伪装通过）：init_window 无原生
窗口句柄、创建离屏 pbuffer 并返回 NULL；set_lights/draw_primitives 的
GL1.x 固定管线在只有 GLES3.2 的 OHOS 上不存在，返回 STATUS_NOT_IMPLEMENTED。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, patch)
from conan.tools.layout import basic_layout

# 上游 modules.mk 里 pin 的内嵌依赖版本（*_VERSION）
EMBEDDED_SOURCES = {
    "lsp-common-lib": "1.0.49",
    "lsp-r3d-iface": "1.0.31",
    "lsp-r3d-base-lib": "1.0.31",
    "lsp-test-fw": "1.0.35",
}


class LspR3dGlxLibConan(ConanFile):
    name = "lsp-r3d-glx-lib"
    version = "1.0.31"
    description = "GLX-based 3D backend library for rendering scenes (lsp-plugins project)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/lsp-plugins/lsp-r3d-glx-lib"
    url = "https://github.com/lsp-plugins/lsp-r3d-glx-lib"
    topics = ("lsp-plugins", "r3d", "3d", "backend", "glx")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # patches/modules/ 下的补丁作用于**预置后**才存在的内嵌依赖源码，不能进
        # conandata 的 patches 表（clean-verify 的 G0 会无差别打到主源码树上），
        # 因此手动导出、由 source() 在预置完成后应用。
        copy(self, "patches/modules/*.patch", src=self.recipe_folder,
             dst=self.export_sources_folder)
        # OHOS 平台后端源码（上游无此目录；由 source() 拷入 src/ohos/）。
        copy(self, "ohos/*.cpp", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 上游依赖类型 *_TYPE=src：目标码已内嵌编译进本包归档；这里按 R27 用
        # 完整 user/channel 声明为 Conan 依赖并加 transitive_headers=True：
        # 本包公共头 include/lsp-plug.in/r3d/glx/backend.h 引用
        # <lsp-plug.in/r3d/base/backend.h>，后者又引用
        # <lsp-plug.in/r3d/iface/backend.h> 与 <lsp-plug.in/common/types.h>，
        # 消费者必须拿到这两条链的头文件（上游 install 只装本包头文件）。
        self.requires("lsp-r3d-iface/1.0.31@ohpcd/stable",
                      transitive_headers=True, transitive_libs=True)
        self.requires("lsp-r3d-base-lib/1.0.31@ohpcd/stable",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._stage_embedded_modules()
        self._stage_ohos_backend()

    def _stage_embedded_modules(self):
        """把上游 `make fetch` 要 git clone 的内嵌依赖源码预置到 modules/。

        路径与上游 modules.mk 的 MODULES（= $(BASEDIR)/modules）一致，目录名取
        上游 $(<ID>_NAME)。四个依赖都以 -D<ID>_BUILTIN 内嵌编译进本包产物。
        """
        for name, version in EMBEDDED_SOURCES.items():
            table = self.conan_data.get(name)
            if not table:
                raise ConanException(
                    "conandata.yml 缺少 {} 条目，无法离线预置内嵌依赖".format(name))
            data = table.get(version)
            if data is None:
                raise ConanException(
                    "conandata.yml 缺少 {}/{} 条目（上游 pin 版本）".format(name, version))

            dest = os.path.join(self.source_folder, "modules", name)
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            # strip_root=True：tarball 唯一根目录 <name>-<version>/ 被剥掉
            get(self, destination=dest, strip_root=True, **data)

        self._patch_embedded_modules()

    def _patch_embedded_modules(self):
        """对预置好的内嵌依赖源码打 OHOS 修正补丁（见 conandata 说明）。"""
        for entry in self.conan_data.get("module_patches", []):
            patch_file = os.path.join(self.export_sources_folder,
                                      *entry["patch_file"].split("/"))
            if not os.path.isfile(patch_file):
                raise ConanException(
                    "内嵌依赖补丁缺失: {}".format(entry["patch_file"]))
            self.output.info("Patching embedded module: {}".format(entry["patch_file"]))
            patch(self, base_path=entry.get("base_path", ""), patch_file=patch_file)

    def _stage_ohos_backend(self):
        """把 OHOS 平台后端源码拷入上游源码树 src/ohos/。

        src/Makefile 的 rwildcard 会自动收集该目录的 *.cpp（在补丁 0002 的
        PLATFORM_OHOS=1 分支里）。上游文件保持零改动。
        """
        dst = os.path.join(self.source_folder, "src", "ohos")
        os.makedirs(dst, exist_ok=True)
        copy(self, "*.cpp", src=os.path.join(self.export_sources_folder, "ohos"),
             dst=dst)

    def build(self):
        # patches/ 顶层补丁（公共头条件化 + src/Makefile 平台分支），作用在主源码树。
        apply_conandata_patches(self)

        # R33: compiler comes from Conan conf, never from raw shell env
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cxx", "clang++")

        # 平台与源码选择：
        #   PLATFORM=Linux   — 上游 make 的 uname -s 探测在 OHOS PC 返回
        #                       "HarmonyOS"（未识别），显式按 Linux 语义配置；
        #                       OHOS aarch64 与上游 Linux 路径一致。
        #   PLATFORM_OHOS=1  — src/Makefile 据此编译 src/ohos/*.cpp（EGL 后端）
        #                       替代 src/main/backend.cpp（X11/GLX 后端）；
        #                       平台标识只经 make 变量注入，源码不裸用平台宏（R8）。
        #   INSTALL_HEADERS=1 — project.mk 的 ARTIFACT_EXPORT_HEADERS=0，但
        #                       Conan 包必须向消费者安装公共头文件。
        #   LSP_R3D_GLX_LIB_LDFLAGS — OHOS 后端只链接 EGL；GL 入口全部经
        #                       eglGetProcAddress 运行时解析（直连符号是
        #                       调度空桩），故无需 -lGLESv3。
        #   LIBX11_*/LIBGL_* 显式清空 — dependencies.mk 在 PLATFORM=Linux 下把
        #                       LIBX11/LIBGL（pkg 型）加入依赖，其 CFLAGS/LDFLAGS
        #                       经 pkg-config 探测填充；构建机若装着 X11（如本机
        #                       brew libx11）就会把宿主 -lX11 注入交叉链接。OHOS
        #                       后端不依赖 X11/GL，这里以 make 命令行变量置空
        #                       （命令行变量优先于 makefile 内的 eval 赋值），
        #                       使构建结果与宿主机 pkg-config 环境无关。
        self.run(
            'make -C "{}" config PLATFORM=Linux PLATFORM_OHOS=1 '
            'FEATURES="test strict" INSTALL_HEADERS=1 '
            'LIBX11_CFLAGS= LIBX11_LDFLAGS= LIBGL_CFLAGS= LIBGL_LDFLAGS= '
            'LSP_R3D_GLX_LIB_LDFLAGS="-lEGL" '
            'PREFIX="{}" CXX="{}"'.format(self.source_folder, self.package_folder, cxx)
        )

        # src/Makefile 会递归 `make -C modules/<dep> compile` 内嵌编译四个依赖，
        # 无需（也不能）走上游联网的 `make fetch`。
        self.run(
            'make -C "{}" -j1 PLATFORM_OHOS=1 '
            'LIBX11_CFLAGS= LIBX11_LDFLAGS= LIBGL_CFLAGS= LIBGL_LDFLAGS= '
            'CXX="{}"'.format(self.source_folder, cxx)
        )
        self.run(
            'make -C "{}" install PLATFORM_OHOS=1 '
            'LIBX11_CFLAGS= LIBX11_LDFLAGS= LIBGL_CFLAGS= LIBGL_LDFLAGS='.format(self.source_folder)
        )

    def package(self):
        # make install 已按 PREFIX 布局；shared=False 时按 Conan 语义只保留静态库
        if not self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            for name in os.listdir(libdir):
                if ".so" in name:
                    os.remove(os.path.join(libdir, name))
        else:
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        # OHOS 动态加载器要求 .so 持有有效代码签名（见 lsp-r3d-base-lib recipe）
        signer = shutil.which("binary-sign-tool")
        if signer is None and os.path.exists("/data/service/hnp/bin/binary-sign-tool"):
            signer = "/data/service/hnp/bin/binary-sign-tool"
        if signer is None:
            return

        libdir = os.path.join(self.package_folder, "lib")
        for name in os.listdir(libdir):
            if ".so" not in name:
                continue
            path = os.path.join(libdir, name)
            if os.path.islink(path):
                continue
            # strip a possibly stale signature section; missing is fine
            self.run(f'llvm-objcopy --remove-section=.codesign "{path}" "{path}"',
                     ignore_errors=True)
            self.run(f'"{signer}" sign -selfSign 1 -inFile "{path}" -outFile "{path}"')

    def package_info(self):
        self.cpp_info.libs = ["lsp-r3d-glx-lib"]
        self.cpp_info.set_property("cmake_file_name", "lsp-r3d-glx-lib")
        self.cpp_info.set_property("cmake_target_name", "lsp-r3d-glx-lib::lsp-r3d-glx-lib")
        self.cpp_info.set_property("pkg_config_name", "lsp-r3d-glx-lib")
        # OHOS 后端经 eglGetProcAddress 解析全部 GL 入口，仅 EGL 是链接依赖
        # （glfw 先例：OHOS 目标下 system_libs 会传递给消费者）。
        if self.settings.os == "OHOS":
            self.cpp_info.system_libs = ["EGL"]
