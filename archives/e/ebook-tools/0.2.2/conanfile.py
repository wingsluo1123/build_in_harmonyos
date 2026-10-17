#!/usr/bin/env python3
"""Conan recipe — ebook-tools 0.2.2（cmake；libepub 解析库 + einfo 命令行）。

上游与源码（R39）：SourceForge 官方直链
    https://downloads.sourceforge.net/project/ebook-tools/ebook-tools/0.2.2/ebook-tools-0.2.2.tar.gz
    实测 200 / 46889 字节 / sha256 cbc35996e91114…（与登记记录一致）。

构建要点：
- 上游 `cmake_minimum_required(VERSION 2.4.0)`，CMake 4.x 已移除 <3.5 兼容 ⇒ 必须
  `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（与 archives/l/libzip/1.11.4 同法）。
- `find_package(LibXml2 REQUIRED)` / `find_package(LibZip REQUIRED)`：LibZip 走上游自带
  cmake/FindLibZip.cmake（LIBZIP_LIBRARY/LIBZIP_INCLUDE_DIR 缓存即命中），LibXml2 走 CMake
  内置模块 ⇒ 按 libzip 配方经验**直接预置 find 缓存变量**为依赖真实路径，绕开交叉编译
  FIND_ROOT_PATH=ONLY 与宿主系统同名库污染。
- 依赖注入统一走 `CMAKE_PROJECT_TOP_LEVEL_INCLUDES`（在 toolchain 之后、project() 之前生效，
  压得住 ohos.toolchain 用普通 set() 设的 MODE ONLY）。
- 交叉编译统一用自发现的 ohos.toolchain.cmake + 裸 cmake，绕开 conan_toolchain 在
  os=OHOS 下的 CMAKE_SYSTEM_NAME 映射问题（ML-0035）。
- 产物含 .so 与可执行文件 bin/einfo，鸿蒙 XPM 要求二者都签名，否则 dlopen/exec 报
  Permission denied ⇒ package() 内签名（同 libzip 配方实证做法）。

依赖（W0 已核 ohpcd 已发布）：libxml2/2.15.3.1（OPF/OCF XML 解析）、libzip/1.11.4（EPUB 容器即 zip）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class EbookToolsConan(ConanFile):
    name = "ebook-tools"
    version = "0.2.2"
    description = "EPUB/Mobipocket container parsing library (libepub) with einfo tool"
    license = "MIT"
    homepage = "https://ebook-tools.sourceforge.net/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3.1")
        self.requires("libzip/1.11.4")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── OHOS 工具链/依赖接线（与 archives/l/libzip/1.11.4 同法，实证可用） ──

    def _ohos_toolchain(self):
        """自发现 ohos.toolchain.cmake：profile [conf] → OHOS_NDK_HOME → glob 设备/CI SDK 布局。"""
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        """OHOS SDK 只带 llvm-ar 没有 llvm-ranlib，造静态库时会报无头案（同 libzip 实证）。

        返回 "" 表示不覆盖（SDK 自带的就用它）；本包上游只产 .so，留此兜底以防
        工具链变体（shared=False 或新增静态产物）重踩。
        """
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _find_deps_preload(self):
        """把依赖包目录塞进 CMAKE_PREFIX_PATH/CMAKE_FIND_ROOT_PATH（MODE 置 BOTH）。

        必须经 CMAKE_PROJECT_TOP_LEVEL_INCLUDES 注入：ohos.toolchain 用普通 set()（非 CACHE）
        把 MODE 设成 ONLY，命令行 cache 变量盖不住。
        """
        deps = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        if not deps:
            return ""
        path = os.path.join(self.build_folder, "ohos-find-deps.cmake")
        with open(path, "w", encoding="utf-8") as f:
            for d in deps:
                p = d.replace("\\", "/")
                f.write('list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % p)
                f.write('list(APPEND CMAKE_PREFIX_PATH "%s")\n' % p)
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n")
            f.write("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n")
        return path

    def _dep_inc(self, ref_name):
        dep = self.dependencies[ref_name]
        for p in dep.cpp_info.includedirs:
            if os.path.isfile(os.path.join(p, "zip.h")) or os.path.isfile(os.path.join(p, "libxml", "parser.h")):
                return p
        return dep.cpp_info.includedirs[0] if dep.cpp_info.includedirs else ""

    def _dep_lib(self, ref_name, stem):
        dep = self.dependencies[ref_name]
        for ld in dep.cpp_info.libdirs:
            for pat in ("lib%s.so" % stem, "lib%s.so.*" % stem, "lib%s.a" % stem):
                hits = sorted(glob.glob(os.path.join(ld, pat)))
                if hits:
                    return hits[0]
        return ""

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")

        xml_inc = self._dep_inc("libxml2")
        xml_lib = self._dep_lib("libxml2", "xml2")
        zip_inc = self._dep_inc("libzip")
        zip_lib = self._dep_lib("libzip", "zip")

        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            # 上游 cmake_minimum_required(VERSION 2.4.0)，CMake 4 必需
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        _pre = self._find_deps_preload()
        if _pre:
            defs.append('-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="{}"'.format(_pre))
        # 预置上游两个 find 模块的缓存变量（直接指向依赖真实产物，绕开交叉 FIND_ROOT_PATH）
        if xml_inc:
            defs += ["-DLIBXML2_INCLUDE_DIR={}".format(xml_inc),
                     "-DLIBXML2_INCLUDE_DIRS={}".format(xml_inc)]
        if xml_lib:
            defs += ["-DLIBXML2_LIBRARY={}".format(xml_lib),
                     "-DLIBXML2_LIBRARIES={}".format(xml_lib)]
        if zip_inc:
            defs.append("-DLIBZIP_INCLUDE_DIR={}".format(zip_inc))
        if zip_lib:
            defs.append("-DLIBZIP_LIBRARY={}".format(zip_lib))

        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """鸿蒙 XPM 要求 dlopen 的 .so 与 exec 的可执行文件都要代码签名（同 libzip 实证）。"""
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            # `.codesign` 段可能本来就不存在：无该段时 remove-section 报错属预期，
            # 这里刻意容忍失败（真正的成功判据是下面 sign 的退出码）。
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["epub"]
        # 本包装了可执行文件 bin/einfo（+ bin/lit2epub 脚本）⇒ 按 R38 显式声明 bindirs，
        # 与软件级 commands.json 成对（PF8 的 is_cli 判据即 package_type/bindirs 二选一）。
        # package_type 必须保持 "library"：这是「库 + CLI」混合包，若写 "application"，
        # Conan 2.29.1 不再向消费者暴露 cpp_info（下游拿不到 include/libs）——
        # 纯可执行、无人 include/链接的包才用 application。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "ebook-tools")
        self.cpp_info.set_property("cmake_target_name", "ebook-tools::ebook-tools")
