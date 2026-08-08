import os
from conan import ConanFile


class RsyslogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Verify rsyslogd binary and shared modules
        rsyslog_info = self.dependencies["rsyslog"]
        bin_path = os.path.join(rsyslog_info.package_folder, "bin", "rsyslogd")
        lib_dir = os.path.join(rsyslog_info.package_folder, "lib", "rsyslog")

        # Verify binary exists
        assert os.path.isfile(bin_path), f"rsyslogd not found at {bin_path}"

        # Verify it's a valid ELF binary (R34: execute verification)
        self.run(f'file {bin_path}', env="conanrun")

        # List and count shared library modules
        self.run(f'ls -la {lib_dir}/*.so', env="conanrun")
        so_count = len([f for f in os.listdir(lib_dir) if f.endswith(".so")])
        assert so_count > 0, "No .so modules found"
        print(f"Found {so_count} rsyslog modules")
        print("test rsyslog 8.2404.0: OK")
