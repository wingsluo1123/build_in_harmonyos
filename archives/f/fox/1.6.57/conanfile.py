#!/usr/bin/env python3
"""Conan recipe for the FOX C++ GUI Toolkit (Free Objects for X).

FOX installs three artefacts from one build:

* ``libFOX-1.6``          — the GUI toolkit shared library (headers in
                            ``include/fox-1.6``).
* ``bin/reswrap``         — upstream's resource compiler, required by every
                            downstream FOX application (rezound among them) to
                            turn ``.xpm``/``.gif``/``.png`` files into C++
                            sources at build time.
* ``bin/fox-config``      — the upstream build-configuration helper.

X11 stack note: the OHOS registry publishes ``libxext/6.4.0.1`` (upstream
libXext 1.8.10 era) which pins ``libx11/6.4.0``, while the Xft/Xcursor/Xrender/
Xrandr/Xfixes/XInput packages published today all pin ``libx11/1.8.13``.  Both
stacks cannot be co-installed in one dependency graph, and ``libxext/1.3.7``
(the libX11 1.8.x counterpart) is not published yet, so this recipe stays on
the libX11 6.4.0 stack and disables the extras that live on the other one.
FOX keeps full functionality on core X11 + Xext (SHM, Shape) and the image
formats it detects below.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Extensions FOX probes for and enables when their headers are reachable.  All
# of them arrive with the libX11 1.8.x stack, so they are switched off
# explicitly to keep the build deterministic instead of relying on the absence
# of host headers inside the OHOS sysroot.
DISABLED_X_EXTRAS = (
    "--without-xft",
    "--without-xcursor",
    "--without-xrender",
    "--without-xrandr",
    "--without-xfixes",
    "--without-xinput",
    "--without-opengl",
)


class FoxConan(ConanFile):
    name = "fox"
    version = "1.6.57"
    description = (
        "FOX is a C++ based Toolkit for developing Graphical User Interfaces "
        "easily and effectively"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://www.fox-toolkit.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Core: FOX always links -lX11 -lXext and needs their headers.
        self.requires("libx11/6.4.0", transitive_headers=True)
        self.requires("libxext/6.4.0.1", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        # Image formats FOX auto-detects through AC_CHECK_HEADERS.
        self.requires("libpng/1.6.58", transitive_headers=True)
        self.requires("libjpeg-turbo/3.2.0", transitive_headers=True)
        self.requires("libtiff/4.7.2", transitive_headers=True)
        # zlib is both a direct FOX dependency (compressed resources) and a
        # libpng/libtiff one, so it is pinned to the version libpng/1.6.58
        # requires to keep a single zlib in the graph.
        self.requires("zlib/1.3.1.1", transitive_headers=True)
        self.requires("bzip2/1.0.8", transitive_headers=True)

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports the armv8 (aarch64) OHOS target, "
                f"got {self.settings.arch}"
            )

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly (accountsservice pattern).
        source_data = self.conan_data["sources"][self.version]
        get(
            self,
            url=source_data["url"],
            sha256=source_data["sha256"],
            strip_root=True,
        )

    def generate(self):
        if str(self.settings.os) != "OHOS":
            AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-static" if self.options.shared else "--enable-static",
                "--enable-shared" if self.options.shared else "--disable-shared",
                *DISABLED_X_EXTRAS,
            ]
        )
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-linux-ohos",
                    "--host=aarch64-linux-ohos",
                ]
            )

        env = tc.environment()
        # configure.ac calls AC_C_BIGENDIAN for FOX_BYTEORDER.  The probe either
        # runs a target binary (impossible while cross building) or has to guess
        # from headers, so state the answer for aarch64 instead.
        env.define("ac_cv_c_bigendian", "no")
        if str(self.settings.os) == "OHOS":
            self._add_dependency_search_paths(tc, env)
            deps_include, deps_library = self._stage_dependency_prefix()
            # configure.ac:82 runs AC_PATH_X/AC_PATH_XTRA, which take exactly one
            # include and one library directory and otherwise search a fixed list
            # of system paths only, so the X11 stack from the conan cache is
            # invisible to them unless it is handed over through these options.
            tc.configure_args.extend(
                [
                    f"--x-includes={deps_include}",
                    f"--x-libraries={deps_library}",
                ]
            )
            env.append("CPPFLAGS", f"-I{deps_include}")
            env.append("LDFLAGS", f"-L{deps_library}")
            tc.extra_ldflags.append(f"-L{deps_library}")
            self._add_runtime_library_paths(env)
        tc.generate(env)

    def _add_dependency_search_paths(self, toolchain, environment):
        """Hand configure the dependency search paths (libx11 pattern).

        AutotoolsDeps puts every transitive library into LIBS, which makes
        configure's trivial "can we run it" probe link against shared libraries
        that live in the conan cache - the loader cannot find them, the probe
        exits non-zero and configure dies with "cannot run C compiled programs".
        FOX probes each library itself with AC_CHECK_LIB/AC_CHECK_HEADERS and
        appends the matching -l to its own Makefiles, so -I/-L are all it needs.
        """
        for _, dependency in self.dependencies.items():
            folder = dependency.package_folder
            if not folder:
                continue
            for include_dir in dependency.cpp_info.includedirs or ["include"]:
                path = include_dir if os.path.isabs(include_dir) else os.path.join(folder, include_dir)
                if os.path.isdir(path):
                    # configure.ac:60 resets CXXFLAGS to "", so the include paths
                    # have to travel in CPPFLAGS, which configure leaves alone.
                    environment.append("CPPFLAGS", f"-I{path}")
            for lib_dir in dependency.cpp_info.libdirs or ["lib"]:
                path = lib_dir if os.path.isabs(lib_dir) else os.path.join(folder, lib_dir)
                if os.path.isdir(path):
                    toolchain.extra_ldflags.append(f"-L{path}")

    def _stage_dependency_prefix(self):
        """Mirror the dependencies' headers and libraries into one private prefix.

        The tree lives in the build folder and contains symlinks only, so a build
        never writes into a shared system prefix.  It exists because
        AC_PATH_X/AC_PATH_XTRA accept a single directory for headers and a single
        one for libraries, while the X11 stack is spread over libx11, xorgproto,
        libxext and friends.
        """
        root = os.path.join(self.build_folder, "deps-prefix")
        include_root = os.path.join(root, "include")
        library_root = os.path.join(root, "lib")
        os.makedirs(include_root, exist_ok=True)
        os.makedirs(library_root, exist_ok=True)
        for _, dependency in self.dependencies.items():
            folder = dependency.package_folder
            if not folder:
                continue
            for include_dir in dependency.cpp_info.includedirs or ["include"]:
                source = include_dir if os.path.isabs(include_dir) else os.path.join(folder, include_dir)
                self._link_tree(source, include_root)
            for lib_dir in dependency.cpp_info.libdirs or ["lib"]:
                source = lib_dir if os.path.isabs(lib_dir) else os.path.join(folder, lib_dir)
                if not os.path.isdir(source):
                    continue
                for name in os.listdir(source):
                    self._link_file(os.path.join(source, name), os.path.join(library_root, name))
        return include_root, library_root

    @staticmethod
    def _link_tree(source, destination_root):
        """Link every file below `source` into `destination_root`, keeping the layout.

        Linking the directory itself is not enough: X11 headers are spread over
        several packages that all have to contribute files to the same X11/ tree.
        """
        if not os.path.isdir(source):
            return
        for current, _, files in os.walk(source):
            relative = os.path.relpath(current, source)
            destination = destination_root if relative == "." else os.path.join(destination_root, relative)
            os.makedirs(destination, exist_ok=True)
            for name in files:
                FoxConan._link_file(os.path.join(current, name), os.path.join(destination, name))

    @staticmethod
    def _link_file(source, destination):
        """Link `source` to `destination`, keeping the first package that provides it."""
        if os.path.exists(destination) or os.path.islink(destination):
            return
        os.symlink(source, destination)

    def _add_runtime_library_paths(self, environment):
        # Programs built here (reswrap, the example applications) load the X11
        # stack from the conan cache, which is not on the default search path.
        for _, dependency in self.dependencies.items():
            folder = dependency.package_folder
            if not folder:
                continue
            for lib_dir in dependency.cpp_info.libdirs or ["lib"]:
                path = lib_dir if os.path.isabs(lib_dir) else os.path.join(folder, lib_dir)
                if os.path.isdir(path):
                    environment.prepend_path("LD_LIBRARY_PATH", path)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        autotools = Autotools(self)
        autotools.install()
        # libtool archives record build-machine paths and are not consumed by
        # conan, so they are dropped from the package.  fox.pc and fox-config are
        # kept: downstream autotools projects (rezound uses AX_PATH_GENERIC)
        # discover the toolkit through them.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "fox")
        self.cpp_info.libs = ["FOX-1.6"]
        # Upstream installs the public headers under <prefix>/include/fox-1.6 and
        # compiles with -I<prefix>/include/fox-1.6, so <fx.h> and friends are
        # reachable from the default include path.
        self.cpp_info.includedirs = ["include/fox-1.6"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "xorgproto::xorgproto",
            "libpng::libpng",
            "libjpeg-turbo::libjpeg-turbo",
            "libtiff::libtiff",
            "zlib::zlib",
            "bzip2::bzip2",
        ]
