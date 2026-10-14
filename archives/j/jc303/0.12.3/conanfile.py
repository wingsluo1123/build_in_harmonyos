#!/usr/bin/env python3
"""Conan recipe — jc303 0.12.3（JUCE 合成器插件：VST3 + LV2 + CLAP，OHOS aarch64）。

上游 midilab/jc303 是 JUCE 8 插件工程（project(JC303 VERSION 0.12.3)）：
juce_add_plugin(FORMATS AU VST3 LV2)（AU 仅 macOS，Linux/OHOS 实际编译
VST3 + LV2）+ clap_juce_extensions_plugin 产出 CLAP，另含 vendored
src/dsp/open303（MIT）、src/dsp/guitarml-byod（GPL-3，37 个 JSON 音色模型经
juce_add_binary_data 内嵌，31MB）与 src/gui 两套 GUI 资源。

OHOS 适配（最小 diff，源内联于 source()，jc303 源为 LF）：
  1. 构建期网络去除（CI 无构建期网络，用户已批方案）：
     - JUCE 改为消费已发布 conan 包：根 CMakeLists 的 FetchContent(juce) 块
       替换为 find_package(JUCE REQUIRED CONFIG)（juce/8.0.5 为 INTERFACE 源码
       分发 + 官方 JUCEConfig，内置预构建 juceaide/juce_lv2_helper/
       juce_vst3_helper IMPORTED 工具；jc303 为 juce_add_plugin 消费方，兼容性
       已由 juce run 的 test_package 消费范式验证）。
     - 其余五个 FetchContent 源（clap-juce-extensions / chowdsp_utils /
       RTNeural / math_approx / ea_variant）由 source() 按 conandata.yml
       fetchcontent 段固定 URL+SHA256 预解包到 <source>/deps/，经
       FETCHCONTENT_SOURCE_DIR_* 工具链变量注入（E292 先例）；
       RTNeural 的 xsimd 二跳 submodule（RTNEURAL_XSIMD=ON 必需）同样解包到
       deps/RTNeural/modules/xsimd。
  2. 去除 juce::juce_recommended_lto_flags（根 CMakeLists 1 处 +
     guitarml CMakeLists 2 处）：全量 -flto 对三格式插件目标在 OHOS
     clang-15/lld 上未验证且按格式倍增链接成本；config/warning flags 保留。
  3. 运行期共享库闭包（E505）：插件 .so 经 juce_graphics/juce_audio_devices
     链接 freetype2/fontconfig（及传递 libxml2）与 alsa 共享库；OHOS musl
     加载器无法经版本化符号链接别名解析 .so，且用户存储 .so 未签名 dlopen
     即 EACCES。generate() 向全部插件共享目标注入 --disable-new-dtags 的
     $ORIGIN 多级 DT_RPATH（覆盖 VST3 bundle Contents/<arch>/、LV2 bundle
     根、CLAP 平级三种深度指向 lib/jc303-runtime）；package() 将依赖闭包
     （freetype/fontconfig/libxml2/alsa-lib 的全部 .so 实体）物化进包内
     lib/jc303-runtime/ 并逐文件 binary-sign-tool selfSign（juce run 配方
     _sign_elf 同款），插件 .so 一并签名；最后以 llvm-readelf 断言每个插件
     ELF 的 NEEDED 闭包均落在 视图 ∪ 系统库（libc/libc++_shared）内。

上游测试：无（归档全树 grep enable_testing/add_test(/catch2/gtest/doctest/
ctest/unittest 均 0 命中；无 tests/ 目录；Dockerfile 仅构建产物发布环境）。
按 NO_UPSTREAM_TESTS 处理，验证主路径为消费式 test_package：对安装后插件
产物做 bundle 布局断言 + dlopen/dlsym 符号探针（VST3 GetPluginFactory /
LV2 lv2_descriptor / CLAP clap_entry；E505 签名+rpath 闭包在真机上真实
生效），不带 GUI 运行（无显示后端，不做音频设备初始化）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import PkgConfigDeps

# E505：插件 .so 实际链接的 conan 依赖共享库来源包（NEEDED 闭包）。
# libx11/xorgproto 为 NOLINK 头文件依赖（运行期 JUCE 全 dlopen，不产生
# DT_NEEDED）；mesa/gl 仅 juce_opengl 使用，本包未链接。
_RUNTIME_VIEW_PACKAGES = ("freetype", "fontconfig", "libxml2", "alsa-lib")
_VIEW_DIRNAME = "jc303-runtime"
# 插件 bundle 各布局深度的 $ORIGIN rpath 前缀（构建树与包内 lib 布局同深度；
# 实测 OHOS musl dlopen 语义下 $ORIGIN 有效——LV2 路径全通）。
_PLUGIN_RPATH_PREFIX = (" -Wl,--disable-new-dtags -Wl,-rpath,"
                        "$ORIGIN/{v}:$ORIGIN/../{v}:$ORIGIN/../../{v}:"
                        "$ORIGIN/../../../{v}:$ORIGIN/../../../../{v}").format(v=_VIEW_DIRNAME)
# 绝对路径双保险（juceaide 先例同款）：包内视图与构建树视图的绝对入口，
# 覆盖 link 环节 shell 对 $ORIGIN 的展开差异与宿主 DAW 任意加载路径。
# 包内绝对路径随包前缀移动会失效，属已知取舍（L5 门禁只查 NEEDED）。


class Jc303Conan(ConanFile):
    name = "jc303"
    version = "0.12.3"
    description = ("JC303: JUCE-based Roland TB-303 bassline synthesizer plugin "
                   "(VST3/LV2/CLAP) with Open303 DSP and GuitarML neural amp models.")
    # 上游 LICENSE=GPL-3.0；内嵌第三方：open303=MIT、guitarml-byod=GPL-3
    # （详见 manifest.yaml）。
    license = "GPL-3.0-only"
    homepage = "https://github.com/midilab/jc303"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "compiler", "build_type", "arch"
    # 插件产物包（无头文件/链接库消费面），下游不做 C/C++ 链接消费；
    # 不声明 package_type / bindirs 安装（R38：非 CLI 工具包）。

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "jc303/0.12.3 OHOS adaptation currently targets os=OHOS arch=armv8 only")

    def requirements(self):
        # JUCE 8.0.5 已发布（ohpcd rrev 2fdfcee76e9c350e6d329223a07f9f97，
        # OHOS armv8/clang15/libc++/cppstd17 包 991ac77b…）；freetype/
        # fontconfig/libxml2/alsa-lib/libx11/xorgproto 等为其传递依赖，
        # 本配方经 self.dependencies 取用，不重复声明。
        self.requires("juce/8.0.5")

    def layout(self):
        cmake_layout(self)

    # ── 源获取：上游归档 + 五小件/xsimd 预解包（全部 SHA256 固定）+ 最小适配补丁 ──
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # ── 1. 根 CMakeLists：JUCE 改为消费已发布 conan 包（find_package 路径，
        #     juce run test_package 消费范式）；其余 FetchContent declare 保留
        #     原样（FETCHCONTENT_SOURCE_DIR_* 只覆盖 SOURCE_DIR，不再访问网络）。──
        replace_in_file(
            self, "CMakeLists.txt",
            """FetchContent_Declare(juce
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG        ${LIB_JUCE_TAG}
    GIT_SHALLOW    TRUE
    GIT_CONFIG     advice.detachedHead=false
    SOURCE_DIR     "${FETCHCONTENT_BASE_DIR}/JUCE"
    SUBBUILD_DIR   "${FETCHCONTENT_BASE_DIR}/JUCE-Subbuild"
    BINARY_DIR     "${FETCHCONTENT_BASE_DIR}/JUCE-Build")""",
            """# OHOS adaptation (jc303 conan recipe): JUCE is consumed from the published
# conan package (installed INTERFACE distribution with prebuilt juceaide /
# juce_lv2_helper / juce_vst3_helper) through the official find_package(JUCE)
# path instead of FetchContent. The remaining FetchContent dependencies are
# pre-staged by the recipe (conandata.yml fetchcontent sources, SHA256-fixed)
# and injected via FETCHCONTENT_SOURCE_DIR_* toolchain variables, so the
# configure step needs no network access.
list(APPEND CMAKE_PREFIX_PATH "${JUCE_PACKAGE_DIR}")
find_package(JUCE REQUIRED CONFIG)

# OHOS adaptation: pin the plugin-format manifest helpers to the prebuilt
# binaries shipped inside the juce package. JUCEUtils otherwise builds them
# from module sources and JUCE's POST_BUILD invokes them by bare name, which
# resolves through PATH inside the make shell and fails here (Error 127).
# Pre-registering IMPORTED targets makes CMake expand the POST_BUILD
# COMMANDs to absolute locations with proper dependencies.
if(NOT TARGET juce_lv2_helper)
    add_executable(juce_lv2_helper IMPORTED GLOBAL)
    set_target_properties(juce_lv2_helper PROPERTIES
        IMPORTED_LOCATION "${JUCE_PACKAGE_DIR}/bin/JUCE-8.0.5/juce_lv2_helper")
endif()
if(NOT TARGET juce_vst3_helper)
    add_executable(juce_vst3_helper IMPORTED GLOBAL)
    set_target_properties(juce_vst3_helper PROPERTIES
        IMPORTED_LOCATION "${JUCE_PACKAGE_DIR}/bin/JUCE-8.0.5/juce_vst3_helper")
endif()""")
        replace_in_file(
            self, "CMakeLists.txt",
            "FetchContent_MakeAvailable(juce juce-clap-extensions chowdsp_utils)",
            "# OHOS adaptation: juce removed (consumed via find_package above).\n"
            "FetchContent_MakeAvailable(juce-clap-extensions chowdsp_utils)")

        # ── 2. 去除 juce_recommended_lto_flags（3 处）：全量 -flto 对三格式
        #     插件目标在 OHOS clang-15/lld 上未验证且按格式倍增链接成本。──
        replace_in_file(
            self, "CMakeLists.txt",
            """        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags)""",
            """        juce::juce_recommended_config_flags
        # OHOS adaptation: juce_recommended_lto_flags dropped — full -flto
        # links of the multi-format plugin targets are unvalidated on the
        # OHOS clang-15/lld toolchain and multiply link cost per format.
        juce::juce_recommended_warning_flags)""")
        replace_in_file(
            self, os.path.join("src", "dsp", "guitarml-byod", "CMakeLists.txt"),
            """    target_link_libraries(${target}
        PRIVATE
            math_approx
            config_flags
            juce::juce_recommended_lto_flags
            warning_flags
    )""",
            """    target_link_libraries(${target}
        PRIVATE
            math_approx
            config_flags
            # OHOS adaptation: lto flags dropped (see root CMakeLists).
            warning_flags
    )""")
        replace_in_file(
            self, os.path.join("src", "dsp", "guitarml-byod", "CMakeLists.txt"),
            """  PUBLIC
    config_flags
    juce::juce_recommended_lto_flags
    warning_flags
)""",
            """  PUBLIC
    config_flags
    # OHOS adaptation: lto flags dropped (see root CMakeLists).
    warning_flags
)""")

        replace_in_file(
            self, "CMakeLists.txt",
            "    COPY_PLUGIN_AFTER_BUILD FALSE)              # Should the plugin be installed to a default location after building?",
            """    # OHOS adaptation: the VST3_AUTO_MANIFEST post-build runs a host helper
    # that dlopens the freshly linked plugin .so to write the optional
    # moduleinfo.json cache metadata; that path proved fragile on OHOS
    # (round-15: loader resolution failure inside the helper). moduleinfo.json
    # is optional for hosts (plugin scanning works via the module entry), so
    # its generation is disabled and the bundle keeps Contents/<arch>/<name>.so.
    VST3_AUTO_MANIFEST FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE)              # Should the plugin be installed to a default location after building?""")

        replace_in_file(
            self, "CMakeLists.txt",
            """        JUCE_WEB_BROWSER=0  # If you remove this, add `NEEDS_WEB_BROWSER TRUE` to the `juce_add_plugin` call
        JUCE_USE_CURL=0     # If you remove this, add `NEEDS_CURL TRUE` to the `juce_add_plugin` call
        JUCE_VST3_CAN_REPLACE_VST2=0)""",
            """        JUCE_WEB_BROWSER=0  # If you remove this, add `NEEDS_WEB_BROWSER TRUE` to the `juce_add_plugin` call
        JUCE_USE_CURL=0     # If you remove this, add `NEEDS_CURL TRUE` to the `juce_add_plugin` call
        JUCE_VST3_CAN_REPLACE_VST2=0
        # OHOS adaptation: the published juce/8.0.5 package lost the vendored
        # oggvorbis libvorbis-1.3.7/lib source subtree (verified on-package:
        # only docs remain under oggvorbis/libvorbis-1.3.7/, so
        # juce_OggVorbisAudioFormat.cpp's #include
        # "oggvorbis/libvorbis-1.3.7/lib/analysis.c" cannot compile); the
        # vendored flac tree is complete (all.h + libFLAC/*.c verified) and
        # stays enabled. This plugin does not decode Ogg assets, so only the
        # Ogg Vorbis codec is disabled (package defect reported to the juce
        # run owner).
        JUCE_USE_OGGVORBIS=0)""")

        # ── 3. 五小件 + xsimd 预解包（conandata fetchcontent 段，SHA256 固定）──
        # conan get() 是"解包到临时目录再 shutil.move 到 destination"：
        # destination 已存在时按 mv 语义嵌套进旧目录。二跳 submodule 的落点
        # （父归档的空 submodule 目录 / 前序解包的父目录树）必然已存在，
        # 故 submodule 一律先解包到 _staging 再受控 rename 就位。
        deps_dir = os.path.join(self.source_folder, "deps")
        fc = self.conan_data["fetchcontent"]
        subs = {
            "RTNeural-xsimd": ("RTNeural", "modules", "xsimd"),
            "clap": ("clap-juce-extensions", "clap-libs", "clap"),
            "clap-helpers": ("clap-juce-extensions", "clap-libs", "clap-helpers"),
        }
        staging_order = [
            "clap-juce-extensions",   # 父工程
            "chowdsp_utils",
            "math_approx",
            "ea_variant",
            "RTNeural",
            "RTNeural-xsimd",         # → RTNeural/modules/xsimd（二跳 submodule）
            "clap",                   # → clap-juce-extensions/clap-libs/clap
            "clap-helpers",           # → clap-juce-extensions/clap-libs/clap-helpers
        ]
        if sorted(fc) != sorted(staging_order):
            raise ConanInvalidConfiguration(
                "conandata fetchcontent keys mismatch: %s" % sorted(fc))
        for key in staging_order:
            entry = fc[key]
            if key in subs:
                tmp = os.path.join(deps_dir, "_staging", key)
                get(self, entry["url"], sha256=entry["sha256"],
                    destination=tmp, strip_root=True)
                final = os.path.join(deps_dir, *subs[key])
                if os.path.isdir(final):
                    if os.listdir(final):
                        raise ConanInvalidConfiguration(
                            "fetchcontent target not empty: %s" % final)
                    os.rmdir(final)
                os.rename(tmp, final)
            else:
                target = os.path.join(deps_dir, key)
                get(self, entry["url"], sha256=entry["sha256"],
                    destination=target, strip_root=True)

        # ── 4. RTNeural CPM bootstrap 守卫：cmake/CPM.cmake 第 19 行构建期从
        #     github releases 下载 CPM 模块（CI 无构建期网络必挂）；CPM 仅被
        #     BUILD_TESTS/BUILD_BENCH/BUILD_EXAMPLES 路径使用（本插件构建全部
        #     OFF，默认行为不变），故仅在需要时 include。──
        replace_in_file(
            self, os.path.join("deps", "RTNeural", "CMakeLists.txt"),
            "include(cmake/CPM.cmake)",
            "# OHOS adaptation: CPM.cmake bootstraps via a github release\n"
            "# download; only tests/bench/examples (all OFF in this plugin\n"
            "# build) consume CPM, so include it only when requested.\n"
            "if(BUILD_TESTS OR BUILD_BENCH OR BUILD_EXAMPLES)\n"
            "    include(cmake/CPM.cmake)\n"
            "endif()")

        # ── 5. musl 数学函数补丁：两份 vendored xsimd 的 float exp10 走
        #     ::exp10f/__GLIBC__ 分支，OHOS musl 的 math.h 完全不暴露 exp10
        #     家族（exp10/exp10f 均无）；统一改走可移植的 std::pow（<cmath>
        #     两文件均已包含）。──
        for rel in (os.path.join("deps", "chowdsp_utils", "modules", "dsp",
                                 "chowdsp_simd", "third_party", "xsimd",
                                 "include", "xsimd", "arch", "xsimd_scalar.hpp"),
                    os.path.join("deps", "RTNeural", "modules", "xsimd",
                                 "include", "xsimd", "arch", "xsimd_scalar.hpp")):
            replace_in_file(
                self, rel,
                "        return ::exp10f(x);",
                "        return std::pow(10.0f, x);  // OHOS musl: no exp10 family")
            replace_in_file(
                self, rel,
                "        return ::exp10(x);",
                "        return std::pow(10.0, x);  // OHOS musl: no exp10 family")
        # 预解包完整性 fail-fast（防止静默注入空目录导致 configure 期报错难读）
        markers = [
            os.path.join("clap-juce-extensions", "CMakeLists.txt"),
            os.path.join("clap-juce-extensions", "clap-libs", "clap",
                         "CMakeLists.txt"),
            os.path.join("clap-juce-extensions", "clap-libs", "clap-helpers",
                         "CMakeLists.txt"),
            os.path.join("chowdsp_utils", "CMakeLists.txt"),
            os.path.join("math_approx", "CMakeLists.txt"),
            os.path.join("ea_variant", "CMakeLists.txt"),
            os.path.join("RTNeural", "CMakeLists.txt"),
            os.path.join("RTNeural", "modules", "xsimd", "include",
                         "xsimd", "xsimd.hpp"),
        ]
        for rel in markers:
            if not os.path.isfile(os.path.join(deps_dir, rel)):
                raise ConanInvalidConfiguration(
                    "fetchcontent staging incomplete: %s missing" % rel)

    def generate(self):
        # 依赖 .pc（freetype2/fontconfig/alsa/x11/xproto/gl）：JUCEConfig 的
        # juce_add_module linuxPackages 分支在 configure 期按 pkg-config 名探测
        # （E468：探测名与生成 .pc 名一致，freetype→freetype2、xorgproto→xproto）。
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # xorgproto 自带真实 .pc（share/pkgconfig，${pcfiledir} 相对前缀），
        # PkgConfigDeps 不代生成，这里并入 PKG_CONFIG_PATH 供 xproto 解析
        # （juce run 配方同款；X11 协议头断层教训：libx11 包内头不含
        # X.h/Xatom.h/keysym.h，必须 xorgproto 只取 Cflags）。
        try:
            xp_pc = os.path.join(self.dependencies["xorgproto"].package_folder,
                                 "share", "pkgconfig")
            if os.path.isdir(xp_pc):
                self.buildenv_info.append_path("PKG_CONFIG_PATH", xp_pc)
        except KeyError:
            pass

        tc = CMakeToolchain(self)
        # E092/juce run test_package 先例：强制上游 Linux 平台分支。JUCE 包内
        # 补丁只覆盖了 JUCEModuleSupport.cmake 的四处分支；插件目标侧
        # JUCEUtils.cmake 的 VST3 bundle 布局（LIBRARY_OUTPUT_DIRECTORY →
        # Contents/<arch>-linux）等仍直接判 CMAKE_SYSTEM_NAME=="Linux"，
        # 不强制会使 VST3 退化为单文件 .so 且 POST_BUILD moduleinfo 步骤
        # 失配（实测 round-12）。build==host 设备上语义等价。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # find_package(JUCE) 解析包内官方 JUCEConfig.cmake（juce run
        # test_package 消费范式：包前缀经工具链变量传入）。
        tc.variables["JUCE_PACKAGE_DIR"] = self.dependencies["juce"].package_folder
        # E292：FetchContent 五小件预解包注入（上游 declare 保留原样，仅覆盖
        # SOURCE_DIR；FetchContent 不再访问网络）。
        deps_src = os.path.join(self.source_folder, "deps")
        for uc_name, staging in (
                ("JUCE-CLAP-EXTENSIONS", "clap-juce-extensions"),
                ("CHOWDSP_UTILS", "chowdsp_utils"),
                ("RTNEURAL", "RTNeural"),
                ("MATH_APPROX", "math_approx"),
                ("EA_VARIANT", "ea_variant")):
            tc.variables["FETCHCONTENT_SOURCE_DIR_" + uc_name] = os.path.join(
                deps_src, staging)
        # E505：插件 bundle 各布局深度的 $ORIGIN rpath + 包内/构建树视图的
        # 绝对路径双保险（包内 lib/jc303-runtime 与插件 bundle 同前缀自洽，
        # 构建树视图保证构建期 helper/探针可用）。
        plugin_rpath = (_PLUGIN_RPATH_PREFIX
                        + " -Wl,-rpath," + os.path.join(
                            self.package_folder, "lib", _VIEW_DIRNAME)
                        + " -Wl,-rpath," + os.path.join(
                            self.build_folder, _VIEW_DIRNAME))
        for var in ("CMAKE_MODULE_LINKER_FLAGS", "CMAKE_SHARED_LINKER_FLAGS"):
            tc.variables[var] = plugin_rpath
        tc.generate()

        # E505（构建树侧）：LV2/VST3 的 POST_BUILD 会运行包内预构建 helper
        # （juce_lv2_helper/juce_vst3_helper）真实 dlopen 刚链接的插件 .so
        # 生成 bundle 元数据（.ttl 等），因此运行期视图必须在构建树同样就位
        # 且逐文件签名（用户存储未签名 .so dlopen 即 EACCES），位置 =
        # <build>/jc303-runtime（与包内 lib/jc303-runtime 对 $ORIGIN 同深度）。
        view = os.path.join(self.build_folder, _VIEW_DIRNAME)
        if not os.path.isdir(view):
            os.makedirs(view, exist_ok=True)
            self._materialise_runtime_view(view)

    def _materialise_runtime_view(self, view):
        """把依赖共享库实体化（真实文件，逐别名名一份）进 view 并逐文件
        binary-sign-tool selfSign（OHOS 安全策略：用户存储 .so 未签名
        dlopen 即 EACCES；mlton/alsa-lib/bam/juce run 配方先例）。"""
        for name in _RUNTIME_VIEW_PACKAGES:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isdir(libdir):
                    continue
                for fn in os.listdir(libdir):
                    if ".so" not in fn:
                        continue
                    src = os.path.join(libdir, fn)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(view, fn)
                    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                    self._sign_elf(dst)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── 打包：插件 bundle + 运行期共享库视图（实体化+签名）+ NEEDED 闭包断言 ──
    def package(self):
        # 上游无 install 规则；从构建树收集三格式插件产物（VST3/LV2/CLAP
        # 均为目录形态：VST3=JC303.vst3/Contents/<arch>/、LV2=JC303.lv2/、
        # CLAP=JC303.clap/ 内层同名二进制）。
        bundle_root = os.path.join(self.package_folder, "lib", "jc303")
        found = {"JC303.vst3": None, "JC303.lv2": None, "JC303.clap": None}
        for root, dirs, files in os.walk(self.build_folder):
            for name in dirs:
                if name in found and found[name] is None:
                    found[name] = os.path.join(root, name)
            for name in files:
                if name in found and found[name] is None:
                    found[name] = os.path.join(root, name)
        missing = [k for k, v in found.items() if v is None]
        if missing:
            raise ConanInvalidConfiguration(
                "plugin bundles not found in build tree: %s" % ", ".join(missing))
        for name, src in sorted(found.items()):
            dst = os.path.join(bundle_root, name)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=dst, keep_path=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                copy(self, os.path.basename(src), src=os.path.dirname(src), dst=dst)

        # 依赖共享库实体化视图：复用 generate() 期已在构建树就位并签名的
        # <build>/jc303-runtime（E505；包内 lib/jc303-runtime 与插件 bundle
        # 的 $ORIGIN 同深度，包自洽、跨机可用）。
        view = os.path.join(self.package_folder, "lib", _VIEW_DIRNAME)
        build_view = os.path.join(self.build_folder, _VIEW_DIRNAME)
        if not os.path.isdir(build_view):
            raise ConanInvalidConfiguration(
                "build-tree runtime view missing: %s" % build_view)
        os.makedirs(os.path.dirname(view), exist_ok=True)
        copy(self, "*", src=build_view, dst=view, keep_path=True)

        # 插件 ELF 一并签名（VST3/LV2 内 .so 与 CLAP 单文件本体）。
        for root, _, files in os.walk(bundle_root):
            for fn in files:
                if fn.endswith(".so") or fn == "JC303.clap":
                    self._sign_elf(os.path.join(root, fn))

        # NEEDED 闭包断言：每个插件 ELF 的非系统 NEEDED 必须落在视图内
        # （防"链接成功但产物不可 dlopen"的隐式闭包，implement-policy §5）；
        # 并断言 $ORIGIN 多级 rpath 真实进入 ELF（防 shell/make 层把 $ORIGIN
        # 展开成空串导致 rpath 失效的静默故障）。
        view_names = set(os.listdir(view))
        allowed = view_names | {"libc.so", "libc++_shared.so", "libdl.so", "libm.so",
                                "libpthread.so", "librt.so", "libresolv.so"}
        for root, _, files in os.walk(bundle_root):
            for fn in sorted(files):
                if not (fn.endswith(".so") or fn == "JC303.clap"):
                    continue
                path = os.path.join(root, fn)
                needed = self._elf_needed(path)
                unresolved = [n for n in needed if n not in allowed]
                if unresolved:
                    raise ConanInvalidConfiguration(
                        "unresolved DT_NEEDED closure in %s: %s (view has %d entries)"
                        % (os.path.relpath(path, self.package_folder),
                           ", ".join(unresolved), len(view_names)))
                rpaths = self._elf_rpaths(path)
                pkg_view = os.path.join(self.package_folder, "lib", _VIEW_DIRNAME)
                if (not any("$ORIGIN" in r for r in rpaths)
                        and not any(r.rstrip("/") == pkg_view for r in rpaths)):
                    raise ConanInvalidConfiguration(
                        "neither $ORIGIN nor package runtime-view rpath present "
                        "in %s (rpaths=%r)" % (
                            os.path.relpath(path, self.package_folder), rpaths))

        # 证件照：license/README（GPL-3.0 单文件 LICENSE）。
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 插件产物包：无头文件/链接消费面（宿主 DAW 经插件扫描加载，不链接）。
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []

    # ── helpers ──
    @staticmethod
    def _find_tool(name, extra_dirs):
        found = shutil.which(name)
        if found:
            return found
        for d in extra_dirs:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration(
            "jc303/0.12.3 requires '%s'; not found in PATH or %s"
            % (name, ", ".join(extra_dirs)))

    def _sign_elf(self, path):
        """OHOS ELF 自签名（binary-sign-tool selfSign）；签名产物固定 640，
        恢复执行位（mlton/alsa-lib/bam/juce 先例）。"""
        signer = self._find_tool("binary-sign-tool",
                                 ("/storage/Users/currentUser/usr/local/bin",
                                  "/data/service/hnp/bin"))
        objcopy = self._find_tool("llvm-objcopy", ("/data/service/hnp/bin",))
        clean, signed = path + ".clean", path + ".signed"
        subprocess.run([objcopy, "--remove-section", ".codesign", path, clean],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", clean, "-outFile", signed,
                        "-selfSign", "1"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.chmod(signed, 0o750)
        os.replace(signed, path)
        if os.path.exists(clean):
            os.remove(clean)

    def _elf_needed(self, path):
        readelf = self._find_readelf()
        if readelf is None:
            # 无 readelf 可用时跳过断言（不阻塞打包；test_package dlopen 探针
            # 仍是运行期闭包的权威验证）。
            return []
        out = subprocess.run([readelf, "-d", path], capture_output=True,
                             text=True, check=False).stdout
        names = []
        for line in out.splitlines():
            if "(NEEDED)" in line and "[" in line and "]" in line:
                names.append(line.split("[", 1)[1].rsplit("]", 1)[0])
        return names

    def _elf_rpaths(self, path):
        readelf = self._find_readelf()
        if readelf is None:
            # 与 _elf_needed 同理：无 readelf 时视为通过（test_package 兜底）。
            return ["$ORIGIN/" + _VIEW_DIRNAME]
        out = subprocess.run([readelf, "-d", path], capture_output=True,
                             text=True, check=False).stdout
        names = []
        for line in out.splitlines():
            if "(RPATH)" in line or "(RUNPATH)" in line:
                if "[" in line and "]" in line:
                    names.append(line.split("[", 1)[1].rsplit("]", 1)[0])
        return names

    @staticmethod
    def _find_readelf():
        for tool in ("llvm-readelf", "readelf"):
            try:
                return Jc303Conan._find_tool(tool, ("/data/service/hnp/bin",))
            except ConanInvalidConfiguration:
                continue
        return None
