#!/usr/bin/env python3
"""Conan recipe for glib 2.84.0 on HarmonyOS PC (arm64).

Build system: meson
R26: glib is a system same-name library → default_library=static
R27: Dependencies reference @ohpcd/stable
R28: test_package/ exists
R32: settings.os judgment uses in ("Linux", "OHOS")
E090: Meson host_system == 'linux' fix applied via patches (0001, 0003, 0004)
Netlink disabled for HarmonyOS via patch (0004)
getpass() declaration added via patch (0002)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class GlibConan(ConanFile):
    name = "glib"
    version = "2.84.0"
    description = "GNOME core C utility library (glib, gobject, gio, gmodule, gthread)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glib"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.40")
        # zlib is system pre-installed
        # gettext (intl) is provided by musl libc on OHOS

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # Populate gvdb subproject (empty in git archive tarball)
        # Declared in conandata.yml as "gvdb" source
        gvdb_data = self.conan_data.get("gvdb")
        if gvdb_data:
            gvdb_dir = os.path.join(self.source_folder, "subprojects", "gvdb")
            if not os.path.exists(os.path.join(gvdb_dir, "meson.build")):
                get(self, **gvdb_data, strip_root=True,
                    destination=gvdb_dir)
                self.output.info("gvdb subproject populated from conandata")

        # Create proxy-libintl subproject
        # On OHOS, gettext functions are provided by system musl libc.
        # This subproject provides libintl.h header and an empty dependency
        # (no link_args needed — musl libc has gettext built in).
        proxy_dir = os.path.join(self.source_folder, "subprojects", "proxy-libintl")
        if not os.path.exists(os.path.join(proxy_dir, "meson.build")):
            os.makedirs(proxy_dir, exist_ok=True)

            # meson.build: link against system musl libc for gettext functions
            # On OHOS, gettext is in system musl libc (ld-musl-aarch64.so.1)
            # but not in SDK's libc.so. Using -l: syntax (standard linker
            # mechanism) instead of absolute path.
            with open(os.path.join(proxy_dir, "meson.build"), 'w') as f:
                f.write(
                    "project('proxy-libintl', 'c', version: '1.0')\n"
                    "# On OHOS, gettext functions are in system musl libc.\n"
                    "# SDK's libc.so lacks gettext, system musl libc has it.\n"
                    "cc = meson.get_compiler('c')\n"
                    "intl_dep = declare_dependency(\n"
                    "  include_directories: include_directories('.'),\n"
                    "  link_args: ['-L/lib', '-l:ld-musl-aarch64.so.1'],\n"
                    ")\n"
                )

            # libintl.h: minimal header for OHOS musl libc gettext API
            with open(os.path.join(proxy_dir, "libintl.h"), 'w') as f:
                f.write(
                    '#ifndef _LIBINTL_H\n'
                    '#define _LIBINTL_H\n'
                    '\n'
                    '#include <locale.h>\n'
                    '\n'
                    '#ifdef __cplusplus\n'
                    'extern "C" {\n'
                    '#endif\n'
                    '\n'
                    'extern char *gettext(const char *) __attribute__((__format_arg__(1)));\n'
                    'extern char *dgettext(const char *, const char *) __attribute__((__format_arg__(2)));\n'
                    'extern char *dcgettext(const char *, const char *, int) __attribute__((__format_arg__(2)));\n'
                    'extern char *ngettext(const char *, const char *, unsigned long);\n'
                    'extern char *dngettext(const char *, const char *, const char *, unsigned long);\n'
                    'extern char *dcngettext(const char *, const char *, const char *, unsigned long, int);\n'
                    'extern char *bind_textdomain_codeset(const char *, const char *);\n'
                    'extern char *bindtextdomain(const char *, const char *);\n'
                    'extern char *textdomain(const char *);\n'
                    '\n'
                    '#ifdef __cplusplus\n'
                    '}\n'
                    '#endif\n'
                    '\n'
                    '#endif\n'
                )
            self.output.info("proxy-libintl subproject created with libintl.h")

    def generate(self):
        tc = MesonToolchain(self)
        # R26: System same-name library must use static linking
        tc.project_options["default_library"] = "static"
        # Disable optional features not available on OHOS
        tc.project_options["selinux"] = "disabled"
        tc.project_options["libmount"] = "disabled"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["documentation"] = "false"
        tc.project_options["man-pages"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()

    def build(self):
        # Merge system PKG_CONFIG_PATH (from conan profile buildenv) into
        # the meson native file. MesonToolchain sets pkg_config_path to
        # the conan build folder only; system library paths (pcre2, libffi,
        # zlib) are provided by the profile's buildenv, which is only
        # available at build() time after conanbuild.sh is sourced.
        native_ini = os.path.join(self.build_folder, "conan_meson_native.ini")
        if os.path.exists(native_ini):
            with open(native_ini, 'r') as f:
                lines = f.readlines()
            # Find pkg_config_path line and append system paths from
            # the conanbuildenv script (generated by profile's [buildenv])
            import glob
            sys_pkg_path = ""
            for env_script in glob.glob(
                os.path.join(self.build_folder, "conanbuildenv-*.sh")
            ):
                with open(env_script, 'r') as f:
                    for line in f:
                        if line.startswith("export PKG_CONFIG_PATH="):
                            sys_pkg_path = line.split('"')[1] if '"' in line else ""
                            break
                if sys_pkg_path:
                    break
            if sys_pkg_path:
                new_lines = []
                for line in lines:
                    if line.startswith("pkg_config_path = '"):
                        # Merge conan build path with system path
                        existing = line.split("'")[1]
                        new_lines.append(
                            f"pkg_config_path = '{existing}:{sys_pkg_path}'\n"
                        )
                        self.output.info(
                            "Merged system PKG_CONFIG_PATH into meson native file"
                        )
                    else:
                        new_lines.append(line)
                with open(native_ini, 'w') as f:
                    f.writelines(new_lines)

        # Apply all patches declared in conandata.yml (R3)
        apply_conandata_patches(self)

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        # R32: settings.os judgment must use in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

        self.cpp_info.set_property("cmake_file_name", "glib")
        self.cpp_info.set_property("pkg_config_name", "glib-2.0")

        # Main glib libraries
        self.cpp_info.libs = ["glib-2.0", "gobject-2.0", "gio-2.0",
                              "gmodule-2.0", "gthread-2.0"]

        # System dependencies:
        # - m, pthread, rt, dl: standard libc/runtime
        # - z: zlib (system pre-installed)
        # gettext functions are in system musl libc (ld-musl-aarch64.so.1)
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl", "z"]

        # Link against system musl libc for gettext functions.
        # OHOS SDK's libc.so lacks gettext, but system musl libc has it.
        # Using -l: syntax (standard linker mechanism) instead of
        # hardcoding absolute path /lib/ld-musl-aarch64.so.1.
        self.cpp_info.sharedlinkflags = ["-L/lib", "-l:ld-musl-aarch64.so.1"]
        self.cpp_info.exelinkflags = ["-L/lib", "-l:ld-musl-aarch64.so.1"]

        # Include paths: standard + glibconfig.h location
        self.cpp_info.includedirs = ["include/glib-2.0", "lib/glib-2.0/include"]
