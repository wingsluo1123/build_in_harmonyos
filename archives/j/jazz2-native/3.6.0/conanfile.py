#!/usr/bin/env python3
"""Conan recipe — jazz2-native 3.6.0 (Jazz² Resurrection).

Jazz² Resurrection is an open-source reimplementation of Jazz Jackrabbit 2
(1998), built on the nCine engine, GPL-3.0-or-later, C++17 + CMake.
Upstream: https://github.com/deathkiller/jazz2-native

OHOS 适配要点：
  - 上游默认 NCINE_DOWNLOAD_DEPENDENCIES=ON，会在 configure 阶段用
    ExternalProject 从 GitHub（jazz2-libraries）下载依赖——CI 沙箱无外网，
    置 OFF 并改由 Conan CMakeDeps 提供 SDL2 / OpenAL / Vorbis / zlib；
  - NCINE_WITH_OPENMPT=OFF：libopenmpt 未在制品仓发布（详见 notes.md），
    模块音乐（.j2b/.mod）播放能力暂缺，其余音频（Ogg Vorbis）不受影响；
  - aarch64 上 NCINE_ARM_PROCESSOR=TRUE，上游据此默认 NCINE_WITH_OPENGLES=ON
    （OpenGL ES 2.0 渲染路径），故桌面 GLEW 路径关闭（NCINE_WITH_GLEW=OFF）；
  - E092：CMAKE_SYSTEM_NAME=Linux / CMAKE_SYSTEM_PROCESSOR=aarch64
    （OHOS 下 CMakeToolchain 会映射为 HarmonyOS，需显式覆盖，仓库多库先例）；
  - LTO 关闭：clang 15 + OHOS lld 下 LTO 链接易超时且无收益；
  - 产物 jazz2 需 llvm-objcopy 剥 .codesign + binary-sign-tool 自签，
    否则运行报 Operation not permitted（milkytracker / chromono 先例）；
  - 上游无任何自动化测试（无 ctest / add_test，见 test_package/MANIFEST.yml），
    但 main() 原生支持 `--version` 早退（Sources/Main.cpp:2243），
    test_package 直接运行该二进制做冒烟验证（无需打补丁）。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class Jazz2NativeConan(ConanFile):
    name = "jazz2-native"
    version = "3.6.0"
    description = "Jazz² Resurrection - open-source reimplementation of Jazz Jackrabbit 2"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/deathkiller/jazz2-native"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("openal-soft/1.25.2")
        self.requires("libvorbis/1.3.7")
        # 与 libcurl/8.5.0 传递依赖对齐（1.3.1 会触发版本冲突）
        self.requires("zlib/1.3.1.1")
        # Sources/Shared/IO/WebRequest.cpp 在非 Windows 平台上无条件包含
        # <curl/curl.h>（上游无 WITH_CURL 守卫）→ curl 在 Linux/OHOS 上是硬依赖
        self.requires("libcurl/8.5.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_sysroot_libdir(self):
        """通过编译器自身定位 OHOS SDK sysroot 库目录（casacore/3.7.1 先例）。

        CMake 不知道 OHOS sysroot（toolchain 未设 CMAKE_SYSROOT），上游自带的
        cmake/FindOpenGLES2.cmake 只搜 /usr/lib 等桌面路径 → OPENGLES2_FOUND
        FALSE → 既不链 GLESv2/EGL 也不走 ES 渲染路径。这里用 clang 自己的
        -print-file-name=libm.a 反查 sysroot 库目录，再据此填 4 个查找变量。
        """
        if self.settings.os != "OHOS":
            return None
        cc_map = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        candidates = [cc_map.get("c"), cc_map.get("cpp"),
                      shutil.which("clang"), shutil.which("clang++"),
                      "/data/service/hnp/bin/clang", "/data/service/hnp/bin/clang++"]
        for cc in candidates:
            if not cc:
                continue
            try:
                out = subprocess.check_output([cc, "-print-file-name=libm.a"],
                                              stderr=subprocess.DEVNULL, text=True, timeout=30).strip()
            except Exception:
                continue
            if not out.endswith("libm.a"):
                continue
            libdir = os.path.normpath(os.path.dirname(out))
            if os.path.isfile(os.path.join(libdir, "libGLESv2.so")):
                return libdir
        return None

    def generate(self):
        deps = CMakeDeps(self)
        # 上游硬编码查找 Conan 目标名（ncine_compiler_options / ncine_extra_sources）：
        #   zlib → ZLIB::ZLIB、sdl2 → SDL2::SDL2、libvorbis → Vorbis::Vorbisfile
        # 而制品的声明名是 zlib::zlib / sdl2::sdl2 / libvorbis::vorbisfile，
        # 目标名大小写不匹配会导致 generate 阶段 "target was not found"。
        # 用 CMakeDeps 属性对齐到上游期望名，避免为改名打上游补丁。
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("sdl2", "cmake_file_name", "SDL2")
        deps.set_property("sdl2", "cmake_target_name", "SDL2::SDL2")
        deps.set_property("libvorbis", "cmake_target_name", "Vorbis::Vorbisfile")
        deps.generate()

        tc = CMakeToolchain(self)
        # CMake 4.x 兼容 + E092 平台绕过（仓库多库先例）
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # 依赖全部来自 Conan（CI 无外网，禁止 configure 期下载）
        tc.cache_variables["NCINE_DOWNLOAD_DEPENDENCIES"] = "OFF"
        tc.cache_variables["NCINE_PREFERRED_BACKEND"] = "SDL2"
        tc.cache_variables["NCINE_WITH_OPENGLES"] = "ON"
        tc.cache_variables["NCINE_WITH_GLEW"] = "OFF"
        tc.cache_variables["NCINE_WITH_BACKWARD"] = "OFF"
        # libopenmpt 未发布（见 notes.md）：模块音乐能力暂缺
        tc.cache_variables["NCINE_WITH_OPENMPT"] = "OFF"
        tc.cache_variables["NCINE_VERSION_FROM_GIT"] = "OFF"
        tc.cache_variables["NCINE_CREATE_CONTENT_SYMLINK"] = "OFF"
        tc.cache_variables["NCINE_LINKTIME_OPTIMIZATION"] = "OFF"
        # OHOS musl 的 ldso 不实现 R_AARCH64_IRELATIVE：带 ifunc 的可执行文件一启动就报
        # "unsupported relocation type 1032" 退出（实测本二进制 5 个 IRELATIVE 全部来自
        # nCine 的 StringUtils/StringView 运行时分发）。上游只用
        # check_cxx_source_compiles 验证工具链能否生成 ifunc，并不验证目标加载器能否重定位，
        # 所以这里显式关闭，回退到上游等价的 DEATH_CPU_DISPATCHED_POINTER 运行时指针分发
        tc.cache_variables["DEATH_CPU_USE_IFUNC"] = "OFF"
        # 安装路径 share/<PACKAGE_DIRECTORY>/Content：默认含 "Jazz² Resurrection"
        # （含 U+00B2 非 ASCII 字符），改为 ascii 名避免路径问题
        tc.cache_variables["NCINE_LINUX_PACKAGE"] = "jazz2"

        # SDL2 制品头文件位于 include/SDL2/ 下，而 CMakeDeps 只把包根 include/ 加进
        # 搜索路径；上游在 CMAKE_BUILD 模式下按发行版惯例包含 <SDL.h>/<SDL_events.h>
        # （pkg-config 会额外给 -I.../include/SDL2，Conan 不会）→ 这里补齐该子目录，
        # 避免为头文件写法给上游打补丁
        sdl2_include = os.path.join(self.dependencies["sdl2"].package_folder, "include", "SDL2")
        if os.path.isdir(sdl2_include):
            tc.extra_cxxflags.extend(["-isystem", sdl2_include])

        # OHOS：给上游 FindOpenGLES2.cmake 补 sysroot 线索（否则找不到 GLESv2/EGL）
        libdir = self._ohos_sysroot_libdir()
        if libdir:
            incdir = os.path.join(os.path.dirname(os.path.dirname(libdir)), "include")
            # 上游 ES 渲染路径用到 ES3 入口点（glGenVertexArrays / glTexStorage2D /
            # glMapBufferRange / glGetStringi 等），而 sysroot 的 libGLESv2.so 只导出
            # ES2 核心 → 链接期 undefined symbol；libGLESv3.so 同时导出 ES2 核心与
            # ES3 全部入口点（nm -D 实测），故优先选它
            gles_lib = os.path.join(libdir, "libGLESv3.so")
            if not os.path.isfile(gles_lib):
                gles_lib = os.path.join(libdir, "libGLESv2.so")
            tc.cache_variables["OPENGLES2_LIBRARY"] = gles_lib
            tc.cache_variables["EGL_LIBRARY"] = os.path.join(libdir, "libEGL.so")
            tc.cache_variables["OPENGLES2_INCLUDE_DIR"] = incdir
            tc.cache_variables["EGL_INCLUDE_DIR"] = incdir
            self.output.info("OHOS sysroot GLES/EGL libdir: %s" % libdir)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游无自动化测试（无 ctest / add_test），验证见 test_package

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _sign_binaries(self):
        """OHOS ELF 必须自签，否则运行报 Operation not permitted。"""
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in glob.glob(os.path.join(bindir, "*")):
            if not os.path.isfile(f):
                continue
            # 未签名的产物没有 .codesign 段，此时 llvm-objcopy 返回非零属预期，
            # 故忽略其退出码（签名由下一行 binary-sign-tool 完成）
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
