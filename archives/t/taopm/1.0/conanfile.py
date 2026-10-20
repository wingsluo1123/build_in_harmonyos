#!/usr/bin/env python3
"""Conan recipe for taopm 1.0 — Tao: sound synthesis with physical models.

Tao renders virtual acoustic instruments built from masses and springs and
writes the resulting sample streams to disk (`.dat`), which `tao2wav` /
`tao2aiff` (libaudiofile) turn into WAVE / AIFF files.  Upstream ships a
2006 autoconf-2.13 / automake / libtool-1.3 tree (`configure' is pre-generated
and 200 kB large).

Why this recipe does not run `./configure`
------------------------------------------
1. `configure' hard-requires desktop OpenGL, GLU, GLUT *and* the X11
   libraries: it aborts with "No OpenGL or Mesa GL library found",
   "No GLUT library found" and friends.  OHOS has no desktop GL at all — the
   SDK ships EGL + GLES only.  freeglut/3.6.0 *is* published for OHOS, but it
   is an EGL-pbuffer/GLES2 port whose GL calls are dispatched through
   eglGetProcAddress(); the OHOS GLES driver does not export the immediate-mode
   entry points the viewer is written against (glBegin/glEnd/glVertex3f ...),
   so `TaoGraphicsEngine.cc` can only be ported by rewriting it, not by
   linking it (see knowledge/drafts/DRAFT-mupdf-gl-*).
2. Regenerating `configure' from `configure.in' is not possible with a
   supported autoconf: the tree uses `AM_PROG_LIBTOOL', `AC_DIVERT_PUSH',
   `AM_SANITY_CHECK' and a one-argument `AC_INIT', all removed from modern
   autoconf/automake, and its libtool-1.3 `config.guess' predates aarch64.
3. Upstream has no test suite (`make check' is empty) and its `Makefile.am'
   files are only thin `lib_LTLIBRARIES' / `bin_PROGRAMS' wrappers.

The recipe therefore compiles the documented source lists explicitly, with
the compiler taken from the Conan profile instead of the shell (R33), and
builds the package headless:

* `libtao`            — the synthesis engine (patch 0001 compiles the viewer
                        out via `-DTAO_NO_GRAPHICS'), 17 of upstream's 18
                        translation units
* `taoparse`          — the `.tao` script -> C++ translator (bison + flex,
                        both published for OHOS)
* `tao2wav`, `tao2aiff`, `taosf`
                      — `.dat` -> WAVE / AIFF via audiofile/0.3.6

Everything that makes sound is therefore preserved; only the interactive
OpenGL instrument viewer (`tao -g`) is unavailable, and the library prints a
one-line notice and keeps synthesising when `-g` is passed.

The two source-level patches carry what the target compiler needs:

* 0001 turns the viewer into a compile-time option (`TAO_NO_GRAPHICS`).
* 0002 makes the 1999-era C++ compile as C++11 and later (removed `register`
  specifier, implicit-int `main()` in taoparse, tao2wav/tao2aiff and the
  generated score programs, missing <cstring>, a missing return value, and the
  order in which generated programs include taodefs.h's unit macros).
* 0003 fixes the TaoPitch name buffers, which the removed C++98 stream
  constructor had been silently papering over — AddressSanitizer reports a
  heap-buffer-overflow on the first `TaoString` construction without it.

Validation on this branch is host-side only (the OHOS worker was busy):
the patched tree compiles clean under C++17, AddressSanitizer is clean on the
synthesis path, and the test_package's API test renders 11000 frames of a
220 Hz string (measured 216.5 Hz) at 44100 Hz.  See notes.md for the evidence
and for the single-package device/CI commands that still have to run.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, mkdir)
from conan.tools.layout import basic_layout


# Upstream libtao/Makefile.am's libtao_la_SOURCES minus TaoGraphicsEngine.cc,
# which patch 0001 removes from the build (TAO_NO_GRAPHICS).
LIBTAO_SOURCES = [
    "Tao.cc",
    "TaoSynthEngine.cc",
    "TaoAccessPoint.cc",
    "TaoInstrument.cc",
    "TaoString.cc",
    "TaoRectangle.cc",
    "TaoCircle.cc",
    "TaoTriangle.cc",
    "TaoEllipse.cc",
    "TaoDevice.cc",
    "TaoBow.cc",
    "TaoHammer.cc",
    "TaoConnector.cc",
    "TaoStop.cc",
    "TaoOutput.cc",
    "TaoPitch.cc",
    "TaoCell.cc",
]

# Command line tools the package installs (R38: declared in commands.json).
CLI_TOOLS = ["taoparse", "tao2wav", "tao2aiff"]


class TaopmConan(ConanFile):
    name = "taopm"
    version = "1.0"
    description = ("Tao: sound synthesis with physical models — headless "
                   "synthesis engine (libtao), .tao script translator and "
                   "WAVE/AIFF converters")
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/taopm/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "sound-synthesis", "physical-modelling", "music")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        # Static by default: every consumer (taoparse/tao2wav/tao2aiff and the
        # tao-generated score programs) is a self-contained executable, and a
        # static libtao keeps OHOS from having to re-sign the shared object.
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: platform checks must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"taopm/1.0 is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"taopm/1.0 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # tao2wav/tao2aiff link libaudiofile; the synthesis engine itself only
        # needs libm.
        self.requires("audiofile/0.3.6")

    def build_requirements(self):
        # taoparse is a bison/flex program; both are published for OHOS.
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        # flex shells out to m4, and the OHOS flex package was configured with a
        # build-time absolute path to it; keep m4 in this build environment so
        # the M4 override below can point at a path that really exists.
        self.tool_requires("m4/1.4.19")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # Puts the tool_requires (bison, flex) on PATH inside `conanbuild'.
        VirtualBuildEnv(self).generate()

    # ------------------------------------------------------------------ #
    # build
    # ------------------------------------------------------------------ #
    def _compilers(self):
        """Compiler/driver paths from the Conan profile, never from the shell.

        R33: the release workers do not export CC/CXX, so the executables are
        taken from `tools.build:compiler_executables' (as the ohos-aarch64
        profile defines), then looked for next to the compiler, then on PATH.
        """
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = conf.get("cpp") or shutil.which("clang++") or "clang++"
        bindir = os.path.dirname(cxx) if os.path.sep in cxx else ""

        def pick(key, names):
            value = conf.get(key)
            if value:
                return value
            for name in names:
                if bindir:
                    candidate = os.path.join(bindir, name)
                    if os.path.isfile(candidate):
                        return candidate
                found = shutil.which(name)
                if found:
                    return found
            return names[-1]

        return cxx, pick("ar", ["llvm-ar", "ar"]), pick("ranlib", ["llvm-ranlib", "ranlib"])

    def _cxx_flags(self):
        flags = ["-g", "-O0"] if self.settings.build_type == "Debug" else ["-O2"]
        cppstd = self.settings.compiler.get_safe("cppstd")
        if cppstd:
            cppstd = str(cppstd)
            flags.append("-std=gnu++" + cppstd[3:] if cppstd.startswith("gnu")
                         else "-std=c++" + cppstd)
        elif str(self.settings.compiler) in ("clang", "gcc"):
            flags.append("-std=gnu++17")
        if self.options.shared or self.options.get_safe("fPIC"):
            flags.append("-fPIC")
        return flags

    def _dependency_flags(self, name):
        dep = self.dependencies[name]
        cpp_info = dep.cpp_info
        includes = [f"-I{os.path.join(dep.package_folder, p)}" for p in cpp_info.includedirs]
        libdirs = [f"-L{os.path.join(dep.package_folder, p)}" for p in cpp_info.libdirs]
        libs = [f"-l{lib}" for lib in cpp_info.libs]
        return includes, libdirs + libs

    def _run(self, command, cwd=None):
        self.output.info(command)
        self.run(command, cwd=cwd, env="conanbuild")

    def _build_tool_folder(self, name):
        """Package folder of a build-requirement (tool_requires) dependency."""
        for collection in ("build", None):
            try:
                deps = self.dependencies.build if collection else self.dependencies
                values = deps.values()
            except Exception:
                continue
            for dep in values:
                if dep.ref.name == name and dep.package_folder:
                    return dep.package_folder
        return None

    def _build_tool(self, package, binary):
        """Absolute path of a tool taken from its own package, never from PATH.

        CI workers expose a system bison/flex/... under `/data/service/hnp/bin`
        whose compiled-in pkgdatadir is `/data/service/hnp/share`; a PATH lookup
        therefore resolves the *system* copy, whose data directory does not
        exist, instead of the Conan tool_requires copy.  Resolving the tool
        through its package folder keeps binary and data directory consistent.
        """
        folder = self._build_tool_folder(package)
        if folder:
            candidate = os.path.join(folder, "bin", binary)
            if os.path.isfile(candidate):
                return candidate
        return binary

    def _compile(self, cxx, flags, source, obj):
        self._run(f'"{cxx}" {" ".join(flags)} -c "{source}" -o "{obj}"')

    def build(self):
        apply_conandata_patches(self)

        cxx, ar, ranlib = self._compilers()
        self.output.info(f"using C++ compiler: {cxx}")
        self.output.info(f"using archiver: {ar}")

        source = self.source_folder
        include = os.path.join(source, "include")
        objdir = os.path.join(self.build_folder, "obj")
        libdir = os.path.join(self.build_folder, "lib")
        bindir = os.path.join(self.build_folder, "bin")
        mkdir(self, objdir)
        mkdir(self, libdir)
        mkdir(self, bindir)

        flags = self._cxx_flags() + ["-DTAO_NO_GRAPHICS", f"-I{include}"]

        # ---- libtao ------------------------------------------------------
        objects = []
        for name in LIBTAO_SOURCES:
            obj = os.path.join(objdir, os.path.splitext(name)[0] + ".o")
            self._compile(cxx, flags, os.path.join(source, "libtao", name), obj)
            objects.append(obj)

        obj_list = " ".join(f'"{o}"' for o in objects)
        if self.options.shared:
            soname = "libtao.so.0"
            real = os.path.join(libdir, "libtao.so.0.0.0")
            self._run(f'"{cxx}" -shared -o "{real}" {obj_list} -Wl,-soname,{soname} -lm')
            self._link_or_copy(real, os.path.join(libdir, soname))
            self._link_or_copy(real, os.path.join(libdir, "libtao.so"))
        else:
            archive = os.path.join(libdir, "libtao.a")
            self._run(f'"{ar}" rcs "{archive}" {obj_list}')
            self._run(f'"{ranlib}" "{archive}"')

        # ---- taoparse (bison + flex) -------------------------------------
        parse_src = os.path.join(self.build_folder, "taoparse")
        copy(self, "*", src=os.path.join(source, "taoparse"), dst=parse_src)
        # The OHOS bison/flex packages were configured with prefix `/`, so their
        # runtimes look for their data under `/share/...`, which does not exist
        # in a Conan cache:
        #   bison: "/share/bison/m4sugar/m4sugar.m4: cannot open"
        #   flex : "fatal internal error, exec of <build-time>/bin/m4 failed"
        # Both tools and their data are therefore taken from the packages that
        # this build depends on: a PATH lookup is not safe, because CI workers
        # also ship a system bison under /data/service/hnp/bin whose pkgdatadir
        # (/data/service/hnp/share) is missing.
        bison = self._build_tool("bison", "bison")
        flex = self._build_tool("flex", "flex")
        m4 = self._build_tool("m4", "m4")
        bison_folder = self._build_tool_folder("bison")
        bison_data = os.path.join(bison_folder, "share", "bison") if bison_folder else ""
        if not bison_data or not os.path.isdir(bison_data):
            raise ConanException(
                "bison data directory not found in the bison package "
                f"({bison_data!r}); refusing to fall back to a PATH lookup, "
                "which can resolve a system bison without its pkgdatadir")
        self.output.info(f"using bison: {bison} (BISON_PKGDATADIR={bison_data})")
        self.output.info(f"using flex: {flex} (M4={m4})")
        tool_env = (f'BISON_PKGDATADIR="{bison_data}"; export BISON_PKGDATADIR; '
                    f'M4="{m4}"; export M4; ')
        # bison writes the two file names the scanner expects to include.
        self._run(f'{tool_env}"{bison}" -d -o taoparser.cc '
                  "--defines=taoparser.h taoparser.yy", cwd=parse_src)
        self._run(f'{tool_env}"{flex}" -o taoscanner.cc taoscanner.ll', cwd=parse_src)
        parse_objects = []
        for name in ("taoparser.cc", "taoscanner.cc"):
            obj = os.path.join(objdir, "taoparse_" + name + ".o")
            self._compile(cxx, flags + [f"-I{parse_src}"],
                          os.path.join(parse_src, name), obj)
            parse_objects.append(obj)
        self._run(f'"{cxx}" -o "{os.path.join(bindir, "taoparse")}" '
                  + " ".join(f'"{o}"' for o in parse_objects))

        # ---- tao2wav / tao2aiff (libaudiofile) ---------------------------
        audio_includes, audio_link = self._dependency_flags("audiofile")
        for tool in ("tao2wav", "tao2aiff"):
            tool_src = os.path.join(source, tool)
            # `#include "audiofile.h"' resolves to the private copy bundled in
            # the tool directory first — exactly what upstream's Makefile does.
            tool_flags = flags + [f"-I{tool_src}"] + audio_includes
            self._run(f'"{cxx}" {" ".join(tool_flags)} '
                      f'-o "{os.path.join(bindir, tool)}" '
                      f'"{os.path.join(tool_src, tool + ".cc")}" '
                      f'{" ".join(audio_link + ["-lm"])}')
        if self.options.shared and self.settings.os == "OHOS":
            self._sign_so_files(libdir)

    @staticmethod
    def _link_or_copy(source, destination):
        if os.path.lexists(destination):
            os.remove(destination)
        try:
            os.symlink(os.path.basename(source), destination)
        except OSError:
            shutil.copy2(source, destination)

    def _sign_so_files(self, folder):
        """OHOS refuses to dlopen an unsigned .so (see freeglut/glu recipes)."""
        signer = next((p for p in ("/data/service/hnp/bin/binary-sign-tool",
                                   shutil.which("binary-sign-tool") or "")
                       if p and os.path.isfile(p)), None)
        objcopy = next((p for p in ("/data/service/hnp/bin/llvm-objcopy",
                                    shutil.which("llvm-objcopy") or "")
                        if p and os.path.isfile(p)), None)
        if signer is None:
            self.output.warning("binary-sign-tool not found; shared libtao.so is "
                                "left unsigned and cannot be dlopen()ed on OHOS")
            return
        for name in sorted(os.listdir(folder)):
            if ".so" not in name or os.path.islink(os.path.join(folder, name)):
                continue
            so = os.path.join(folder, name)
            if objcopy:
                self.run(f'"{objcopy}" --remove-section .codesign "{so}" '
                         '2>/dev/null || true', ignore_errors=True)
            self.run(f'"{signer}" sign -inFile "{so}" -outFile "{so}" -selfSign 1')
            os.chmod(so, 0o755)

    # ------------------------------------------------------------------ #
    # package
    # ------------------------------------------------------------------ #
    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # The viewer header needs <GL/glut.h>, which OHOS does not have; the
        # package is the headless build, so its header is not shipped.
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             excludes="TaoGraphicsEngine.h", keep_path=False)

        libdir = os.path.join(self.build_folder, "lib")
        bindir = os.path.join(self.build_folder, "bin")
        package_lib = os.path.join(self.package_folder, "lib")
        package_bin = os.path.join(self.package_folder, "bin")
        if self.options.shared:
            copy(self, "*.so*", src=libdir, dst=package_lib, keep_path=False)
        else:
            copy(self, "libtao.a", src=libdir, dst=package_lib, keep_path=False)
        copy(self, "*", src=bindir, dst=package_bin, keep_path=False)

        # Shell helper and example scores.
        copy(self, "taosf", src=os.path.join(self.source_folder, "user-scripts"),
             dst=package_bin, keep_path=False)
        copy(self, "*.tao", src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(self.package_folder, "share", "tao", "examples"),
             keep_path=False)

        # copy() does not keep the executable bit, and taosf is a shell script.
        for name in sorted(os.listdir(package_bin)):
            path = os.path.join(package_bin, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["tao"]
        # Consumers include taodefs.h, which only skips TaoGraphicsEngine.h
        # when this define is present.
        self.cpp_info.defines = ["TAO_NO_GRAPHICS"]
        self.cpp_info.set_property("cmake_file_name", "taopm")
        self.cpp_info.set_property("cmake_target_name", "taopm::taopm")
        self.cpp_info.set_property("pkg_config_name", "taopm")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
