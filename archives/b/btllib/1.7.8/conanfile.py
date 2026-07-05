#!/usr/bin/env python3
"""Conan recipe — btllib 1.7.8 (Meson project).

btllib is a Birol Lab Library - bioinformatics C++ toolkit.
The GitHub archive doesn't include git submodules (cpptoml, sdsl-lite, argparse).
sdsl-lite itself has sub-submodules (libdivsufsort, googletest).
We pre-download all of them, fix CMake version issues, then configure with Meson.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout


class BtllibConan(ConanFile):
    name = "btllib"
    version = "1.7.8"
    description = "Birol Lab Library - bioinformatics C++ toolkit"
    license = "MIT"
    homepage = "https://github.com/BirolLab/btllib"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "static"
        tc.generate()

    def _fix_cmake_min_version(self, filepath):
        """Fix cmake_minimum_required and deprecated cmake_policy for CMake 4.x."""
        if not os.path.exists(filepath):
            return
        with open(filepath, "r") as f:
            content = f.read()
        # Replace cmake_minimum_required with 3.5...4.1
        content = re.sub(
            r'cmake_minimum_required\(VERSION\s+[\d.]+\s*\)',
            'cmake_minimum_required(VERSION 3.5...4.1)',
            content
        )
        # Fix deprecated cmake_policy CMP0048 OLD (not supported in CMake 4.x)
        content = re.sub(
            r'cmake_policy\s*\(\s*SET\s+CMP0048\s+OLD\s*\)',
            'cmake_policy(SET CMP0048 NEW)',
            content
        )
        # Remove any other OLD policy settings that CMake 4.x doesn't support
        content = re.sub(
            r'cmake_policy\s*\(\s*SET\s+CMP\d+\s+OLD\s*\)',
            '# cmake_policy SET OLD removed for CMake 4.x compatibility',
            content
        )
        with open(filepath, "w") as f:
            f.write(content)

    def _download_submodule(self, dest, url, name):
        """Download and extract a git submodule to dest if dest is empty."""
        if os.path.isdir(dest) and not os.listdir(dest):
            tmp_extract = os.path.join(os.path.dirname(dest), f"_tmp_{name}")
            os.makedirs(tmp_extract, exist_ok=True)
            try:
                get(self, url=url, strip_root=True, destination=tmp_extract)
                for item in os.listdir(tmp_extract):
                    src_item = os.path.join(tmp_extract, item)
                    dst_item = os.path.join(dest, item)
                    shutil.move(src_item, dst_item)
                os.rmdir(tmp_extract)
                self.output.info(f"Downloaded submodule: {name}")
                return True
            except Exception as e:
                self.output.warning(f"Failed to download {name} from {url}: {e}")
                try:
                    os.rmdir(tmp_extract)
                except OSError:
                    pass
                return False
        return True  # Already populated

    def build(self):
        apply_conandata_patches(self)

        hnp_bin = "/data/service/hnp/bin"
        if hnp_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = hnp_bin + ":" + os.environ.get("PATH", "")
        os.environ["AR"] = "/data/service/hnp/bin/llvm-ar"
        os.environ["CC"] = "/data/service/hnp/bin/clang"
        os.environ["CXX"] = "/data/service/hnp/bin/clang++"

        mirror = "https://ghfast.top/"
        subprojects_dir = os.path.join(self.source_folder, "subprojects")

        # Level 1: btllib submodules
        self._download_submodule(
            os.path.join(subprojects_dir, "cpptoml"),
            mirror + "https://github.com/skystrife/cpptoml/archive/master.tar.gz",
            "cpptoml"
        )
        self._download_submodule(
            os.path.join(subprojects_dir, "sdsl-lite"),
            mirror + "https://github.com/simongog/sdsl-lite/archive/master.tar.gz",
            "sdsl-lite"
        )
        self._download_submodule(
            os.path.join(subprojects_dir, "argparse"),
            mirror + "https://github.com/p-ranav/argparse/archive/master.tar.gz",
            "argparse"
        )

        # Level 2: sdsl-lite sub-submodules
        sdsl_external = os.path.join(subprojects_dir, "sdsl-lite", "external")
        self._download_submodule(
            os.path.join(sdsl_external, "libdivsufsort"),
            mirror + "https://github.com/simongog/libdivsufsort/archive/master.tar.gz",
            "libdivsufsort"
        )
        self._download_submodule(
            os.path.join(sdsl_external, "googletest"),
            mirror + "https://github.com/google/googletest/archive/main.tar.gz",
            "googletest"
        )

        # Fix CMake version compatibility in all subproject CMakeLists.txt files
        cmake_files_to_fix = [
            os.path.join(subprojects_dir, "cpptoml", "CMakeLists.txt"),
            os.path.join(subprojects_dir, "sdsl-lite", "CMakeLists.txt"),
            os.path.join(sdsl_external, "libdivsufsort", "CMakeLists.txt"),
            os.path.join(sdsl_external, "googletest", "CMakeLists.txt"),
            os.path.join(sdsl_external, "googletest", "googletest", "CMakeLists.txt"),
        ]
        for cmake_file in cmake_files_to_fix:
            self._fix_cmake_min_version(cmake_file)

        # Patch sdsl-lite external/CMakeLists.txt:
        # 1. Remove broken EXECUTE_PROCESS calls (empty git submodule init)
        # 2. Skip googletest (only needed for tests, CMake 4.x incompatibility)
        ext_cmake = os.path.join(sdsl_external, "CMakeLists.txt")
        if os.path.exists(ext_cmake):
            with open(ext_cmake, "r") as f:
                content = f.read()
            # Remove EXECUTE_PROCESS calls with empty COMMAND
            content = re.sub(
                r'if\(NOT EXISTS [^\)]+\)\s*\n\s*EXECUTE_PROCESS\(COMMAND ;.*?endif\(NOT EXISTS [^\)]+\)',
                '',
                content,
                flags=re.DOTALL
            )
            # Skip googletest subdirectory (only needed for unit tests)
            content = content.replace(
                "add_subdirectory(googletest/googletest)",
                "# googletest skipped (not needed for release build)"
            )
            with open(ext_cmake, "w") as f:
                f.write(content)

        # Skip Python wrappers (get-python-flags script fails due to OHOS getcwd issue)
        wrappers_meson = os.path.join(self.source_folder, "wrappers", "meson.build")
        if os.path.exists(wrappers_meson):
            with open(wrappers_meson, "w") as f:
                f.write("message('Python wrappers skipped for OHOS build.')\n")

        # Fix strerror_r return type issue (OHOS uses POSIX version, not GNU)
        status_cpp = os.path.join(self.source_folder, "src", "btllib", "status.cpp")
        if os.path.exists(status_cpp):
            with open(status_cpp, "r") as f:
                content = f.read()
            # Replace the GNU strerror_r branch with POSIX behavior
            content = content.replace(
                "#else\n  return strerror_r(errno, buf, buflen);\n#endif",
                "#else\n  strerror_r(errno, buf, buflen);\n  return buf;\n#endif"
            )
            with open(status_cpp, "w") as f:
                f.write(content)

        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["btllib"]
