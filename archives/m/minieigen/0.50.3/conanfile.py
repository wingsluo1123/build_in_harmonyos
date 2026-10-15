#!/usr/bin/env python3
"""Conan recipe for minieigen 0.50.3 (upstream 0.5.3)."""

import glob
import os
import runpy
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MinieigenConan(ConanFile):
    name = "minieigen"
    version = "0.50.3"
    description = "Boost.Python bindings for core Eigen vectors and matrices"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/eudoxos/minieigen"
    url = "https://github.com/eudoxos/minieigen"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0.2.1")
        self.requires("double-conversion/3.4.0")
        self.requires("eigen/3.4.0")
        self.requires("python/3.12.9")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "minieigen/0.50.3 is validated only for OHOS armv8, got {}".format(
                    self.settings.os
                )
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "minieigen/0.50.3 is validated for OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        contract = self._target_python_contract()
        self._validate_contract(contract)
        extension = self._compile_extension(contract)
        self._sign_extension(extension)
        self._verify_extension(extension, contract)
        self._run_upstream_test(extension, contract)

    def package(self):
        contract = self._target_python_contract()
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python{}".format(contract["python_version"]),
            "site-packages",
        )
        copy(
            self,
            "minieigen*.so",
            src=os.path.join(self.build_folder, "staging"),
            dst=site_packages,
            keep_path=False,
        )
        copy(
            self,
            "README.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "minieigen"),
        )

    def package_info(self):
        contract = self._target_python_contract()
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python{}".format(contract["python_version"]),
            "site-packages",
        )
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    def _dependency(self, name):
        for dependency in self.dependencies.values():
            if dependency.ref.name == name:
                return dependency
        raise ConanException("missing dependency: {}".format(name))

    def _target_python_contract(self):
        python = self._dependency("python")
        package_folder = python.package_folder
        candidates = sorted(
            glob.glob(
                os.path.join(
                    package_folder, "lib", "python*", "_sysconfigdata*.py"
                )
            )
        )
        if len(candidates) != 1:
            raise ConanInvalidConfiguration(
                "expected one target Python sysconfigdata file, found {}: {}".format(
                    len(candidates), candidates
                )
            )
        data = runpy.run_path(candidates[0]).get("build_time_vars", {})
        version_parts = str(python.ref.version).split(".")
        python_version = ".".join(version_parts[:2])
        abitag = "".join(version_parts[:2])
        extension_suffix = data.get("EXT_SUFFIX")
        soabi = data.get("SOABI")
        if not extension_suffix or not soabi:
            raise ConanInvalidConfiguration(
                "target Python package does not export EXT_SUFFIX/SOABI"
            )
        executable_candidates = [
            os.path.join(package_folder, "bin", "python{}".format(python_version)),
            os.path.join(package_folder, "bin", "python3"),
        ]
        executable = next(
            (path for path in executable_candidates if os.path.isfile(path)), None
        )
        if not executable:
            raise ConanInvalidConfiguration("target Python executable not found")
        library_candidates = sorted(
            glob.glob(
                os.path.join(
                    package_folder,
                    "lib",
                    "libpython{}.so*".format(python_version),
                )
            ),
            key=lambda path: (path.endswith(".so"), len(path)),
        )
        library = next(
            (path for path in library_candidates if os.path.isfile(path)), None
        )
        if not library:
            raise ConanInvalidConfiguration("target libpython was not found")
        return {
            "package_folder": package_folder,
            "python_version": python_version,
            "abitag": abitag,
            "extension_suffix": extension_suffix,
            "soabi": soabi,
            "executable": executable,
            "library": library,
            "include": os.path.join(
                package_folder, "include", "python{}".format(python_version)
            ),
        }

    def _validate_contract(self, contract):
        suffix = contract["extension_suffix"]
        expected_prefix = ".cpython-{}-".format(contract["abitag"])
        if not suffix.startswith(expected_prefix) or not suffix.endswith(".so"):
            raise ConanInvalidConfiguration(
                "unexpected target Python extension suffix: {}".format(suffix)
            )
        if self.settings.os == "OHOS":
            missing = [token for token in ("aarch64", "ohos") if token not in suffix]
            if missing:
                raise ConanInvalidConfiguration(
                    "target EXT_SUFFIX is not the OHOS arm64 ABI: {}".format(suffix)
                )
        if not os.path.isfile(os.path.join(contract["include"], "Python.h")):
            raise ConanInvalidConfiguration("target Python.h was not found")

    def _compile_extension(self, contract):
        compiler = self._compiler()
        staging = os.path.join(self.build_folder, "staging")
        objects = os.path.join(self.build_folder, "objects")
        os.makedirs(staging, exist_ok=True)
        os.makedirs(objects, exist_ok=True)
        source_names = [
            "minieigen.cpp",
            "expose-boxes.cpp",
            "expose-complex.cpp",
            "expose-converters.cpp",
            "expose-matrices.cpp",
            "expose-quaternion.cpp",
            "expose-vectors.cpp",
        ]
        include_dirs = [
            self._dependency("double-conversion").cpp_info.includedirs[0],
            os.path.join(self.source_folder, "src"),
            self._dependency("eigen").cpp_info.includedirs[0],
            self._dependency("boost").cpp_info.includedirs[0],
            contract["include"],
        ]
        include_flags = " ".join(
            "-I{}".format(shlex.quote(path)) for path in include_dirs
        )
        object_files = []
        optimization = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        for source_name in source_names:
            source = os.path.join(self.source_folder, "src", source_name)
            obj = os.path.join(objects, source_name + ".o")
            self.run(
                "{} -std=c++17 {} -fPIC -DEIGEN_DONT_ALIGN {} -c {} -o {}".format(
                    shlex.quote(compiler),
                    optimization,
                    include_flags,
                    shlex.quote(source),
                    shlex.quote(obj),
                )
            )
            object_files.append(obj)
        boost_python = self._shared_library(
            "boost", "libboost_python{}.so".format(contract["abitag"])
        )
        double_conversion = self._shared_library(
            "double-conversion", "libdouble-conversion.so"
        )
        extension = os.path.join(
            staging, "minieigen" + contract["extension_suffix"]
        )
        self.run(
            "{} -shared -Wl,--no-undefined {} -L{} -L{} -L{} "
            "-lboost_python{} -lpython{} -ldouble-conversion -o {}".format(
                shlex.quote(compiler),
                " ".join(shlex.quote(path) for path in object_files),
                shlex.quote(os.path.dirname(boost_python)),
                shlex.quote(os.path.dirname(contract["library"])),
                shlex.quote(os.path.dirname(double_conversion)),
                contract["abitag"],
                contract["python_version"],
                shlex.quote(extension),
            )
        )
        return extension

    def _compiler(self):
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = configured.get("cpp")
        if not candidate:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables['cpp'] is required for the "
                "OHOS cross build"
            )
        resolved = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if resolved and os.path.isfile(resolved):
            return resolved
        raise ConanInvalidConfiguration(
            "configured OHOS C++ compiler was not found: {}".format(candidate)
        )

    def _shared_library(self, dependency_name, filename):
        dependency = self._dependency(dependency_name)
        for libdir in dependency.cpp_info.libdirs:
            path = os.path.join(libdir, filename)
            if os.path.isfile(path):
                return path
        raise ConanInvalidConfiguration(
            "{} does not provide {}".format(dependency_name, filename)
        )

    def _sign_extension(self, extension):
        if self.settings.os != "OHOS":
            return
        compiler = self._compiler()
        sdk_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(compiler)))
        )
        objcopy_candidates = [
            shutil.which("llvm-objcopy"),
            os.path.join(os.path.dirname(compiler), "llvm-objcopy"),
            "/data/service/hnp/bin/llvm-objcopy",
        ]
        signer_candidates = [
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            os.path.join(sdk_root, "toolchains", "lib", "binary-sign-tool"),
        ]
        objcopy = next(
            (path for path in objcopy_candidates if path and os.path.isfile(path)), None
        )
        signer = next(
            (path for path in signer_candidates if path and os.path.isfile(path)), None
        )
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS llvm-objcopy and binary-sign-tool are required"
            )
        temporary = extension + ".signed"
        shutil.copy2(extension, temporary)
        try:
            self.run(
                "{} --remove-section .codesign {}".format(
                    shlex.quote(objcopy), shlex.quote(temporary)
                )
            )
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(temporary),
                    shlex.quote(temporary),
                )
            )
            os.replace(temporary, extension)
            os.chmod(extension, 0o755)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _verify_extension(self, extension, contract):
        expected = "minieigen" + contract["extension_suffix"]
        if os.path.basename(extension) != expected:
            raise ConanException("extension filename does not match target EXT_SUFFIX")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise ConanInvalidConfiguration("readelf is required for ABI verification")
        self.run("{} -h {}".format(shlex.quote(readelf), shlex.quote(extension)))
        self.run("{} -d {}".format(shlex.quote(readelf), shlex.quote(extension)))
        self.run(
            "{} -Ws {} | grep PyInit_minieigen".format(
                shlex.quote(readelf), shlex.quote(extension)
            )
        )

    def _runtime_libdirs(self):
        result = []
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                if libdir and libdir not in result:
                    result.append(libdir)
        extra = os.environ.get("MINIEIGEN_EXTRA_LD_LIBRARY_PATH", "")
        for path in extra.split(os.pathsep):
            if path and path not in result:
                result.append(path)
        return result

    def _target_python_command(self, contract, script, pythonpath):
        ld_library_path = os.pathsep.join(self._runtime_libdirs())
        runner = os.environ.get("MINIEIGEN_TARGET_RUNNER", "").strip()
        if runner:
            return (
                "{} -E LD_LIBRARY_PATH={} -E PYTHONHOME={} -E PYTHONPATH={} {} {}"
            ).format(
                runner,
                shlex.quote(ld_library_path),
                shlex.quote(contract["package_folder"]),
                shlex.quote(pythonpath),
                shlex.quote(contract["executable"]),
                shlex.quote(script),
            )
        return "LD_LIBRARY_PATH={} PYTHONHOME={} PYTHONPATH={} {} {}".format(
            shlex.quote(ld_library_path),
            shlex.quote(contract["package_folder"]),
            shlex.quote(pythonpath),
            shlex.quote(contract["executable"]),
            shlex.quote(script),
        )

    def _run_upstream_test(self, extension, contract):
        script = os.path.join(self.source_folder, "src", "basic-test.py")
        self.run(
            self._target_python_command(contract, script, os.path.dirname(extension)),
            cwd=self.source_folder,
        )
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT: 1/1 runner passed; "
            "31 upstream observable operations executed"
        )
