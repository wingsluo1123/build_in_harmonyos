#!/usr/bin/env python3
"""Conan recipe for kdsoap-ws-discovery 0.4.0 on HarmonyOS PC (aarch64).

kdsoap-ws-discovery-client is a KDAB/KDE Qt6 library implementing a WS-Discovery
client on top of KDSoap: WSDiscoveryClient (low level send/receive),
WSDiscoveryProbeJob (periodic probing) and WSDiscoveryServiceAggregator
(multi-source aggregation of the same target service).

OHOS / OHOS-native (build == host) adaptations:
  - ECM (extra-cmake-modules/6.26.0) is a build tool; the upstream CMakeLists
    does ``set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`` (it overwrites the
    module path), so ECM_MODULE_PATH must be non-empty. It is set explicitly
    and ECM's own share/ECM/cmake is put on CMAKE_PREFIX_PATH so
    ``find_package(ECM NO_MODULE)`` resolves the real ECMConfig.cmake
    (kdbusaddons precedent).
  - qtbase uses cmake_find_mode=none and kdsoap does too, so CMakeDeps does not
    emit conan_cmakedeps_paths.cmake. It is written manually so the toolchain
    prepends qtbase/lib/cmake and kdsoap/lib/cmake, letting
    find_package(Qt6 COMPONENTS Core Network Xml Test) and
    find_package(KDSoap-qt6) resolve (adwaita-qt/libkode/kdsoap precedent).
  - QT_MAJOR_VERSION=6 selects the Qt6 code path (KDSoap-qt6 + Qt6::*).
  - ``KDSOAP_GENERATE_WSDL`` runs kdwsdl2cpp-qt6 (an OHOS aarch64 host tool
    shipped in the kdsoap package under bin/) during the build, so qtbase/lib
    is put on LD_LIBRARY_PATH for the build steps.
  - Upstream autotests (autotests/test_wsdiscoveryclient.cpp, one ctest entry
    with four QTest slots) are built with BUILD_TESTING=ON and run inside
    build(); per-item counts and the raw ctest log are preserved.
  - Installed OHOS ELF files (the shared library) are code-signed with
    binary-sign-tool so the OHOS loader accepts them (adwaita-qt precedent).
"""

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KDSoapWSDiscoveryConan(ConanFile):
    name = "kdsoap-ws-discovery"
    version = "0.4.0"
    description = "Qt6 WS-Discovery client library based on KDSoap"
    license = "GPL-3.0-or-later"
    homepage = "https://invent.kde.org/libraries/kdsoap-ws-discovery-client"
    url = "https://invent.kde.org/libraries/kdsoap-ws-discovery-client"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # Upstream autotests/CMakeLists.txt registers exactly one ctest entry
    # (test_wsdiscoveryclient) built from a single QTest program with four
    # Q_SLOTS (testSendProbe, testSendResolve, testReceiveProbeMatch,
    # testReceiveResolveMatch). ctest_entries (discovered) = 1; the four
    # QTest slots are the per-item assertions reported by the QTest output.
    _upstream_ctest_entries = 1
    _upstream_slots = 4

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # kdsoap/2.3.0 is REQUIRED (find_package(KDSoap-qt6 2.0.0 REQUIRED)).
        # qtbase/6.11.1 provides Qt6::Core/Network/Xml (and Qt6::Test for
        # BUILD_TESTING); it is the exact qtbase release kdsoap/2.3.0 was built
        # against, so the dependency graph resolves to a single qtbase.
        self.requires("kdsoap/2.3.0")
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        # ECM >= 5.54.0 is REQUIRED by the top-level CMakeLists
        # (find_package(ECM 5.54.0 NO_MODULE)); KDE cmake modules are consumed
        # at configure time only.
        self.tool_requires("extra-cmake-modules/6.26.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()

        qtbase = self.dependencies.get("qtbase")
        kdsoap = self.dependencies.get("kdsoap")
        ecm = None
        try:
            ecm = self.dependencies.build.get("extra-cmake-modules")
        except Exception:
            ecm = None

        tc = CMakeToolchain(self)
        tc.variables["QT_MAJOR_VERSION"] = "6"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        # HarmonyOS has no CMake platform module, so CMAKE_SHARED_LIBRARY_SONAME_*_FLAG
        # is empty and CMake never passes -Wl,-soname even when SOVERSION is set.
        # The shared library ships without DT_SONAME, which the CI L5a gate rejects
        # and which forces downstream consumers to link by full path. Provide the
        # soname flag so the linker receives -Wl,-soname,libKDSoapWSDiscoveryClient.so
        # (knowledge E207/E537, libharu/mtxclient precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        if qtbase and qtbase.package_folder:
            qt_cmake = os.path.join(qtbase.package_folder, "lib", "cmake")
            for component in (
                "Qt6",
                "Qt6Core",
                "Qt6CoreTools",
                "Qt6Network",
                "Qt6Xml",
                "Qt6Test",
            ):
                tc.cache_variables[f"{component}_DIR"] = os.path.join(qt_cmake, component)
        if kdsoap and kdsoap.package_folder:
            tc.cache_variables["KDSoap-qt6_DIR"] = os.path.join(
                kdsoap.package_folder, "lib", "cmake", "KDSoap-qt6"
            )
            # The published kdsoap has no DT_SONAME; expose its lib dir so the
            # patched src/CMakeLists.txt can link it by SONAME-style basename
            # instead of by absolute cache path (knowledge E537).
            tc.variables["KDSOAP_DEP_LIB_DIRS"] = os.path.join(kdsoap.package_folder, "lib")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )
        tc.generate()

        # qtbase and kdsoap use cmake_find_mode=none; ECM ships its real
        # ECMConfig.cmake under share/ECM/cmake. Write conan_cmakedeps_paths.cmake
        # so the generated toolchain puts all three on the CMake search path.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if qtbase and qtbase.package_folder:
            pkg = qtbase.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{pkg}/lib")')
        if kdsoap and kdsoap.package_folder:
            kp = kdsoap.package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{kp}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{kp}/lib")')
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake").replace(
                "\\", "/"
            )
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def _runtime_environment(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins = os.path.join(dep.package_folder, "plugins")
                if os.path.isdir(plugins):
                    env.prepend_path("QT_PLUGIN_PATH", plugins)
        # KDECMakeSettings sets CMAKE_LIBRARY_OUTPUT_DIRECTORY to <build>/bin,
        # so the in-tree shared library lives there; the upstream autotests need
        # it on LD_LIBRARY_PATH (they are linked without a build RPATH).
        for rel in ("bin", "lib", os.path.join("lib", "src"), "src"):
            candidate = os.path.join(self.build_folder, rel)
            if os.path.isdir(candidate):
                env.prepend_path("LD_LIBRARY_PATH", candidate)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        cmake = CMake(self)
        with self._runtime_environment().vars(self).apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
        if can_run(self):
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._runtime_environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        try:
            os.chmod(xdg_runtime, 0o700)
        except OSError:
            pass
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))

        discovered = self._ctest_discover()
        log_path = os.path.join(self.build_folder, "hmbs_ctest.log")
        command = 'ctest --test-dir "{0}" --output-on-failure --no-tests=error --timeout 120'.format(
            self.build_folder
        )
        with open(log_path, "w", encoding="utf-8", newline="\n") as log_stream:
            with test_env.vars(self).apply():
                return_code = self.run(command, stdout=log_stream, ignore_errors=True)
        executed, passed, failed, skipped = self._parse_ctest_log(log_path, discovered)
        self._emit_upstream_result(
            discovered, executed, passed, failed, skipped, return_code, command
        )

    def _ctest_discover(self):
        log_path = os.path.join(self.build_folder, "hmbs_ctest_discover.log")
        with open(log_path, "w", encoding="utf-8", newline="\n") as log_stream:
            with self._runtime_environment().vars(self).apply():
                try:
                    self.run(
                        'ctest --test-dir "{0}" -N'.format(self.build_folder),
                        stdout=log_stream,
                        ignore_errors=True,
                    )
                except Exception:
                    return self._upstream_ctest_entries
        try:
            with open(log_path, encoding="utf-8", errors="replace") as stream:
                content = stream.read()
        except OSError:
            return self._upstream_ctest_entries
        found = re.findall(r"(?m)^\s*Test\s+#\d+:", content)
        if found:
            return len(found)
        match = re.search(r"(?m)Total Tests:\s*(\d+)", content)
        if match:
            return int(match.group(1))
        return self._upstream_ctest_entries

    @staticmethod
    def _parse_ctest_log(log_path, discovered):
        executed = passed = failed = skipped = 0
        try:
            with open(log_path, encoding="utf-8", errors="replace") as stream:
                content = stream.read()
        except OSError:
            content = ""
        if content:
            per_test = re.findall(
                r"(?m)^\s*\d+/\d+\s+Test\s+#\d+:.*?\b(Passed|Failed|Not Run)\b",
                content,
            )
            if per_test:
                passed = per_test.count("Passed")
                failed = per_test.count("Failed")
                skipped = per_test.count("Not Run")
                executed = passed + failed
            if executed == 0:
                summary = re.search(
                    r"(?m)(\d+)%\s+tests passed,\s*(\d+)\s+tests failed\s+out of\s+(\d+)",
                    content,
                )
                if summary:
                    percent = int(summary.group(1))
                    failed = int(summary.group(2))
                    total = int(summary.group(3))
                    executed = total
                    passed = total - failed if percent == 100 else max(total - failed, 0)
        return executed, passed, failed, skipped

    def _emit_upstream_result(self, discovered, executed, passed, failed, skipped, return_code, command):
        fields = [discovered, executed, passed, failed, skipped]
        identity_ok = (
            all(isinstance(v, int) and v >= 0 for v in fields)
            and passed + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
        )
        if not identity_ok:
            raise ConanException(
                "HMBS upstream identity violated: discovered={} executed={} "
                "passed={} failed={} skipped={}".format(
                    discovered, executed, passed, failed, skipped
                )
            )
        status = "passed" if (failed == 0 and executed > 0) else "failed"
        reason = (
            "ctest -N discovered {}; ctest ran {} ({}+{}+{}); QTest slots={}."
            .format(discovered, executed, passed, failed, skipped, self._upstream_slots)
            + (" return_code={}".format(return_code) if return_code else "")
        )
        payload = {
            "status": status,
            "framework": "ctest",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "qtest_slots": self._upstream_slots,
            "reason": reason,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload, separators=(",", ":"))
        print(line, flush=True)
        self.output.info(line)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as stream:
                json.dump(payload, stream, separators=(",", ":"))
                stream.write("\n")
        except Exception as exc:
            self.output.info("hmbs_upstream persist skipped: {}".format(exc))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir, "hmbs_upstream.json"))
                self.output.info("hmbs_upstream.json carried to package/res")
        except Exception as exc:
            self.output.info("carry hmbs_upstream.json skipped: {}".format(exc))
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            return

        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed, "-selfSign", "1"],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool([objdump, "-h", path], f"inspect ELF sections in {path}")
        return any(".codesign" in line.split() for line in section_table.splitlines())

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved or not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        # The project installs its own KDSoapWSDiscoveryClientConfig.cmake with
        # proper find_dependency(Qt6Core) / find_dependency(KDSoap-qt6) tracking.
        # Use cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KDSoapWSDiscoveryClient"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
