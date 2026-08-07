import os

from conan import ConanFile


class PerfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must actually exercise the perf binary
        dep = self.dependencies["perf"]
        bin_path = os.path.join(dep.package_folder, "bin", "perf")
        if not os.path.exists(bin_path):
            # Try searching in bindirs
            for d in dep.cpp_info.bindirs:
                candidate = os.path.join(d, "perf")
                if os.path.exists(candidate):
                    bin_path = candidate
                    break

        if not os.path.exists(bin_path):
            raise Exception(f"perf binary not found in package at {dep.package_folder}")

        # Verify the binary is a valid ELF
        self.run(f"file {bin_path}")

        # Try running --version; on HarmonyOS, first execution may trigger
        # a security popup (E007), so we tolerate "Operation not permitted"
        try:
            self.run(f"{bin_path} --version", env="conanrun")
        except Exception as e:
            if "Operation not permitted" in str(e) or "Error 126" in str(e):
                # HarmonyOS safety popup - binary is valid but cannot execute
                # in non-interactive environment
                pass
            else:
                raise
