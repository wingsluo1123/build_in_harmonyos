#!/usr/bin/env python3
"""Conan recipe for Qt Multimedia 6.11.1 (CMake).

6.11.1.1 — same upstream sources, packaging fix: the Qt install emits
libQt6MultimediaWidgets/libQt6SpatialAudio WITHOUT a SONAME and with a
relative NEEDED ('../../lib/libQt6Multimedia.so').  Dependents therefore
inherit path-shaped NEEDED entries and dlopen fails at runtime
("Error loading shared library ../../lib/libQt6Multimedia.so").  Normalise
SONAME/NEEDED after install and re-sign, so consumers link by soname.
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class QtMultimediaConan(ConanFile):
    name = "qtmultimedia"
    version = "6.11.1.1"
    description = "Qt Multimedia module (audio, video, camera APIs)"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtmultimedia-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "qtshadertools/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qtmultimedia supports Linux and OHOS"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtshadertools = self.dependencies["qtshadertools"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6ShaderTools_DIR"] = os.path.join(
            qtshadertools, "lib", "cmake", "Qt6ShaderTools"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = True
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = True
        tc.variables["QT_BUILD_EXAMPLES"] = False
        tc.variables["QT_BUILD_EXAMPLES_BY_DEFAULT"] = False
        tc.variables["QT_BUILD_BENCHMARKS"] = False
        tc.variables["QT_BUILD_MANUAL_TESTS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def _ctest_executable(self):
        for candidate in (
            shutil.which("ctest"),
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest",
        ):
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("ctest executable was not found")

    def _locate_build_dir(self, rel_path):
        """Locate a directory inside the CMake build tree regardless of generator layout."""
        candidates = [
            os.path.join(self.build_folder, rel_path),
            os.path.join(self.build_folder, "Release", rel_path),
            os.path.join(self.build_folder, "Debug", rel_path),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return candidates[0]

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # The Qt Shader Baker (qsb) host tool runs during the build to
        # pre-compile shaders; export LD_LIBRARY_PATH so it can load
        # libQt6ShaderTools/libQt6Core from the dependency packages.
        qt_libs = self._locate_build_dir("lib")
        qtbase_lib = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib"
        )
        qtshadertools_lib = os.path.join(
            self.dependencies["qtshadertools"].package_folder, "lib"
        )
        library_path = os.pathsep.join(
            path for path in (qt_libs, qtbase_lib, qtshadertools_lib) if path
        )
        self.run(
            "cmake -E env LD_LIBRARY_PATH={} cmake --build \"{}\" "
            "--parallel 4".format(
                shlex.quote(library_path),
                self.build_folder,
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.output.info(
                "Running configured upstream Qt Multimedia auto tests with "
                "the Conan runtime environment"
            )
            ctest = self._ctest_executable()
            build_root = self.build_folder
            if os.path.basename(build_root) in ("Release", "Debug", "RelWithDebInfo"):
                build_root = os.path.dirname(build_root)
            build_lib = os.path.join(build_root, "lib")
            if (
                not os.path.lexists(build_lib)
                and os.path.isdir(qt_libs)
                and os.path.realpath(build_lib) != os.path.realpath(qt_libs)
            ):
                try:
                    relative_target = os.path.relpath(qt_libs, build_root)
                    os.symlink(relative_target, build_lib)
                    self.output.info(
                        "Linked %s -> %s for Qt test NEEDED paths",
                        build_lib,
                        relative_target,
                    )
                except (OSError, AttributeError):
                    self.output.info(
                        "Could not create build/lib symlink; "
                        "relative NEEDED tests may fail"
                    )
            self.run(
                "cmake -E env LD_LIBRARY_PATH={} \"{}\" --test-dir \"{}\" "
                "--output-on-failure -j1 "
                "-R '^(module_includes|tst_multiapp|tst_qaudiobuffer|"
                "tst_qaudiohelpers|tst_qaudiorecorder|tst_qaudioringbuffer|"
                "tst_qerrorinfo|tst_qmediaformatbackend|tst_qmediametadata|"
                "tst_qmediaplayer|tst_qmediarecorder|"
                "tst_qmediastoragelocation|tst_qrhivaluemapper|"
                "tst_qsamplecache|tst_qsoundeffect_concurrent|"
                "tst_qvideobuffers|tst_qvideoframe_nogui|"
                "tst_qvideotransformation)$'".format(
                    shlex.quote(library_path),
                    ctest,
                    self.build_folder,
                ),
                env="conanbuild",
            )
        else:
            self.output.info(
                "Cross-building: upstream Qt Multimedia tests require "
                "a runnable target"
            )

    # ── SONAME normalisation ─────────────────────────────────────────────

    @staticmethod
    def _tool(name):
        for d in ("/data/service/hnp/bin",
                  "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/"
                  "native/llvm/bin",
                  "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/"
                  "toolchains/lib",
                  "/storage/Users/currentUser/usr/local/bin"):
            cand = os.path.join(d, name)
            if os.path.exists(cand):
                return cand
        return shutil.which(name)

    def _sign_elf(self, path, objcopy, signer):
        """Self-sign an ELF so OHOS will dlopen it."""
        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    return
        except OSError:
            return
        tmp = path + ".signed"
        st = os.stat(path)
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=120)
        r = subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp,
                            "-selfSign", "1"],
                           capture_output=True, timeout=600)
        if r.returncode != 0 or not os.path.exists(tmp) \
                or os.path.getsize(tmp) == 0:
            raise ConanInvalidConfiguration("ELF signing failed: %s" % path)
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, path)

    def _normalise_sonames(self):
        """Give every installed Qt6 lib a SONAME and basename-only NEEDED.

        The Qt install for this platform leaves libQt6MultimediaWidgets and
        libQt6SpatialAudio without a SONAME and with a relative
        NEEDED ('../../lib/libQt6Multimedia.so'); anything linking against
        them records that path and fails to dlopen at runtime in a consumer
        tree.  Rewriting here (before the package is sealed) is the real fix
        — consumers can then link by soname like any well-formed library.
        """
        patchelf = self._tool("patchelf")
        objcopy = self._tool("llvm-objcopy")
        signer = self._tool("binary-sign-tool")
        if not (patchelf and objcopy and signer):
            self.output.warning(
                "patchelf/objcopy/signer missing — SONAME left as shipped")
            return

        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return

        def run(*args):
            return subprocess.run([patchelf] + list(args),
                                  capture_output=True, text=True, timeout=300)

        fixed = 0
        for name in sorted(os.listdir(libdir)):
            if not (name.startswith("libQt6") and ".so" in name):
                continue
            lib = os.path.join(libdir, name)
            if not os.path.isfile(lib) or os.path.islink(lib):
                continue
            soname = (run("--print-soname", lib).stdout or "").strip()
            needed = (run("--print-needed", lib).stdout or "").split()
            bad = [n for n in needed if "/" in n]
            if soname and not bad:
                continue
            if not soname:
                # name may be libFoo.so.6.11.1 -> SONAME should be libFoo.so.6
                target = name
                parts = name.split(".so")
                if len(parts) == 2 and parts[1].startswith("."):
                    major = parts[1].split(".")[1] if len(
                        parts[1].split(".")) > 1 else ""
                    if major:
                        target = parts[0] + ".so." + major
                run("--set-soname", target, lib)
            for n in bad:
                run("--replace-needed", n, os.path.basename(n), lib)
            self._sign_elf(lib, objcopy, signer)
            fixed += 1
        if fixed:
            self.output.info("normalised SONAME/NEEDED on %d lib(s)" % fixed)

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._normalise_sonames()

    def package_info(self):
        self.cpp_info.libs = ["Qt6Multimedia"]
        # Qt installs complete Qt6MultimediaConfig.cmake files. Reuse them so
        # consumers keep the upstream Qt6::Multimedia target and avoid a
        # generated CMakeDeps config that would search for qtbaseConfig.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
