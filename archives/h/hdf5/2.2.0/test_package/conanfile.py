import os
import shlex
import stat
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestParallelHdf5(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            import shutil
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            signer = self.conf.get("user.harmony:signer", default=None) or shutil.which("binary-sign-tool")
            objcopy = compilers.get("objcopy") or shutil.which("llvm-objcopy")
            if not signer or not objcopy:
                raise ConanInvalidConfiguration("Actual signer and objcopy needed")
            self._signer, self._objcopy = signer, objcopy
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("Real two-rank target execution required")
        binary = os.path.join(self.cpp.build.bindirs[0], "real_parallel")
        if self.settings.os == "OHOS":
            import shutil
            signer = self.conf.get("user.harmony:signer", default=None) or shutil.which("binary-sign-tool")
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            objcopy = compilers.get("objcopy") or shutil.which("llvm-objcopy")
            if not signer or not objcopy:
                raise ConanInvalidConfiguration("Target signing unavailable")
            self.run(shlex.quote(objcopy) + " --remove-section .codesign " + shlex.quote(binary))
            self.run(shlex.quote(signer) + " sign -inFile " + shlex.quote(binary)
                     + " -outFile " + shlex.quote(binary) + " -selfSign 1")
        mpi = self.dependencies["mpich"]
        launcher = os.path.join(mpi.cpp_info.bindirs[0], "mpiexec")
        self.run(shlex.quote(launcher) + " -n 2 " + shlex.quote(binary), env="conanrun")
        if self.settings.os == "OHOS":
            harmony = os.path.join(self.cpp.build.bindirs[0], "harmony_tests", "harmony_overflow")
            self.run(shlex.quote(objcopy) + " --remove-section .codesign " + shlex.quote(harmony))
            self.run(shlex.quote(signer) + " sign -inFile " + shlex.quote(harmony)
                     + " -outFile " + shlex.quote(harmony) + " -selfSign 1")
            # HMDFS projects inode ownership; the production secure stream
            # requires actual process ownership, not the projected storage UID.
            parent = self.conf.get("user.harmony:private_tmp_root", default=None) or "/data/storage/el2/base/cache"
            if not os.path.isabs(parent) or os.path.realpath(parent) != parent:
                raise ConanInvalidConfiguration("Literal POSIX private temporary root required")
            part = parent
            while True:
                info = os.lstat(part)
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise ConanInvalidConfiguration("Temporary root traversal is not a real directory")
                previous = os.path.dirname(part)
                if previous == part:
                    break
                part = previous
            if os.stat(parent).st_uid != os.getuid() or not os.access(parent, os.W_OK | os.X_OK):
                raise ConanInvalidConfiguration("Actual process-owned writable POSIX root required")
            temporary = tempfile.mkdtemp(prefix="hdf5-harmony-", dir=parent)
            info = os.lstat(temporary)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ConanInvalidConfiguration("Exclusive private temporary directory ownership/mode invalid")
            try:
                # The production owner checks and immediate-unlink oracle remain.
                self.run("TMPDIR=" + shlex.quote(temporary) + " " + shlex.quote(harmony), env="conanrun")
                if os.listdir(temporary):
                    raise ConanInvalidConfiguration("Production temporary stream leaked a name")
            finally:
                # Only this exclusively created directory; do not delete contents
                # or alter ownership to force a successful security assertion.
                if not os.listdir(temporary):
                    os.rmdir(temporary)
            # Emit the pipeline's standard marker only after the actual
            # production oracle returned successfully and cleanup completed.
            self.output.info("HARMONY_TEST_PASS=1/1")
