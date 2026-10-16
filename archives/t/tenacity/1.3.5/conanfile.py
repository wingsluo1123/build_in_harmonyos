#!/usr/bin/env python3
"""Conan 2.x recipe — tenacity 1.3.5（路径 B：非 GUI 核心库适配）

tenacity 是 wxWidgets 的音频编辑器（Audacity 分支），上游顶层 CMakeLists 要求
    find_package(wxWidgets 3.1 REQUIRED COMPONENTS base core html net)
其中 core/html/net 均为 wxUSE_GUI=ON 才构建的 GUI 组件。

OHOS 阻塞（W0/R36 实证）：
    ohpcd 已合入的 wxWidgets 全部版本（3.2.10 / 3.3.3 / 3.3.3.1 / 3.3.3.2）都以
    wxUSE_GUI=OFF 构建——recipe 原文 "builds the base toolkit (non-GUI)"、
    tc.variables["wxUSE_GUI"]="OFF"；发布包 setup.h 中 #define wxUSE_GUI 0，
    lib/ 仅 libwx_baseu-*.a / libwxregexu-*.a，无 core/html/net 实体。
    全盘穷举 libwx*core* / libwx*html* / libwx_net* 零命中；
    wx-config --selected-config 唯一配置 base-unicode-static-3.x。

wxWidgets 版本选定（R36 实证后改版）：
    初版依赖 wxwidgets/3.2.10，其**已发布制品**（ohpcd 与本地逐字同修订
    b145b32324b9d8283025188312c9964b）缺全部平台源——libwx_baseu-3.2.a 的
    93 个成员中 unix/msw/osx 零命中，真实链接消费者报 52 个未定义 wx 平台符号
    （wxDir::* / wxAppTraits::* / wxStandardPaths::* / wxMutex / wxThread /
    wxGetEnv / wxUILocaleImpl::* 等）。根因：上游 build/cmake/lib/base/CMakeLists.txt
    用 elseif(UNIX) 选平台源，交叉编译 CMAKE_SYSTEM_NAME=HarmonyOS 时 UNIX 为假；
    同仓 wxwidgets/3.2.6 配方有正解（tc.cache_variables["UNIX"]="ON"），3.2.10 回归丢失。
    处置（用户裁决走 b）：改用 wxwidgets/3.3.3.2——ohpcd 有完整二进制
    （rev a6cd2c0c9ad9ff214ff5ab9c2cec50b4 / pkg 4b9772641a1c74e82bd6bb51b63cc9aadc4cfa），
    6 个归档（baseu / baseu_net / baseu_xml / wxregexu / wxzlib / wxexpat）且配方自带
    includedirs=["include/wx-3.3", ...]；其 cmake_target_name 为驼峰
    wxWidgets::wxWidgets（与上游同名，CMakeDeps 直接提供，patch 0001 的 bridge 自动跳过）。
    证据：reports/r36-wxwidgets-3.2.10-link-undefined-symbols.log

适配手法（与本仓库 aegisub 3.4.2「libaegisub 核心库 + 禁用 GUI 前端」同构）：
    仅构建 libraries/lib-* 的 17 个非 GUI 核心库（251 个源文件）。
    实证：这 17 个子库对 GUI-only wx 头零引用，仅用 wxBase；与 src/ 零反向依赖；
    外部依赖仅 PortAudio / Soxr / PortMidi(未发布，自动关) / wxBase。
    见 patches/0001..0004 与 reports/adaptation-analysis.md。

依赖处理（与 archives/a/accountsservice/26.27.3 同构）：
    交付物真实传递依赖 4 个 —— wxwidgets( wxBase ) / portaudio / libsoxr / expat，
    全部 visible=True 并列入 cpp_info.requires。上游顶层 CMakeLists.txt:497-502
    另有 7 个 find_package(... REQUIRED) 探针，其中只服务 GUI 前端的
    mp3lame/SndFile/SQLite3 标 visible=False（构建期私有依赖，不向消费者传播），
    zlib 因同时是 wxwidgets 的可见直接依赖而保持可见并列入 cpp_info.requires
    （否则触发 Conan "required both with visible=True and visible=False" 风险告警）。
    详见 requirements() / package_info() 内注释。

上游测试入口（如实申报）：
    无 CTest（全仓 add_test / enable_testing / include(CTest) 零命中）；
    tests/ 未接入构建，且 tests/SequenceTest.cpp 与 tests/SimpleBlockFileTest.cpp
    是 Audacity 时代陈旧残留——引用的 DirManager.h 与 blockfile/SimpleBlockFile.h
    在 1.3.5 源码中均不存在，无法编译。故上游测试 0/0，附技术原因；
    可行性验证由 test_package 的鸿蒙消费者用例承担（真实链接 + 真实 API 调用 +
    --selftest 无头断言 + no-display fail-closed）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class TenacityConan(ConanFile):
    name = "tenacity"
    version = "1.3.5"
    description = ("Tenacity — non-GUI core libraries (lib-*) of the "
                   "wxWidgets-based multitrack audio editor")
    license = "GPL-2.0-or-later"
    homepage = "https://tenacityaudio.org"
    url = ""
    topics = ("audio", "wxwidgets", "core-library")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            # 与 libsoxr 等同构：shared 时 fPIC 由构建系统自行处理
            self.options.rm_safe("fPIC")
        # 本包只交付静态核心库；shared 形态未验证，显式拒绝而非静默产出错架构
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "tenacity/1.3.5 仅适配静态核心库（BUILD_STATIC_LIBS=ON）；"
                "shared 形态未验证，请使用 -o tenacity/*:shared=False")

    def requirements(self):
        # 全部经 W0 三证探针核验（每依赖全新空 CONAN_HOME + conan download
        # -r=ohpcd，排除本地缓存污染；正对照 RC=0 证明网络与匿名可读）。
        # wxwidgets 传递 zlib/1.3.1.1、expat/2.8.2、curl/8.15.0、openssl/3.5.6.1。
        #
        # ① 交付物的真实传递依赖（visible=True，全部列入 cpp_info.requires）。
        #    17 个 lib-* 对这些库的引用已逐库核验：
        #      wxwidgets → 11 个子库用 wxString/wxFileName/wxFileConfig 等 wxBase
        #      portaudio → lib-audio-devices（AudioIOBase.h / DeviceManager.cpp 含 portaudio.h）
        #      libsoxr   → lib-math（Resample.cpp 含 <soxr.h>）
        #      expat     → lib-xml（XMLFileReader.cpp 含 "expat.h"）
        #
        # transitive_headers=True 的判定依据（实测，非预防性设置）：
        #   本包 package_type="library"（编译型库），Conan 对这类包的依赖边默认取
        #   transitive_headers=False —— 即消费者不会继承"本包依赖"的 include 目录。
        #   而本包的**公开头文件**直接 #include 了依赖的头，故必须逐边显式打开。
        #   统计（对安装后的 include/tenacity/ 全量扫描）：
        #      <wx/...>      42 处（lib-strings/Interned 等 15 个库的公开头）
        #      <portaudio.h>  1 处（lib-audio-devices/AudioIOBase.h:24）
        #      <expat.h>/<soxr.h>/<zlib.h>  0 处 → 无需打开
        #   未打开时的实测症状：消费者 CMakeDeps 生成
        #      set(wxwidgets_INCLUDE_DIRS_RELEASE )   ← 空（3.2.10 变量前缀；3.3.x 为 wxWidgets_）
        #      → 编译 CodeConversions.h 报 "fatal error: 'wx/string.h' file not found"。
        #   同构先例：knowledge/drafts/DRAFT-cpp-rotor-0.35-boost-trimmed-recipe-missing-components
        #   （其配方同样显式 self.requires(..., transitive_headers=True)）。
        # wxwidgets 版本：3.3.3.2（见文件头「wxWidgets 版本选定」——3.2.10 制品缺
        # 全部平台源，无法链接真实消费者；3.3.3.2 制品完整且自带 includedirs）。
        self.requires("wxwidgets/3.3.3.2", transitive_headers=True)   # wxBase（GUI=OFF）
        self.requires("portaudio/19.7.0", transitive_headers=True)   # lib-audio-devices
        self.requires("libsoxr/0.1.3")        # lib-math（仅 .cpp 引用 soxr.h）
        self.requires("expat/2.8.2")          # lib-xml（仅 .cpp 引用 expat.h）
        #
        # ② 仅服务上游顶层 REQUIRED 探针的构建期私有依赖（visible=False）。
        #    CMakeLists.txt:497-502 有 7 个 find_package(... REQUIRED)；其中
        #      ZLIB:497 / mp3lame:499 / SndFile:500 / SQLite3:502
        #    四者的消费者只有 ZLIB::ZLIB（src/CMakeLists.txt:1065）与
        #    SndFile::sndfile（src/CMakeLists.txt:1068）——均在 GUI 前端，
        #    本包不构建该目录；mp3lame/SQLite3 更连消费者都没有。
        #    libraries/ 与 lib-src/ 对四者零引用（已逐库核验）。
        #    标 visible=False = 私有构建依赖：本节点 build 时 CMakeDeps 照常为其
        #    生成 config（已实测 lame-config.cmake / SndFileConfig.cmake /
        #    sqlite3-config.cmake 均落盘，find_package 仍解析成功），但不再向
        #    消费者传播、也不进消费者 package_id。同构先例：
        #    archives/a/accountsservice/26.27.3（该配方注释原文即
        #    "avoids the Conan 'direct dependency not used by cpp_info.requires' check"）。
        self.requires("lame/3.100", visible=False)        # CMakeLists.txt:499
        self.requires("libsndfile/1.2.2", visible=False)  # CMakeLists.txt:500
        self.requires("sqlite3/3.49.1", visible=False)    # CMakeLists.txt:502
        #
        #    zlib（CMakeLists.txt:497）情形特殊：它同时是 wxwidgets 的**可见**直接
        #    依赖（依赖图内 wxwidgets→zlib 边 visible=True）。此处若同样标
        #    visible=False，Conan 会报
        #      "WARN: risk: Packages required both with visible=True and visible=False
        #       zlib/1.3.1.1: Required by tenacity/1.3.5"（已用最小探针实证）。
        #    故 zlib 保持默认可见并在 cpp_info.requires 中列出——对消费者零边际
        #    成本（zlib 恒经 wxwidgets 进入其闭包），同时满足 Conan 的
        #    "直接依赖必须出现在 cpp_info/components requires 中"完整性校验。
        self.requires("zlib/1.3.1.1")
        #
        # 未发布（ohpcd 零配方）→ 上游 cmake_dependent_option 自动关，不声明：
        #   portmidi（USE_MIDI）、libmatroska（MATROSKA）、lilv（LV2）

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps 为 find_package(ZLIB/EXPAT/mp3lame/SndFile/Soxr/SQLite3/
        # PortAudio/wxWidgets) 生成 config 目标；CMakeToolchain 注入 OHOS 交叉
        # 编译 flag 与各依赖的 package_folder 到 CMAKE_PREFIX_PATH
        # （FindSoxr/FindPortAudio 等 MODULE 模式经该路径实测解析成功）。
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def _configure_variables(self):
        # Conan 2 的 CMake() 助手通过 configure(variables={...}) 传入 -D 变量；
        # 不存在 configure_variables 属性（Conan 1.x 写法，已废弃）。
        return {
            # 仅构建 libraries/lib-* 静态核心库（上游 option 默认 OFF = shared，
            # 静态化既避免 OHOS .so 代码签名要求，也让消费者链接确定性最高）
            "BUILD_STATIC_LIBS": "ON",
            # 宿主 CMake 为 4.1.2：4.x 移除了对 cmake_minimum_required(<3.5) 的
            # 兼容，上游多处声明 3.0/2.8 → 不放开会直接 hard error。
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            # 顶层 find_package(Python3) 非 REQUIRED；仅消息编目用，显式关闭以避免
            # 交叉环境误拾宿主 python
            "CMAKE_DISABLE_FIND_PACKAGE_Python3": "ON",
            # 源码自带 vcpkg.json / VCPKG option 默认 OFF（非 WIN32/APPLE），
            # 仍显式钉死以防将来上游改默认
            "VCPKG": "OFF",
        }

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables=self._configure_variables())
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # 仅交付库与头文件；去掉 configure 期生成的 CMake 包配置缓存噪音
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        # libraries/CMakeLists.txt 的 LIBRARIES 顺序为"依赖在前"（注释原文：
        # "ordered so that each library occurs after any others that it depends on"）。
        # 静态库链接顺序需相反（被依赖方在前会被先扫过），故反转。
        # 17 个库模块名 == 上游 CMake 目标名 == 头文件安装目录名。
        modules = [
            "lib-project-rate", "lib-screen-geometry", "lib-project",
            "lib-audio-devices", "lib-xml", "lib-utility", "lib-track",
            "lib-strings", "lib-registries", "lib-string-utils",
            "lib-preferences", "lib-math", "lib-files", "lib-ffmpeg-support",
            "lib-exceptions", "lib-components", "lib-basic-ui",
        ]
        # cpp_info.libs 条目须写成"去掉 lib 前缀但保留连字符"的形式（如 -project-rate）。
        # 不能直接写 lib-project-rate。原因链（三步均有实测证据）：
        #   1) TenacityFunctions.cmake:379 的库分支对目标设 PREFIX ""，而目标名本身已含
        #      lib- 前缀 → 归档实际名为 lib-<name>.a（非 Unix 惯例 lib<name>.a）；
        #   2) Conan CMakeDeps 用 find_library(NAMES <cpp_info.libs 条目> PATHS <libdir>)
        #      解析（生成的 cmakedeps_macros.cmake:33），逐个条目走 find_library；
        #   3) CMake find_library 会强制拼接 CMAKE_FIND_LIBRARY_PREFIXES（默认 "lib"），
        #      即实际查找 "lib" + <条目> + ".a"。
        # 实测（cmake -P，PATHS 指向真实包目录 $CONAN_HOME/p/<pkg>/p/lib）：
        #   NAMES=lib-project-rate → NOTFOUND（拼成 liblib-project-rate.a）
        #   NAMES=project-rate     → NOTFOUND（拼成 libproject-rate.a）
        #   NAMES=-project-rate    → 命中 lib-project-rate.a      ✔
        # 该写法对下游两类消费方式均正确：CMakeDeps 与裸 -l 参数（-l-project-rate 同样
        # 查找 lib-project-rate.a）。归档文件保持上游构建产物原名，不做重命名，
        # 以便审计/elf_check 证据与真实构建输出逐字对应。
        self.cpp_info.libs = ["-" + m[len("lib-"):] for m in modules]
        # 各 lib-* 的公开头文件用 import/export 符号宏标注（如 extern MATH_API ...、
        # class EXCEPTIONS_API ...）。上游由 cmake-proxies/cmake-modules/
        # TenacityFunctions.cmake 的 import_symbol_define() 生成，取值取决于
        # HAVE_VISIBILITY；而顶层 CMakeLists.txt 在 add_subdirectory(libraries) 之后
        # 才 set(HAVE_VISIBILITY 1)，故实测构建命令中的形态一律为空值
        # （-DMATH_API=""）。符号宏取空值即退化为普通声明，这里逐一还原成同样的空定义；
        # 不导出的话消费者编译头文件会直接报 "unknown type name 'MATH_API'"。
        # USE_FFMPEG 虽在上游声明为 PUBLIC，但 libraries/ 下无任何头文件或源码读它
        # （仅 lib-ffmpeg-support/CMakeLists.txt 用它挑选源文件），故不导出。
        self.cpp_info.defines = [
            "AUDIO_DEVICES_API=", "BASIC_UI_API=", "COMPONENTS_API=",
            "EXCEPTIONS_API=", "FFMPEG_SUPPORT_API=", "FILES_API=",
            "MATH_API=", "PREFERENCES_API=", "PROJECT_API=",
            "PROJECT_RATE_API=", "REGISTRIES_API=", "SCREEN_GEOMETRY_API=",
            "STRINGS_API=", "STRING_UTILS_API=", "TRACK_API=",
            "UTILITY_API=", "XML_API=",
        ]
        # 每个 lib-* 的头文件装在 include/tenacity/<lib>/，与 tenacity_module_fn()
        # 给各目标设置的 PUBLIC ${TARGET_ROOT} 包含目录一一对应，消费者因此可以
        # 沿用上游的扁平 basename 风格（如 #include "Prefs.h"）跨库引用头文件。
        self.cpp_info.includedirs = ["include/tenacity/" + m for m in modules]
        # 传递依赖：仅列 lib-* 静态库真实引用符号/头的依赖（已逐库核验）：
        #   wxwidgets::wxwidgets  —— 11 个子库（wxString/wxFileName/wxFileConfig 等 wxBase）
        #   portaudio::portaudio   —— lib-audio-devices（AudioIOBase/DeviceManager 含 portaudio.h）
        #   libsoxr::libsoxr       —— lib-math（Resample.cpp 含 soxr.h）
        #   expat::expat           —— lib-xml（XMLFileReader.cpp 含 expat.h）
        #   zlib::zlib             —— lib-* 自身零引用（无 #include <zlib.h>），此处列出
        #     是出于 Conan 的完整性校验：只要 cpp_info.requires 里出现 pkg::comp
        #     形式，所有 visible 的直接依赖都必须出现（否则报 "The direct dependency
        #     'x' is not used by any '(cpp_info/components).requires'"）。zlib 只服务
        #     顶层 CMakeLists.txt:497 的 REQUIRED 探针、且同时是 wxwidgets 的可见
        #     直接依赖（详见 requirements() 内注释），列出它对消费者零边际成本
        #     ——zlib 恒经 wxwidgets 进入其闭包。同理被探针要求但已标 visible=False
        #     的 lame/libsndfile/sqlite3 无需列出（不可见依赖不参与该校验）。
        # 注：条目中的 "wxwidgets" 是**依赖引用名**（与 requirements() 中逐字一致，
        # Conan 按包名匹配）；消费者侧 CMake target 名由 wxwidgets 配方自身的
        # cmake_target_name 决定（3.3.x 为驼峰 wxWidgets::wxWidgets），两者无关。
        self.cpp_info.requires = [
            "wxwidgets::wxwidgets",
            "portaudio::portaudio",
            "libsoxr::libsoxr",
            "expat::expat",
            "zlib::zlib",
        ]
