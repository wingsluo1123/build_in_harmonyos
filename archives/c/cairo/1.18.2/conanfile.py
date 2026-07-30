#!/usr/bin/env python3
"""Conan recipe — cairo 1.18.2 (meson)

OHOS PC (aarch64-ohos) 适配要点:
- 使用裸 meson + ninja（绕开 conan MesonToolchain 的 OHOS 兼容问题）
- -DHAVE_CTIME_R 跳过 cairo static ctime_r（与 OHOS sysroot time.h 冲突）
- 系统依赖来自 cmd-pkgs（pixman/fontconfig/freetype/glib/libpng）
- .so 需用 binary-sign-tool 签名（OHOS 强制 dlopen 签名校验）
- --native-file 指定编译器路径（绕过 conan conanbuild.sh 覆盖 PATH）
- -Dwrap_mode=nofallback 禁止 meson 下载 subproject（避免 git 挂死）
- export CC/CXX/PATH 内联在 meson 命令前（绕过 conan 环境覆盖）
"""
import os
import glob
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# ─── OHOS 环境路径（可通过环境变量覆盖，适配不同设备/SDK 版本）───
HNP = os.environ.get("OHOS_HNP", "/data/service/hnp")
HOME = os.environ.get("OHOS_USER_HOME", "/storage/Users/currentUser")
SDK_VER = os.environ.get("OHOS_SDK_VERSION", "26.0.0.18")
SDK_LIB = f"{HNP}/ohos-sdk.org/ohos-sdk_{SDK_VER}/ohos/native/llvm/lib"
SYS_LIB = f"{HOME}/usr/local/lib"
CLANG = f"{HNP}/bin/clang"
CLANGXX = f"{HNP}/bin/clang++"
MESON_BIN = f"{HOME}/usr/local/bin/meson"
NINJA_BIN = f"{HNP}/bin/ninja"
SIGN_TOOL = f"{HNP}/bin/binary-sign-tool"
READELF = f"{HNP}/bin/llvm-readelf"


class CairoConan(ConanFile):
    name = "cairo"
    version = "1.18.2"
    description = "2D graphics library with multiple output backends"
    license = "LGPL/MPL"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        native_file = os.path.join(self.build_folder, "ohos-native.ini")
        with open(native_file, "w") as f:
            f.write(f"[binaries]\nc = '{CLANG}'\ncpp = '{CLANGXX}'\n")
        self._native_file = native_file

    def _env_prefix(self):
        return (
            f'export CC="{CLANG}" CXX="{CLANGXX}" '
            f'PATH="{HNP}/bin:{HOME}/usr/local/bin:/usr/local/bin:$PATH" '
            f'PKG_CONFIG_PATH="{SYS_LIB}/pkgconfig" '
            f'LD_LIBRARY_PATH="{SDK_LIB}:{SYS_LIB}:{HNP}/lib" '
            f'GIT_TERMINAL_PROMPT=0 GIT_CEILING_DIRECTORIES="{HOME}" && '
        )

    def build(self):
        apply_conandata_patches(self)
        build_dir = os.path.join(self.build_folder, "build-ohos")
        ep = self._env_prefix()
        self.run(
            ep +
            f'"{MESON_BIN}" setup "{build_dir}" "{self.source_folder}" '
            f'--prefix=/ --default-library=shared '
            f'-Dbuildtype=release '
            f'--native-file="{self._native_file}" '
            f'-Dc_args="-I{HOME}/usr/local/include -I/usr/local/include -DHAVE_CTIME_R" '
            f'-Dtests=disabled -Dxlib=disabled -Dxcb=disabled '
            f'-Dfontconfig=enabled -Dwrap_mode=nofallback'
        )
        self.run(ep + f'"{NINJA_BIN}" -C "{build_dir}" -j4')

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        ep = self._env_prefix()
        self.run(ep + f'DESTDIR="{self.package_folder}" "{NINJA_BIN}" -C "{build_dir}" install')
        self._sign_shared_libs()
        self._create_soname_symlinks()

    def _sign_shared_libs(self):
        """签名 .so 文件（OHOS 强制 dlopen 签名校验）"""
        readelf = READELF
        if not os.path.isfile(readelf):
            readelf = f"{SDK_LIB}/../bin/llvm-readelf"
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for so in glob.glob(os.path.join(lib_dir, "*.so*")):
            if os.path.islink(so):
                continue
            if os.path.isfile(readelf):
                r = subprocess.run([readelf, "-S", so], capture_output=True, text=True)
                if ".codesign" in r.stdout:
                    self.output.info(f"Already signed: {os.path.basename(so)}")
                    continue
            if os.path.isfile(SIGN_TOOL):
                try:
                    self.run(f'{SIGN_TOOL} sign -mode localSign -selfSign 1 '
                             f'-inFile "{so}" -outFile "{so}.signed" && mv "{so}.signed" "{so}"')
                    self.output.info(f"Signed: {os.path.basename(so)}")
                except Exception as e:
                    raise ConanException(f"Sign failed for {os.path.basename(so)}: {type(e).__name__}: {e}")
            else:
                raise ConanException(f"binary-sign-tool not found at {SIGN_TOOL}, cannot sign {os.path.basename(so)} (OHOS requires .so signing)")

    def _create_soname_symlinks(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for f in os.listdir(lib_dir):
            if ".so." in f and not f.endswith(".so"):
                parts = f.rsplit(".so.", 1)
                if len(parts) == 2:
                    base = parts[0]
                    major = parts[1].split(".")[0]
                    soname = f"{base}.so.{major}"
                    full_path = os.path.join(lib_dir, f)
                    soname_path = os.path.join(lib_dir, soname)
                    if not os.path.exists(soname_path):
                        os.symlink(f, soname_path)
                    dev_path = os.path.join(lib_dir, f"{base}.so")
                    if not os.path.exists(dev_path):
                        os.symlink(f, dev_path)

    def package_info(self):
        self.cpp_info.libs = ["cairo"]
        self.cpp_info.includedirs = ["include/cairo"]
        self.cpp_info.set_property("cmake_file_name", "cairo")
        self.cpp_info.set_property("cmake_target_name", "cairo::cairo")
        self.cpp_info.set_property("pkg_config_name", "cairo")
        self.runenv_info.define("LD_LIBRARY_PATH", f"{SYS_LIB}:{HNP}/lib")
