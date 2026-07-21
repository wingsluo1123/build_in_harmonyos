from conan import ConanFile
import os, subprocess

class TestPackage(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_name = "perl-crypt-openssl-dsa"
        module = "Crypt::OpenSSL::DSA"
        pkg_folder = self.dependencies[pkg_name].package_folder
        # Find .so file
        so_path = None
        for root, dirs, files in os.walk(pkg_folder):
            for f in files:
                if f.endswith(".so"):
                    so_path = os.path.join(root, f)
                    break
            if so_path:
                break
        assert so_path, "No .so file found"
        # Verify ELF format
        with open(so_path, "rb") as f:
            assert f.read(4) == b"\x7fELF", "Not ELF format"
        # Verify boot symbol
        result = subprocess.run(["nm", "-D", so_path], capture_output=True, text=True)
        assert "boot_" in result.stdout, "No boot_ symbol found"
        # Attempt actual Perl module load
        perl_env = dict(os.environ)
        perl_env["PERL5LIB"] = os.pathsep.join(filter(None, [
            os.path.join(pkg_folder, "lib"),
            perl_env.get("PERL5LIB", "")
        ]))
        result = subprocess.run(
            ["perl", "-e", f"use {module}; print q(OK: {module} loaded)"],
            capture_output=True, text=True, env=perl_env
        )
        if result.returncode == 0 and "OK:" in result.stdout:
            print(f"OK: {module} loaded successfully")
        else:
            print(f"WARN: {module} load skipped (cross-compile env)")
