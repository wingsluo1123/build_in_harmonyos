#!/usr/bin/env python3
"""Conan recipe for libQuotient 0.8.0 (Qt6 flavour) on HarmonyOS PC.

libQuotient is the Matrix client-server library behind Quaternion/NeoChat.
0.8.0 is the last upstream line that still supports Qt5 and Qt6 side by
side; this recipe builds the Qt6 flavour (BUILD_WITH_QT6=ON), which is what
the HarmonyOS PC qtbase-sql-dbus package provides. All adaptation stays on
the Conan/CMake layer -- the upstream sources are built unmodified:

  * E2EE (Olm/OpenSSL/QtSql) keeps the upstream default OFF, since the
    platform does not ship the libolm ratchet library; the HTTP connection
    layer, the event/room models and the complete public API are unaffected.
  * BUILD_TESTING=ON compiles and runs the upstream autotest suite
    (callcandidateseventtest, utiltests) via ctest inside conan create.
    quotest -- the upstream manual integration suite that needs a live
    homeserver -- is compiled as a build smoke test but not executed (it is
    not registered with ctest upstream).
  * Quotient_INSTALL_TESTS=OFF keeps bin/quotest out of the package (this
    is a library deliverable).
  * OHOS /storage rejects symlink creation (XPM EPERM; plain Linux has no
    such constraint). The library is built with VERSION 0.8.0 / SOVERSION
    0.8, whose build-graph step `cmake -E cmake_symlink_library` (a ninja
    rule or a Makefile link recipe, depending on the generator) would fail
    the build; on OHOS the step is rewritten to per-path real copies
    (lfortran 0.64.0 precedent), which the dynamic loader resolves
    identically.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibQuotientConan(ConanFile):
    name = "libquotient"
    version = "0.8.0"
    description = "Multi-platform library for building Matrix clients (Qt6 build)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/quotient-im/libQuotient"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtkeychain/0.14.2")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_WITH_QT6"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["Quotient_ENABLE_E2EE"] = "OFF"
        tc.variables["Quotient_INSTALL_TESTS"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        self._define_cmake_paths(tc)
        tc.generate()

    def _define_cmake_paths(self, tc):
        prefixes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        qtbase = self.dependencies["qtbase-sql-dbus"]
        add_unique(prefixes, qtbase.package_folder)
        add_unique(prefixes, os.path.join(qtbase.package_folder, "lib", "cmake"))
        add_unique(
            modules,
            os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6", "platforms"),
        )

        keychain = self.dependencies.get("qtkeychain")
        if keychain and keychain.package_folder:
            add_unique(prefixes, keychain.package_folder)
            add_unique(prefixes, os.path.join(keychain.package_folder, "lib", "cmake"))

        tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        tc.variables["CMAKE_MODULE_PATH"] = ";".join(modules)

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        env = self._library_runtime_env(include_build=True)
        # E132 (kitemviews 6.26.0 / kscreenlocker 6.7.2 precedent): the OHOS
        # SDK lld links against libxml2.so.16 shipped in the SDK's llvm/lib
        # directory, which CI workers may not export via LD_LIBRARY_PATH;
        # prepend it so every link step can run the linker.
        sdk_llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        if os.path.isdir(sdk_llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        with env.vars(self).apply():
            cmake.configure()
            if str(self.settings.os) in ("OHOS", "HarmonyOS"):
                self._replace_symlink_rule_with_copy(self.build_folder)
            cmake.build()
            self._run_upstream_ctests()

    @staticmethod
    def _replace_symlink_rule_with_copy(build_dir):
        """Turn the versioned-library symlink step into real copies on OHOS.

        The library is built with VERSION 0.8.0 / SOVERSION 0.8, so the
        build graph materialises the libQuotientQt6.so.0.8 -> .so.0.8.0
        chain via `cmake -E cmake_symlink_library` -- as a ninja rule under
        the Ninja generator, as a link recipe line in
        CMakeFiles/<target>.dir/build.make under the Unix Makefiles
        generator (which the platform CI profile selects). OHOS /storage
        rejects symlink creation with EPERM (XPM restriction; plain Linux
        has no such constraint), and both generators unconditionally re-run
        a failed edge, so no second pass can get past it. Rewrite the
        command to copy each output path instead -- the dynamic loader
        resolves DT_NEEDED by file name and does not distinguish a symlink
        from a regular file (lfortran 0.64.0 / kea precedents). The CMake
        install script only copies whatever sits under these names (it
        creates no symlinks of its own), so the installed tree is
        unaffected. OHOS-only; Linux and CI keep the stock behaviour.
        """
        ninja_pattern = re.compile(r"\S*cmake -E cmake_symlink_library \$in \$SONAME \$out")
        ninja_replacement = (
            'python3 -c "import shutil,sys; '
            "[shutil.copyfile(sys.argv[1], f) for f in sys.argv[2:]]\" $in $out"
        )
        make_pattern = re.compile(r"\$\(CMAKE_COMMAND\) -E cmake_symlink_library")
        make_replacement = (
            'python3 -c "import shutil,sys; '
            '[shutil.copyfile(sys.argv[1], f) for f in sys.argv[2:]]"'
        )
        for rules in glob.glob(
            os.path.join(build_dir, "**", "rules.ninja"), recursive=True
        ):
            with open(rules, encoding="utf-8") as handle:
                content = handle.read()
            if "cmake_symlink_library" in content:
                with open(rules, "w", encoding="utf-8") as handle:
                    handle.write(ninja_pattern.sub(ninja_replacement, content))
        for makefile in glob.glob(
            os.path.join(build_dir, "**", "*.make"), recursive=True
        ):
            with open(makefile, encoding="utf-8") as handle:
                content = handle.read()
            if "cmake_symlink_library" in content:
                with open(makefile, "w", encoding="utf-8") as handle:
                    handle.write(make_pattern.sub(make_replacement, content))

    def _run_upstream_ctests(self):
        # autotests/CMakeLists.txt registers exactly these two offline cases
        # in a non-E2EE build (the six testolm*/testfilecrypto/testkey*
        # cases are gated on Quotient_ENABLE_E2EE, which stays OFF); quotest
        # is not a ctest case upstream.
        test_env = Environment()
        test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
        with test_env.vars(self).apply():
            self.run(
                'ctest --output-on-failure -R "^(callcandidateseventtest|utiltests)$"',
                cwd=self.build_folder,
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "LGPL-2.1-or-later.txt",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_ohos_elf_tree(self.package_folder, "package")

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
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder, label):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        if not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "Cannot locate OHOS llvm-objcopy/binary-sign-tool for ELF signing"
            )

        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS {label} ELF file(s)")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["QuotientQt6"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
