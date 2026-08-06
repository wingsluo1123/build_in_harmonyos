from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches

import os
import subprocess
import tempfile


class StkConan(ConanFile):
    name = "stk"
    version = "latest"
    description = "The Synthesis ToolKit in C++ - audio synthesis library"
    license = "MIT"
    homepage = "https://github.com/thestk/stk"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Both patches are portability fixes for thread cancellation; see
        # conandata.yml and notes.md. Neither introduces a platform macro:
        # the CMake patch probes for pthread_cancel() with
        # check_symbol_exists() and the source patch keys off that result.
        apply_conandata_patches(self)

    def _has_pthread_testcancel(self):
        """Feature probe for pthread_testcancel() (musl/OHOS lacks it).

        R8 compliance: rather than keying the sources off a platform macro, we
        probe whether ``pthread_testcancel`` is actually usable and expose the
        result as ``STK_HAVE_PTHREAD_CANCEL``. The patched Thread.cpp branches on
        that macro (by value), so OHOS -- where musl does not declare
        pthread_testcancel -- compiles the cancel paths out. Default to present
        on any platform we cannot probe.
        """
        if self.settings.os == "OHOS":
            # musl-based OHOS libc does not implement pthread_testcancel().
            return False
        cc = os.environ.get("CC") or "clang"
        src = (
            "#include <pthread.h>\n"
            "int main(void){ return (int)(long)(void*)pthread_testcancel; }\n"
        )
        fd, path = tempfile.mkstemp(suffix=".c")
        try:
            os.write(fd, src.encode())
        finally:
            os.close(fd)
        out = path + ".o"
        try:
            proc = subprocess.run(
                [cc, "-c", path, "-o", out],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
            )
            return proc.returncode == 0
        except Exception:
            return True
        finally:
            for p in (path, out):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    def generate(self):
        # Only the Conan toolchain/presets here. All STK CMake *options* are
        # passed on the cmake command line in build() because tc.variables
        # (toolchain file) is NOT honoured by a direct `cmake` invocation,
        # which is how Conan drives configure().
        tc = CMakeToolchain(self)
        # STK derives its platform macro from the audio backend macro:
        #   Stk.h: #elif defined(__LINUX_OSS__) || defined(__LINUX_ALSA__)
        #          || defined(__UNIX_JACK__) || defined(__LINUX_PULSE__)
        #            #define __OS_LINUX__
        # Those backend macros are only added by the CMake REALTIME block,
        # which we must keep OFF here (its else-branch is a hard
        # FATAL_ERROR "Unknown system type for realtime support.").
        # With REALTIME=OFF nothing defines __OS_LINUX__, so Mutex.h and
        # Socket.h skip <pthread.h> / <netinet/in.h> / <netinet/tcp.h> and
        # MUTEX, CONDITION, THREAD_HANDLE, THREAD_FUNCTION, THREAD_RETURN and
        # struct sockaddr_in all go missing -- yet CMakeLists globs *every*
        # src/*.cpp, so InetWvIn.cpp / InetWvOut.cpp / UdpSocket.cpp are
        # compiled anyway and fail.
        # __OS_LINUX__ is STK's own switch for "POSIX threads + BSD sockets",
        # which is exactly what this target offers, so selecting that code
        # path is semantically correct. It is NOT a platform macro of ours
        # and it is set for every configuration, not per-OS.
        # __STK_REALTIME__ stays undefined: no realtime audio backend is built.
        tc.preprocessor_definitions["__OS_LINUX__"] = 1
        # R8: advertise whether pthread_cancel()/pthread_testcancel() are
        # *declared* (not merely linkable).  The patched Thread.cpp guards the
        # cancel paths on STK_HAVE_PTHREAD_CANCEL (by value), so on OHOS -- where
        # musl omits the declarations -- the paths compile out.  The probe result
        # is passed as the STK_HAVE_PTHREAD_CANCEL CMake cache variable in build()
        # (the mechanism actually honoured by Conan's direct cmake invocation); the
        # CMakeLists patch deliberately no longer runs check_symbol_exists(), which
        # returns
        # a false positive on OHOS (the symbol links but is undeclared).
        tc.generate()

    def build(self):
        cmake = CMake(self)
        shared = bool(self.options.shared)
        # Every STK option MUST be on the command line (-D):
        #  - CMAKE_POLICY_VERSION_MINIMUM=3.5: CMake >= 4.0 removed
        #    compatibility with cmake_minimum_required(<3.5); STK declares 3.1.
        #  - REALTIME=OFF: REQUIRED here. STK's realtime block ends with
        #    FATAL_ERROR "Unknown system type for realtime support." for any
        #    system that is not Linux/Darwin/Windows.
        #  - COMPILE_PROJECTS=OFF: skip the example/demo executables.
        #  - BUILD_SHARED/STATIC: match the Conan shared option.
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            # STK calls include(TestBigEndian) + TEST_BIG_ENDIAN unconditionally
            # (outside the REALTIME block). Under this toolchain CMake may treat
            # the build as cross-compiling and try_run() cannot execute the probe.
            # Pinning the byte order avoids the run-based probe entirely
            # (aarch64 is little-endian). Requires CMake >= 3.19 (present).
            "CMAKE_CXX_BYTE_ORDER": "LITTLE_ENDIAN",
            "BUILD_SHARED": "ON" if shared else "OFF",
            "BUILD_STATIC": "OFF" if shared else "ON",
            "REALTIME": "OFF",
            "COMPILE_PROJECTS": "OFF",
            "ENABLE_ALSA": "OFF",
            "ENABLE_JACK": "OFF",
            # Declaration-based probe result for thread cancellation.  Passed as
            # a CMake cache variable (honoured by Conan's cmake invocation) so
            # the patched Thread.cpp compiles the cancel paths out on OHOS,
            # where pthread_cancel()/pthread_testcancel() are undeclared.
            "STK_HAVE_PTHREAD_CANCEL": (
                "1" if self._has_pthread_testcancel() else "0"),
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["stk"]
        self.cpp_info.includedirs = ["include/stk"]
        # The installed headers are not self-contained: Thread.h, Mutex.h and
        # Socket.h only declare THREAD_HANDLE / MUTEX / sockaddr_in when one of
        # STK's __OS_* switches is set, and Stk.h derives those from an audio
        # backend macro that a REALTIME=OFF build never defines. The library
        # objects were compiled with __OS_LINUX__ (see generate()), so consumers
        # must see the same switch or they get compile errors -- and, worse,
        # a different view of the classes than the one that was compiled.
        self.cpp_info.defines = ["__OS_LINUX__"]
