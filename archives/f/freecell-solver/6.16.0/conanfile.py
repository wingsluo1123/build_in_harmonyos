#!/usr/bin/env python3
"""Conan recipe for Freecell Solver 6.16.0 on HarmonyOS PC.

Upstream ships a C library plus command-line solvers and board generators:

  - lib/libfreecell-solver.so  — solver API (fcs_user.h / fcs_move.h)
  - bin/fc-solve, freecell-solver-range-parallel-solve,
    freecell-solver-fc-pro-range-solve
  - bin/pi-make-microsoft-freecell-board and five Python board helpers
  - include/freecell-solver/ + lib/pkgconfig/libfreecell-solver.pc

The upstream CMake project lives in ``fc-solve/source`` of the release
tarball (the tarball also carries docs and the scripts/ generators), so
every build step is rooted there.  The release does not bundle the
rinutils headers its CMakeLists includes; the recipe stages rinutils
0.6.0 at ``fc-solve/source/rinutils``, the exact path
cmake/rinutils_bootstrap.cmake expects.

Dependencies (all real, each one checked against the upstream CMakeLists):

  - gperf/3.3 (tool)             — FIND_PROGRAM(_GPERF ...) FATAL_ERROR
  - libpath-tiny-perl/0.118 (tool) — every configure/build generator
    (gen-c-lookup-files.pl, gen-cmd-line-radix-tree.pl, gen-presets.pl,
    gen-move-funcs.pl, gen-man-page.pl, t/generate-card-tests.pl) does
    ``use Path::Tiny``; the OHOS Perl has no CPAN
  - cmocka/2.0.2 (test)          — the upstream C unit-test programs in t/

OHOS specifics:

  - CMake 4.1 has no Platform/HarmonyOS.cmake; a
    ``_cmake_modules/Platform/HarmonyOS.cmake`` shim includes
    Platform/Linux (fluidsynth 2.5.7 pattern), keeping the native
    HarmonyOS platform name instead of faking a Linux cross build.
  - HMDFS rejects symlink(): CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE
    emits a single unversioned libfreecell-solver.so with a bare
    DT_SONAME (E330).
  - The upstream RPATH block bakes CMAKE_INSTALL_FULL_LIBDIR into every
    executable; DISABLE_APPLYING_RPATH=ON keeps the package relocatable
    and a $ORIGIN-based install RPATH lets the installed CLI tools find
    the library in place (L2 smoke test runs them directly).
  - /tmp is read-only and Path::Tiny->tempdir honours TMPDIR; point it at
    $HOME/tmp.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)

# The tarball root is the CMake source tree (fc-solve/source in the upstream
# repository), staged under this prefix so the patch headers and the
# rinutils bootstrap expectations line up.
_UPSTREAM_ROOT = "fc-solve/source"

# The five C unit-test programs the adaptation registers with CTest
# (upstream only registers the Perl run-tests.pl harness).
_CTEST_PROGRAMS = (
    "card-test-render.t.exe",
    "card-test-parse.t.exe",
    "bit-reader-and-writer-test.t.exe",
    "dbm-kaztree-compare-records-test.t.exe",
)
_CTEST_DELTA_PROGRAMS = {
    "delta-states-debondt-test.t.exe",
    "delta-states-test.t.exe",
}


class FreecellSolverConan(ConanFile):
    name = "freecell-solver"
    version = "6.16.0"
    description = (
        "Freecell Solver — C library and command-line tools that solve "
        "Freecell and similar card solitaire games"
    )
    license = "MIT"
    homepage = "https://fc-solve.shlomifish.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # configure-time hard requirement (FIND_PROGRAM + FATAL_ERROR).
        self.tool_requires("gperf/3.3")
        # All configure/build Perl generators use Path::Tiny.
        self.tool_requires("libpath-tiny-perl/0.118")
        # Upstream C unit tests in t/ are built and run through CTest.
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Stage the CMake project at fc-solve/source (its repository path).
        get(
            self,
            **self.conan_data["sources"],
            destination=os.path.join(self.source_folder, "fc-solve", "source"),
            strip_root=True,
        )
        # rinutils 0.6.0 -> fc-solve/source/rinutils/rinutils/include/...
        rinutils = self.conan_data["additional_sources"]["rinutils"]
        get(
            self,
            **rinutils,
            destination=os.path.join(
                self.source_folder, "fc-solve", "source", "rinutils"
            ),
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Never bake the conan cache prefix into installed binaries.
        tc.variables["DISABLE_APPLYING_RPATH"] = True
        # The main library is shared-only upstream (ADD_LIBRARY ... SHARED);
        # the optional static twin only doubles build time.
        tc.variables["BUILD_STATIC_LIBRARY"] = False
        # Upstream test suite: enabled, but the Perl harness and the
        # Perl-generated .t scripts need CPAN modules absent on OHOS.
        tc.variables["FCS_WITH_TEST_SUITE"] = True
        tc.variables["FCS_SKIP_PERL_TEST_HARNESS"] = True
        tc.variables["FCS_SKIP_PERL_GENERATED_TESTS"] = True
        tc.variables["SKIP_PERL_TESTING_TASK_CHECK"] = True

        if str(self.settings.os) == "OHOS":
            platform_modules = os.path.join(self.build_folder, "_cmake_modules")
            save(
                self,
                os.path.join(platform_modules, "Platform", "HarmonyOS.cmake"),
                "include(Platform/Linux)\n",
            )
            tc.variables["CMAKE_MODULE_PATH"] = ";".join(
                (platform_modules, self.generators_folder)
            )
            # HMDFS rejects the versioned symlink chain (E330).
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
            # Relocatable lookups for the installed CLI tools.
            tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN:$ORIGIN/../lib"
            tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
            # OHOS loader: pin the 4K segment layout (analitza precedent).
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        self._define_build_environment()
        CMakeDeps(self).generate()
        tc.generate()

    def _define_build_environment(self):
        # Path::Tiny for the Perl generators; the package installs the
        # module tree at lib/perl5 (libpath-tiny-perl 0.118 layout).
        perl_tiny = self.dependencies.build.get("libpath-tiny-perl")
        if perl_tiny and perl_tiny.package_folder:
            self.buildenv.prepend_path(
                "PERL5LIB",
                os.path.join(perl_tiny.package_folder, "lib", "perl5"),
            )
        # Path::Tiny->tempdir and pod2man-wrapper.pl honour TMPDIR; /tmp is
        # read-only on the device.
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.buildenv.define("TMPDIR", tmpdir)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=_UPSTREAM_ROOT)
        cmake.build(build_tool_args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if not can_run(self) or self.conf.get(
            "tools.build:skip_test", default=False
        ):
            self.output.info(
                "NOT_RUN FREECELL_SOLVER_UPSTREAM_TESTS=0/5 "
                "reason=cross_building_or_skip_test"
            )
            return

        test_dir = os.path.join(self.build_folder, "t")
        expected = [name for name in _CTEST_PROGRAMS]
        delta_present = [
            name
            for name in sorted(_CTEST_DELTA_PROGRAMS)
            if os.path.isfile(os.path.join(test_dir, name))
        ]
        if len(delta_present) != 1:
            raise ConanInvalidConfiguration(
                "expected exactly one upstream delta-states test program, "
                f"found {delta_present}"
            )
        expected.append(delta_present[0])
        missing = [
            name
            for name in expected
            if not os.path.isfile(os.path.join(test_dir, name))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "upstream C test programs were not built: " + ", ".join(missing)
            )

        self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                self.build_folder
            ),
            env="conanbuild",
        )
        self.output.info(
            f"FREECELL_SOLVER_UPSTREAM_TESTS={len(expected)}/{len(expected)}"
        )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next(
            (path for path in candidates if path and os.path.isfile(path)), ""
        )

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        """CMake rewrites the RUNPATH of installed binaries, which invalidates
        the OHOS build-time .codesign section; the loader then refuses them
        ("Permission denied"). Re-sign every packaged ELF (analitza/ki18n
        precedent)."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") \
                or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    "{} --remove-section .codesign {}".format(
                        self._quote(objcopy), self._quote(path)
                    ),
                    ignore_errors=True,
                )
                self.run(
                    "{} sign -inFile {} -outFile {} -selfSign 1".format(
                        self._quote(signer), self._quote(path),
                        self._quote(path)
                    )
                )
                signed += 1
        self.output.info(
            "Signed {} OHOS package ELF file(s)".format(signed)
        )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING.txt",
            src=os.path.join(self.source_folder, *_UPSTREAM_ROOT.split("/")),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["freecell-solver"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "freecell-solver")
        self.cpp_info.set_property(
            "cmake_target_name", "freecell-solver::freecell-solver"
        )
        self.cpp_info.set_property("pkg_config_name", "libfreecell-solver")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
