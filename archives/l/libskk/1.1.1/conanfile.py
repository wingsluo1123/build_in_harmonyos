#!/usr/bin/env python3
"""Conan recipe for libskk 1.1.1."""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibskkConan(ConanFile):
    name = "libskk"
    version = "1.1.1"
    description = "GObject-based Japanese kana-kanji conversion library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/ueno/libskk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libskk is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration(
                "OHOS registry GLib/libgee artifacts include static GLib copies; "
                "build libskk as a static archive to avoid duplicate GType registration"
            )

    def requirements(self):
        # These are hard configure.ac requirements. Mark their headers and link
        # interfaces transitive because libskk's public header uses GObject types.
        self.requires("glib/2.84.0", transitive_headers=True, transitive_libs=True)
        self.requires("libgee/0.20.8.2", transitive_headers=True, transitive_libs=True)
        self.requires("json-glib/1.6.6", transitive_headers=True, transitive_libs=True)
        self.requires("libxkbcommon/1.6.0", transitive_headers=True, transitive_libs=True)
        # The upstream external gettext mode needs the target libintl runtime
        # to keep NLS enabled and link the translation lookup functions.
        self.requires("libintl/0.26.1", transitive_libs=True)

    def build_requirements(self):
        # The official release archive includes configure and generated Makefiles.
        # gettext is used only for msgfmt when the bundled NLS catalog is rebuilt.
        self.tool_requires("gettext/0.22.5.1")
        self.tool_requires("vala/0.56.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename=f"libskk-{self.version}.tar.xz",
            strip_root=True,
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        self._prepare_libtool_overlay()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend([
            "--disable-fep",
            "--disable-docs",
            "--disable-introspection",
        ])
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        toolchain.generate()

        build_env = VirtualBuildEnv(self)
        self._prepare_build_environment(build_env)
        build_env.generate()
        VirtualRunEnv(self).generate()

    def _prepare_build_environment(self, build_env):
        env = build_env.environment()
        gettext = self.dependencies.build["gettext"]
        libintl = self.dependencies.host["libintl"]
        gettext_bin = os.path.join(gettext.package_folder, "bin")
        gettext_include = os.path.join(gettext.package_folder, "include")
        gettext_lib = os.path.join(gettext.package_folder, "lib")
        libintl_lib = os.path.join(libintl.package_folder, "lib")
        if not os.path.isfile(os.path.join(gettext_bin, "msgfmt")):
            raise ConanInvalidConfiguration(
                "gettext/0.22.5.1 build tool package does not contain bin/msgfmt"
            )
        if (
            not os.path.isfile(os.path.join(gettext_include, "libintl.h"))
            or not os.path.isdir(gettext_lib)
            or not os.path.isfile(os.path.join(libintl_lib, "libintl.so.8"))
        ):
            raise ConanInvalidConfiguration(
                "gettext/0.22.5.1 or libintl/0.26.1 is missing the required build files/libraries"
            )
        # gettext's package does not export these paths through buildenv_info.
        # Add msgfmt and its runtime paths explicitly so the bundled Japanese
        # catalog remains buildable when gettext tools are absent from system PATH.
        env.prepend_path("PATH", gettext_bin)
        env.prepend("CPPFLAGS", "-I" + gettext_include)
        env.prepend("LDFLAGS", "-L" + libintl_lib)
        env.prepend("LIBS", "-lintl")
        host_lib_dirs = self._dependency_paths(("lib", "lib64"))
        if host_lib_dirs:
            env.prepend_path("LD_LIBRARY_PATH", os.pathsep.join(host_lib_dirs))
        env.prepend_path("LD_LIBRARY_PATH", gettext_lib)
        # Put the combined libintl shim first: shared GLib in the platform
        # packages also needs its g_libintl_* symbols at tool runtime.
        env.prepend_path("LD_LIBRARY_PATH", libintl_lib)
        pkg_config_dirs = self._dependency_paths((
            "lib/pkgconfig",
            "lib64/pkgconfig",
            "share/pkgconfig",
        ))
        if pkg_config_dirs:
            # Keep PkgConfigDeps' generated .pc files first; the platform
            # packages provide additional modules such as gio-2.0.pc.
            env.append_path("PKG_CONFIG_PATH", os.pathsep.join(pkg_config_dirs))
        return env

    def _dependency_paths(self, relative_paths):
        paths = []
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for relative in relative_paths:
                path = os.path.join(dependency.package_folder, relative)
                if os.path.isdir(path) and path not in paths:
                    paths.append(path)
        return paths

    def _prepare_libtool_overlay(self):
        """Create local library wrappers for platform packages with broken .la paths."""
        overlay = os.path.join(self.build_folder, "libtool-dependencies")
        os.makedirs(overlay, exist_ok=True)
        library_names = []

        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            libdir = os.path.join(dependency.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for filename in os.listdir(libdir):
                if not filename.endswith(".la"):
                    continue
                source = os.path.join(libdir, filename)
                with open(source, "r", encoding="utf-8") as archive:
                    content = archive.read()
                # The platform Conan artifacts are staged with prefix=/, so
                # their libtool archives can point at //lib and at a different
                # Conan home. The generated pkg-config files already provide
                # transitive link flags; the wrapper and its referenced
                # libraries live in the local overlay for this build only.
                content = re.sub(
                    r"^dependency_libs=.*$", "dependency_libs=''", content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r"^libdir='[^']*'$", f"libdir='{overlay}'", content,
                    flags=re.MULTILINE,
                )
                for variable in ("dlname", "library_names", "old_library"):
                    match = re.search(
                        rf"^{variable}='([^']*)'$", content, flags=re.MULTILINE
                    )
                    if not match:
                        continue
                    for library in shlex.split(match.group(1)):
                        source_library = os.path.join(libdir, library)
                        if not os.path.isfile(source_library):
                            continue
                        overlay_library = os.path.join(overlay, library)
                        if os.path.lexists(overlay_library):
                            os.remove(overlay_library)
                        if os.path.islink(source_library):
                            os.symlink(os.path.realpath(source_library), overlay_library)
                        else:
                            shutil.copy2(source_library, overlay_library)
                with open(os.path.join(overlay, filename), "w", encoding="utf-8") as archive:
                    archive.write(content)
                library_name = filename[:-3]
                if library_name.startswith("lib"):
                    library_name = library_name[3:]
                library_names.append(library_name)

        if not library_names:
            return

        for root, _, filenames in os.walk(self.build_folder):
            if os.path.abspath(root).startswith(os.path.abspath(overlay)):
                continue
            for filename in filenames:
                if not filename.endswith(".pc"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as pkgconfig:
                    lines = pkgconfig.readlines()
                changed = False
                for index, line in enumerate(lines):
                    if not line.startswith("Libs:"):
                        continue
                    if any(f"-l{name}" in line for name in library_names):
                        lines[index] = line.replace("Libs:", f"Libs: -L{overlay}", 1)
                        changed = True
                if changed:
                    with open(path, "w", encoding="utf-8", newline="\n") as pkgconfig:
                        pkgconfig.writelines(lines)

        deps_script = os.path.join(self.build_folder, "conan", "conanautotoolsdeps.sh")
        if not os.path.isfile(deps_script):
            raise ConanInvalidConfiguration("AutotoolsDeps environment script was not generated")
        with open(deps_script, "r", encoding="utf-8") as generated:
            content = generated.read()
        marker = 'export LDFLAGS="${LDFLAGS:-}${LDFLAGS:+ }'
        if content.count(marker) != 1:
            raise ConanInvalidConfiguration("Could not prepend the local libtool overlay to LDFLAGS")
        content = content.replace(
            marker,
            f'export LDFLAGS="-L{overlay} ${{LDFLAGS:-}}${{LDFLAGS:+ }}',
            1,
        )
        with open(deps_script, "w", encoding="utf-8", newline="\n") as generated:
            generated.write(content)
        self.output.info(
            f"Created temporary libtool wrappers for host package archives in {overlay}"
        )

    def _fix_config_status_temp_umask(self):
        """Keep Autoconf temp dirs writable by the device's shared build group."""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8") as generated:
            content = generated.read()

        patterns = (
            '(umask 077 && mktemp -d "./confXXXXXX")',
            '(umask 077 && mkdir "$tmp")',
        )
        changed = 0
        for pattern in patterns:
            if pattern in content:
                content = content.replace(pattern, pattern.replace("077", "007"))
                changed += 1
        if changed == 0:
            if all(pattern.replace("077", "007") in content for pattern in patterns):
                return
            raise ConanInvalidConfiguration(
                "Autoconf temporary-directory setup did not match the tested pattern"
            )
        if changed != len(patterns):
            raise ConanInvalidConfiguration(
                "Autoconf temporary-directory setup only partially matched"
            )
        with open(configure, "w", encoding="utf-8", newline="\n") as generated:
            generated.write(content)
        self.output.info("Adjusted Autoconf temp dir umask for the shared device build group")

    def _vala_assignment(self):
        """Add Conan dependency VAPI directories to upstream Vala flags."""
        vapi_dirs = []
        # The library VAPI is generated during the first make pass; the later
        # tools/ target needs it from the out-of-tree build's libskk directory.
        vapi_dirs.append(os.path.join(self.build_folder, "libskk"))
        source_vapi_dir = os.path.join(self.source_folder, "libskk")
        if os.path.isdir(source_vapi_dir):
            # config.vapi and xkbcommon.vapi are shipped by upstream. The
            # out-of-tree generated Makefile build runs valac from build-release/libskk,
            # so its upstream --vapidir=. does not point at the source files.
            vapi_dirs.append(source_vapi_dir)
        dependencies = list(self.dependencies.host.values()) + list(self.dependencies.build.values())
        for dependency in dependencies:
            if not dependency.package_folder:
                continue
            for relative in (
                "share/vala/vapi",
                "share/vala-0.56/vapi",
                "share/vala-0.56.19/vapi",
            ):
                directory = os.path.join(dependency.package_folder, relative)
                if os.path.isdir(directory) and directory not in vapi_dirs:
                    vapi_dirs.append(directory)
        # tools/skk.vala directly uses Gee, but generated Makefile's skk-1.0 package
        # resolution does not load the source .deps file in this out-of-tree build.
        flags = "--pkg=gee-0.8 " + " ".join(
            "--vapidir=" + directory for directory in vapi_dirs
        )
        return "VALAFLAGS=" + shlex.quote(flags)

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "The official libskk 1.1.1 release archive must provide configure"
            )
        apply_conandata_patches(self)
        self._fix_config_status_temp_umask()

        build_env = VirtualBuildEnv(self)
        env = self._prepare_build_environment(build_env)
        autotools = Autotools(self)
        jobs = max(1, self.conf.get("tools.build:jobs", default=1, check_type=int) or 1)
        # Use the release archive's generated configure and Makefiles directly.
        with env.vars(self).apply():
            autotools.configure()
            autotools.make(args=[f"-j{jobs}", self._vala_assignment()])
        # Verbose GLib test output makes the registered case count auditable.
        self.run(
            f"G_TEST_VERBOSE=1 make -j{jobs} check V=1",
            env=["conanbuild", "conanrun"],
        )

    def package(self):
        Autotools(self).install()
        # Do not ship libtool's build-time wrapper in the Conan package.
        for directory, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                if filename.endswith(".la"):
                    os.remove(os.path.join(directory, filename))

    def package_info(self):
        self.cpp_info.libs = ["skk"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libskk")
        self.cpp_info.set_property("cmake_target_name", "libskk::libskk")
        self.cpp_info.set_property("pkg_config_name", "skk-1.0")
        self.runenv_info.append_path(
            "LIBSKK_DATA_PATH", os.path.join(self.package_folder, "share", "libskk")
        )
