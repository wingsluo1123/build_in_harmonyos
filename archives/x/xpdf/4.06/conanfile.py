#!/usr/bin/env python3
"""Conan recipe — xpdf 4.06 (CMake)

xpdf ships a set of PDF command-line tools (pdftotext / pdfinfo / pdffonts / pdfimages /
pdfdetach / pdftops / pdftoppm / pdftopng / pdftohtml) plus the optional Qt GUI `xpdf`.
Only the CLI tools are the delivery surface here: the GUI needs a Qt QPA platform plugin
that does not exist on OHOS, so the recipe deliberately keeps it out (see notes.md).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class XpdfConan(ConanFile):
    name = "xpdf"
    version = "4.06"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # CI rewrites conandata `url` into a [mirror, official] list, so normalise first;
        # calling .startswith() on a list raises AttributeError on CI while staying green
        # locally (conan_data["sources"] entries may be a str or a list).
        candidates = list(self.conan_data["sources"]["xpdf-4.06.tar.gz"]["url"]) \
            if isinstance(self.conan_data["sources"]["xpdf-4.06.tar.gz"]["url"], list) \
            else [self.conan_data["sources"]["xpdf-4.06.tar.gz"]["url"]]
        get(self, filename="xpdf-4.06.tar.gz", url=candidates[0],
            sha256=self.conan_data["sources"]["xpdf-4.06.tar.gz"]["sha256"],
            strip_root=True)

    def requirements(self):
        # CLI tools only need the PDF core + font handling; the graphics tools that need
        # rasterisation pull in splash/freetype, the rest link only goo+fofi.
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        # fontconfig/2.18.1 的已发布 libfontconfig.so.1 记录了**绝对路径** DT_NEEDED
        # （readelf -d: NEEDED /…/.conan2/p/expat…/lib/libexpat.so），因 expat/2.8.2 的 .so
        # 无 SONAME，链接器写入被链库绝对路径。OHOS/musl 加载器对含 '/' 的 NEEDED 按字面
        # 路径解析，LD_LIBRARY_PATH 无法覆盖；CI worker 活跃 conan home 是 ~/.cache/conan2，
        # 该绝对路径处只剩一份陈旧 expat → 加载期 XML_* symbol not found，消费者 CLI 全挂。
        # 2.18.1.1 改用 expat/2.8.2.1 重新链接，得到可重定位 NEEDED（记 libexpat.so.1）。
        # 详见 archives/f/fontconfig/2.18.1.1/notes.md。
        self.requires("fontconfig/2.18.1.1")
        self.requires("lcms2/2.19")
        self.requires("libtiff/4.7.2")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # conan maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, but cmake ships
            # Modules/Platform/OHOS.cmake (not HarmonyOS.cmake). The name mismatch is NOT
            # fatal: cmake just prints "System is unknown to cmake" and continues with a
            # batch of platform variables empty — including
            # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG, so link lines get no -Wl,-soname, and
            # CMAKE_SYSTEM_PROCESSOR stays "unknown", which mis-selects SIMD/asm branches.
            # Guarded on os: forcing it unconditionally would break os=Linux profiles
            # (cmake would load Platform/OHOS.cmake instead of Linux.cmake and pin
            # CMAKE_SYSTEM_PROCESSOR=aarch64) — opencascade 7.9.3 MR review hit exactly this.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # Upstream hardcodes `set(CMAKE_CXX_STANDARD 11)` in cmake-config.txt and the
        # OHOS profile is cppstd=17; declaring 11 explicitly keeps the build on the level
        # upstream actually tests instead of silently inheriting the profile value.
        tc.variables["CMAKE_CXX_STANDARD"] = "11"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "OFF"
        # The GUI is out of scope (no QPA platform plugin on OHOS). qt5 stays a plain
        # require-less nothing here: no find_package(Qt*) is satisfied, so upstream's
        # `xpdf-qt` guard is false and no GUI target is added.
        tc.variables["XPDFWIDGET_PRINTING"] = "OFF"
        tc.variables["NO_FONTCONFIG"] = "OFF"
        # 64-bit installs would land in lib64 while conan's cpp_info/test_package look in lib.
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # Upstream's own Find* logic uses bare library names (-lfreetype, -lfontconfig),
        # so cmake needs explicit search dirs; without -L it fails with
        # "unable to find library". Only search paths here — appending -l would break the
        # upstream link separation (hwloc precedent). poppler 25.12.0.2 hit the same thing.
        _ldirs = []
        for _ref, _dep in self.dependencies.items():
            for _p in _dep.cpp_info.libdirs:
                _ldirs.append("-L" + _p)
        _ldflags = " ".join(dict.fromkeys(_ldirs))
        for _k in ("CMAKE_EXE_LINKER_FLAGS", "CMAKE_SHARED_LINKER_FLAGS",
                   "CMAKE_MODULE_LINKER_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _ldflags).strip()

        # Include dirs only (never -l): upstream mixes plain #include <ft2build.h> and
        # <freetype/freetype.h> styles, and freetype needs both include roots.
        _incs = []
        for _ref, _dep in self.dependencies.items():
            for _p in _dep.cpp_info.includedirs:
                _incs.append("-I" + _p)
        _incflags = " ".join(dict.fromkeys(_incs))
        for _k in ("CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _incflags).strip()

        tc.generate()
        CMakeDeps(self).generate()
        # CMakeToolchain (unlike AutotoolsToolchain) does not set PKG_CONFIG_PATH, and
        # several upstream Find*.cmake modules go through pkg_check_modules, so the .pc
        # files would be generated but never found.
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # Code signing is OHOS-specific: both tools live in the device's
        # /data/service/hnp/bin. On other profiles they simply do not exist, and the
        # self.run() would abort the whole conan create in package(). Guarded inside the
        # method so every build-system template that calls it inherits the guard.
        if self.settings.os != "OHOS":
            return
        # OHOS PC XPM requires anything exec'd or dlopen'd to be signed, else
        # Permission denied. The signature is a content hash (stored in a .codesign
        # section), so it is invalidated by any later byte edit — strip/objcopy/patchelf
        # and in-place RUNPATH edits all break it. Copying does NOT break it (verified
        # 2026-08-04 on real hardware).
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "bin", "*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # CLI tool package: the executables are the product, and test_package/PF3/R38
        # all key off bindirs being non-empty.
        self.cpp_info.bindirs = ["bin"]
