from conan import ConanFile
import os, subprocess

class TestPackage(ConanFile):
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_name = "perl-mime-base64"
        module = "MIME::Base64"
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
        # site_arch is where .pm files are installed by make install DESTDIR
        site_arch = os.path.join(pkg_folder,
                                 "data", "service", "hnp", "perl.org",
                                 "perl_5.42.2", "lib", "site_perl", "5.42.2",
                                 "aarch64-linux")
        perl_env["PERL5LIB"] = os.pathsep.join(filter(None, [
            site_arch,
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
            self.output.warning(f"{module} load failed (may be cross-compile env): {result.stderr}")
            if not os.environ.get("CROSS_COMPILE"):
                raise AssertionError(f"{module} failed to load: {result.stderr}")
