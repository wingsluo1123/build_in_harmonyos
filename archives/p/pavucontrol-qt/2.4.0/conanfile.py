#!/usr/bin/env python3
"""Conan recipe for pavucontrol-qt 2.4.0 on HarmonyOS PC (arm64).

pavucontrol-qt is a Qt-based volume control for PulseAudio (LXQt project).
This recipe builds the application from source, including building its
dependencies (libsndfile, glib, pulseaudio, lxqt-build-tools) from source
because they are not available as conan packages in the ohpcd repository.

Build system: CMake (pavucontrol-qt), Meson (glib, pulseaudio), CMake (libsndfile)
Qt6 is provided by conan (qtbase/6.11.1).
System packages (libffi, pcre2, gettext) are provided by HNP.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class PavucontrolQtConan(ConanFile):
    name = "pavucontrol-qt"
    version = "2.4.0"
    description = "Qt-based volume control for PulseAudio (LXQt)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lxqt/pavucontrol-qt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Also export glib patches (not in conandata patches list, applied manually in build())
        import os, shutil
        patches_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patches_dir):
            for f in os.listdir(patches_dir):
                if f.startswith("glib-") and f.endswith(".patch"):
                    dst = os.path.join(self.export_folder, "patches", f)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(os.path.join(patches_dir, f), dst)

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # Build dependencies from source (not available in ohpcd conan repository)
        dep_prefix = os.path.join(self.build_folder, "dep_prefix")
        os.makedirs(dep_prefix, exist_ok=True)

        self._build_libsndfile(dep_prefix)
        self._build_glib(dep_prefix)
        self._build_pulseaudio(dep_prefix)
        self._install_lxqt_build_tools(dep_prefix)

        # Apply pavucontrol-qt patches
        apply_conandata_patches(self)

        # Build pavucontrol-qt using all locally built dependencies
        qt_dir = self.dependencies["qtbase"].package_folder

        # Set up environment for cmake
        gettext_prefix = "/data/service/hnp/gettext.org/gettext_0.26"
        pcre2_prefix = "/data/service/hnp/pcre2.org/pcre2_10.47"
        libffi_prefix = "/data/service/hnp/libffi.org/libffi_3.4.4"

        pkg_config_path = (
            f"{dep_prefix}/lib/pkgconfig:"
            f"{dep_prefix}/lib/pulseaudio:"
            f"{pcre2_prefix}/lib/pkgconfig:"
            f"{libffi_prefix}/lib/pkgconfig:"
            f"{qt_dir}/lib/pkgconfig"
        )
        cmake_prefix_path = (
            f"{qt_dir}:{dep_prefix}:{dep_prefix}/share/cmake/lxqt2-build-tools"
        )

        # Fix libffi pkg-config if needed (wrong prefix)
        libffi_pc = os.path.join(dep_prefix, "lib/pkgconfig/libffi.pc")
        if not os.path.exists(libffi_pc):
            # Create corrected libffi.pc
            os.makedirs(os.path.dirname(libffi_pc), exist_ok=True)
            with open(libffi_pc, "w") as f:
                f.write(
                    f"prefix={libffi_prefix}\n"
                    "exec_prefix=${prefix}\n"
                    "libdir=${exec_prefix}/lib\n"
                    "includedir=${prefix}/include\n"
                    "Name: libffi\n"
                    "Description: Library supporting Foreign Function Interfaces\n"
                    "Version: 3.4.4\n"
                    "Libs: -L${libdir} -lffi\n"
                    "Cflags: -I${includedir}\n"
                )

        cmake = CMake(self)
        cmake.configure(
            variables={
                "CMAKE_PREFIX_PATH": cmake_prefix_path,
                "CMAKE_EXE_LINKER_FLAGS": f"-L/lib -L{gettext_prefix}/lib",
            }
        )
        cmake.build()

    def _build_libsndfile(self, prefix):
        """Build libsndfile from source (minimal, no external codecs)."""
        self.output.info("Building libsndfile from source...")
        src = os.path.join(self.build_folder, "libsndfile-src")
        get(self, **self.conan_data["libsndfile"], strip_root=True, destination=src)

        build_dir = os.path.join(self.build_folder, "libsndfile-build")
        os.makedirs(build_dir, exist_ok=True)

        cc = self._get_compiler()
        cmake_vars = {
            "CMAKE_INSTALL_PREFIX": prefix,
            "CMAKE_BUILD_TYPE": "Release",
            "ENABLE_EXTERNAL_LIBS": "OFF",
            "ENABLE_MPEG": "OFF",
            "BUILD_SHARED_LIBS": "OFF",
            "BUILD_PROGRAMS": "OFF",
            "BUILD_EXAMPLES": "OFF",
            "BUILD_REGTEST": "OFF",
            "ENABLE_CPACK": "OFF",
            "INSTALL_PKGCONFIG_MODULE": "ON",
            "CMAKE_C_COMPILER": cc,
            "CMAKE_C_FLAGS": "-fPIC -O2",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        }
        cmake = CMake(self)
        cmake.configure(build_dir=build_dir, variables=cmake_vars, build_script_folder=src)
        cmake.build()
        cmake.install()

    def _build_glib(self, prefix):
        """Build glib 2.84.0 from source with HarmonyOS patches."""
        self.output.info("Building glib 2.84.0 from source...")
        src = os.path.join(self.build_folder, "glib-src")
        get(self, **self.conan_data["glib"], strip_root=True, destination=src)

        # Populate gvdb subproject
        gvdb_dir = os.path.join(src, "subprojects", "gvdb")
        os.makedirs(gvdb_dir, exist_ok=True)
        get(self, **self.conan_data["gvdb"], strip_root=True, destination=gvdb_dir)

        # Create proxy-libintl subproject
        proxy_dir = os.path.join(src, "subprojects", "proxy-libintl")
        os.makedirs(proxy_dir, exist_ok=True)
        with open(os.path.join(proxy_dir, "meson.build"), "w") as f:
            f.write(
                "project('proxy-libintl', 'c', version: '1.0')\n"
                "cc = meson.get_compiler('c')\n"
                "intl_dep = declare_dependency(\n"
                "  include_directories: include_directories('.'),\n"
                "  link_args: ['-L/lib', '-l:ld-musl-aarch64.so.1'],\n"
                ")\n"
            )
        with open(os.path.join(proxy_dir, "libintl.h"), "w") as f:
            f.write(
                "#ifndef _LIBINTL_H\n#define _LIBINTL_H\n#include <locale.h>\n"
                "#ifdef __cplusplus\nextern \"C\" {\n#endif\n"
                "extern char *gettext(const char *) __attribute__((__format_arg__(1)));\n"
                "extern char *dgettext(const char *, const char *) __attribute__((__format_arg__(2)));\n"
                "extern char *dcgettext(const char *, const char *, int) __attribute__((__format_arg__(2)));\n"
                "extern char *ngettext(const char *, const char *, unsigned long);\n"
                "extern char *dngettext(const char *, const char *, const char *, unsigned long);\n"
                "extern char *dcngettext(const char *, const char *, const char *, unsigned long, int);\n"
                "extern char *bind_textdomain_codeset(const char *, const char *);\n"
                "extern char *bindtextdomain(const char *, const char *);\n"
                "extern char *textdomain(const char *);\n"
                "#ifdef __cplusplus\n}\n#endif\n#endif\n"
            )

        # Apply glib HarmonyOS patches
        patches_dir = os.path.join(self.recipe_folder, "patches")
        import subprocess
        for p in sorted(os.listdir(patches_dir)):
            if p.startswith("glib-") and p.endswith(".patch"):
                patch_file = os.path.join(patches_dir, p)
                try:
                    subprocess.run(
                        ["patch", "-p1", "-i", patch_file],
                        cwd=src, check=True, capture_output=True
                    )
                    self.output.info(f"Applied glib patch: {p}")
                except subprocess.CalledProcessError as e:
                    self.output.warn(f"Failed to apply glib patch {p}: {e}")

        # Build glib with meson
        build_dir = os.path.join(self.build_folder, "glib-build")
        os.makedirs(build_dir, exist_ok=True)

        gettext_prefix = "/data/service/hnp/gettext.org/gettext_0.26"
        pcre2_prefix = "/data/service/hnp/pcre2.org/pcre2_10.47"
        libffi_prefix = "/data/service/hnp/libffi.org/libffi_3.4.4"

        # Create corrected libffi pkg-config
        libffi_pc = os.path.join(prefix, "lib/pkgconfig/libffi.pc")
        os.makedirs(os.path.dirname(libffi_pc), exist_ok=True)
        with open(libffi_pc, "w") as f:
            f.write(
                f"prefix={libffi_prefix}\n"
                "exec_prefix=${prefix}\n"
                "libdir=${exec_prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "Name: libffi\n"
                "Description: Library supporting Foreign Function Interfaces\n"
                "Version: 3.4.4\n"
                "Libs: -L${libdir} -lffi\n"
                "Cflags: -I${includedir}\n"
            )

        env = {
            "CC": self._get_compiler(),
            "CXX": self._get_compiler("cpp"),
            "CFLAGS": f"-fPIC -O2 -I{gettext_prefix}/include -Wno-error=implicit-function-declaration -Wno-error=missing-prototypes",
            "PKG_CONFIG_PATH": f"{prefix}/lib/pkgconfig:{pcre2_prefix}/lib/pkgconfig",
            "PATH": f"/data/service/hnp/bin:{os.environ.get('PATH', '')}",
        }

        native_file = os.path.join(build_dir, "native.ini")
        with open(native_file, "w") as f:
            f.write(
                "[binaries]\n"
                f"c = '{self._get_compiler()}'\n"
                f"cpp = '{self._get_compiler('cpp')}'\n"
                "ar = '/data/service/hnp/bin/llvm-ar'\n"
                "ranlib = '/data/service/hnp/bin/llvm-ranlib'\n"
                "nm = '/data/service/hnp/bin/llvm-nm'\n"
                "pkg-config = '/data/service/hnp/bin/pkg-config'\n"
                "ninja = '/data/service/hnp/bin/ninja'\n"
                "[built-in options]\n"
                f"c_args = ['-I{gettext_prefix}/include', '-Wno-error=implicit-function-declaration', '-Wno-error=missing-prototypes']\n"
                f"c_link_args = ['-L{gettext_prefix}/lib', '-L/lib', '-l:ld-musl-aarch64.so.1']\n"
            )

        self._run_meson(src, build_dir, prefix, env, native_file,
                        ["--default-library=static", "-Dselinux=disabled",
                         "-Dlibmount=disabled", "-Dnetlink=disabled",
                         "-Dsysprof=disabled", "-Ddocumentation=false",
                         "-Dman-pages=disabled", "-Dtests=false",
                         "-Dwrap_mode=nodownload"])
        self._run_meson_install(build_dir, prefix)

    def _build_pulseaudio(self, prefix):
        """Build pulseaudio 17.0 from source (client-only)."""
        self.output.info("Building pulseaudio 17.0 from source...")
        src = os.path.join(self.build_folder, "pulseaudio-src")
        get(self, **self.conan_data["pulseaudio"], strip_root=True, destination=src)

        # Create .tarball-version for version detection
        with open(os.path.join(src, ".tarball-version"), "w") as f:
            f.write("17.0")

        build_dir = os.path.join(self.build_folder, "pulseaudio-build")
        os.makedirs(build_dir, exist_ok=True)

        gettext_prefix = "/data/service/hnp/gettext.org/gettext_0.26"
        pcre2_prefix = "/data/service/hnp/pcre2.org/pcre2_10.47"
        libffi_prefix = "/data/service/hnp/libffi.org/libffi_3.4.4"

        env = {
            "CC": self._get_compiler(),
            "CXX": self._get_compiler("cpp"),
            "CFLAGS": f"-fPIC -O2 -I{gettext_prefix}/include -Wno-error=implicit-function-declaration",
            "PKG_CONFIG_PATH": f"{prefix}/lib/pkgconfig:{prefix}/lib/pulseaudio:{pcre2_prefix}/lib/pkgconfig:{libffi_prefix}/lib/pkgconfig",
            "PATH": f"/data/service/hnp/bin:{os.environ.get('PATH', '')}",
        }

        native_file = os.path.join(build_dir, "native.ini")
        with open(native_file, "w") as f:
            f.write(
                "[binaries]\n"
                f"c = '{self._get_compiler()}'\n"
                f"cpp = '{self._get_compiler('cpp')}'\n"
                "ar = '/data/service/hnp/bin/llvm-ar'\n"
                "ranlib = '/data/service/hnp/bin/llvm-ranlib'\n"
                "nm = '/data/service/hnp/bin/llvm-nm'\n"
                "pkg-config = '/data/service/hnp/bin/pkg-config'\n"
                "ninja = '/data/service/hnp/bin/ninja'\n"
                "[built-in options]\n"
                f"c_args = ['-I{gettext_prefix}/include', '-Wno-error=implicit-function-declaration']\n"
                f"c_link_args = ['-L{gettext_prefix}/lib', '-lintl', '-L/lib', '-l:ld-musl-aarch64.so.1']\n"
            )

        meson_options = [
            "--default-library=static", "-Ddaemon=false", "-Dclient=true",
            "-Ddoxygen=false", "-Dman=false", "-Dtests=false",
            "-Ddatabase=simple", "-Dglib=enabled",
            "-Dalsa=disabled", "-Dasyncns=disabled", "-Davahi=disabled",
            "-Dbluez5=disabled", "-Dconsolekit=disabled", "-Ddbus=disabled",
            "-Dfftw=disabled", "-Dgsettings=disabled", "-Dgstreamer=disabled",
            "-Dgtk=disabled", "-Djack=disabled", "-Dlirc=disabled",
            "-Dopenssl=disabled", "-Dorc=disabled", "-Doss-output=disabled",
            "-Dsoxr=disabled", "-Dspeex=disabled", "-Dsystemd=disabled",
            "-Dtcpwrap=disabled", "-Dudev=disabled", "-Dx11=disabled",
            "-Delogind=disabled", "-Dvalgrind=disabled", "-Dwebrtc-aec=disabled",
            "-Dsamplerate=disabled", "-Dbashcompletiondir=no", "-Dzshcompletiondir=no",
        ]
        self._run_meson(src, build_dir, prefix, env, native_file, meson_options)
        self._run_meson_install(build_dir, prefix)

    def _install_lxqt_build_tools(self, prefix):
        """Install lxqt-build-tools CMake modules."""
        self.output.info("Installing lxqt-build-tools CMake modules...")
        src = os.path.join(self.build_folder, "lxqt-build-tools-src")
        get(self, **self.conan_data["lxqt_build_tools"], strip_root=True, destination=src)

        cmake_dir = os.path.join(prefix, "share/cmake/lxqt2-build-tools")
        os.makedirs(cmake_dir, exist_ok=True)

        # Copy cmake modules
        shutil.copytree(
            os.path.join(src, "cmake"),
            os.path.join(cmake_dir, "cmake"),
            dirs_exist_ok=True
        )
        # Move modules to expected locations
        modules_src = os.path.join(cmake_dir, "cmake/modules")
        modules_dst = os.path.join(cmake_dir, "modules")
        find_src = os.path.join(cmake_dir, "cmake/find-modules")
        find_dst = os.path.join(cmake_dir, "find-modules")
        if os.path.exists(modules_src) and not os.path.exists(modules_dst):
            shutil.move(modules_src, modules_dst)
        if os.path.exists(find_src) and not os.path.exists(find_dst):
            shutil.move(find_src, find_dst)

        # Create config files
        with open(os.path.join(cmake_dir, "lxqt2-build-tools-config.cmake"), "w") as f:
            f.write(
                f"set(LXQTBT_VERSION 2.4.0)\n"
                "set(lxqt2-build-tools_FOUND TRUE)\n"
                "set(LXQT_BUILD_TOOLS_DIR ${CMAKE_CURRENT_LIST_DIR})\n"
                "set(LXQT_CMAKE_MODULES_DIR ${CMAKE_CURRENT_LIST_DIR}/modules)\n"
                "set(LXQT_CMAKE_FIND_MODULES_DIR ${CMAKE_CURRENT_LIST_DIR}/find-modules)\n"
                "list(APPEND CMAKE_MODULE_PATH ${LXQT_CMAKE_MODULES_DIR} ${LXQT_CMAKE_FIND_MODULES_DIR})\n"
            )
        with open(os.path.join(cmake_dir, "lxqt2-build-tools-config-version.cmake"), "w") as f:
            f.write(
                "set(PACKAGE_VERSION 2.4.0)\n"
                "if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)\n"
                "  set(PACKAGE_VERSION_COMPATIBLE FALSE)\n"
                "else()\n"
                "  set(PACKAGE_VERSION_COMPATIBLE TRUE)\n"
                "endif()\n"
            )

        # Create LXQtTranslateTs.cmake (from .cmake.in template, LinguistTools optional)
        translate_ts = os.path.join(cmake_dir, "modules/LXQtTranslateTs.cmake")
        template = os.path.join(cmake_dir, "modules/LXQtTranslateTs.cmake.in")
        with open(translate_ts, "w") as f:
            f.write(
                "find_package(Qt6 COMPONENTS LinguistTools)\n"
                "function(lxqt_translate_ts qmFiles)\n"
                "    set(oneValueArgs UPDATE_TRANSLATIONS TEMPLATE TRANSLATION_DIR INSTALL_DIR COMPONENT)\n"
                "    set(multiValueArgs SOURCES UPDATE_OPTIONS)\n"
                "    cmake_parse_arguments(TR \"${options}\" \"${oneValueArgs}\" \"${multiValueArgs}\" ${ARGN})\n"
                "    if(NOT DEFINED TR_TEMPLATE)\n"
                "        set(TR_TEMPLATE \"${PROJECT_NAME}\")\n"
                "    endif()\n"
                "    if(NOT DEFINED TR_TRANSLATION_DIR)\n"
                "        set(TR_TRANSLATION_DIR \"translations\")\n"
                "    endif()\n"
                "    get_filename_component(TR_TRANSLATION_DIR \"${TR_TRANSLATION_DIR}\" ABSOLUTE)\n"
                "    if(EXISTS \"${TR_TRANSLATION_DIR}\")\n"
                "        file(GLOB tsFiles \"${TR_TRANSLATION_DIR}/${TR_TEMPLATE}_*.ts\")\n"
                "    endif()\n"
                "    if(Qt6LinguistTools_FOUND)\n"
                "        qt6_add_translation(QM ${tsFiles})\n"
                "    else()\n"
                "        message(STATUS \"LinguistTools not found, skipping translation compilation for ${TR_TEMPLATE}\")\n"
                "        set(QM \"\")\n"
                "    endif()\n"
                "    if(DEFINED TR_INSTALL_DIR AND QM)\n"
                "        if(NOT DEFINED TR_COMPONENT)\n"
                "            set(TR_COMPONENT \"Runtime\")\n"
                "        endif()\n"
                "        install(FILES ${QM} DESTINATION \"${TR_INSTALL_DIR}\" COMPONENT \"${TR_COMPONENT}\")\n"
                "    endif()\n"
                "    set(${qmFiles} ${QM} PARENT_SCOPE)\n"
                "endfunction()\n"
            )
        # Remove the .in template
        if os.path.exists(template):
            os.unlink(template)

    def _get_compiler(self, lang="c"):
        """Get compiler path from conan config or environment."""
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        if lang == "c":
            return executables.get("c", "clang")
        return executables.get("cpp", "clang++")

    def _run_meson(self, src, build_dir, prefix, env, native_file, options):
        """Run meson setup."""
        import subprocess
        cmd = [
            "meson", "setup", build_dir, src,
            f"--prefix={prefix}",
            f"--native-file={native_file}",
        ] + options
        merged_env = {**os.environ, **env}
        result = subprocess.run(cmd, env=merged_env, capture_output=True, text=True)
        if result.returncode != 0:
            self.output.error(f"Meson setup failed:\n{result.stdout}\n{result.stderr}")
            raise Exception(f"Meson setup failed for {src}")

        # Build
        cmd = ["ninja", "-C", build_dir, "-j2"]
        result = subprocess.run(cmd, env=merged_env, capture_output=True, text=True)
        if result.returncode != 0:
            self.output.error(f"Ninja build failed:\n{result.stdout}\n{result.stderr}")
            raise Exception(f"Ninja build failed for {src}")

    def _run_meson_install(self, build_dir, prefix):
        """Run meson install."""
        import subprocess
        cmd = ["meson", "install", "-C", build_dir, "--destdir=/"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.output.warn(f"Meson install had issues:\n{result.stdout}\n{result.stderr}")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # pavucontrol-qt is a GUI application, not a library
        self.cpp_info.set_property("cmake_file_name", "pavucontrol-qt")
        self.cpp_info.set_property("pkg_config_name", "pavucontrol-qt")
