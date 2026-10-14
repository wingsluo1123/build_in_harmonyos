#!/usr/bin/env python3
"""Conan recipe — scribus 1.6.6 (Scribus desktop publishing, Qt5 + CMake).

Scribus is a Qt5 GUI application (desktop publishing / page layout) built
with CMake.  This recipe builds the full application for HarmonyOS PC.

Key adaptations:
- Qt5LinguistTools is not shipped by the published qt5-qtbase variants (it
  belongs to the qttools module), so the upstream REQUIRED find_package is
  downgraded to QUIET (patch 0002) and the translations subdirectory is
  skipped (patch 0001) — translations are loaded at runtime from .qm files,
  the GUI falls back to English strings.
- Qt5OpenGL: the qt5-qtbase package actually ships libQt5OpenGL.so and the
  native Qt5OpenGL cmake config under its lib/cmake/, but the conan component
  list omits Qt5OpenGL.  QT_PREFIX is pointed at the qtbase package folder so
  CMake discovers the relocatable Qt5Config.cmake and the Qt5OpenGL module
  config directly (same approach as the qastools E438 precedent).
- CMAKE_PREFIX_PATH is appended (not overwritten) by the upstream
  CMakeLists_Dependencies.cmake so conan-generated package configs stay
  discoverable (patch 0002).
- PoDoFo / OSG / GraphicsMagick have no published conan packages on OHOS;
  the upstream find logic degrades gracefully (all optional).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class ScribusConan(ConanFile):
    name = "scribus"
    version = "1.6.6"
    description = "Scribus — Qt5 desktop publishing (page layout) application"
    license = "GPL-2.0-or-later"
    homepage = "https://www.scribus.net"
    url = "https://sourceforge.net/projects/scribus/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5 modules (Core/Widgets/Gui/Xml/Network/OpenGL/PrintSupport)
        self.requires("qt5-qtbase/5.15.2.2")
        # PDF import (hard requirement)
        self.requires("poppler/25.12.0")
        # Image / font / colour / XML / text-shaping libraries
        # zlib: poppler/cairo/libpng/libtiff 制品仓二进制均基于 zlib/1.3.1.1
        # 构建（如 libpng/1.6.58、poppler/25.12.0 的 requires 精确 pin 1.3.1.1），
        # override 到 1.3.1 会连锁触发这些 autotools 包在 OHOS 上从源码重建，
        # 而它们基于旧 config.guess 无法识别 HarmonyOS（实测 libpng 构建失败）。
        # qt5-qtbase 制品仓二进制基于 zlib/1.3.1，但 Qt 的 configure 不走
        # config.guess，重建成本可接受（已设 14400s 超时）。故统一 override
        # 到 1.3.1.1，qt5-qtbase 走 rebuild，其余包全部复用制品仓。
        self.requires("zlib/1.3.1.1", override=True)  # aligned with poppler/cairo/libpng chain
        self.requires("libjpeg-turbo/3.2.0")   # provides jpeglib.h + libjpeg
        self.requires("libpng/1.6.58")         # aligned with poppler chain
        self.requires("libtiff/4.7.2")         # aligned with poppler chain
        self.requires("freetype/2.14.3")
        # fontconfig: cairo 链 pin 到 2.18.1.1（2.18.1 的 libfontconfig.so 的
        # DT_NEEDED 烤着构建机 cache 绝对路径，换机器加载失败；2.18.1.1 为
        # 干净重建），统一 override 保持一致。
        self.requires("fontconfig/2.18.1.1", override=True)
        # expat: fontconfig/2.18.1.1 链 pin expat/2.8.2.1（该版 .so 有 SONAME），
        # qt5-qtbase(dbus) 链声明 2.8.2（.so 无 SONAME 会污染 DT_NEEDED），
        # 统一 override 到 2.8.2.1（baka 配方同款先例）。
        self.requires("expat/2.8.2.1", override=True)
        # openssl: python 链 pin 1.1.1w（精确），cups 链 pin 3.5.6（精确），
        # 统一 override 到 1.1.1w —— python 是重依赖（重建成本高）且
        # cups 2.4.19 的 --with-tls=openssl 兼容 1.1.1 系列。
        self.requires("openssl/1.1.1w", override=True)
        self.requires("cairo/1.18.4")
        self.requires("lcms2/2.19")
        self.requires("libxml2/2.15.3")
        self.requires("cups/2.4.19")
        self.requires("harfbuzz/14.2.0")
        self.requires("icu/76.1")
        self.requires("python/3.12.9")
        # Optional features enabled by default upstream (hunspell / boost)
        self.requires("hunspell/1.7.3")
        self.requires("boost/1.90.0.3")
        self.requires("librevenge/0.0.5")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        # Scribus resolves poppler/cairo/harfbuzz/icu/hunspell/librevenge via
        # pkg-config (custom Find*.cmake modules use pkg_search_module /
        # pkg_check_modules), so .pc files must be on PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # E092: CMake does not know HarmonyOS; OHOS is Linux-kernel based, so
        # let CMake use its Linux platform module (compilers still come from
        # the conan toolchain pointing at the OHOS clang).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Dependency resolution: exclude $HOME/usr/local from find_* searches.
        # The environment carries stale cmake configs there (e.g. an obsolete
        # tiff-config.cmake referencing /usr/local/lib/libtiff.so.6.3.0 which
        # does not exist); without this, find_package(TIFF) binds to the stale
        # config instead of the conan libtiff package (JPEG/PNG fall through to
        # conan because they have no stale config there).  All real deps come
        # from conan packages, whose folders are on CMAKE_PREFIX_PATH already.
        tc.cache_variables["CMAKE_IGNORE_PREFIX_PATH"] = os.path.expanduser("~/usr/local")
        # Optional features without a published OHOS conan package:
        #  * PoDoFo (WITH_PODOFO): upstream find_package uses pkg_search_module
        #    REQUIRED and aborts configure when the package is absent; there is
        #    no podofo recipe in the registry.  Disable it — the only loss is
        #    importing PDF data embedded inside Adobe Illustrator files.
        tc.variables["WITH_PODOFO"] = "OFF"
        # cmake 4.x removed compatibility with policies < 3.5; upstream
        # requires cmake_minimum_required 3.14.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Qt5OpenGL: the published qt5-qtbase conan component list omits
        # Qt5OpenGL, but the package ships the native relocatable Qt5 cmake
        # configs. Point QT_PREFIX at the qtbase package folder; upstream
        # CMakeLists_Dependencies.cmake appends it to CMAKE_PREFIX_PATH.
        qt5_pkg = self.dependencies["qt5-qtbase"].package_folder
        tc.variables["QT_PREFIX"] = qt5_pkg
        # Upstream unit tests: scribus/tests registers cellareatests via
        # add_test() under if(WITH_TESTS). Upstream enable_testing() is
        # commented out (no ctest registration), so we run the test binary
        # directly in build() below. Qt5Test ships inside the qt5-qtbase
        # package, but conan CMakeDeps does not set the upstream
        # ${QT_QTTEST_LIBRARY}/${QT_LIBRARIES} variables — inject them so
        # cellareatests links against the real libQt5Test.so.
        tc.variables["WITH_TESTS"] = "ON"
        tc.cache_variables["QT_QTTEST_LIBRARY"] = os.path.join(qt5_pkg, "lib", "libQt5Test.so")
        tc.cache_variables["QT_LIBRARIES"] = ";".join(
            os.path.join(qt5_pkg, "lib", "libQt5{}.so".format(m))
            for m in ("Core", "Widgets", "Gui", "Xml", "Network", "OpenGL", "PrintSupport")
        )
        # Python3: conan python package does not register a cmake file name
        # matching FindPython3, so pass the interpreter / include / library
        # paths explicitly.
        py_pkg = self.dependencies["python"].package_folder
        tc.variables["Python3_EXECUTABLE"] = os.path.join(py_pkg, "bin", "python3.12")
        tc.variables["Python3_INCLUDE_DIR"] = os.path.join(py_pkg, "include", "python3.12")
        tc.variables["Python3_LIBRARY"] = os.path.join(py_pkg, "lib", "libpython3.12.so")
        # Upstream relies on system-default include paths for boost and ICU
        # headers; in the conan world those live in package-private prefixes.
        # Expose the include dirs via the variable names the top-level
        # CMakeLists.txt include_directories() block references (added by
        # patch 0001), so subdirectory targets (lib2geom, storytext, …) can
        # find boost/optional/optional.hpp and <unicode/…>.
        boost_pkg = self.dependencies["boost"].package_folder
        tc.cache_variables["Boost_INCLUDE_DIRS"] = os.path.join(boost_pkg, "include")
        icu_pkg = self.dependencies["icu"].package_folder
        tc.cache_variables["ICU_INCLUDE_DIRS"] = os.path.join(icu_pkg, "include")
        # fontconfig: cairo-ft.h includes <fontconfig/fontconfig.h>, and the
        # top-level include_directories() block references FONTCONFIG_INCLUDE_DIR
        # (re-enabled by patch 0001); point it at the conan package.
        fc_pkg = self.dependencies["fontconfig"].package_folder
        tc.cache_variables["FONTCONFIG_INCLUDE_DIR"] = os.path.join(fc_pkg, "include")
        # harfbuzz: scfonts.cpp includes <harfbuzz/hb.h> directly; expose the
        # conan include dir through the global include_directories() block.
        hb_pkg = self.dependencies["harfbuzz"].package_folder
        tc.cache_variables["HARFBUZZ_INCLUDE_DIRS"] = os.path.join(hb_pkg, "include")
        # lcms2: paletteloader_cxf.cpp / about.cpp include <lcms2.h>; the
        # top-level include_directories() block references LCMS2_INCLUDE_DIR.
        lcms_pkg = self.dependencies["lcms2"].package_folder
        tc.cache_variables["LCMS2_INCLUDE_DIR"] = os.path.join(lcms_pkg, "include")
        # poppler: about.cpp includes <poppler/cpp/poppler-version.h> under
        # HAVE_POPPLER; expose the conan include dir globally.
        pop_pkg = self.dependencies["poppler"].package_folder
        # poppler-config.h lives under include/poppler (poppler internal
        # headers include it by name), so add both the include root and the
        # poppler subdir to the global include path.
        pop_inc = os.path.join(pop_pkg, "include")
        # CMake list separator is ";" (not os.pathsep ":"), so both paths
        # stay valid entries of the POPPLER_INCLUDE_DIRS list.
        tc.cache_variables["POPPLER_INCLUDE_DIRS"] = pop_inc + ";" + os.path.join(pop_inc, "poppler")
        # Link libraries: Scribus links ${LCMS2_LIBRARIES} (its own
        # FindLCMS2.cmake only searches /usr/lib, /usr/local/lib — not the
        # conan prefix) and a `Fontconfig::Fontconfig` target (conan CMakeDeps
        # exports lowercase `fontconfig::fontconfig`). Inject both so the
        # Fc*/cms* symbols resolve.
        lcms_pkg2 = self.dependencies["lcms2"].package_folder
        tc.cache_variables["LCMS2_LIBRARIES"] = os.path.join(lcms_pkg2, "lib", "liblcms2.so")
        fc_pkg2 = self.dependencies["fontconfig"].package_folder
        tc.cache_variables["FONTCONFIG_LIBRARIES"] = os.path.join(fc_pkg2, "lib", "libfontconfig.so")
        # Optional dependencies without published OHOS conan packages are
        # kept at their upstream defaults; the find logic degrades gracefully.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # python3.12 解释器运行时需要其包内 libpython3.12.so.1.0，否则
        # CMake 的 find_package(Python3) 报 "Cannot run the interpreter
        # .../python3.12"（CI 干净环境无外层 LD_LIBRARY_PATH，须在配方内
        # 注入，configure/build/test 全程保证 python 可执行）。
        _env = Environment()
        _py_pkg = self.dependencies["python"].package_folder
        _env.prepend_path("LD_LIBRARY_PATH", os.path.join(_py_pkg, "lib"))
        with _env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            # Limit parallelism (-j4) to avoid OOM on the big Qt upload: full
            # builds under -j20 have been observed to die mid-compile with no
            # error marker (baka recipe uses -j2 for the same reason).
            cmake.build(cli_args=["--parallel", "4"])
            # Upstream unit test: cellareatests (QTest-based, registered via
            # add_test in scribus/tests under WITH_TESTS=ON). Upstream
            # enable_testing() is commented out, so ctest does not register it;
            # run the test binary directly. It needs Qt5Test + the SDK c++ dir
            # (libc++_shared.so) at runtime (same root cause as binary-sign-tool).
            tests_bin = os.path.join(self.build_folder, "scribus", "tests", "cellareatests")
            if os.path.isfile(tests_bin):
                _llvm_lib = ""
                for _d in sorted(__import__("glob").glob(
                        "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos/c++")):
                    _llvm_lib = _d
                if _llvm_lib:
                    _env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
                _qt5_pkg = self.dependencies["qt5-qtbase"].package_folder
                _env.prepend_path("LD_LIBRARY_PATH", os.path.join(_qt5_pkg, "lib"))
                # libtiff 制品链接了 libwebp/libzstd（WebP/ZSTD 符号），scribus --tests
                # 运行时须能解析。二者是 libtiff 的传递依赖，位于依赖图内，通过
                # self.dependencies 取 package_folder 注入（标准 conan 2 API，
                # 本地与 CI 通用；此前 glob 扫描 cache 目录在 CI 上不可靠）。
                for _dep in ("libwebp", "zstd"):
                    if _dep in self.dependencies:
                        _dep_folder = self.dependencies[_dep].package_folder
                        if _dep_folder:
                            _env.prepend_path("LD_LIBRARY_PATH",
                                              os.path.join(_dep_folder, "lib"))
                        else:
                            self.output.warning("runtime dep %s has empty package_folder" % _dep)
                    else:
                        self.output.warning("runtime dep %s not in dependency graph" % _dep)
                with _env.vars(self).apply():
                    self.run('QT_QPA_PLATFORM=offscreen "%s"' % tests_bin)
                # Upstream TestStoryText: 主程序 --tests 入口（WITH_TESTS=1 编译生效）
                # 经 RunTests::runTests 聚合运行 9 个 TestStoryText 测试函数。
                scribus_bin = os.path.join(self.build_folder, "scribus", "scribus")
                if os.path.isfile(scribus_bin):
                    with _env.vars(self).apply():
                        self.run('QT_QPA_PLATFORM=offscreen "%s" --tests' % scribus_bin)
                else:
                    self.output.warning("scribus bin not built; skipping TestStoryText via --tests")
            else:
                self.output.warning("cellareatests not built; skipping upstream unit test")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # E077: OHOS 内核只允许加载带有效 .codesign 签名的 ELF；用户存储路径的
        # 未签名 ELF 在执行时被拒（execve EPERM，rc=126）。scribus GUI 二进制在
        # 打包期自签，使 test_package 的真实 exec 探针与后续安装运行均可用
        # （qastools/cronutils 先例；签名输出会丢执行位，须恢复 0o755）。
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in ("scribus",):
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._sign_ohos_binary(path)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        # E077 runtime: binary-sign-tool (a C++ binary on OHOS) needs
        # libc++_shared.so from the SDK per-arch llvm lib dir; without it
        # the tool aborts with "Error relocating ... symbol not found"
        # (same root cause as genstrings during the cups rebuild).
        _llvm_lib = ""
        for _d in sorted(__import__("glob").glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos/c++")):
            _llvm_lib = _d
        if _llvm_lib and os.path.isdir(_llvm_lib):
            _env = Environment()
            _env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
            with _env.vars(self).apply():
                self._do_sign_ohos(path)
        else:
            self._do_sign_ohos(path)

    def _do_sign_ohos(self, path):

        signer = self.conf.get(
            "user.ohos:sign_tool",
            default="",
            check_type=str,
        )
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get(
            "user.ohos:objcopy",
            default="",
            check_type=str,
        )
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        # binary-sign-tool is a C++ binary needing libc++_shared.so from the
        # SDK per-arch llvm lib dir; prefix LD_LIBRARY_PATH on the command
        # line so the tool can resolve its libc++ symbols (same issue as
        # genstrings during the cups rebuild).
        _llvm_lib2 = ""
        for _d in sorted(__import__("glob").glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos/c++")):
            _llvm_lib2 = _d
        # Use ONLY the SDK c++ dir (no $LD_LIBRARY_PATH suffix): appending
        # the ambient path re-exposes the SDK stub libc++.so that breaks
        # symbol resolution (manual test: c++ dir alone signs OK).
        _ld_pre = f'LD_LIBRARY_PATH="{_llvm_lib2}" ' if _llvm_lib2 else ""
        self.run(
            f'{_ld_pre}"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
