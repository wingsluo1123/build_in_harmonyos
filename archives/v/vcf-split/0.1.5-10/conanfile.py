#!/usr/bin/env python3
"""Conan recipe — vcf-split 0.1.5-10 (Makefile)"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

# vcf-split 0.1.5-10 is the snapshot 10 commits after upstream tag 0.1.5
# (git describe: 0.1.5-10-g0f2fd0a).  Upstream derives VERSION from git at
# build time; a source tarball has no .git, so the recipe supplies it.
UPSTREAM_VERSION = "0.1.5-10"


class VcfSplitConan(ConanFile):
    name = "vcf-split"
    version = "0.1.5-10"
    description = "Splits a combined-sample VCF stream into single-sample VCF files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/auerlab/vcf-split"
    url = "https://github.com/auerlab/vcf-split"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml", "patches/*"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def requirements(self):
        self.requires("biolibc/0.2.7")
        self.requires("libxtend/0.2.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = Environment()
        env.define("TMP", tmp_dir)
        env.define("TEMP", tmp_dir)
        env.define("TMPDIR", tmp_dir)
        env.vars(self).save_script("vcf_split_build")

    @staticmethod
    def _quote(value):
        text = str(value)
        return f'"{text}"' if " " in text else text

    @staticmethod
    def _make():
        return "make"

    def _tool(self, key, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        value = compilers.get(key, fallback)
        if isinstance(value, (list, tuple)):
            value = " ".join(str(part) for part in value)
        return self._resolve_tool(str(value), fallback)

    @staticmethod
    def _resolve_tool(candidate, fallback):
        if candidate and os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate.replace("\\", "/")
        lookup = os.path.basename(candidate) if candidate and os.path.isabs(candidate) else candidate
        found = shutil.which(lookup or fallback)
        if found:
            return found.replace("\\", "/")
        return fallback.replace("\\", "/")

    def _conf_flags(self, name):
        values = self.conf.get(name, default=[], check_type=list) or []
        return [str(value) for value in values]

    def _dependency_flags(self):
        cflags = []
        ldflags = []
        for name in ("biolibc", "libxtend"):
            cpp_info = self.dependencies[name].cpp_info
            cflags.extend(f"-isystem {path.replace(chr(92), '/')}" for path in cpp_info.includedirs)
            cflags.extend(f"-D{define}" for define in cpp_info.defines)
            ldflags.extend(f"-L{path.replace(chr(92), '/')}" for path in cpp_info.libdirs)
            ldflags.extend(f"-l{lib}" for lib in cpp_info.libs)
        return cflags, ldflags

    def _sign_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = self._resolve_tool(os.environ.get("BINARY_SIGN_TOOL"), "binary-sign-tool")
        objcopy = self._resolve_tool(os.environ.get("LLVM_OBJCOPY"), "llvm-objcopy")
        if not os.path.exists(sign_tool):
            raise ConanInvalidConfiguration("OHOS binary-sign-tool is required to sign vcf-split")
        if os.path.exists(objcopy):
            # The .codesign section is absent on a freshly linked binary, so a
            # failing --remove-section here is expected and safe to ignore.
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true', quiet=True)
        tmp_signed = path + ".signed"
        self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{tmp_signed}" -selfSign 1', quiet=True)
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def _run_upstream_fixture(self):
        """Replay the non-interactive assertions of upstream Test/test.sh.

        Upstream test.sh wraps its checks in an interactive pause() prompt and
        relies on the caller having run ./cave-man-install.sh first, so the
        recipe runs the same two split invocations and all 22 diff comparisons
        against the checked-in expected fixtures.
        """
        if not can_run(self):
            self.output.info("Skipping upstream Test fixture replay because target binaries cannot run")
            return
        columns = " ".join(str(column) for column in range(1, 12))
        command = (
            "rm -f test-*.vcf && "
            "../vcf-split test-all-fields- 1 11 < test.vcf && "
            "../vcf-split --fields chrom,pos,ref,alt,format test-limited-fields- 1 11 < test.vcf && "
            f"for col in {columns}; do "
            'diff -u "correct-all-fields-$col.vcf" "test-all-fields-$col.vcf" && '
            'diff -u "correct-limited-fields-$col.vcf" "test-limited-fields-$col.vcf"; '
            "done && "
            "rm -f test-*.vcf"
        )
        self.run(command, cwd=os.path.join(self.source_folder, "Test"), env=["conanbuild", "vcf_split_build"])

    def build(self):
        apply_conandata_patches(self)
        dep_cflags, dep_ldflags = self._dependency_flags()
        cflags = [
            f"-DVERSION='\\\"{UPSTREAM_VERSION}\\\"'",
            "-O2",
            "-DNDEBUG",
        ]
        cflags.extend(self._conf_flags("tools.build:cflags"))
        cflags.extend(dep_cflags)
        ldflags = list(dep_ldflags)
        ldflags.extend(self._conf_flags("tools.build:exelinkflags"))

        assignments = {
            "CC": self._tool("c", "clang"),
            "LD": self._tool("c", "clang"),
            "CFLAGS": " ".join(cflags),
            "LDFLAGS": " ".join(ldflags),
        }
        args = " ".join(f"{key}={self._quote(value)}" for key, value in assignments.items())
        self.run(f"{self._make()} -j1 {args} vcf-split", cwd=self.source_folder, env=["conanbuild", "vcf_split_build"])
        self._sign_binary(os.path.join(self.source_folder, "vcf-split"))
        self._run_upstream_fixture()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "share", "doc", "vcf-split"), keep_path=False)
        copy(self, "vcf-split", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "vcf-split.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        test_src = os.path.join(self.source_folder, "Test")
        test_dst = os.path.join(self.package_folder, "share", "vcf-split", "Test")
        copy(self, "test.vcf", test_src, test_dst, keep_path=False)
        copy(self, "correct-*.vcf", test_src, test_dst, keep_path=False)
        self._sign_binary(os.path.join(self.package_folder, "bin", "vcf-split"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
