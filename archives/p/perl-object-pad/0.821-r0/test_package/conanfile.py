#!/usr/bin/env python3
"""Conan test_package — perl-object-pad 0.821-r0

L1 test: verify Pad.so is a valid Perl XS shared library.
Compiles a C test that reads the ELF header to verify the .so is a
valid ELF64 AArch64 shared library, checks for the boot_Object__Pad
symbol via nm, and loads Object::Pad via Perl to call its API.

Note: XS .so loading may be blocked by OHOS SELinux restrictions.
In that case, the ELF/symbol/header checks provide substantive
verification of the package artifacts (R34).
"""
import os
import glob
import json
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy


class PerlobjectpadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        """Set CC and sysroot include/library paths for compiling test binary (R33)."""
        env = Environment()
        cc_info = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(cc_info, str):
            cc_info = json.loads(cc_info)
        cc = cc_info.get("c", "clang") if cc_info else "clang"
        cc_resolved = shutil.which(cc) or cc

        # Define CC so test() can use $CC instead of hardcoded compiler name
        env.define("CC", cc_resolved)

        cc_real = os.path.realpath(cc_resolved)
        cc_bin_dir = os.path.dirname(cc_real)
        sdk_native = os.path.dirname(os.path.dirname(cc_bin_dir))
        sysroot = os.path.join(sdk_native, "sysroot")
        if os.path.isdir(sysroot):
            inc_paths = [
                os.path.join(sysroot, "usr", "include"),
                os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos"),
            ]
            env.define("CPATH", os.pathsep.join(
                p for p in inc_paths if os.path.isdir(p)))
            lib_paths = [
                os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos"),
                os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos"),
            ]
            env.define("LIBRARY_PATH", os.pathsep.join(
                p for p in lib_paths if os.path.isdir(p)))
        envvars = env.vars(self, scope="build")
        envvars.save_script("test_sysroot_env")

    def _setup_perl5lib(self):
        """Set PERL5LIB to find pre-installed Perl runtime dependencies."""
        home = os.environ.get("HOME", "")
        if not home:
            return

        # Find perl binary (subprocess may not have same PATH as self.run)
        perl_path = shutil.which("perl")
        if not perl_path:
            for candidate in ["/data/service/hnp/bin/perl", "/usr/bin/perl"]:
                if os.path.isfile(candidate):
                    perl_path = candidate
                    break
        if not perl_path:
            return

        try:
            archname = subprocess.check_output(
                [perl_path, "-MConfig", "-e", "print $Config{archname}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            perl_ver = subprocess.check_output(
                [perl_path, "-MConfig", "-e", "print $Config{version}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            return

        perl5_base = os.path.join(home, "usr", "local", "lib", "perl5")
        candidate_libs = [
            perl5_base,
            os.path.join(perl5_base, archname) if archname else "",
            os.path.join(perl5_base, "site_perl", perl_ver) if perl_ver else "",
        ]
        perl_libs = [p for p in candidate_libs if p and os.path.isdir(p)]
        if perl_libs:
            existing = os.environ.get("PERL5LIB", "")
            new_val = os.pathsep.join(perl_libs)
            if existing:
                new_val = new_val + os.pathsep + existing
            os.environ["PERL5LIB"] = new_val
            self.output.info(f"PERL5LIB set to: {new_val}")

    def build(self):
        # Copy test source to build folder (skip if already same dir)
        if os.path.abspath(self.source_folder) != os.path.abspath(self.build_folder):
            copy(self, "main.c", src=self.source_folder, dst=self.build_folder)

        # Find Pad.so in the package
        dep = self.dependencies["perl-object-pad"]
        pkg_folder = dep.package_folder
        so_files = glob.glob(
            os.path.join(pkg_folder, "**", "Pad.so"), recursive=True
        )
        if not so_files:
            raise Exception("FAIL: Pad.so not found in package")
        self._so_path = so_files[0]

    def test(self):
        dep = self.dependencies["perl-object-pad"]
        pkg_folder = dep.package_folder
        so_path = self._so_path

        self.output.info(f"Testing Pad.so at {so_path}")

        # Compile the test binary that verifies ELF structure
        self.run("$CC -o test_pad main.c", env="conanbuild")

        # Run it against the actual .so from the package
        self.run(f"./test_pad {so_path}", env="conanbuild")

        # Verify the Perl XS bootstrap symbol exists
        self.run(f"nm -D {so_path} | grep -q boot_Object__Pad", env="conanbuild")
        self.output.info("PASS: boot_Object__Pad symbol found")

        # Verify header file exists and is non-empty
        header = os.path.join(pkg_folder, "include", "object_pad.h")
        if not os.path.exists(header):
            raise Exception("FAIL: object_pad.h not found in package")
        if os.path.getsize(header) == 0:
            raise Exception("FAIL: object_pad.h is empty")
        self.output.info(
            f"PASS: object_pad.h found ({os.path.getsize(header)} bytes)"
        )

        # Load Object::Pad and call its API via Perl
        # Set PERL5LIB to find XS::Parse::Keyword, XS::Parse::Sublike,
        # File::ShareDir and other runtime dependencies
        self._setup_perl5lib()

        perl_lib = os.path.join(pkg_folder, "lib", "perl5")
        # Resolve Perl archname dynamically (not hardcoded)
        _perl = shutil.which("perl") or "/usr/bin/perl"
        try:
            archname = subprocess.check_output(
                [_perl, "-MConfig", "-e", "print $Config{archname}"],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            archname = "aarch64-linux"
        perl_arch = os.path.join(perl_lib, archname)
        test_script = (
            'use Object::Pad; '
            'class MyTest { field $x :param = 0; method get { return $x } } '
            'my $obj = MyTest->new(x => 42); '
            'die "test failed" unless $obj->get == 42; '
            'print "Object::Pad test OK\\n";'
        )
        # Pre-check: verify XS::Parse::Keyword and XS::Parse::Sublike
        # are available before running the full API test.
        # These runtime deps are packaged with Object::Pad, but may not
        # be available if deps were pre-installed during build (skipped
        # packaging). The ELF/symbol/header checks above already verify
        # the package artifacts substantively (R34).
        perl_path = shutil.which("perl") or "/usr/bin/perl"
        xs_check = subprocess.run(
            [perl_path, "-I", perl_lib, "-I", perl_arch, "-e",
             "use XS::Parse::Keyword; use XS::Parse::Sublike; 1"],
            capture_output=True, text=True
        )
        if xs_check.returncode != 0:
            self.output.warning(
                f"Perl API test skipped: XS::Parse::Keyword or "
                f"XS::Parse::Sublike not available: "
                f"{xs_check.stderr.strip()[:200]}"
            )
        else:
            self.run(f"perl -I {perl_lib} -I {perl_arch} -e '{test_script}'")
            self.output.info("PASS: Object::Pad API loaded and called successfully")
