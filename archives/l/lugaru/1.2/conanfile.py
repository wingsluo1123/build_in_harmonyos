#!/usr/bin/env python3
"""Conan recipe for lugaru 1.2 on HarmonyOS PC (OHOS / aarch64 / musl / libc++).

Lugaru is the 3D action game Wolfire Games open sourced in 2010; this recipe
tracks the community continuation at gitlab.com/osslugaru/lugaru, tag 1.2
(2017-02-11, commit c7b99378439735c60f84869b05c6ebde53083667).  Upstream
ships a CMake build and needs SDL2 + desktop OpenGL + OpenAL + PNG/JPEG and
Ogg/Vorbis.

OHOS adaptation points
----------------------
1. OpenGL provider.  OHOS has neither desktop GL/GLX nor an `opengl` Conan
   package (`conan download --only-recipe opengl/4.6` against the configured
   remote -> recipe not published).  Lugaru is a plain **fixed-function GL 1.x** renderer
   (glBegin/glEnd/glMatrixMode/glVertex3f/glOrtho/glColor4f ... see
   Source/Graphic/gamegl.hpp) plus one GLU call (gluPerspective, in
   Source/GameInitDispose.cpp), so linking straight against the system
   GLESv2/EGL is not an option: GLES2 exposes no fixed-function entry points
   and no GLU.  The OHOS stack for legacy GL is gl4es/1.1.6 (libGL.so, GL 1.x
   emulated over GLES) - the same choice critter/2.0.4 and logstalgia/1.1.4
   made.  FindOpenGL is therefore pinned onto the gl4es provider by seeding
   OPENGL_gl_LIBRARY/OPENGL_INCLUDE_DIR; GLU comes from glu/9.0.3
   (libGLU.so exports gluPerspective; gl4es' own libGL.so does not, even though
   gl4es does install include/GL/glu.h).  glu/9.0.3 declares
   cpp_info.requires=["mesa::mesa"], so mesa/24.3.4.1 joins the graph
   transitively - do not pin mesa/24.3.4.1.1.1 by hand, that version's X11
   closure has no prebuilt binary for this profile (libxrender/0.9.12).
2. CMake 4.x.  Upstream declares `cmake_minimum_required(VERSION 3.0)`, which
   CMake >= 4 rejects ("Compatibility with CMake < 3.5 has been removed").
   patches/0001 bumps the floor to 3.5 (the same fix gl4es/1.1.6 needed).
3. C++ standard.  The profile pins compiler.cppstd=17, and conan's
   CMAKE_CXX_STANDARD=17 standard flag is appended *after* CMAKE_CXX_FLAGS by
   CMake, so upstream's own `--std=gnu++11` cannot win however it is
   concatenated (verified: the compile line ends with `... --std=gnu++11
   -O3 -DNDEBUG -std=c++17`).  Source/Math/XYZ.hpp declares
   `fast_sqrt(register float)` and clang rejects `register` outright in C++17
   ("ISO C++17 does not allow 'register' storage class specifier"), so
   patches/0001 drops the two redundant `register` qualifiers - the keyword
   has been a no-op hint since C++11.
4. Legacy CMake variables.  The root CMakeLists consumes ${OPENAL_LIBRARY},
   ${PNG_LIBRARY}, ${JPEG_LIBRARY}, ${ZLIB_LIBRARIES}, ${SDL2_LIBRARIES},
   ${OPENGL_LIBRARIES}, ${OPENGL_glu_LIBRARY}, ${VORBISFILE_LIBRARY},
   ${OGG_LIBRARY} and their include dirs - the variables produced by CMake's
   FindOpenAL/FindPNG/FindJPEG/FindZLIB/FindOpenGL and by the upstream
   CMake/Modules/FindOggVorbis.cmake.  CMakeDeps only emits modern IMPORTED
   targets, so all legacy cache variables are seeded from the dependency
   package folders before configure runs.
5. SDL2 is looked up with `pkg_check_modules(SDL2 sdl2 REQUIRED)`, so the
   PkgConfigDeps output is put on PKG_CONFIG_PATH; pkgconf itself comes from
   the registry (no system pkg-config is guaranteed on the CI worker).
6. The version string is hard-coded in the CMakeLists (1.2.0), so no -DVERSION
   injection is needed.  The game looks for its assets in `Data/` next to the
   executable (Source/Utils/Folders.hpp: DATA_DIR "Data" -> Folders.cpp:39),
   hence package() installs bin/lugaru together with bin/Data/.
7. Runtime.  gl4es dlopen()s its EGL/GLES backend instead of linking it, so
   package_info() exports LIBGL_EGL/LIBGL_GLES pointing at the system OHOS
   GLES stack (the same consumer contract as critter/2.0.4 and
   logstalgia/1.1.4).
"""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, CMakeToolchain
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Executable name produced by add_executable(lugaru ...).
_EXE_NAME = "lugaru"


class LugaruConan(ConanFile):
    name = "lugaru"
    version = "1.2"
    description = ("Lugaru - 3D action game with ragdoll physics "
                   "(open source release, osslugaru continuation)")
    license = "GPL-2.0-or-later"
    url = "https://gitlab.com/osslugaru/lugaru"
    homepage = "https://osslugaru.gitlab.io"
    topics = ("game", "sdl2", "opengl", "gl4es", "ohos")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # ------------------------------------------------------------------
    # configuration
    # ------------------------------------------------------------------
    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: the OHOS build host reports "OHOS"; Linux stays accepted so the
        # recipe can be reasoned about on a normal host.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux/OHOS only (gl4es + SDL2 OpenGL stack)")

    def requirements(self):
        # Direct dependencies of the root CMakeLists find_package() calls.
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        # CMake's FindJPEG wants jpeglib.h + libjpeg: libjpeg-turbo provides both.
        self.requires("libjpeg-turbo/3.2.0")
        # find_package(OggVorbis) (upstream module) wants ogg + vorbis + vorbisfile + vorbisenc.
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("openal/1.25.2")
        self.requires("sdl2/2.30.10")
        # Legacy GL stack: libGL.so (fixed function GL 1.x over GLES) + libGLU.so.
        self.requires("gl4es/1.1.6")
        self.requires("glu/9.0.3")

    def build_requirements(self):
        # pkg_check_modules(SDL2 sdl2 REQUIRED) needs a pkg-config implementation;
        # the CI worker has no guarantee of a system one.
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # dependency helpers
    # ------------------------------------------------------------------
    def _dep_folder(self, name):
        """Package folder of a (possibly transitive) dependency, or None."""
        try:
            folder = self.dependencies[name].package_folder
        except (KeyError, ConanException):
            return None
        return folder or None

    def _dep_include(self, name):
        folder = self._dep_folder(name)
        return os.path.join(folder, "include") if folder else None

    @staticmethod
    def _pick(folder, patterns, kind="lib"):
        """First usable library in `folder`/kind matching `patterns`.

        Preference: a plain/static archive before a versioned shared object,
        then the shortest name (libz.a before libz.so.1.3.1.1).
        """
        for pattern in patterns:
            hits = sorted(glob.glob(os.path.join(folder, kind, pattern)))
            if hits:
                hits.sort(key=lambda path: (".so." in path, len(path)))
                return hits[0]
        return None

    def _require_lib(self, name, patterns):
        folder = self._dep_folder(name)
        if folder is None:
            raise ConanException(f"dependency {name} has no package folder")
        lib = self._pick(folder, patterns)
        if not lib:
            raise ConanException(
                f"no library matching {patterns} in {folder}/lib "
                f"(dependency {name})")
        return lib

    def _header_dir(self, name, header):
        """Directory that actually contains `header` inside a dependency.

        libpng installs png.h under include/libpng16 and SDL2 installs SDL.h
        under include/SDL2, so the plain include/ root is not enough for the
        upstream `#include <png.h>` / `#include <SDL.h>`.
        """
        root = self._dep_include(name)
        if not root:
            return None
        for base, _dirs, files in os.walk(root):
            if header in files:
                return base
        return None

    def _include_dirs(self):
        """Header trees the upstream CMakeLists does not resolve itself."""
        dirs = []
        for name, extra in (("gl4es", None), ("glu", None), ("sdl2", "SDL2"),
                            ("libpng", "libpng16"), ("libjpeg-turbo", None),
                            ("openal", None), ("libogg", None),
                            ("libvorbis", None), ("zlib", None)):
            base = self._dep_include(name)
            if base and os.path.isdir(base) and base not in dirs:
                dirs.append(base)
            if extra:
                nested = os.path.join(base, extra) if base else None
                if nested and os.path.isdir(nested) and nested not in dirs:
                    dirs.append(nested)
        # png.h / SDL.h may live under a versioned subdirectory instead.
        for name, header in (("libpng", "png.h"), ("sdl2", "SDL.h")):
            found = self._header_dir(name, header)
            if found and found not in dirs:
                dirs.append(found)
        return dirs

    # ------------------------------------------------------------------
    # cmake invocation
    # ------------------------------------------------------------------
    def _cmake_args(self):
        gl_lib = self._require_lib("gl4es", ["libGL.so*", "libGL.a"])
        glu_lib = self._require_lib("glu", ["libGLU.a", "libGLU.so*"])
        sdl_lib = self._require_lib("sdl2", ["libSDL2.a", "libSDL2.so*", "libSDL2-2.0.so*"])
        png_lib = self._require_lib("libpng", ["libpng.a", "libpng*.a", "libpng*.so*"])
        jpeg_lib = self._require_lib(
            "libjpeg-turbo", ["libjpeg.a", "libjpeg.so*", "libturbojpeg.so*"])
        zlib_lib = self._require_lib("zlib", ["libz.a", "libz.so*"])
        ogg_lib = self._require_lib("libogg", ["libogg.a", "libogg.so*"])
        vorbis_lib = self._require_lib("libvorbis", ["libvorbis.a", "libvorbis.so*"])
        vorbisfile_lib = self._require_lib(
            "libvorbis", ["libvorbisfile.a", "libvorbisfile.so*"])
        vorbisenc_lib = self._require_lib(
            "libvorbis", ["libvorbisenc.a", "libvorbisenc.so*"])
        openal_lib = self._require_lib("openal", ["libopenal.a", "libopenal.so*"])

        png_inc = self._header_dir("libpng", "png.h") or self._dep_include("libpng")

        args = [
            f"-DCMAKE_TOOLCHAIN_FILE={os.path.join(self.generators_folder, 'conan_toolchain.cmake')}",
            # Upstream install rules split between SYSTEM_INSTALL on/off; packing is
            # done by hand in package(), so keep the simple local-Data layout.
            "-DSYSTEM_INSTALL=OFF",
            # CMake's FindZLIB / FindPNG / FindJPEG (module mode) honour seeded cache vars.
            f"-DZLIB_LIBRARY={zlib_lib}",
            f"-DZLIB_INCLUDE_DIR={self._dep_include('zlib')}",
            f"-DPNG_LIBRARY={png_lib}",
            f"-DPNG_PNG_INCLUDE_DIR={png_inc}",
            f"-DPNG_INCLUDE_DIR={png_inc}",
            f"-DJPEG_LIBRARY={jpeg_lib}",
            f"-DJPEG_INCLUDE_DIR={self._dep_include('libjpeg-turbo')}",
            # FindOpenAL (module mode): OHOS has no system OpenAL.
            f"-DOPENAL_LIBRARY={openal_lib}",
            f"-DOPENAL_INCLUDE_DIR={self._dep_include('openal')}",
            # FindOpenGL (module mode) pinned onto gl4es; OHOS has no GLX/desktop GL.
            f"-DOPENGL_gl_LIBRARY={gl_lib}",
            f"-DOPENGL_INCLUDE_DIR={self._dep_include('gl4es')}",
            # patches/0001 adds ${OPENGL_glu_LIBRARY} to the link line for gluPerspective.
            f"-DOPENGL_glu_LIBRARY={glu_lib}",
            # upstream CMake/Modules/FindOggVorbis.cmake (uses find_library/find_path).
            f"-DOGG_LIBRARY={ogg_lib}",
            f"-DOGG_INCLUDE_DIR={self._dep_include('libogg')}",
            f"-DVORBIS_INCLUDE_DIR={self._dep_include('libvorbis')}",
            f"-DVORBIS_LIBRARY={vorbis_lib}",
            f"-DVORBISFILE_LIBRARY={vorbisfile_lib}",
            f"-DVORBISENC_LIBRARY={vorbisenc_lib}",
            # SDL2 comes from pkg_check_modules(); pin it to the CMakeDeps prefix so
            # a host SDL2 cannot leak into the link line.
            f"-DSDL2_LIBRARIES={sdl_lib}",
            f"-DSDL2_INCLUDE_DIRS={self._dep_include('sdl2')}",
        ]
        return args

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # CMake 4.x: keep the policy floor explicit even though patches/0001 already
        # raises cmake_minimum_required to 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["SYSTEM_INSTALL"] = "OFF"
        # Upstream adds no include dirs of its own beyond SDL2's, so every component
        # include tree goes onto the compile line.
        for inc in self._include_dirs():
            tc.extra_cflags.append(f"-I{inc}")
            tc.extra_cxxflags.append(f"-I{inc}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # cmake is driven directly so the seeded legacy variables stay visible next
        # to the comments explaining why each one is required.
        generator = "Ninja" if shutil.which("ninja") else "Unix Makefiles"
        configure = ["cmake", "-S", self.source_folder, "-B", self.build_folder,
                     "-G", generator,
                     f"-DCMAKE_BUILD_TYPE={self.settings.build_type}"]
        configure += self._cmake_args()
        # pkgconf must see the PkgConfigDeps output (sdl2.pc).
        pkg_config_path = ('PKG_CONFIG_PATH=%s:"${PKG_CONFIG_PATH:-}"'
                           % shlex.quote(self.generators_folder))
        command = pkg_config_path + " " + " ".join(shlex.quote(arg) for arg in configure)
        self.output.info(f"cmake configure: {command}")

        # R33/runtime: OHOS /bin/sh is mksh and resets LD_LIBRARY_PATH, which kills
        # the conan-injected loader paths; env="conanbuild" routes through the bash
        # from the profile instead.
        self.run(command, env="conanbuild")
        self.run(" ".join(shlex.quote(arg) for arg in (
            ["cmake", "--build", self.build_folder, "-j",
             str(os.cpu_count() or 2)])), env="conanbuild")

    # ------------------------------------------------------------------
    # packaging
    # ------------------------------------------------------------------
    def _built_executable(self):
        candidates = [path for path in glob.glob(
            os.path.join(self.build_folder, "**", _EXE_NAME), recursive=True)
            if os.path.isfile(path) and not path.endswith((".o", ".a"))]
        if not candidates:
            raise ConanException(
                f"{_EXE_NAME} executable not found under {self.build_folder}")
        candidates.sort(key=len)
        exe = candidates[0]
        with open(exe, "rb") as handle:
            if handle.read(4) != b"\x7fELF":
                raise ConanException(f"{exe} is not an ELF binary")
        return exe

    def package(self):
        exe = self._built_executable()
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, os.path.basename(exe), src=os.path.dirname(exe), dst=bindir)
        # The game mounts its assets relative to the executable
        # (DATA_DIR "Data" -> Folders.cpp), so Data/ ships next to the binary.
        copy(self, "*", src=os.path.join(self.source_folder, "Data"),
             dst=os.path.join(bindir, "Data"))
        copy(self, "lugaru.6", src=os.path.join(self.source_folder, "Dist", "Linux"),
             dst=os.path.join(self.package_folder, "share", "man", "man6"))
        copy(self, "COPYING.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "CONTENT-LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "AUTHORS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # gl4es dlopen()s its backend, so consumers that launch lugaru need the
        # LIBGL_* contract pointed at the OHOS system GLES/EGL stacks.
        self.runenv_info.define("LIBGL_GLES", "/system/lib64/libGLESv3.so")
        self.runenv_info.define("LIBGL_EGL", "/system/lib64/libEGL.so")
