#!/usr/bin/env python3
"""Conan recipe for tabixpp 1.1.2 (Makefile).

tabixpp is a C++ wrapper around the tabix indexer for bgzf-compressed,
tabix-indexed files (VCF/BED/GFF). Upstream build entry is the raw
repository-root Makefile: `make all` produces the `tabix++` CLI, the static
`libtabix.a` and the versioned shared `libtabix.so.1`; `make test` runs the
single bundled integration check `./tabix++ test/vcf_file.vcf.gz`.

OHOS notes:
- The release tarball ships an empty `htslib/` directory (git submodule is
  not archived). The recipe links against the external Conan package
  `htslib/1.24-r0` instead: INCLUDES/LIBPATH are overridden on the make
  command line and the `HTS_HEADERS`/`HTS_LIB` submodule prerequisites are
  cleared (both are `?=` in the Makefile, so command-line override wins).
- Upstream links `-lcurl -lbz2`; htslib 1.24-r0 builds with
  `--disable-libcurl --disable-bz2`, and static libhts.a additionally needs
  libdeflate. patches/0001 rewrites the link line to
  `-lhts -lpthread -lm -lz -llzma -ldeflate`.
- R26 does not apply: libtabix is not a system library name.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TabixppConan(ConanFile):
    name = "tabixpp"
    version = "1.1.2"
    description = "C++ wrapper to the tabix indexer for bgzf-compressed files"
    license = "MIT"
    homepage = "https://github.com/vcflib/tabixpp"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tabix", "bgzf", "vcf", "genomics", "htslib")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tabixpp requires a POSIX-like target (Linux or OHOS), "
                "not {}".format(self.settings.os)
            )

    def requirements(self):
        self.requires("htslib/1.24-r0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, key, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        value = compilers.get(key)
        if value:
            return value
        c_dir = os.path.dirname(compilers.get("c", ""))
        return os.path.join(c_dir, fallback) if c_dir else fallback

    def _htslib_flags(self):
        htslib = self.dependencies["htslib"]
        root = htslib.package_folder
        cpp_info = htslib.cpp_info

        def _abs(dirs, default_sub):
            if dirs:
                return [d if os.path.isabs(d) else os.path.join(root, d) for d in dirs]
            return [os.path.join(root, default_sub)]

        include_dirs = _abs(cpp_info.includedirs, "include")
        lib_dirs = _abs(cpp_info.libdirs, "lib")
        for dep in self.dependencies.values():
            if dep.ref.name == "htslib":
                continue
            dep_root = dep.package_folder
            for d in dep.cpp_info.libdirs or []:
                lib_dirs.append(d if os.path.isabs(d) else os.path.join(dep_root, d))
        includes = " ".join("-I{}".format(d) for d in include_dirs)
        libpath = " ".join(["-L."] + ["-L{}".format(d) for d in lib_dirs])
        return includes, libpath

    def _make_base(self):
        cc = self._tool("c", "clang")
        cxx = self._tool("cpp", "clang++")
        ar = self._tool("ar", "llvm-ar")
        includes, libpath = self._htslib_flags()
        return (
            'make CC="{cc}" CXX="{cxx}" AR="{ar}" '
            'INCLUDES="{includes}" LIBPATH="{libpath}" '
            'HTS_HEADERS="" HTS_LIB="" -j1'.format(
                cc=cc, cxx=cxx, ar=ar, includes=includes, libpath=libpath
            )
        )

    def build(self):
        apply_conandata_patches(self)
        make_base = self._make_base()
        self.run("{} all".format(make_base), cwd=self.source_folder)
        if can_run(self):
            self._run_upstream_test()
        else:
            self.output.info(
                "Cross build: tabixpp upstream test was not executed here; "
                "run `./tabix++ test/vcf_file.vcf.gz` on the HarmonyOS PC target."
            )

    def _dep_libdirs(self):
        dirs = []
        for dep in self.dependencies.values():
            root = dep.package_folder
            if not root:
                continue
            for d in dep.cpp_info.libdirs or []:
                dirs.append(d if os.path.isabs(d) else os.path.join(root, d))
        seen = []
        for d in dirs:
            if d not in seen:
                seen.append(d)
        return seen

    def _sign_binary(self, path):
        """Self-sign a freshly built ELF so HarmonyOS allows execution.
        Best-effort: missing tool or unsupported fs capability only warns."""
        if not os.path.isfile(path):
            return
        signer = (
            shutil.which("binary-sign-tool")
            or os.environ.get("OHOS_SIGN_TOOL")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not signer or not os.path.isfile(signer):
            self.output.info("sign: binary-sign-tool not found, skipping signing")
            return
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        try:
            if objcopy and os.path.isfile(objcopy):
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            signed = path + ".signed"
            subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if os.path.isfile(signed):
                shutil.move(signed, path)
            try:
                os.chmod(path, 0o755)
            except OSError as e:
                self.output.warning("sign: chmod failed (fs may not support it): {}".format(e))
            self.output.info("sign: self-signed {}".format(path))
        except (OSError, subprocess.CalledProcessError) as e:
            self.output.warning("sign: self-sign failed, continuing unsigned: {}".format(e))

    def _run_upstream_test(self):
        test_cmd = "./tabix++ test/vcf_file.vcf.gz"
        src = self.source_folder
        cli = os.path.join(src, "tabix++")
        fixture = os.path.join(src, "test", "vcf_file.vcf.gz")
        self.output.info("upstream test preflight: cli={} exists={}".format(cli, os.path.isfile(cli)))
        self.output.info("upstream test preflight: fixture={} exists={}".format(fixture, os.path.isfile(fixture)))
        try:
            self.output.info("upstream test preflight: ls={}".format(sorted(os.listdir(src))))
        except OSError:
            pass
        try:
            self.output.info("upstream test preflight: ls-test={}".format(sorted(os.listdir(os.path.join(src, "test")))))
        except OSError as e:
            self.output.warning("upstream test preflight: test dir missing: {}".format(e))
        # The link line prefers a shared libhts when the package ships one;
        # expose all dependency libdirs at runtime like htslib does for its own tests.
        libdirs = self._dep_libdirs()
        if libdirs:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs + ([old] if old else []))
            self.output.info("upstream test LD_LIBRARY_PATH={}".format(os.environ["LD_LIBRARY_PATH"]))
        self._sign_binary(cli)
        # Always dump the log even when the CLI fails; `&& cat` would hide it
        # (previous Error 127 came with an empty message for this reason).
        run_cmd = "./tabix++ test/vcf_file.vcf.gz > upstream_test.log 2>&1; rc=$?; cat upstream_test.log; exit $rc"
        failed_run = ""
        try:
            self.run(run_cmd, cwd=src)
        except Exception as e:
            failed_run = str(e)
            self.output.warning("upstream test CLI failed (log dumped above): {}".format(e))
        log_file = os.path.join(src, "upstream_test.log")
        content = ""
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            content = ""
        data_lines = [ln for ln in content.splitlines() if ln.strip() != ""]
        discovered = 1
        executed = 1
        passed = 0
        failed = 0
        skipped = 0
        if failed_run:
            failed = 1
        elif len(content) > 0 and len(data_lines) >= 1:
            passed = 1
        else:
            failed = 1
        self.output.info("upstream test output bytes={} data_lines={}".format(len(content), len(data_lines)))
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={{"status":"{}","framework":"make-test",'
            '"command":"{}","discovered":{},"executed":{},"passed":{},"failed":{},'
            '"skipped":{}}}'.format(
                "passed" if failed == 0 else "failed", test_cmd,
                discovered, executed, passed, failed, skipped,
            )
        )
        if failed:
            if failed_run:
                raise ConanInvalidConfiguration(
                    "tabixpp upstream test CLI failed: {}".format(failed_run)
                )
            raise ConanInvalidConfiguration("tabixpp upstream test produced empty output")

    def package(self):
        # Upstream `make install` relies on `install -c` with multiple
        # sources (`install -c libtabix.a libtabix.so.1 <dir>`), which the
        # HarmonyOS install shim rejects (Error 64). Manual copy() is
        # portable and replicates the same layout without the shim.
        copy(self, "tabix++", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.hpp", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libtabix.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libtabix.so*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        self._sign_binary(os.path.join(self.package_folder, "bin", "tabix++"))

    def package_info(self):
        self.cpp_info.libs = ["tabix"]
        self.cpp_info.set_property("cmake_file_name", "tabixpp")
        self.cpp_info.set_property("cmake_target_name", "tabixpp::tabixpp")
        self.cpp_info.set_property("pkg_config_name", "tabixpp")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
