#!/usr/bin/env python3
"""Conan recipe — irony-mode 1.6.1

Emacs irony-mode: C/C++ code completion & syntax checking for Emacs.
The buildable, portable component is `irony-server`, a C++11 executable
wrapping libclang that serves the Emacs Lisp client over a line protocol
(the .el frontend is distributed via MELPA and intentionally NOT part of
this package — same client/server split as emacs-clang-complete-async).

Build system: CMake, with CMakeLists.txt only under server/. The tarball
layout must be preserved: server/src/CMakeLists.txt derives the package
version from `../irony.el`, so the CMake source dir is <source>/server
(handled via CMake.configure(build_script_folder="server")).

Dependency note (R36/R33): libclang is NOT available as a Conan package
(archives/l/llvm is built with LLVM_ENABLE_PROJECTS="" and ships no
libclang). It is provided by the OHOS system SDK (LLVM/Clang 15.0.4),
discovered dynamically via `llvm-config` (PATH from the Conan profile
buildenv, no hardcoded paths).

Upstream's find_package(Clang) config mode CANNOT be used with this SDK:
the exported LLVMExports.cmake/ClangTargets.cmake import static archive
targets (libLLVMDemangle.a, libclangBasic.a, ...) that the SDK does not
ship, and CMake hard-errors on them while including those files. So we
set CMAKE_DISABLE_FIND_PACKAGE_Clang=TRUE and drive upstream's fallback
FindLibClang.cmake module with LIBCLANG_INCLUDE_DIR/LIBCLANG_LIBRARY
plus CLANG_RESOURCE_DIR (via `clang -print-resource-dir`, needed at
runtime for libclang builtin headers — TUManager.cpp passes
-resource-dir when it is defined).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import export_conandata_patches, get


class IronyModeConan(ConanFile):
    name = "irony-mode"
    version = "1.6.1"
    description = "irony-server: libclang-based C/C++ completion server for the Emacs irony-mode package"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Sarcasm/irony-mode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libclang comes from the OHOS system SDK (see module docstring),
        # not from a Conan package — deliberately no self.requires() (R36).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # strip_root keeps the tarball layout: irony.el sits next to server/,
        # which upstream's version detection (../irony.el) depends on.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: application package — no shared libraries of our own.
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        # Upstream declares cmake_minimum_required(3.0.2...3.27); the device
        # ships CMake 4.x which removed <3.5 compatibility. Must be a cache
        # variable (command line), not a plain toolchain variable —
        # cmake_minimum_required is processed before project() and would
        # never see a value set inside conan_toolchain.cmake.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # The SDK's Clang config package (ClangConfig.cmake → LLVMExports.cmake)
        # imports static-archive targets that the SDK does not ship; CMake
        # aborts while including them. Force upstream's fallback FindLibClang.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Clang"] = True
        # R33: discover the system SDK LLVM via llvm-config/clang on PATH —
        # no hardcoded paths.
        llvm_prefix = self._query_llvm_config("--prefix")
        llvm_incdir = self._query_llvm_config("--includedir")
        llvm_libdir = self._query_llvm_config("--libdir")
        # CMAKE_PREFIX_PATH feeds FindLibClang's find_path/find_library default
        # search as a base; the explicit LIBCLANG_* cache vars below pin the
        # result deterministically when llvm-config answered.
        if llvm_prefix:
            tc.cache_variables["CMAKE_PREFIX_PATH"] = llvm_prefix
        if llvm_incdir:
            tc.cache_variables["LIBCLANG_INCLUDE_DIR"] = llvm_incdir
        if llvm_libdir:
            tc.cache_variables["LIBCLANG_LIBRARY"] = os.path.join(
                llvm_libdir, "libclang.so")
        # CLANG_RESOURCE_DIR: libclang cannot locate its builtin headers
        # relative to itself; TUManager.cpp passes -resource-dir when this is
        # defined. The SDK clang is resolved from the llvm-config prefix: a
        # bare PATH lookup proved unreliable in generate() (CI run2 logged
        # "error running ['clang', '-print-resource-dir'] ([Errno 2] No such
        # file or directory: 'clang')" while the llvm-config queries in the
        # same phase resolved fine), so the prefix-derived absolute path is
        # the primary source. Injecting the variable also short-circuits
        # upstream's check_clang_resource_dir() try_run probe (its layout and
        # version-suffix heuristics do not cover LLVM 15).
        resource_dir = self._discover_clang_resource_dir(llvm_prefix)
        if resource_dir:
            tc.cache_variables["CLANG_RESOURCE_DIR"] = resource_dir
        else:
            self.output.warning(
                "CLANG_RESOURCE_DIR could not be discovered; irony-server "
                "may fail to parse translation units at runtime (clang "
                "builtin headers not locatable)")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # CMakeLists.txt lives under server/ only; the sibling ../irony.el
        # must stay reachable for upstream version detection.
        cmake.configure(build_script_folder="server")
        cmake.build()

    def package(self):
        # Upstream install rule:
        #   install(TARGETS irony-server DESTINATION ${CMAKE_INSTALL_BINDIR})
        cmake = CMake(self)
        cmake.install()

        # OHOS: ELF binaries must be signed to be executable.
        # R33: discover signing tools dynamically via PATH (shutil.which),
        # never hardcode absolute paths — release CI workers may differ.
        bindir = os.path.join(self.package_folder, "bin")
        binary = os.path.join(bindir, "irony-server")
        if os.path.isfile(binary) and self.settings.os in ("Linux", "OHOS"):
            signer = shutil.which("binary-sign-tool")
            if signer is None:
                # Signing tool absent on this worker: skip, but record an
                # explicit warning rather than silently swallowing it.
                self.output.warning(
                    "binary-sign-tool not found in PATH; skipping binary "
                    "signing (irony-server may fail to execute on OHOS)")
            else:
                objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
                if objcopy:
                    # Idempotent prep: drop any pre-existing .codesign
                    # section (expected absent on a fresh build; tolerate).
                    self.run(
                        f'{objcopy} --remove-section .codesign "{binary}" || true',
                        ignore_errors=True)
                # Sign — failures here must abort the build.
                self.run(
                    f'{signer} sign -inFile "{binary}" -outFile "{binary}" -selfSign 1')

    def package_info(self):
        # Application package: the artifact is bin/irony-server.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # Runtime: libclang.so from the system SDK. An instance var set in
        # build() does NOT survive Conan's recipe re-instantiation during
        # test_package runenv generation, so query llvm-config again here
        # (subprocess is read-only, no Conan self.run side effects).
        # Use append_path (not define) so VirtualRunEnv serializes
        # LD_LIBRARY_PATH into conanrun.sh.
        if self.settings.os in ("Linux", "OHOS"):
            llvm_libdir = self._query_llvm_config("--libdir")
            if llvm_libdir:
                self.runenv_info.append_path("LD_LIBRARY_PATH", llvm_libdir)

    def _discover_clang_resource_dir(self, llvm_prefix):
        """Locate the clang resource dir (builtin headers) for libclang.

        Order: `clang -print-resource-dir` (clang resolved via PATH, then via
        the llvm-config prefix), then the structural <prefix>/lib/clang/<ver>
        layout (stddef.h must exist). Returns "" when nothing checks out
        (R33: no hardcoded absolute paths).
        """
        candidates = []
        which_clang = shutil.which("clang")
        if which_clang:
            candidates.append(which_clang)
        if llvm_prefix:
            candidates.append(os.path.join(llvm_prefix, "bin", "clang"))
        for clang in candidates:
            resource_dir = self._query_cmd([clang, "-print-resource-dir"])
            if resource_dir:
                return resource_dir
        # Structural fallback: <prefix>/lib/clang/<LLVM version>/include/stddef.h
        if llvm_prefix:
            clang_root = os.path.join(llvm_prefix, "lib", "clang")
            try:
                versions = [
                    d for d in os.listdir(clang_root)
                    if os.path.isfile(
                        os.path.join(clang_root, d, "include", "stddef.h"))
                ]
            except OSError:
                versions = []
            if versions:
                versions.sort(key=lambda v: [
                    int(p) if p.isdigit() else -1 for p in v.split(".")])
                return os.path.join(clang_root, versions[-1])
        return ""

    def _query_llvm_config(self, flag, llvm_config="llvm-config"):
        """Query the system SDK llvm-config for --prefix / --libdir etc.

        Returns "" if llvm-config is unavailable or fails (R33: no
        hardcoded paths; PATH comes from the Conan profile buildenv).
        """
        exe = shutil.which(llvm_config)
        if not exe:
            self.output.warning(
                f"{llvm_config} not found in PATH; cannot query {flag}")
            return ""
        return self._query_cmd([exe, flag])

    def _query_cmd(self, argv):
        """Run a read-only discovery command, returning its stripped stdout
        ("" on any failure). Never raises, no Conan self.run side effects."""
        try:
            res = subprocess.run(argv, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, check=False)
        except Exception as e:
            self.output.warning(f"error running {argv} ({e})")
            return ""
        if res.returncode != 0:
            self.output.warning(
                f"{' '.join(argv)} failed (rc={res.returncode})")
            return ""
        return res.stdout.strip()
