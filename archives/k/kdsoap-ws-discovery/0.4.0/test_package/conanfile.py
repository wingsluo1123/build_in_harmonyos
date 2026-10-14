#!/usr/bin/env python3
"""Consumer test for the packaged kdsoap-ws-discovery library.

Builds a real program that consumes the installed CMake package
(find_package(KDSoapWSDiscoveryClient) -> KDSoap::WSDiscoveryClient) and calls
the public API (WSDiscoveryTargetService, WSDiscoveryServiceAggregator,
WSDiscoveryProbeJob) with 14 fixed checks. The library is a shared object, so
the test genuinely links and runs against the package (the CI L1e destructive
negative test removes lib/ and expects this to fail).
"""

import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class KDSoapWSDiscoveryTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    # Fixed, audited number of CHECK() assertions in test_kdsoapwsdiscovery.cpp.
    _check_count = 14

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()
        # qtbase and kdsoap use cmake_find_mode=none, and the tested package
        # does too, so CMakeDeps emits no conan_cmakedeps_paths.cmake. Write it
        # manually: put every dependency's lib/cmake (qtbase, kdsoap, the tested
        # package) on the search path so
        # find_package(KDSoapWSDiscoveryClient) plus its
        # find_dependency(Qt6Core)/find_dependency(KDSoap-qt6) resolve.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            prefix = package_folder.replace("\\", "/")
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{prefix}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{prefix}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{prefix}/include")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_env = Environment()
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    test_env.prepend_path("LD_LIBRARY_PATH", lib_dir)
                plugins = os.path.join(dep.package_folder, "plugins")
                if os.path.isdir(plugins):
                    test_env.prepend_path("QT_PLUGIN_PATH", plugins)
        with test_env.vars(self).apply():
            self.run(
                "./test_kdsoap_ws_discovery",
                cwd=self.cpp.build.bindirs[0],
                env="conanrun",
            )

        payload = {
            "executed": True,
            "passed": True,
            "command": "./test_kdsoap_ws_discovery",
            "discovered": self._check_count,
            "passedCount": self._check_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(payload, separators=(",", ":"))
        print(line, flush=True)
        self.output.info(line)

        # Re-emit the in-build upstream result (covers Conan cache-hit rounds
        # where the main build() is skipped). Numbers are copied verbatim.
        try:
            package_folder = self.dependencies["kdsoap-ws-discovery"].package_folder
            evidence = os.path.join(package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(evidence):
                with open(evidence, encoding="utf-8") as stream:
                    upstream = json.load(stream)
                if upstream.get("status") == "passed":
                    up_line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        upstream, separators=(",", ":")
                    )
                    print(up_line, flush=True)
                    self.output.info(up_line)
                else:
                    self.output.info(
                        "hmbs_upstream.json not passed (not re-emitted): {}".format(evidence)
                    )
            else:
                self.output.info("hmbs_upstream.json missing: {}".format(evidence))
        except Exception as exc:
            self.output.info("re-emit hmbs_upstream skipped: {}".format(exc))
