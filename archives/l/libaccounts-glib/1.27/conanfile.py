#!/usr/bin/env python3
"""Conan recipe — libaccounts-glib 1.27 (Meson)"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class LibaccountsGlibConan(ConanFile):
    name = "libaccounts-glib"
    version = "1.27"
    description = "GLib-based library for the online accounts framework"
    license = "LGPL-2.1"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # ninja 从 ohpcd 制品仓以 tool 形式提供（本机/CI 无系统 ninja）
        self.tool_requires("ninja-build/1.13.2")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # libaccounts-glib 的 meson_options.txt 仅含 install-py-overrides/
        # py-overrides-dir，无 documentation/tests/introspection 选项；
        # docs/gir/pygobject/tools/tests 的禁用均由补丁处理。
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            tc.ar = ar_path
        strip_path = shutil.which("llvm-strip") or shutil.which("strip")
        if strip_path:
            tc.strip = strip_path

        # 依赖 pkg-config 路径（glib/libxml2/sqlite3 的 .pc）
        for dep_name in ("glib", "libxml2", "sqlite3"):
            dep = self.dependencies[dep_name]
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                tc.pkg_config_path = tc.pkg_config_path + ":" + pc_dir

        tc.generate()

        pc = PkgConfigDeps(self)
        pc.generate()
        # gnome.genmarshal() 需从 glib-2.0.pc 读 glib_genmarshal 变量，
        # conan 生成的 .pc 缺工具变量 → 补上（同 libsignon-glib 配方做法）。
        # OHOS HMDFS 对已存在文件 chmod 不生效，故先把 glib 工具复制为
        # build 目录新文件并置 0o755，.pc 变量指向复制品。
        tool_map = self._install_glib_tools()
        self._patch_pc_files(tool_map)

    def _install_glib_tools(self):
        """复制 glib 包内工具到 build 目录新文件并置执行位（绕开 HMDFS chmod 限制）。"""
        glib_root = self.dependencies["glib"].package_folder
        tool_map = {}
        if not glib_root:
            return tool_map
        tools_dir = os.path.join(self.build_folder, "conan_tools")
        os.makedirs(tools_dir, exist_ok=True)
        for tool in ("glib-genmarshal", "glib-mkenums", "gdbus-codegen"):
            src = os.path.join(glib_root, "bin", tool)
            if not os.path.isfile(src):
                self.output.info(f"glib tool not found: {src}")
                continue
            dst = os.path.join(tools_dir, tool)
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            tool_map[tool] = dst
        return tool_map

    def _patch_pc_files(self, tool_map=None):
        """Add missing glib tool variables to conan-generated pkg-config files."""
        tool_map = tool_map or {}
        glib_info = self.dependencies["glib"]
        glib_root = glib_info.package_folder
        if not glib_root:
            return

        bindir = os.path.join(glib_root, "bin")
        gen_folder = self.generators_folder

        def _tool_path(name):
            return tool_map.get(name, os.path.join(bindir, name))

        pc_patches = {
            "gio-2.0.pc": {"gdbus_codegen": _tool_path("gdbus-codegen")},
            "glib-2.0.pc": {
                "glib_mkenums": _tool_path("glib-mkenums"),
                "glib_genmarshal": _tool_path("glib-genmarshal"),
            },
        }

        for pc_file, variables in pc_patches.items():
            pc_path = os.path.join(gen_folder, pc_file)
            if not os.path.exists(pc_path):
                self.output.info(f"PkgConfigDeps file not found: {pc_path}")
                continue
            with open(pc_path, "r") as f:
                content = f.read()
            additions = []
            for var_name, var_value in variables.items():
                if var_name + "=" not in content:
                    additions.append(f"{var_name}={var_value}")
            if additions:
                addition_text = "\n".join(additions) + "\n"
                if "Name:" in content:
                    content = content.replace("Name:", addition_text + "Name:", 1)
                else:
                    content = addition_text + content
                with open(pc_path, "w") as f:
                    f.write(content)
                self.output.info(f"Patched {pc_file} with: {', '.join(additions)}")

    def build(self):
        apply_conandata_patches(self)
        # OHOS HMDFS 对文件 chmod 不生效（复制新文件置 0o755 仍 Permission denied），
        # 而 glib-genmarshal 是 Python 脚本：用 python3 解释器直接执行（无需执行位），
        # 预生成 ag-marshal.h/c，由 0005 补丁让 meson 跳过 gnome.genmarshal()。
        self._pregen_marshal()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _pregen_marshal(self):
        """用 python3 执行 glib-genmarshal 脚本，预生成 ag-marshal.h / ag-marshal.c。"""
        glib_root = self.dependencies["glib"].package_folder
        if not glib_root:
            return
        gm = os.path.join(glib_root, "bin", "glib-genmarshal")
        marshal_dir = os.path.join(self.source_folder, "libaccounts-glib")
        marshal_list = os.path.join(marshal_dir, "ag-marshal.list")
        if not os.path.isfile(gm) or not os.path.isfile(marshal_list):
            self.output.warning(f"glib-genmarshal or ag-marshal.list not found; skip pregen "
                                f"(gm={gm}, list={marshal_list})")
            return
        for kind, out_name in (("--header", "ag-marshal.h"), ("--body", "ag-marshal.c")):
            out = os.path.join(marshal_dir, out_name)
            self.run(
                f'python3 "{gm}" {kind} --prefix ag_marshal '
                f'--output "{out}" "{marshal_list}"'
            )

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["accounts-glib"]
        self.cpp_info.set_property("pkg_config_name", "libaccounts-glib")
