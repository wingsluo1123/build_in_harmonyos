#!/usr/bin/env python3
"""Conan recipe for spice-gtk 0.42 remote desktop client libraries."""

import os
import re
import sys

from conan import ConanFile
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SpiceGtkConan(ConanFile):
    name = "spice-gtk"
    version = "0.42"
    description = "GTK and GLib client libraries for SPICE remote desktop sessions"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.spice-space.org"
    url = "https://gitlab.freedesktop.org/spice/spice-gtk"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "gtk": [True, False]}
    default_options = {"shared": True, "fPIC": True, "gtk": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("spice-protocol/0.14.5")
        self.requires("glib/2.84.0")
        self.requires("pixman/0.46.4.1")
        self.requires("openssl/3.5.6")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("zlib/1.3.1")
        self.requires("json-glib/1.6.6")
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        if self.options.gtk:
            self.requires("gtk+/3.24.38")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._make_version_helper_executable()
        replace_in_file(
            self,
            os.path.join(self.source_folder, "meson.build"),
            "run_command('build-aux/git-version-gen',",
            "run_command('sh', 'build-aux/git-version-gen',",
        )
        replace_in_file(
            self,
            os.path.join(
                self.source_folder, "subprojects", "spice-common", "meson_options.txt"
            ),
            "option('python-checks',\n    type : 'boolean',\n    value : true,",
            "option('python-checks',\n    type : 'boolean',\n    value : false,",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "meson.build"),
            "subdir('tests')",
            "# Tests are run through Conan test_package in the OHOS recipe.\n# subdir('tests')",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "meson.build"),
            "subdir('man')",
            "# Man pages are not installed in the first OHOS runtime package.\n# subdir('man')",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "meson.build"),
            "subdir('po')",
            "# Translations are skipped to avoid native gettext/msgfmt at cross-build time.\n# subdir('po')",
        )

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        mkenums = self._write_glib_tool_wrapper("glib-mkenums")
        genmarshal = self._write_glib_tool_wrapper("glib-genmarshal")
        self._set_glib_pkg_config_variable("glib_mkenums", mkenums)
        self._set_glib_pkg_config_variable("glib_genmarshal", genmarshal)
        self._create_glib_pkg_config_aliases()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["gtk"] = "enabled" if self.options.gtk else "disabled"
        tc.project_options["wayland-protocols"] = "disabled"
        tc.project_options["webdav"] = "disabled"
        tc.project_options["usbredir"] = "disabled"
        tc.project_options["libcap-ng"] = "disabled"
        tc.project_options["polkit"] = "disabled"
        tc.project_options["coroutine"] = "gthread"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["lz4"] = "disabled"
        tc.project_options["sasl"] = "disabled"
        tc.project_options["opus"] = "disabled"
        tc.project_options["smartcard"] = "disabled"
        tc.project_options["egl"] = "disabled"
        tc.project_options["gtk_doc"] = "disabled"
        tc.project_options["recorder"] = False
        tc.project_options["valgrind"] = False
        tc.generate()
        self._inject_meson_archive_tools()

    def build(self):
        self._ensure_tmpdir()
        self._make_version_helper_executable()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["spice-client-glib-2.0"]
        self.cpp_info.set_property("cmake_file_name", "spice-gtk")
        self.cpp_info.set_property("cmake_target_name", "spice-gtk::spice-gtk")
        self.cpp_info.set_property("pkg_config_name", "spice-client-glib-2.0")
        self.cpp_info.components["glib"].libs = ["spice-client-glib-2.0"]
        self.cpp_info.components["glib"].set_property("pkg_config_name", "spice-client-glib-2.0")
        if self.options.gtk:
            self.cpp_info.libs.insert(0, "spice-client-gtk-3.0")
            self.cpp_info.set_property("pkg_config_name", "spice-client-gtk-3.0")
            self.cpp_info.components["gtk"].libs = ["spice-client-gtk-3.0"]
            self.cpp_info.components["gtk"].requires = ["glib"]
            self.cpp_info.components["gtk"].set_property("pkg_config_name", "spice-client-gtk-3.0")

    def _make_version_helper_executable(self):
        roots = [self.source_folder]
        if self.build_folder:
            roots.extend([self.build_folder, os.path.dirname(self.build_folder)])
        for root in roots:
            helper = os.path.join(root, "build-aux", "git-version-gen")
            if os.path.isfile(helper):
                os.chmod(helper, 0o755)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def _create_glib_pkg_config_aliases(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        aliases = {
            "gobject-2.0.pc": "gobject-2.0",
            "gmodule-2.0.pc": "gmodule-2.0",
            "gmodule-no-export-2.0.pc": "gmodule-no-export-2.0",
            "gthread-2.0.pc": "gthread-2.0",
            "gio-2.0.pc": "gio-2.0",
            "gio-unix-2.0.pc": "gio-unix-2.0",
        }
        for filename, name in aliases.items():
            alias_path = os.path.join(self.generators_folder, filename)
            alias = re.sub(r"^Name:.*$", f"Name: {name}", content, flags=re.M)
            with open(alias_path, "w", encoding="utf-8") as target:
                target.write(alias)

    def _set_glib_pkg_config_variable(self, variable, value):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        replacement = f"{variable}={value}"
        if re.search(rf"^{re.escape(variable)}=.*$", content, flags=re.M):
            content = re.sub(
                rf"^{re.escape(variable)}=.*$", replacement, content, flags=re.M
            )
        else:
            content = content.rstrip() + "\n" + replacement + "\n"
        with open(glib_pc, "w", encoding="utf-8") as target:
            target.write(content)

    def _write_glib_tool_wrapper(self, tool_name):
        glib = self.dependencies["glib"]
        original = os.path.join(glib.package_folder, "bin", tool_name)
        wrapper = os.path.join(self.generators_folder, tool_name)
        script = f"""#!{sys.executable}
import runpy
import sys

sys.argv[0] = {original!r}
runpy.run_path({original!r}, run_name="__main__")
"""
        with open(wrapper, "w", encoding="utf-8", newline="\n") as target:
            target.write(script)
        os.chmod(wrapper, 0o755)
        return wrapper
