#!/usr/bin/env python3
"""Conan recipe for pqmarble 1.3.0 — Marble Gtk application library.

上游: https://gitlab.gnome.org/raggesilver/marble (tag v1.3.0, commit 710a677a)
Debian 包名 pqmarble；meson project 名为 marble，产物 libmarble.so + marble.h +
marble.vapi + Marble-1.3.0.gir/.typelib，pkg-config 名 marble。

构建系统: Meson（Vala + C，valac 编译为 C，产出 C ABI 共享库）。
OHOS 适配要点：见 notes.md。
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PqmarbleConan(ConanFile):
    name = "pqmarble"
    version = "1.3.0"
    description = "Marble — Gtk application library (SideWindow/Settings/Utils) used by GNOME apps"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.gnome.org/raggesilver/marble"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_tests": [True, False],
        "with_typelib": [True, False],
    }
    default_options = {
        "shared": True,
        "with_tests": True,
        # OHOS 侧 glib 包未安装 GLib-2.0/GObject-2.0 的 GIR（构建时
        # introspection 关闭），g-ir-compiler 无法解析 included gir，
        # 默认不生成 .typelib；.gir/.vapi 仍由 valac 正常产出。
        "with_typelib": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 版本按 gtk/3.24.43 配方实际 pin（glib 2.84.0.1）选定，避免图冲突。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        # Vala 编译器：meson 的 vala 编译器后端直接调用 valac
        self.tool_requires("vala/0.56.19")
        if self.options.with_typelib:
            # g-ir-compiler：仅 .typelib 生成时使用
            self.tool_requires("gobject-introspection/1.78.1")
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # meson 的 dependency('gtk+-3.0'/'gio-2.0') 走 pkg-config，
        # PkgConfigDeps 生成 .pc 并把 generators 目录写进 cross file 的
        # pkg_config_path（MesonToolchain 默认值即 generators_folder）。
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # OHOS worker 的 PATH 不含 llvm-ar/llvm-ranlib，meson 在 project() 阶段
        # 探测 clang 配套静态链接器会直接失败（Unknown linker(s): [['llvm-ar']]）；
        # 从 profile 的 compiler_executables 绝对路径推导同目录工具写进 [binaries]。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if cc and os.path.sep in cc:
            tool_dir = os.path.dirname(cc)
            for key, tool in (("ar", "llvm-ar"), ("ranlib", "llvm-ranlib"), ("strip", "llvm-strip")):
                candidate = os.path.join(tool_dir, tool)
                if os.path.isfile(candidate):
                    tc.binaries[key] = candidate
        # valac 的 vapi 搜索路径编译期被硬编码为打包前前缀，包重定位后
        # `valac -C --profile=posix` 找不到 posix/glib-2.0 等 vapi（meson
        # 的 transpiler sanity check 直接失败）。用 wrapper 显式补 --vapidir。
        vala_pkg = self.dependencies.build["vala"].package_folder
        vapi_dir = self._find_vapi_dir(vala_pkg)
        if not vapi_dir:
            raise ConanException(f"valac 的 vapi 目录未在 {vala_pkg}/share 下找到")
        tools_dir = os.path.join(self.generators_folder, "build-tools")
        os.makedirs(tools_dir, exist_ok=True)
        valac_wrapper = os.path.join(tools_dir, "valac")
        with open(valac_wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n"
                    f'exec "{os.path.join(vala_pkg, "bin", "valac")}" '
                    f'--vapidir="{vapi_dir}" "$@"\n')
        os.chmod(valac_wrapper, 0o755)
        tc.binaries["vala"] = valac_wrapper

        # gnome.compile_resources() 通过 state.find_tool() 取构建期工具：
        # 先查 machine file [binaries]，取不到才退到 pkg-config 变量
        # （PkgConfigDeps 生成的 .pc 不含 glib_compile_resources 变量）。
        # OHOS 上 conan 包内的 ELF 工具未签名 → execve 返回 EPERM
        # （Operation not permitted），必须复制到构建目录后自签名；
        # #! 脚本类工具（glib-mkenums 等）改写成 python 包装脚本。
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        for tool in ("glib-compile-resources", "glib-compile-schemas", "gio-querymodules"):
            src = os.path.join(glib_bin, tool)
            if os.path.isfile(src):
                dst = self._copy_and_sign(src, tools_dir)
                tc.binaries[tool] = dst
        for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen"):
            src = os.path.join(glib_bin, tool)
            if os.path.isfile(src):
                tc.binaries[tool] = self._python_wrapper(tool, src, tools_dir)
        if self.options.with_typelib:
            gi_bin = os.path.join(self.dependencies.build["gobject-introspection"].package_folder, "bin")
            compiler = os.path.join(gi_bin, "g-ir-compiler")
            if os.path.isfile(compiler):
                tc.binaries["g-ir-compiler"] = self._copy_and_sign(compiler, tools_dir)

        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "tests": "true" if self.options.with_tests else "false",
            "introspection_typelib": "true" if self.options.with_typelib else "false",
        })
        tc.generate()

        # valac 内部会自调 pkg-config，只认环境变量 PKG_CONFIG_PATH
        # （meson 自己的 dependency() 走 machine file 的 pkg_config_path）。
        # 把 PkgConfigDeps 生成的 .pc 目录补进构建环境。
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)

    @staticmethod
    def _find_vapi_dir(vala_package_folder):
        share = os.path.join(vala_package_folder, "share")
        candidates = [os.path.join(share, "vala", "vapi")]
        if os.path.isdir(share):
            for name in sorted(os.listdir(share)):
                if name.startswith("vala-"):
                    candidates.append(os.path.join(share, name, "vapi"))
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "glib-2.0.vapi")):
                return candidate
        return ""

    @staticmethod
    def _add_binaries(tc, package_folder, tools):
        if not package_folder:
            return
        bin_dir = os.path.join(package_folder, "bin")
        for tool in tools:
            candidate = os.path.join(bin_dir, tool)
            if os.path.isfile(candidate):
                tc.binaries[tool] = candidate

    def _sign_installed_elfs(self):
        """OHOS 加载器拒绝加载未签名的 ELF 共享库（dlopen 报
        "Error loading shared library"），包内 .so 必须自签名。"""
        if self.settings.os != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(f"binary-sign-tool 缺失，跳过签名: {signer}")
            return
        for pattern in ("lib/**/*.so", "lib/**/*.so.*"):
            for binary in sorted(glob.glob(os.path.join(self.package_folder, pattern),
                                           recursive=True)):
                if os.path.islink(binary) or not os.path.isfile(binary):
                    continue
                self.run(shlex.join([signer, "sign", "-inFile", binary,
                                     "-outFile", binary, "-selfSign", "1"]))

    def _copy_and_sign(self, src, tools_dir):
        """复制 ELF 工具并自签名（OHOS 未签名 ELF execve 返回 EPERM）。"""
        dst = os.path.join(tools_dir, os.path.basename(src))
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o755)
        if self.settings.os == "OHOS":
            signer = "/data/service/hnp/bin/binary-sign-tool"
            if not os.path.isfile(signer):
                raise ConanException(f"OHOS ELF 签名工具缺失: {signer}")
            self.run(shlex.join([signer, "sign", "-inFile", dst, "-outFile", dst, "-selfSign", "1"]))
        return dst

    @staticmethod
    def _python_wrapper(name, script, tools_dir):
        """把 #! 脚本工具包成显式调用 python3 的 shell wrapper。"""
        wrapper = os.path.join(tools_dir, name)
        python = shutil.which("python3") or sys.executable
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\nexec '{}' '{}' \"$@\"\n".format(python, script))
        os.chmod(wrapper, 0o755)
        return wrapper

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # 上游 -Dtests=true 会把交互式测试程序 marble_test 装进 bin/；
        # 该可执行文件只用于上游手工验证（GtkApplication GUI），不属于交付物。
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in os.listdir(bin_dir):
                if name.startswith("marble_test"):
                    os.remove(os.path.join(bin_dir, name))
            if not os.listdir(bin_dir):
                os.rmdir(bin_dir)
        # 上游 __init__.py 只在无 DESTDIR 时才跑 icon-cache/schema 那几条
        # gtk/glib 工具；conan install 时 DESTDIR 已设置，故此处无需处理。
        self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["marble"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "marble")
        self.cpp_info.set_property("cmake_file_name", "marble")
        self.cpp_info.set_property("cmake_target_name", "marble::marble")
        self.cpp_info.requires = ["glib::glib", "gtk::gtk"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
