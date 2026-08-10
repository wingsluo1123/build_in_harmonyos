#!/usr/bin/env python3
"""Conan recipe — libaccounts-glib 1.27 (Meson).

libaccounts-glib is the GLib-based core of the accounts-sso (Single Sign-On)
project. It provides a C API for managing online account information via
GLib/GObject, with SQLite-backed storage and libxml2 for XML parsing.

Adapted to HarmonyOS PC (aarch64). All features (library + tools) are built
without trimming. See notes.md for platform adaptation details.
"""
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibAccountsGlibConan(ConanFile):
    name = "libaccounts-glib"
    version = "1.27.1"
    description = "GLib-based library for managing online account information (accounts-sso project)"
    license = "LGPL-2.1"
    homepage = "https://gitlab.com/accounts-sso/libaccounts-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.49.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # check is needed only by the upstream test suite (tests/meson.build)
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_glib_pkg_config_aliases()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["accounts-glib"]
        self.cpp_info.requires = ["glib2::glib2", "libxml2::libxml2", "sqlite3::sqlite3"]
        self.cpp_info.includedirs = ["include", "include/libaccounts-glib"]
        self.cpp_info.set_property("pkg_config_name", "libaccounts-glib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    # ── glib2 pkg-config alias helpers (adapted from vips recipe) ──

    def _create_glib_pkg_config_aliases(self):
        """Create gio-2.0.pc, gobject-2.0.pc, gio-unix-2.0.pc aliases from
        the single glib-2.0.pc that PkgConfigDeps generates for glib2, and
        inject glib_genmarshal / gdbus_codegen variables pointing to staged
        copies of the glib tools."""
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()

        # Inject missing tool variables
        for variable, executable in {
            "glib_genmarshal": "glib-genmarshal",
            "glib_mkenums": "glib-mkenums",
            "gdbus_codegen": "gdbus-codegen",
        }.items():
            if not re.search(rf"^{variable}=", content, flags=re.M):
                tool = self._stage_glib_tool(content, executable)
                content = content.replace(
                    "\nName:",
                    f"\n{variable}={tool}\nName:",
                    1,
                )

        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

        # Create alias .pc files for gio-2.0, gobject-2.0, gio-unix-2.0
        # gio-unix-2.0 needs its own Cflags pointing to include/gio-unix-2.0
        # (not the glib-2.0 includedir which is include/glib-2.0)
        prefix_match2 = re.search(r"^prefix=(.+)$", content, flags=re.M)
        prefix_val = prefix_match2.group(1).strip() if prefix_match2 else "${prefix}"
        gio_unix_cflags = f"-I{prefix_val}/include/gio-unix-2.0"
        aliases = {
            "gio-2.0.pc": ("gio-2.0", None),
            "gobject-2.0.pc": ("gobject-2.0", None),
            "gio-unix-2.0.pc": ("gio-unix-2.0", gio_unix_cflags),
        }
        for filename, (name, cflags_override) in aliases.items():
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            if cflags_override:
                alias = re.sub(r"^Cflags:.*$", f"Cflags: {cflags_override}", alias, flags=re.M)
            with open(os.path.join(self.generators_folder, filename), "w", encoding="utf-8") as target:
                target.write(alias)

    def _inject_archive_tools(self):
        """Inject ar/ranlib paths into meson native.ini to fix 'Unknown
        linker(s)' error when AR env var points to llvm-ar not on PATH."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (os.path.join(bindir, "ar") if bindir else "")
        ranlib = executables.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        if not ar:
            ar = shutil.which("ar") or shutil.which("llvm-ar")
        if not ar:
            raise ConanInvalidConfiguration("Meson needs ar for libaccounts-glib")
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if ranlib and os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def _stage_glib_tool(self, pc_content, executable):
        """Copy a glib tool (glib-genmarshal, gdbus-codegen) from the glib2
        conan package to the generators folder and return its path. For
        Python-based tools, also patches the script to add the correct
        PYTHONPATH for finding glib's codegen module."""
        prefix_match = re.search(r"^prefix=(.+)$", pc_content, flags=re.M)
        if not prefix_match:
            return f"${{bindir}}/{executable}"
        prefix = prefix_match.group(1).strip()
        source = os.path.join(prefix, "bin", executable)
        if not os.path.isfile(source):
            return f"${{bindir}}/{executable}"
        target = os.path.join(self.generators_folder, executable)
        shutil.copyfile(source, target)
        os.chmod(target, 0o755)

        # For Python-based tools, patch sys.path to find the codegen module
        codegen_dir = os.path.join(prefix, "share", "glib-2.0")
        if os.path.isdir(codegen_dir):
            with open(target, "r", encoding="utf-8") as f:
                script_content = f.read()
            if "from codegen import" in script_content or "import codegen" in script_content:
                # Add sys.path.insert right after 'import sys'
                script_content = script_content.replace(
                    "import sys\n",
                    f'import sys\nsys.path.insert(0, "{codegen_dir}")\n',
                    1,
                )
                with open(target, "w", encoding="utf-8") as f:
                    f.write(script_content)

        # Create C wrapper for reliable shebang resolution
        python = (shutil.which("python3") or sys.executable).replace("\\", "/")
        target = target.replace("\\", "/")
        wrapper = self._build_python_tool_wrapper(executable, python, target)
        return wrapper.replace("\\", "/")

    def _build_python_tool_wrapper(self, executable, python, script):
        compiler = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ).get("c") or shutil.which("cc") or shutil.which("clang")
        if not compiler:
            return script
        wrapper = os.path.join(self.generators_folder, f"{executable}-wrapper")
        source = f"{wrapper}.c"
        with open(source, "w", encoding="utf-8") as wrapper_source:
            wrapper_source.write(
                '#include <stdio.h>\n'
                '#include <stdlib.h>\n'
                '#include <unistd.h>\n'
                'int main(int argc, char **argv) {\n'
                f'    const char *python = "{self._c_string(python)}";\n'
                f'    const char *script = "{self._c_string(script)}";\n'
                '    char **cmd = calloc((size_t)argc + 2, sizeof(char *));\n'
                '    if (!cmd) return 127;\n'
                '    cmd[0] = (char *)python;\n'
                '    cmd[1] = (char *)script;\n'
                '    for (int i = 1; i < argc; ++i) cmd[i + 1] = argv[i];\n'
                '    cmd[argc + 1] = NULL;\n'
                '    execv(python, cmd);\n'
                '    perror("execv");\n'
                '    return 127;\n'
                '}\n'
            )
        self.run(f'"{compiler}" "{source}" -o "{wrapper}"')
        os.chmod(wrapper, 0o755)
        return wrapper

    @staticmethod
    def _c_string(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')
