import io
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, replace_in_file, unzip


class MarisaPython3Conan(ConanFile):
    name = "marisa-python3"
    version = "0.3.1"
    description = "Official MARISA Python 3 C++ extension"
    license = "BSD-2-Clause OR LGPL-2.1-or-later"
    homepage = "https://github.com/s-yata/marisa-trie"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        copy(self, "*", src=os.path.join(self.recipe_folder, "upstream_support"),
             dst=os.path.join(self.export_sources_folder, "upstream_support"))

    def requirements(self):
        self.requires("marisa/0.3.1", headers=True, libs=True)
        self.requires("python/3.12.9", headers=True, libs=True, run=True)

    def build_requirements(self):
        self.tool_requires("swig/4.4.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This binding requires a POSIX target")

    def layout(self):
        cmake_layout(self)

    def source(self):
        archive = self.conf.get("user.marisa-python3:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["MARISA_SOURCE"] = self.source_folder
        toolchain.variables["MARISA_BINDING_BUILD"] = os.path.join(self.build_folder, "bindings")
        if str(self.settings.os) == "OHOS":
            for language in ("C", "CXX"):
                toolchain.variables["CMAKE_SHARED_LIBRARY_RUNTIME_" + language + "_FLAG"] = "-Wl,-rpath,"
                toolchain.variables["CMAKE_SHARED_LIBRARY_RUNTIME_" + language + "_FLAG_SEP"] = ":"
            toolchain.variables["CMAKE_INSTALL_RPATH"] = ""
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # MARISA 0.3 changed MARISA_THROW_IF from error-code arguments to
        # exception types; its shipped language bindings still use the old
        # allocation macro. Preserve all five guards with real bad_alloc.
        binding = os.path.join(self.source_folder, "bindings", "marisa-swig-python3.cxx")
        for pointer, error in (("keyset_", "::MARISA_MEMORY_ERROR"),
                               ("agent_", "::MARISA_MEMORY_ERROR"),
                               ("new_buf", "MARISA_MEMORY_ERROR"),
                               ("trie_", "::MARISA_MEMORY_ERROR"),
                               ("buf", "MARISA_MEMORY_ERROR")):
            replace_in_file(self, binding,
                            "MARISA_THROW_IF({} == NULL, {});".format(pointer, error),
                            "if ({} == NULL) throw std::bad_alloc();".format(pointer))
        interface = os.path.join(self.source_folder, "bindings", "marisa-swig-python3.i")
        replace_in_file(self, interface, '#include "marisa-swig-python3.h"',
                        '#include <new>\n#include "marisa-swig-python3.h"')
        replace_in_file(self, interface, "} catch (const marisa::Exception &ex) {",
                        "} catch (const std::bad_alloc &ex) {\n"
                        "    SWIG_exception(SWIG_MemoryError, ex.what());\n"
                        "  } catch (const marisa::Exception &ex) {")
        generated = os.path.join(self.build_folder, "bindings")
        os.makedirs(generated, exist_ok=True)
        with VirtualBuildEnv(self, auto_generate=True).vars().apply():
            swig = shutil.which("swig")
        if not swig:
            raise ConanInvalidConfiguration("Declared SWIG is unavailable")
        self.run(shlex.join([swig, "-Wall", "-c++", "-python",
                             "-I" + os.path.join(self.source_folder, "bindings"),
                             "-outdir", generated, "-o", os.path.join(generated, "marisa_wrap.cxx"),
                             os.path.join(self.source_folder, "bindings", "marisa-swig-python3.i")]))
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "upstream_support"))
        cmake.build()
        self.run(shlex.join(["ctest", "--test-dir", self.build_folder,
                             "--output-on-failure", "--no-tests=error", "-j1"]), env=["conanbuild", "conanrun"])
        self.output.info("MARISA_PYTHON_UPSTREAM_RESULT=5/5")
        python = self.dependencies["python"].package_folder
        executable = os.path.join(python, "bin", "python3.12")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration("Published Python 3.12 executable is absent")
        command = ("PYTHONHOME=" + shlex.quote(python) + " PYTHONPATH=" + shlex.quote(generated) + " " +
                   shlex.join([executable, "-B", os.path.join(self.source_folder, "bindings", "python3", "sample.py")]))
        output = io.StringIO()
        self.run(command, stdout=output, env=["conanbuild", "conanrun"])
        text = output.getvalue()
        if not all(item in text for item in ("no. keys: 4", "cockoo: not found", "ice-age: not found")):
            raise ConanInvalidConfiguration("The complete official Python sample did not produce expected results")
        self.output.info(text)
        self.output.info("MARISA_PYTHON_OFFICIAL_SAMPLE=1/1")

    def package(self):
        CMake(self).install()
        module = os.path.join(self.package_folder, "lib", "python3.12", "site-packages", "_marisa.so")
        if str(self.settings.os) == "OHOS":
            self._resign(module)
        for license_file in ("COPYING.md", "AUTHORS"):
            copy(self, license_file, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def _resign(self, module):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        directory = os.path.dirname(compilers.get("cpp", ""))
        tools = {name: os.path.join(directory, name) for name in
                 ("llvm-objcopy", "llvm-readelf", "binary-sign-tool")}
        if not all(os.path.isfile(path) and os.access(path, os.X_OK) for path in tools.values()):
            raise ConanInvalidConfiguration("Current SDK signing tools are required")
        unsigned, signed = module + ".unsigned", module + ".signed"
        if os.path.lexists(unsigned) or os.path.lexists(signed) or not os.path.isfile(module):
            raise ConanInvalidConfiguration("Invalid installed module or stale signing temporary")
        def count(path):
            output = io.StringIO()
            self.run(shlex.join([tools["llvm-readelf"], "-S", path]), stdout=output)
            return sum(".codesign" in line for line in output.getvalue().splitlines())
        if count(module) > 1:
            raise ConanInvalidConfiguration("Duplicate signature sections")
        try:
            shutil.copy2(module, unsigned)
            self.run(shlex.join([tools["llvm-objcopy"], "--remove-section", ".codesign", unsigned]))
            if count(unsigned):
                raise ConanInvalidConfiguration("Old module signature remains")
            self.run(shlex.join([tools["binary-sign-tool"], "sign", "-inFile", unsigned,
                                 "-outFile", signed, "-selfSign", "1"]), stdout=sys.stderr)
            if not os.path.isfile(signed) or count(signed) != 1:
                raise ConanInvalidConfiguration("Fresh module signature is invalid")
            os.chmod(signed, 0o755)
            os.replace(signed, module)
        finally:
            for temporary in (unsigned, signed):
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        python = self.dependencies["python"].package_folder
        for environment in (self.runenv_info, self.buildenv_info):
            environment.prepend_path("PYTHONPATH", site)
            environment.define("MARISA_PYTHONHOME", python)
            environment.define("MARISA_PYTHON_EXECUTABLE", os.path.join(python, "bin", "python3.12"))
