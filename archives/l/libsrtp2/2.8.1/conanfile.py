"""libSRTP internal crypto backend with its complete upstream CTest suite."""
import io
import json
import os
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, get
from ohos_sign import sign_elf


class Libsrtp2Conan(ConanFile):
    name = "libsrtp2"
    version = "2.8.1"
    description = "Secure RTP and RTCP encryption, authentication and replay protection"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cisco/libsrtp"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "ohos_sign.py"

    def config_options(self):
        if self.settings.os == "Windows": del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("LIBSRTP2_SOURCE_ARCHIVE")
        if local:
            archive = Path(local).resolve(strict=True)
            if not archive.is_file(): raise ConanException("source override must be a regular archive")
            source.update(url=archive.as_uri(), filename=archive.name)
        get(self, **source, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["LIBSRTP_TEST_APPS"] = True
        tc.variables["CMAKE_RUNTIME_OUTPUT_DIRECTORY"] = self.build_folder
        # PCAP only builds an optional standalone decoder, not a CTest case.
        # Do not acquire an undeclared system-PCAP dependency on some workers.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_PCAP"] = True
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
            # The OHOS compiler wrapper appends link-time signing arguments
            # even to -c. Keep upstream -Werror for source diagnostics.
            tc.extra_cflags.append("-Wno-error=unused-command-line-argument")
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "OHOS":
            for path in sorted(Path(self.build_folder).iterdir()):
                if path.is_file() and not path.is_symlink() and path.read_bytes()[:4] == b"\x7fELF": sign_elf(path)
        if can_run(self):
            output = io.StringIO()
            self.run('ctest --test-dir "{}" --show-only=json-v1'.format(self.build_folder), stdout=output)
            tests = json.loads(output.getvalue())["tests"]
            if len(tests) != 12: raise ConanException("upstream internal-backend test inventory changed")
            runtime = Environment()
            if str(self.settings.os) == "OHOS" and self.options.shared:
                runtime.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            output = io.StringIO()
            try:
                with runtime.vars(self).apply():
                    self.run('ctest --test-dir "{}" --output-on-failure -V --no-tests=error --timeout 180'.format(self.build_folder), stdout=output, env="conanrun")
            finally:
                self.output.info(output.getvalue())
            if "100% tests passed, 0 tests failed out of 12" not in output.getvalue():
                raise ConanException("upstream test result missing")
            self.output.info("UPSTREAM_12_OF_12_PASS")

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            for path in Path(self.package_folder, "lib").glob("*.so*"):
                if path.is_file() and not path.is_symlink(): sign_elf(path)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["srtp2"]
        self.cpp_info.set_property("cmake_file_name", "libSRTP")
        self.cpp_info.set_property("cmake_target_name", "libSRTP::srtp2")
        self.cpp_info.set_property("pkg_config_name", "libsrtp2")
