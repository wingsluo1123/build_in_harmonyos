#!/usr/bin/env python3
"""Conan recipe — ktx 1.45 (Kombat Teams eXtreme, QuakeWorld server mod).

Upstream: https://github.com/QW-Group/ktx
Tag 1.45 (commit d05d6ca6dae1a8b5a1ea23aa9e33f6d99bcc9102).

KTX is a QuakeWorld server modification. It is *not* a standalone program: the
QuakeWorld server (MVDSV / FTEQW) loads the mod as a native shared object with
dlopen() and then calls `dllEntry()` to hand over its syscall trampoline.
Upstream's CMakeLists.txt therefore declares exactly one deliverable:

    add_library(qwprogs SHARED ${SRC_COMMON} ${SRC_NATIVE})
    set_target_properties(qwprogs PROPERTIES PREFIX ""   # -> qwprogs.so

Everything else in upstream CMakeLists.txt (the `qvm` target and the bundled
tools/q3asm) is EXCLUDE_FROM_ALL / on-demand only: producing the QVM bytecode
variant would additionally need the id Software `q3lcc` TinyC compiler, which
does not exist on any OHOS toolchain. The default build target is the native
module only, which is exactly what a QuakeWorld server dlopen()s.

Packaging note: the module is a dlopen-only plugin whose only exported symbol is
`dllEntry`, so the package ships it unmodified as lib/qwprogs.so (upstream's name,
which its DT_SONAME also carries) and declares no cpp_info.libs. No source patch
is involved.

HarmonyOS PC adaptation notes:
  * No source patch is required. ktx 1.45 is plain C99 + <math.h> and only
    links libm; it cross-compiles with the OHOS aarch64 clang 15 toolchain
    out of the box (verified: zero errors, zero OHOS-specific warnings).
  * The resulting ELF is `aarch64` / `ET_DYN`, DT_SONAME=qwprogs.so and its
    only DT_NEEDED is `libc.so` (musl) — so it is dlopen-able on device.
  * `settings.os` is accepted for Linux and OHOS (R32).
  * build()/generate() take every compiler and flag from the Conan-generated
    CMakeToolchain — no bare ${CC}/${CFLAGS} shell variables (R33).
  * The product is a shared library, not an executable, so no software-level
    commands.json is declared (R38).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

# Upstream names the module `qwprogs` and strips the `lib` prefix, so the built
# file (and its DT_SONAME) is `qwprogs.so`. The package installs that name
# unmodified; see package_info() and notes.md section 5.1 for why renaming it to
# libqwprogs.so is deliberately NOT done.
MODULE_NAME = "qwprogs"


class KtxConan(ConanFile):
    name = "ktx"
    version = "1.45"
    description = "KTX (Kombat Teams eXtreme) — QuakeWorld server modification, native module"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/QW-Group/ktx"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # R32: settings.os must accept Linux or OHOS
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ktx is a POSIX shared module; os={} is not supported".format(self.settings.os)
            )

    def requirements(self):
        # ktx 1.45 is self-contained: it includes only standard C headers
        # (<assert.h> <ctype.h> <limits.h> <math.h> <stdarg.h> <stdint.h>
        # <stdio.h> <stdlib.h> <string.h> <time.h>) and links only libm.
        # W0 dependency check therefore has nothing to resolve.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Keep the upstream default (BOT_SUPPORT=ON) but pin it explicitly so
        # the built module matches the binaries upstream publishes.
        tc.variables["BOT_SUPPORT"] = "ON"
        # The QVM variant needs the id `q3lcc` TinyC compiler, which is not
        # part of any OHOS toolchain; never try to configure that target.
        tc.variables["FTESV"] = "OFF"
        if self.settings.os == "OHOS":
            # CMake has no built-in HarmonyOS platform module (CMake itself
            # prints "System is unknown to cmake, create: Platform/HarmonyOS"),
            # so CMAKE_SHARED_LIBRARY_SONAME_C_FLAG stays empty and the module
            # is linked without a -soname flag. On Linux the GNU toolchain
            # happens to emit DT_SONAME from the output name, but the OHOS
            # clang/lld toolchain does not -- so on CI (a real OHOS worker)
            # the module comes out with NO DT_SONAME, while a local Linux
            # cross-build looks fine. The QuakeWorld server dlopen()s the
            # module by name and the SONAME must equal the installed file
            # name (qwprogs.so), so make CMake pass the flag explicitly.
            # Same approach as the in-repo jsoncpp / telemetry recipes.
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # --parallel 1: OHOS worker 上并行 make 会因进程/PID 资源耗尽而失败
        # （CI #94773: "/bin/sh: can't fork - try again" → make[2] Error 1 →
        # conan create failed），单进程串行构建可避开这一环境问题；仓内先例：
        # julius/1.8.0 的 cmake.build(cli_args=["--parallel", "1"])（R9/HMDFS
        # jobserver 坑）、box2d/2.4.1 的 tools.build:jobs=1 + 
        # CMAKE_BUILD_PARALLEL_LEVEL=1、meterec/0.9.3 与 musicpc/0.35 的 -j1。
        # 只降低并行度，不改变产物内容与任何判定。
        cmake.build(cli_args=["--parallel", "1"])

    def package(self):
        # Upstream builds the module as `<build>/qwprogs.so` (PREFIX ""). Install
        # it unmodified as lib/qwprogs.so: the QuakeWorld server looks the file
        # up by its bare name and the DT_SONAME upstream emits (qwprogs.so) then
        # matches the installed name exactly. See package_info()/notes.md 5.1
        # for why the package deliberately does NOT rename it to libqwprogs.so.
        pkg_lib_dir = os.path.join(self.package_folder, "lib")
        so_name = MODULE_NAME + ".so"
        if not os.path.isfile(os.path.join(pkg_lib_dir, so_name)):
            candidates = [
                os.path.join(self.build_folder, "lib", so_name),
                os.path.join(self.build_folder, so_name),
                os.path.join(self.build_folder, "Release", so_name),
                os.path.join(self.build_folder, "Debug", so_name),
            ]
            built = next((c for c in candidates if os.path.isfile(c)), None)
            if built is None:
                raise RuntimeError(
                    "ktx build did not produce the native module; looked for: "
                    + ", ".join(candidates)
                )
            copy(self, so_name, os.path.dirname(built), pkg_lib_dir)

        # Ship the module headers so a consumer can compile against the mod ABI
        # (dllEntry / vmMain and the QuakeWorld shared-memory structures).
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include", "ktx"))

        # Upstream LICENSE.md (GPL-2.0-or-later) travels with the package.
        for license_file in ("LICENSE.md", "LICENSE"):
            src = os.path.join(self.source_folder, license_file)
            if os.path.isfile(src):
                copy(self, license_file, self.source_folder,
                     os.path.join(self.package_folder, "licenses"))
                break

    def package_info(self):
        # ktx is a dlopen-type plugin, not a linkable library. The QuakeWorld
        # server loads lib/qwprogs.so *by path* and resolves `dllEntry` with
        # dlsym(); upstream hides every other symbol
        # (set_target_properties(qwprogs PROPERTIES C_VISIBILITY_PRESET hidden)),
        # so there is no API to declare in cpp_info.libs.
        #
        # `libs` is therefore intentionally empty. Declaring libs=["qwprogs"]
        # would be actively wrong here: upstream sets PREFIX "" so the file has
        # no `lib` prefix, and CMakeDeps resolves cpp_info.libs with
        # find_library(NAMES qwprogs), which on this toolchain
        # (CMAKE_FIND_LIBRARY_PREFIXES == "lib") only ever matches
        # libqwprogs.so. Measured: with libs=["qwprogs"] every CMake consumer's
        # find_package(ktx) aborts with
        #   "Library 'qwprogs' not found in package".
        # Renaming the file to libqwprogs.so would fix find_library() but then
        # DT_SONAME (qwprogs.so, emitted by upstream's PREFIX "") would disagree
        # with the installed name and any consumer that *did* link would fail at
        # load time with "cannot open shared object file" - and the SONAME can
        # only be changed from upstream's CMakeLists.txt (a source patch).
        # Keeping upstream's name is therefore both faithful and the only option
        # that needs no patch. See notes.md section 5.1.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # Faithful to upstream's `target_link_libraries(qwprogs PRIVATE m)`; on
        # OHOS musl the linker resolves libm from libc.so (DT_NEEDED is just
        # libc.so), but declaring it keeps the dependency explicit.
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_target_name", "ktx::ktx")
        self.cpp_info.set_property("cmake_file_name", "ktx")