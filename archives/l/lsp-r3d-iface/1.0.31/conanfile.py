#!/usr/bin/env python3
"""Conan recipe — lsp-r3d-iface 1.0.31 (lsp-plugins 3D 渲染后端接口).

上游自研 make 构建系统（make config → make → make install）。生产依赖
lsp-common-lib，测试依赖 lsp-test-fw，两者上游都按 *TYPE=src 以
-D<NAME>_BUILTIN 内嵌编译进本包产物（见源码树 modules.mk 与 src/Makefile 的
$(ARTIFACT_DEPS) 规则）；源码由 conandata.yml 提供同版本 tarball、source()
预置到 modules/（替代上游 `make fetch` 的 git clone，构建期离线可复现）。
lsp-common-lib 另以 headers-only（libs=False）声明为 Conan 依赖：本包公共头
引用它的头文件，但其目标码已内嵌，消费者不应再链它的静态库。

HarmonyOS PC 适配点（同 lsp-common-lib）：上游 make 按 `uname -s` 探测平台，
OpenHarmony PC 返回 "HarmonyOS"（上游不识别，落入 Unknown 分支），构建时
显式传 PLATFORM=Linux。OHOS aarch64 目标（-march=armv8-a+asimd）与上游 Linux
路径 1:1 一致；唯一需要移植的是内嵌 lsp-common-lib 缺失的 GNU qsort_r，
由补丁 0001 处理。

零补丁针对本包源码。
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
    "lsp-test-fw": "1.0.35",
}


class LspR3dIfaceConan(ConanFile):
    name = "lsp-r3d-iface"
    version = "1.0.31"
    description = "3D rendering backend interfaces (lsp-plugins project)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/lsp-plugins/lsp-r3d-iface"
    url = "https://github.com/lsp-plugins/lsp-r3d-iface"
    topics = ("lsp-plugins", "r3d", "3d", "backend", "interfaces")

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

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 上游依赖类型 LSP_COMMON_LIB_TYPE=src：`make` 时由 src/Makefile 的
        # $(ARTIFACT_DEPS) 规则递归 `make -C modules/lsp-common-lib compile` 以
        # -D LSP_COMMON_LIB_BUILTIN 内嵌编译，其目标码已并入本包静态库
        # （ARTIFACT_OBJFILES 含 $(LSP_COMMON_LIB_OBJ)），源码由 source()
        # 从 conandata.yml 预置（见 _stage_embedded_modules）。
        # 这里仍然声明为 Conan 依赖：本包公共头
        # include/lsp-plug.in/r3d/iface/*.h 引用 <lsp-plug.in/common/types.h>，
        # 消费者必须拿到 lsp-common-lib 的头文件（上游 install 只装本包头文件）。
        # 链接层面消费者多链一份静态库无害：ld 单遍扫描先解析本包归档内的
        # 内嵌成员，不会产生重复定义。
        # R27：依赖必须用完整 user/channel 形式；Conan 2 不会把裸 name/version
        # 解析到缓存/制品仓里的 <name>/<version>@ohpcd/stable。
        # transitive_headers=True：本包公共头 include/lsp-plug.in/r3d/iface/*.h
        # 引用 <lsp-plug.in/common/types.h>，其头文件属于本包公共接口，必须向
        # 消费者传递（仓库先例：datatype99 → metalang99、das-watchdog → libgtop）。
        self.requires("lsp-common-lib/1.0.49@ohpcd/stable",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._stage_embedded_modules()

    def _stage_embedded_modules(self):
        """把上游 `make fetch` 要 git clone 的内嵌依赖源码预置到 modules/。

        路径与上游 modules.mk 的 MODULES（= $(BASEDIR)/modules）一致，目录名取
        上游 $(<ID>_NAME)。内嵌依赖以 -D<ID>_BUILTIN 编译进本包产物；lsp-common-lib
        的**头文件**属于本包公共接口，另以 transitive_headers 的 requires 传递。
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
        """对预置好的内嵌依赖源码打 OHOS 修正补丁。

        补丁在 patches/modules/ 下（不进 conandata 的 patches 表：那些表项会被
        clean-verify 的 G0 打到主源码树上，而这些文件只在内嵌源码预置后才存在），
        由这里在预置完成后、make 之前应用。
        """
        for entry in self.conan_data.get("module_patches", []):
            patch_file = os.path.join(self.export_sources_folder,
                                      *entry["patch_file"].split("/"))
            if not os.path.isfile(patch_file):
                raise ConanException(
                    "内嵌依赖补丁缺失: {}".format(entry["patch_file"]))
            self.output.info("Patching embedded module: {}".format(entry["patch_file"]))
            patch(self, base_path=entry.get("base_path", ""), patch_file=patch_file)

    def build(self):
        # 本包源码零补丁；内嵌依赖的 OHOS 修正已在 source() 阶段应用完毕。
        apply_conandata_patches(self)

        # R33: compiler comes from Conan conf, never from raw shell env
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cxx", "clang++")

        # 上游 make 按 uname -s 探测平台；HarmonyOS PC 返回 "HarmonyOS"（未识别），
        # 显式按 Linux 语义配置（aarch64 路径与上游一致）。
        self.run(
            'make -C "{}" config PLATFORM=Linux FEATURES="test strict" '
            'PREFIX="{}" CXX="{}"'.format(self.source_folder, self.package_folder, cxx)
        )

        # src/Makefile 会递归 `make -C modules/<dep> compile` 内嵌编译依赖，
        # 无需（也不能）走上游联网的 `make fetch`。
        self.run('make -C "{}" -j1 CXX="{}"'.format(self.source_folder, cxx))
        self.run('make -C "{}" install'.format(self.source_folder))

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
        # OHOS 动态加载器要求 .so 持有有效代码签名（见 lsp-test-fw recipe）
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
        self.cpp_info.libs = ["lsp-r3d-iface"]
        self.cpp_info.set_property("cmake_file_name", "lsp-r3d-iface")
        self.cpp_info.set_property("cmake_target_name", "lsp-r3d-iface::lsp-r3d-iface")
        self.cpp_info.set_property("pkg_config_name", "lsp-r3d-iface")
