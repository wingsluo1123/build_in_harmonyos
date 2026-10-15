#!/usr/bin/env python3
"""Conan recipe — obs 32.1.2 (CMake).

OBS Studio is a Qt/FFmpeg live-streaming and recording application. This recipe
builds its core library stack for HarmonyOS PC (aarch64) rather than the
desktop GUI application:

  libobs             — the OBS engine (obs-video/audio, sources, encoders,
                       outputs, properties, data serialisation, plugin ABI)
  libobs-opengl      — the OpenGL/EGL renderer backend (loaded at runtime)
  obs-frontend-api   — the plugin-facing frontend API library
  share/obs/libobs/* — the .effect shaders libobs needs at runtime

Why the GUI frontend and the bundled plugins are disabled here:

  OBS's Linux desktop build assumes an X11/Wayland desktop stack for the Qt
  frontend, for the screen-capture plugins and for the OpenGL context. The
  OHOS PC build environment exposes the aarch64-linux-ohos ABI and a GLES/EGL
  stack (gl4es supplies the desktop-GL entry points libobs-opengl links
  against), but no X11/Wayland desktop session, no libv4l2 and no CEF, and the
  GitHub release tarball ships the obs-browser / obs-websocket submodules as
  empty placeholders. The engine and its renderer build and self-test cleanly
  on that surface, so the adaptation stops there.

OHOS adaptation (see patches/):

  1. cmake/common/osconfig.cmake — OBS branches on CMAKE_HOST_SYSTEM_NAME.
     The HarmonyOS kernel reports "HarmonyOS", which matches no upstream
     branch, so include(defaults)/include(compilerconfig)/include(helpers)
     (all resolved through cmake/linux) aborted configure. HarmonyOS PC uses
     the aarch64-linux-ohos ABI, so it is mapped onto the Linux module set.
     The recipe also pins CMAKE_SYSTEM_NAME=Linux so the generator expressions
     OBS uses everywhere ($<PLATFORM_ID:Linux,...>) select the Linux sources;
     without it CMake would default CMAKE_SYSTEM_NAME to the host's
     "HarmonyOS" and silently drop them.

  2. libobs/util/threading-posix.c — os_set_thread_name() only had
     __APPLE__/__FreeBSD__/__GLIBC__ branches; musl-based OHOS defines none of
     them, so the function was an empty stub (and tripped -Werror). OHOS
     exports pthread_setname_np(pthread_t, const char *) with the glibc
     signature, so __OHOS__ joins that branch.

  3. CMakeLists.txt — upstream never adds test/, so test/cmocka (the four
     cmocka unit tests that link OBS::libobs) was unreachable. They are wired
     in under ENABLE_UNIT_TESTS and executed with ctest during build().

Upstream test suite (test/cmocka, cmocka framework, CTest-registered):
  test_serializer, test_darray, test_bitstream, test_os_path — 4 tests, all
  executed by build() via ctest and reported in test_package/MANIFEST.yml.

The test_package adds a consumer-side test that is specific to this platform
port: it exercises the __OHOS__ branch added above by round-tripping a thread
name through os_set_thread_name()/pthread_getname_np(), and additionally
checks the libobs version string and a obs_data JSON round-trip.

Toolchain notes:

  * OBS resolves dependencies with its own CMake find modules (FindFFmpeg,
    FindUthash, Findjansson, FindSIMDe, FindLibdrm, plus CMake's FindX11).
    Conan's CMakeToolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, which
    bypasses all of them and leaves the expected OBS::/Uthash::/Libdrm::
    import targets undefined, so the recipe flips it back to OFF.
  * find_package(X11_XCB)/find_package(XCB) are provided by ECM's
    find-modules (extra-cmake-modules), and conan's generated ECMConfig.cmake
    does not set ECM_MODULE_PATH — the recipe points ECM_MODULE_PATH at the
    package's share/ECM/find-modules so cmake/linux/ecmconfig.cmake can pick
    up FindX11_XCB.cmake / FindXCB.cmake.
  * The X11 and libdrm headers live in separate conan packages (xorgproto,
    libdrm), so their include directories are added explicitly.
  * libuuid lives in the conan cache rather than /usr/include, so the
    uuid/uuid.h probe in cmake/os-linux.cmake is pointed at it through
    CMAKE_REQUIRED_INCLUDES.
  * OpenGL is satisfied by gl4es (the repo's desktop-GL-over-GLES layer) for
    deps/glad.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    copy,
    get,
    save,
    apply_conandata_patches,
    export_conandata_patches,
)


class ObsConan(ConanFile):
    name = "obs"
    version = "32.1.2"
    description = ("OBS Studio core: libobs engine, OpenGL renderer and "
                   "obs-frontend-api (HarmonyOS PC, aarch64)")
    license = "GPL-2.0-or-later"
    homepage = "https://obsproject.com/"
    url = "https://github.com/obsproject/obs-studio"
    topics = ("obs", "video", "streaming", "recording", "multimedia")

    # libobs/libobs-opengl are declared SHARED by upstream CMake; the build is
    # always shared, so no `shared` option is exposed.
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    # The release tarball ships symlinks (.github/scripts/build-macos,
    # build-aux/run-clang-format, ...). Copying sources into the build folder
    # fails to reproduce their metadata on HMDFS (chmod on a symlink is not
    # permitted), so build out of the extracted source tree directly. OBS
    # forbids in-source builds and cmake_layout keeps the build folder
    # separate, so this stays out-of-source.
    no_copy_source = True

    # CMakeDeps: modern targets for deps OBS finds on its own terms.
    # PkgConfigDeps: FFmpeg/X11/libdrm .pc files (OBS's finders also probe
    #   pkg-config). VirtualBuildEnv/VirtualRunEnv: PKG_CONFIG_PATH and the
    #   runtime library path for the ctest step.
    generators = "CMakeDeps", "PkgConfigDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ffmpeg/7.1.5")                 # libavformat/avcodec/avutil/swscale/swresample
        # obs.h -> graphics/vec3.h -> util/sse-intrin.h -> <simde/x86/sse2.h>,
        # so consumers of the public headers need simde transitively.
        self.requires("simde/0.8.4-rc3", transitive_headers=True)
        self.requires("zlib/1.3.1.1")
        self.requires("uthash/2.4.0")                 # hash tables for the plugin API
        self.requires("jansson/2.15.1.1")             # obs_data JSON backend
        self.requires("libuuid/2.42.2")               # os-linux.cmake requires uuid/uuid.h
        self.requires("libx11/1.8.13.1")              # X11 platform selection in libobs
        self.requires("libxcb/1.17.0.1")
        self.requires("xorgproto/2025.1")             # X11/X.h for the libX11 headers
        self.requires("libdrm/2.4.133")               # gl-egl-common.c
        self.requires("gl4es/1.1.6")                  # desktop GL over GLES for deps/glad
        self.requires("extra-cmake-modules/6.29.0")   # FindX11_XCB.cmake / FindXCB.cmake
        self.requires("cmocka/2.0.2")                 # upstream unit tests

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _include_dirs(self, dep):
        """Absolute include directories contributed by a dependency."""
        dirs = []
        components = [dep.cpp_info] + list(dep.cpp_info.components.values())
        for component in components:
            for inc in component.includedirs:
                full = os.path.join(dep.package_folder, inc)
                if os.path.isdir(full) and full not in dirs:
                    dirs.append(full)
        return dirs

    def _dependency_lib_dirs(self):
        """Absolute library directories of every package in the graph.

        CMAKE_SKIP_RPATH is on, so libobs' runtime dependencies (FFmpeg, X11,
        jansson, ...) have to come from the loader search path when the unit
        tests run.
        """
        dirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                full = libdir if os.path.isabs(libdir) \
                    else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(full) and full not in dirs:
                    dirs.append(full)
        return dirs

    def generate(self):
        tc = CMakeToolchain(self)

        # OBS keys its OS_* variables off CMAKE_HOST_SYSTEM_NAME and its source
        # selection off CMAKE_SYSTEM_NAME/PLATFORM_ID. The HarmonyOS kernel
        # reports "HarmonyOS" for both unless told otherwise; the target ABI is
        # aarch64-linux-ohos, so pin the CMake target system to Linux and let
        # patch 0002 map the HarmonyOS host onto OS_LINUX.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # NOTE: OBS_VERSION_OVERRIDE is deliberately *not* set here. OBS's
        # top-level CMakeLists includes cmake/common/bootstrap.cmake (and with
        # it versionconfig.cmake, which resolves the version) at line 3, before
        # its first project() call - and CMake only reads the toolchain file at
        # project() time, so toolchain cache variables are not visible yet.
        # The override is passed as a command-line -D in build() instead; the
        # release tarball has no .git, so without it OBS falls back to its
        # 0.0.1 default and the library reports the wrong version string.

        # Scope: engine + renderer + frontend API. The Qt frontend and the
        # plugin set need the X11/Wayland desktop stack, CEF and the
        # obs-browser/obs-websocket submodules, none of which exist here.
        tc.variables["ENABLE_UI"] = "OFF"
        tc.variables["ENABLE_FRONTEND"] = "OFF"
        tc.variables["ENABLE_PLUGINS"] = "OFF"
        tc.variables["ENABLE_SCRIPTING"] = "OFF"
        tc.variables["ENABLE_PULSEAUDIO"] = "OFF"
        tc.variables["ENABLE_WAYLAND"] = "OFF"

        # Build and run the upstream cmocka suite (test/cmocka) via ctest.
        tc.variables["ENABLE_UNIT_TESTS"] = "ON"
        tc.variables["BUILD_TESTS"] = "OFF"

        # CMake writes a build-tree RPATH into every shared object and strips
        # it again at install time by editing the ELF in place. The OHOS loader
        # rejects the rewritten file with EACCES ("Permission denied") even
        # though the file stays a well-formed ELF - the build-tree copy loads,
        # the installed copy does not. Skipping RPATH entirely avoids both the
        # build-time write and the install-time rewrite. Consumers locate the
        # libraries through the normal conan run environment.
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"

        # ECM find-modules provide FindX11_XCB.cmake / FindXCB.cmake, which
        # cmake/linux/ecmconfig.cmake picks up via ECM_MODULE_PATH. Conan's
        # generated ECMConfig.cmake does not set that variable, so the recipe
        # supplies it (and also appends the directory to CMAKE_MODULE_PATH
        # directly in the toolchain - see the save() below).
        ecm = self.dependencies["extra-cmake-modules"]
        ecm_find_modules = os.path.join(
            ecm.package_folder, "share", "ECM", "find-modules")
        if not os.path.isdir(ecm_find_modules):
            raise ConanInvalidConfiguration(
                f"{ecm.ref} does not provide share/ECM/find-modules; "
                "FindX11_XCB.cmake / FindXCB.cmake are required by "
                "libobs/cmake/os-linux.cmake")
        tc.variables["ECM_MODULE_PATH"] = ecm_find_modules

        # CMake's FindX11 and OBS's FindLibdrm do not know about the split
        # xorgproto / libdrm include locations under the conan cache.
        extra_includes = []
        for ref in ("xorgproto", "libdrm"):
            for inc in self._include_dirs(self.dependencies[ref]):
                flag = f"-I{inc}"
                if flag not in extra_includes:
                    extra_includes.append(flag)
        if extra_includes:
            tc.extra_cflags.extend(extra_includes)
            tc.extra_cxxflags.extend(extra_includes)

        # cmake/os-linux.cmake probes <uuid/uuid.h> with check_c_source_compiles.
        uuid_incs = self._include_dirs(self.dependencies["libuuid"])
        if uuid_incs:
            tc.variables["CMAKE_REQUIRED_INCLUDES"] = ";".join(uuid_incs)

        # gl4es stands in for desktop OpenGL (deps/glad calls
        # find_package(OpenGL REQUIRED)).
        gl4es = self.dependencies["gl4es"]
        tc.variables["OpenGL_GL_PREFERENCE"] = "LEGACY"
        tc.variables["OPENGL_gl_LIBRARY"] = os.path.join(
            gl4es.package_folder, "lib", "libGL.so")
        tc.variables["OPENGL_INCLUDE_DIR"] = os.path.join(
            gl4es.package_folder, "include")

        # Upstream test/cmocka/CMakeLists.txt reads ${CMOCKA_INCLUDE_DIR} and
        # ${CMOCKA_LIBRARIES}; conan's cmocka config only defines the lowercase
        # cmocka_* spelling.
        cmocka = self.dependencies["cmocka"]
        tc.variables["CMOCKA_INCLUDE_DIR"] = os.path.join(
            cmocka.package_folder, "include")
        tc.variables["CMOCKA_LIBRARIES"] = os.path.join(
            cmocka.package_folder, "lib", "libcmocka.a")

        tc.generate()

        # CMakeToolchain forces CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, which
        # makes find_package() resolve the conan config packages instead of the
        # find modules OBS ships (cmake/finders) and would leave
        # Uthash::Uthash / Libdrm::Libdrm / XCB::XCB undefined. The block is
        # emitted by the toolchain, so the override has to follow it.
        save(self,
             os.path.join(self.generators_folder, "conan_toolchain.cmake"),
             "\n# OBS resolves dependencies with its own find modules: keep\n"
             "# module-mode find_package() ahead of conan's config packages.\n"
             "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n"
             "\n# cmake/linux/ecmconfig.cmake appends ${ECM_MODULE_PATH}, but that\n"
             "# variable travelled through the toolchain cache and did not reach\n"
             "# CMAKE_MODULE_PATH on the CI worker, so `find_package(X11_XCB)`\n"
             "# could not see ECM's FindX11_XCB.cmake. Put the directory on the\n"
             "# module path directly - the toolchain is read at project() time,\n"
             "# which is before every find_package() in this project.\n"
             f'list(APPEND CMAKE_MODULE_PATH "{ecm_find_modules}")\n',
             append=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # -D (not a toolchain variable): see the note in generate().
        cmake.configure(cli_args=[f"-DOBS_VERSION_OVERRIDE={self.version}"])
        cmake.build()

        # Upstream unit tests, registered with CTest by patch 0001.
        lib_dirs = [
            os.path.join(self.build_folder, "libobs"),
            os.path.join(self.build_folder, "libobs-opengl"),
        ] + self._dependency_lib_dirs()

        env = Environment()
        env.define("LD_LIBRARY_PATH", ":".join(lib_dirs))
        with env.vars(self).apply():
            self.run(f'ctest --test-dir "{self.build_folder}" '
                     f'--output-on-failure --timeout 300')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # libobs is the consumer-facing library; libobs-opengl is the renderer
        # module libobs dlopen()s at runtime and is shipped in the package but
        # intentionally not put on the link line.
        self.cpp_info.libs = ["obs"]
        self.cpp_info.includedirs = ["include/obs"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "libobs")
        self.cpp_info.set_property("cmake_target_name", "OBS::libobs")
        self.cpp_info.set_property("pkg_config_name", "libobs")
