"""Snappy's unchanged default-enabled upstream suite and C/C++ installed APIs."""
import io
import os
import re
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, get
from ohos_sign import sign_elf


class SnappyConan(ConanFile):
    name = "snappy"
    version = "1.3.1"
    description = "Fast compression and decompression with C and C++ interfaces"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/snappy"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "ohos_sign.py"
    exports_sources = "gtest-subproject/*"

    def config_options(self):
        if self.settings.os == "Windows": del self.options.fPIC

    def build_requirements(self):
        self.test_requires("gtest/1.17.0.2")

    def layout(self): cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("SNAPPY_SOURCE_ARCHIVE")
        if local:
            archive = Path(local).resolve(strict=True)
            if not archive.is_file(): raise ConanException("source override must be a regular archive")
            source.update(url=archive.as_uri(), filename=archive.name)
        get(self, **source, strip_root=True)
        # The official tag archive lacks git submodules. Supply only that
        # missing subproject interface, never overwrite bundled upstream code.
        destination = Path(self.source_folder, "third_party/googletest/CMakeLists.txt")
        if destination.exists():
            raise ConanException("upstream now bundles googletest; reevaluate the shim")
        copy(self, "CMakeLists.txt", str(Path(self.export_sources_folder, "gtest-subproject")), str(destination.parent))

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["SNAPPY_BUILD_TESTS"] = True
        tc.variables["SNAPPY_BUILD_BENCHMARKS"] = False
        # Optional comparison codecs only affect benchmark/test-tool features,
        # not Snappy's complete unit suite. Avoid undeclared system libraries.
        for variable in ("HAVE_LIBZ", "HAVE_LIBLZO2", "HAVE_LIBLZ4"):
            tc.variables[variable] = False
        if str(self.settings.os) == "OHOS":
            for lang in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{lang}_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
            tc.extra_cxxflags.append("-Wno-error=unused-command-line-argument")
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if str(self.settings.os) == "OHOS":
            for p in sorted(Path(self.build_folder).iterdir()):
                if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b"\x7fELF": sign_elf(p)
        if can_run(self):
            cases = re.findall(r"TEST\(([^,]+),\s*(\w+)\)", Path(self.source_folder, "snappy_unittest.cc").read_text())
            disabled = [f"{suite.strip()}.{name}" for suite,name in cases if suite.strip().startswith("DISABLED_") or name.startswith("DISABLED_")]
            enabled = [f"{suite.strip()}.{name}" for suite,name in cases if not suite.strip().startswith("DISABLED_") and not name.startswith("DISABLED_")]
            if len(enabled) != 25 or disabled != ["Snappy.DISABLED_MoreThan4GB"]:
                raise ConanException("upstream default-enabled/disabled inventory changed")
            self.output.info("UPSTREAM_DEFAULT_INVENTORY=" + repr(enabled))
            self.output.info("UPSTREAM_ORIGINALLY_DISABLED=" + repr(disabled))
            runtime = Environment()
            if str(self.settings.os) == "OHOS" and self.options.shared:
                runtime.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            tmp = Path(self.build_folder, "upstream-tmp")
            tmp.mkdir(mode=0o770, exist_ok=False)
            runtime.define("TMPDIR", str(tmp))
            output = io.StringIO()
            try:
                with runtime.vars(self).apply():
                    self.run('ctest --test-dir "{}" --output-on-failure -V --no-tests=error --timeout 300'.format(self.build_folder), stdout=output, env="conanrun")
            finally:
                self.output.info(output.getvalue())
            text = output.getvalue()
            if "[  PASSED  ] 25 tests." not in text or re.search(r"\[\s*(?:FAILED|SKIPPED)\s*\]", text):
                raise ConanException("upstream default suite did not execute 25/25")
            self.output.info("UPSTREAM_25_OF_25_PASS")

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            for p in Path(self.package_folder, "lib").glob("*.so*"):
                if p.is_file() and not p.is_symlink(): sign_elf(p)
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["snappy"]
        self.cpp_info.set_property("cmake_file_name", "Snappy")
        self.cpp_info.set_property("cmake_target_name", "Snappy::snappy")
        self.cpp_info.set_property("pkg_config_name", "snappy")
