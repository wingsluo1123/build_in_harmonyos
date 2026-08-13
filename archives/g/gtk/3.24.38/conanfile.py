#!/usr/bin/env python3
"""Conan recipe — GTK+ 3.24.38 for HarmonyOS PC (aarch64-ohos).

- Meson build system (upstream, >= 0.60).
- HarmonyOS 无原生 X11/Wayland，启用 broadway (HTML5) 后端，
  禁用 x11/wayland/quartz/win32 后端与 introspection (参考 cmd-pkgs 预编译包)。
- E090: meson.build 中 `host_machine.system() == 'linux'` 必须同时接受
  'harmonyos'，否则 os_linux 为 false，Linux 平台分支被跳过。
- E077: meson install 会重写 rpath 使 OHOS ELF 自签失效，package() 后必须
  用 llvm-objcopy --remove-section .codesign + binary-sign-tool 重新签名。
- cairo-gobject 内嵌 (vendored)：制品仓 cairo/1.18.4 配方刻意关闭了
  glib 胶水库（-Dglib=disabled，不产 cairo-gobject），而 gtk meson 硬性
  requires `cairo-gobject` 并链接 cairo_*_get_type() 符号。本配方把上游
  cairo-1.18.4/util/cairo-gobject 的三个原文件 + 独立 meson.build 一并
  打进 gtk 包，先编译 cairo-gobject 再配置 gtk（extras/cairo-gobject/）。
- gio-unix-2.0：glib 配方只暴露 gio-2.0 组件，gtk meson 以 required:false
  查找 gio-unix-2.0；generate() 里生成 gio-unix-2.0.pc 别名指向 gio-2.0，
  使 HAVE_GIO_UNIX 生效。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GtkConan(ConanFile):
    name = "gtk"
    version = "3.24.38"
    description = "GTK+ 3 — cross-platform GUI toolkit (broadway backend on HarmonyOS)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org/"
    url = "https://gitlab.gnome.org/GNOME/gtk"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)
        # 内嵌 cairo-gobject 源文件需要显式导出（conan 默认不导出 extras/）
        extras_src = os.path.join(self.recipe_folder, "extras")
        if os.path.isdir(extras_src):
            copy(self, "*", src=extras_src, dst=os.path.join(self.export_sources_folder, "extras"))

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # GTK3 依赖链全部通过 conan 解析（R36：均已在 ohpcd 发布）。
        # broadway 后端不需要 x11/wayland/xkbcommon/pangoft2/harfbuzz。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("atk/2.38.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 内嵌 cairo-gobject：把 extras/cairo-gobject/ 拷入源码树
        dst = os.path.join(self.source_folder, "cairo-gobject")
        for base in (self.export_sources_folder, self.recipe_folder):
            extras = os.path.join(base, "extras", "cairo-gobject")
            if os.path.isdir(extras):
                shutil.copytree(extras, dst)
                break
        else:
            raise ConanException("extras/cairo-gobject not found in exported sources")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_gio_unix_pc()
        self._augment_glib_pkg_config()
        self._augment_fribidi_pc()
        toolchain = MesonToolchain(self)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.project_options["x11_backend"] = False
        toolchain.project_options["wayland_backend"] = False
        toolchain.project_options["broadway_backend"] = True
        toolchain.project_options["win32_backend"] = False
        toolchain.project_options["quartz_backend"] = False
        toolchain.project_options["introspection"] = False
        toolchain.project_options["tests"] = False
        toolchain.project_options["demos"] = False
        toolchain.project_options["examples"] = False
        toolchain.project_options["gtk_doc"] = False
        toolchain.project_options["man"] = False
        toolchain.project_options["installed_tests"] = False
        toolchain.project_options["cloudproviders"] = False
        toolchain.project_options["profiler"] = False
        toolchain.project_options["tracker3"] = False
        toolchain.c_link_args.extend(self._glib_libintl_link_args())
        # cairo 制品包无 cairo-gobject（未启用 glib）；gtk 源码 include
        # cairo-gobject.h 时 cairo-features.h 未定义 CAIRO_HAS_GOBJECT_FUNCTIONS，
        # 会触发 #error。显式定义以模拟 glib 启用的 cairo。
        toolchain.c_args.append("-DCAIRO_HAS_GOBJECT_FUNCTIONS=1")
        toolchain.generate()
        self._inject_meson_binaries()
        self._append_dependency_pkg_config_paths()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_glib_tools()
        self._build_cairo_gobject()
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._install_cairo_gobject()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gtk")
        self.cpp_info.set_property("cmake_target_name", "gtk::gtk")
        self.cpp_info.set_property("pkg_config_name", "gtk+-3.0")
        self.cpp_info.includedirs = [
            "include/gtk-3.0",
            "include/gail-3.0",
            "include/cairo",
            "include",
        ]
        self.cpp_info.libs = ["gtk-3", "gdk-3", "gailutil-3"]
        self.cpp_info.requires = [
            "glib::gio-2.0",
            "glib::gobject-2.0",
            "glib::glib-2.0",
            "atk::atk",
            "cairo::cairo",
            "gdk-pixbuf::gdk-pixbuf",
            "pango::pango",
            "pango::pangocairo",
            "fribidi::fribidi",
            "libepoxy::libepoxy",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── OHOS / build helpers ───────────────────────────────────────────

    def _build_environment(self):
        # 只 prepend PATH（glib-compile-resources/glib-genmarshal 等工具），
        # 不设 LD_LIBRARY_PATH（避免 glib 的 libintl.so.8 遮蔽 python 自身）。
        # 重签名的 glib ELF 工具 wrapper 目录优先（见 _prepare_glib_tools）。
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        tools_dir = self._glib_tools_dir()
        if os.path.isdir(tools_dir):
            environment.prepend_path("PATH", tools_dir)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
        return environment

    def _alias_gio_unix_pc(self):
        # glib 配方只暴露 gio-2.0 组件；gtk meson 以 required:false 查找
        # gio-unix-2.0。提供别名 .pc 使 HAVE_GIO_UNIX 生效。
        src = os.path.join(self.generators_folder, "gio-2.0.pc")
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            shutil.copy(src, dst)
            content = open(dst, encoding="utf-8").read()
            content = content.replace("Name: gio-2.0", "Name: gio-unix-2.0")
            open(dst, "w", encoding="utf-8").write(content)

    def _augment_fribidi_pc(self):
        # fribidi 配方没声明 includedirs=include/fribidi，生成的 fribidi.pc
        # 缺 -I${includedir}/fribidi，gtk 源码 #include <fribidi.h> 找不到。
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as handle:
            content = handle.read()
        cflags = content.split("Cflags:", 1)
        if len(cflags) == 2 and "/fribidi" not in cflags[1].splitlines()[0]:
            new_line = cflags[1].splitlines()[0].rstrip() + ' -I"${includedir}/fribidi"'
            content = "Cflags:".join([cflags[0], new_line + "\n" + "\n".join(cflags[1].splitlines()[1:])])
            with open(pc, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _augment_glib_pkg_config(self):
        # PkgConfigDeps 生成的 glib-2.0.pc 不带 glib_mkenums/glib_genmarshal
        # 变量，gio-2.0.pc 不带 glib_compile_resources；gtk 的 gnome module
        # 必须从 pkg-config 变量获取这些 glib 工具，否则
        # "Could not get pkg-config variable and no default provided"。
        # ELF 工具指向 build 目录中的重签名 wrapper（见 _prepare_glib_tools）。
        paths = self._glib_tool_var_paths()
        variables = {
            "glib-2.0": [
                f"glib_mkenums={paths['glib-mkenums']}",
                f"glib_genmarshal={paths['glib-genmarshal']}",
                f"gobject_query={paths['gobject-query']}",
            ],
            "gobject-2.0": [
                f"glib_mkenums={paths['glib-mkenums']}",
            ],
            "gio-2.0": [
                f"glib_compile_resources={paths['glib-compile-resources']}",
                f"glib_compile_schemas={paths['glib-compile-schemas']}",
                f"gio_querymodules={paths['gio-querymodules']}",
                f"gdbus_codegen={paths['gdbus-codegen']}",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if not inserted:
                continue
            name_index = content.find("\nName:")
            addition = "\n" + "\n".join(inserted)
            if name_index >= 0:
                content = content[:name_index] + addition + content[name_index:]
            else:
                content = "\n".join(inserted) + "\n" + content
            with open(pc_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _glib_tools_dir(self):
        return os.path.join(self.build_folder, "tools")

    def _prepare_glib_tools(self):
        """glib 制品包 bin/ 的编译工具未签名，且运行需要 glib 共享库。
        这里把 4 个 ELF 工具复制到 build 目录、重新签名，并生成 shell 包装
        脚本（包装脚本内设置 LD_LIBRARY_PATH=glib libdir，避免全局污染导致
        python/meson 加载到 g_libintl_* 版 libintl 崩溃）。
        python 工具（glib-mkenums/glib-genmarshal/gdbus-codegen）可直接运行。
        """
        tools_dir = self._glib_tools_dir()
        os.makedirs(tools_dir, exist_ok=True)
        elf_tools = (
            "glib-compile-resources",
            "glib-compile-schemas",
            "gio-querymodules",
            "gobject-query",
        )
        glib_pkg = None
        for dependency in self.dependencies.host.values():
            if os.path.isfile(os.path.join(dependency.package_folder, "bin", "glib-compile-resources")):
                glib_pkg = dependency.package_folder
                break
        if glib_pkg is None:
            self.output.warning("glib package not found; glib tools not prepared")
            return
        glib_bin = os.path.join(glib_pkg, "bin")
        # 工具运行期需要依赖包的共享库（glib-compile-resources 还会拉起
        # gdk-pixbuf-pixdata 等）。收集全部 host 依赖的 lib 目录组成
        # LD_LIBRARY_PATH；注意只在 C 工具 wrapper 内部生效，不影响 python。
        lib_paths = []
        for dependency in self.dependencies.host.values():
            libdir = os.path.join(dependency.package_folder, "lib")
            if os.path.isdir(libdir):
                lib_paths.append(libdir)
        lib_path_str = ":".join(lib_paths)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in elf_tools:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                continue
            signed = os.path.join(tools_dir, f"{tool}.signed")
            if not os.path.isfile(signed):
                shutil.copy2(src, signed)
                self.run(f'"{objcopy}" --remove-section .codesign "{signed}" 2>/dev/null || true')
                self.run(f'"{signer}" sign -inFile "{signed}" -outFile "{signed}" -selfSign 1')
            wrapper = os.path.join(tools_dir, tool)
            if not os.path.isfile(wrapper):
                save(
                    self,
                    wrapper,
                    "#!/bin/sh\n"
                    f'LD_LIBRARY_PATH="{lib_path_str}"${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\n'
                    "export LD_LIBRARY_PATH\n"
                    f'exec "{signed}" "$@"\n',
                )
                os.chmod(wrapper, 0o755)
        return tools_dir

    def _glib_tool_var_paths(self):
        """generate() 阶段用：binary 工具指向 build 目录的 wrapper（存在则用
        wrapper，不存在回退到 glib bin），python 工具直接用 glib bin。"""
        tools_dir = self._glib_tools_dir()
        result = {}
        for tool in (
            "glib-compile-resources",
            "glib-compile-schemas",
            "gio-querymodules",
            "gobject-query",
        ):
            result[tool] = os.path.join(tools_dir, tool)
        for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen"):
            found = None
            for dependency in self.dependencies.host.values():
                candidate = os.path.join(dependency.package_folder, "bin", tool)
                if os.path.isfile(candidate):
                    found = candidate
                    break
            result[tool] = found or tool
        return result

    def _build_cairo_gobject(self):
        cg_src = os.path.join(self.source_folder, "cairo-gobject")
        cg_build = os.path.join(self.build_folder, "cairo-gobject-build")
        native = self._make_cairo_gobject_native_file()
        env = self._build_environment()
        jobs = max(1, (os.cpu_count() or 2) // 2)
        with env.vars(self).apply():
            self.run(
                f'meson setup "{cg_build}" "{cg_src}"'
                f' --native-file "{native}" --prefix {cg_build} -Dbuildtype=release'
            )
            self.run(f'meson compile -C "{cg_build}" -j {jobs}')
        self._write_cairo_gobject_pc(cg_src, cg_build)

    def _make_cairo_gobject_native_file(self):
        # 主 native 文件的 [project options] 是 gtk 专有选项，cairo-gobject 子构建
        # 不认识（Unknown option）。生成一个只含 [binaries] + [built-in options]
        # 的最小 native 文件供子 meson 工程使用。
        src_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(src_file):
            return src_file
        with open(src_file, encoding="utf-8") as handle:
            lines = handle.readlines()
        out_lines = []
        in_project_options = False
        for line in lines:
            stripped = line.strip()
            if stripped == "[project options]":
                in_project_options = True
                continue
            if in_project_options:
                if stripped.startswith("[") and stripped.endswith("]"):
                    in_project_options = False
                else:
                    continue
            out_lines.append(line)
        native = os.path.join(self.generators_folder, "conan_meson_native_cg.ini")
        with open(native, "w", encoding="utf-8") as handle:
            handle.writelines(out_lines)
        return native

    def _write_cairo_gobject_pc(self, cg_src, cg_build):
        content = (
            f"prefix={cg_build}\n"
            f"libdir={cg_build}\n"
            f"includedir={cg_src}\n"
            "\n"
            "Name: cairo-gobject\n"
            "Description: cairo-gobject for cairo graphics library\n"
            "Version: 1.18.4\n"
            "Requires: cairo glib-2.0 gobject-2.0\n"
            f"Libs: -L${{libdir}} -lcairo-gobject\n"
            f"Libs.private: -Wl,-rpath,{cg_build}\n"
            f"Cflags: -I{cg_src}\n"
        )
        save(self, os.path.join(self.generators_folder, "cairo-gobject.pc"), content)

    def _install_cairo_gobject(self):
        cg_src = os.path.join(self.source_folder, "cairo-gobject")
        cg_build = os.path.join(self.build_folder, "cairo-gobject-build")
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        candidates = sorted(
            [
                path
                for path in glob.glob(os.path.join(cg_build, "libcairo-gobject.so.*"))
                if os.path.isfile(path)
            ]
            + [os.path.join(cg_build, "libcairo-gobject.so")],
            key=len,
            reverse=True,
        )
        if not candidates:
            raise ConanException("cairo-gobject library not built")
        source = candidates[0]
        shutil.copy2(source, libdir)
        base = os.path.basename(source)
        for alias in ("libcairo-gobject.so.2", "libcairo-gobject.so"):
            dest = os.path.join(libdir, alias)
            if os.path.exists(dest):
                continue
            try:
                os.symlink(base, dest)
            except (OSError, NotImplementedError):
                shutil.copy2(source, dest)
        incdir = os.path.join(self.package_folder, "include", "cairo")
        os.makedirs(incdir, exist_ok=True)
        copy(self, "cairo-gobject.h", src=cg_src, dst=incdir)
        # 随包分发 cairo-gobject.pc（gdk-3.0.pc 的 Requires 引用它）
        pc_content = (
            f"prefix=${{pcfiledir}}/../..\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include/cairo\n"
            "\n"
            "Name: cairo-gobject\n"
            "Description: cairo-gobject for cairo graphics library\n"
            "Version: 1.18.4\n"
            "Requires: cairo glib-2.0 gobject-2.0\n"
            "Libs: -L${libdir} -lcairo-gobject\n"
            "Cflags: -I${includedir}\n"
        )
        pcdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        save(self, os.path.join(pcdir, "cairo-gobject.pc"), pc_content)

    def _append_dependency_pkg_config_paths(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique_paths = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique_paths:
                unique_paths.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_binaries(self):
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def _glib_libintl_link_args(self):
        # gtk 源码通过 glib/gi18n-lib.h 引用 g_libintl_dgettext 等符号（由
        # glib 包的 libintl 提供）。用 -L/-lintl/-rpath 形式：绝对路径会让
        # meson sanity check 二进制 NEED libintl.so.8 却无搜索路径 →
        # "Error loading shared library libintl.so.8"；-rpath 保证 sanity
        # check 与最终库都能找到。
        if self.settings.os != "OHOS":
            return []
        for dependency in self.dependencies.host.values():
            libdir = os.path.join(dependency.package_folder, "lib")
            for library_name in ("libintl.so", "libintl.a"):
                if os.path.isfile(os.path.join(libdir, library_name)):
                    return [
                        f"-L{libdir}".replace("\\", "/"),
                        "-lintl",
                        f"-Wl,-rpath,{libdir}".replace("\\", "/"),
                    ]
        return []

    def _sign_installed_elfs(self):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
            os.path.join(self.package_folder, "bin", "**", "*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target) or not os.path.isfile(target):
                continue
            if not self._is_elf(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}" 2>/dev/null || true')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False
