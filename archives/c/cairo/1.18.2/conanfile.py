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
        hnp = "/data/service/hnp"
        with open(native_file, "w") as f:
            f.write(f"[binaries]\nc = '{hnp}/bin/clang'\ncpp = '{hnp}/bin/clang++'\n")
        self._native_file = native_file

    def _env_prefix(self):
        hnp = "/data/service/hnp"
        home = "/storage/Users/currentUser"
        sdk_lib = f"{hnp}/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        return (
            f'export CC="{hnp}/bin/clang" CXX="{hnp}/bin/clang++" '
            f'PATH="{hnp}/bin:{home}/usr/local/bin:/usr/local/bin:$PATH" '
            f'PKG_CONFIG_PATH="{home}/usr/local/lib/pkgconfig" '
            f'LD_LIBRARY_PATH="{sdk_lib}:{home}/usr/local/lib:{hnp}/lib" '
            f'GIT_TERMINAL_PROMPT=0 GIT_CEILING_DIRECTORIES="{home}" && '
        )

    def build(self):
        apply_conandata_patches(self)
        build_dir = os.path.join(self.build_folder, "build-ohos")
        meson_bin = "/storage/Users/currentUser/usr/local/bin/meson"
        ninja_bin = "/data/service/hnp/bin/ninja"
        home = "/storage/Users/currentUser"
        ep = self._env_prefix()
        self.run(
            ep +
            '"%s" setup "%s" "%s" --prefix=/ --default-library=shared '
            '-Dbuildtype=release '
            '--native-file="%s" '
            '-Dc_args="-I%s/usr/local/include -I/usr/local/include -DHAVE_CTIME_R" '
            '-Dtests=disabled -Dxlib=disabled -Dxcb=disabled '
            '-Dfontconfig=enabled -Dwrap_mode=nofallback' % (meson_bin, build_dir, self.source_folder, self._native_file, home)
        )
        self.run(ep + '"%s" -C "%s" -j4' % (ninja_bin, build_dir))

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        ninja_bin = "/data/service/hnp/bin/ninja"
        ep = self._env_prefix()
        self.run(ep + 'DESTDIR="%s" "%s" -C "%s" install' % (self.package_folder, ninja_bin, build_dir))
        self._sign_shared_libs()
        self._create_soname_symlinks()

    def _sign_shared_libs(self):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            readelf = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-readelf"
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
            if os.path.isfile(sign_tool):
                try:
                    self.run('%s sign -mode localSign -selfSign 1 -inFile "%s" -outFile "%s.signed" && mv "%s.signed" "%s"' % (
                        sign_tool, so, so, so, so))
                    self.output.info(f"Signed: {os.path.basename(so)}")
                except Exception as e:
                    raise ConanException(f"Sign failed for {os.path.basename(so)}: {type(e).__name__}: {e}")
            else:
                raise ConanException(f"binary-sign-tool not found at {sign_tool}, cannot sign {os.path.basename(so)} (OHOS requires .so signing)")

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
        self.runenv_info.define("LD_LIBRARY_PATH", "/storage/Users/currentUser/usr/local/lib:/data/service/hnp/lib")
