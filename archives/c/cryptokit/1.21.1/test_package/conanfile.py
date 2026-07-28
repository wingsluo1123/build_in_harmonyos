import os
from conan import ConanFile
from conan.tools.build import can_run

class CryptokitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R34: Test must actually verify the package contents
        # Verify that the compiled C stubs exist in the package
        lib_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "lib")
        header_dir = os.path.join(self.dependencies[self.tested_reference_str].package_folder, "include", "cryptokit")

        # Check lib directory has compiled objects
        if os.path.isdir(lib_dir):
            objects = [f for f in os.listdir(lib_dir) if f.endswith('.o')]
            assert len(objects) > 0, f"No compiled .o files found in {lib_dir}"
            print(f"cryptokit test: {len(objects)} compiled objects verified OK")
        else:
            raise Exception(f"Lib directory not found: {lib_dir}")

        # Check header files exist
        if os.path.isdir(header_dir):
            headers = [f for f in os.listdir(header_dir) if f.endswith('.h')]
            assert len(headers) > 0, f"No header files found in {header_dir}"
            print(f"cryptokit test: {len(headers)} header files verified OK")
        else:
            raise Exception(f"Header directory not found: {header_dir}")

        print("cryptokit/1.21.1: C stubs package verification PASSED")
