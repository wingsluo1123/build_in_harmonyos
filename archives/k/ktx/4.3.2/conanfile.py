#!/usr/bin/env python3
"""Conan recipe for KTX-Software (Khronos Texture) -- CMake build.

Package name `ktx`, version `4.3.2`, exactly as requested by the task pool
(activity: 开源鸿蒙PC专项积分赛-依赖, task id 14729).

Upstream is the same project as the already archived
`archives/k/ktx-software/4.4.2` recipe, which is used here as the template: it
needs no external dependencies (basisu / astc-encoder / zstd / miniz are all
vendored in the source tree).

Three differences between upstream 4.3.2 and 4.4.2 drive every deviation from
that template.  Each one was established by diffing the two real source trees
(v4.4.2 CMakeLists.txt 62199 B vs v4.3.2 CMakeLists.txt 50722 B) and reading
the respective cmake/version.cmake and mkversion:

  1. Library type switch.
     4.3.2 : KTX_FEATURE_STATIC_LIBRARY  (ON => static; default OFF => SHARED)
     4.4.2 : BUILD_SHARED_LIBS           (standard CMake switch)
     Setting only BUILD_SHARED_LIBS on 4.3.2 is silently ignored, which would
     produce a *shared* libktx where the platform expects the 4.4.2 layout
     (static).  Both variables are therefore set, so the intent is unambiguous
     on either source tree.

  2. Version string.
     4.4.2 reads an explicit `KTX_GIT_VERSION_FULL` override inside
     cmake/version.cmake; 4.3.2 calls git_describe_raw() unconditionally.  The
     released tarball carries no .git, so 4.3.2 degrades to `0.0.0-noversion`
     and emits a configure WARNING, and its ./mkversion stamps version.h with
     the v4.0 fallback.  patches/0001 backports the 4.4.2 override mechanism,
     and the recipe passes the same -DKTX_GIT_VERSION_FULL=v<version> that the
     4.4.2 recipe uses.

  3. Version generator location: ./mkversion at the repo root in 4.3.2, moved
     to scripts/mkversion in 4.4.2 (4.4.2 also gained a `-v` option, which is
     what lets it work without a patch at all).

Two more issues are OHOS-specific and were found by running `conan create` on a
HarmonyOS PC workstation (both are handled by patches/0001 and by passing the
version as a -D below, not through the toolchain):

  4. `cmake/version.cmake` is include()d at line 13 of the top-level
     CMakeLists, i.e. BEFORE project() at line 25 -- and cmake only reads
     CMakeToolchain's conan_toolchain.cmake at project() time.  A toolchain
     variable is therefore still EMPTY there, which is why
     -DKTX_GIT_VERSION_FULL must be a real command-line cache variable (an
     empty value sends version.cmake down the git_describe_raw() path, which
     cannot work without .git and warns "Falling back to 0.0.0-noversion").

  5. Upstream generates version.h with the ./mkversion shell script, invoked
     directly, i.e. it relies on the kernel exec'ing a file that lives in the
     build tree.  On HarmonyOS PC the whole conan -> cmake -> make chain runs
     in the restricted `adhoc_bin` domain, which refuses to execute files
     outside the preinstalled hnp paths, so the build dies with
     `/bin/sh: ./mkversion: Permission denied` (make Error 126) even though
     the file is present and mode 0770.  patches/0001 hands the script to
     ${BASH_EXECUTABLE} (guaranteed by find_package(Bash REQUIRED)) so the
     interpreter reads it instead of the kernel executing it.

Nothing in the GL/VK upload surface is enabled: both are dlopen-based and the
task's downstream only needs the KTX read/write + transcode core.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KtxConan(ConanFile):
    name = "ktx"
    version = "4.3.2"
    description = "Khronos KTX library and tools for reading/writing KTX texture files"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/KTX-Software"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "tools": [True, False],
        "gl_upload": [True, False],
        "vk_upload": [True, False],
    }
    default_options = {
        "shared": False,
        "tools": True,
        "gl_upload": False,
        "vk_upload": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # --- 差异 1：库类型开关（4.3.2 用 KTX_FEATURE_STATIC_LIBRARY）--------
        tc.variables["KTX_FEATURE_STATIC_LIBRARY"] = (
            "OFF" if self.options.shared else "ON")
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # --- 其余开关与 4.4.2 模板保持一致 ---------------------------------
        tc.variables["KTX_FEATURE_TESTS"] = "OFF"
        tc.variables["KTX_FEATURE_LOADTEST_APPS"] = "OFF"
        tc.variables["KTX_FEATURE_DOC"] = "OFF"
        tc.variables["KTX_FEATURE_JNI"] = "OFF"
        tc.variables["KTX_FEATURE_PY"] = "OFF"
        tc.variables["KTX_FEATURE_TOOLS"] = "ON" if self.options.tools else "OFF"
        tc.variables["KTX_FEATURE_GL_UPLOAD"] = "ON" if self.options.gl_upload else "OFF"
        tc.variables["KTX_FEATURE_VK_UPLOAD"] = "ON" if self.options.vk_upload else "OFF"
        # --- 差异 2：版本号（需 patches/0001 把 4.4.2 的机制搬回 4.3.2）------
        # 注意：KTX_GIT_VERSION_FULL **不能**放在这里。cmake/version.cmake 由顶层
        # CMakeLists 的第 13 行 include()，早于第 25 行的 project()；而 cmake 只在
        # project() 时才读取 conan_toolchain.cmake。实测（真机 CMakeCache.txt 里确实
        # 有 KTX_GIT_VERSION_FULL:STRING=v4.3.2，但那是 project() 之后才写进去的）
        # ⇒ 工具链变量在第 13 行仍是空值，version.cmake 会走 git_describe_raw() 并对
        # 无 .git 的 tarball 报 "Falling back to 0.0.0-noversion"。改为在 build() 里
        # 用真实命令行 -D 传入（见下）。
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 必须用命令行 -D（configure 一开始就建立的 cache 项，任何 CMakeLists 命令
        # 之前就存在），而不是工具链变量：理由见上面的 generate() 注释与 patches/0001。
        cmake.configure(
            variables={"KTX_GIT_VERSION_FULL": "v{}".format(self.version)})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ktx"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["c++", "dl", "pthread", "m"]
        if self.options.tools:
            self.cpp_info.bindirs = ["bin"]
