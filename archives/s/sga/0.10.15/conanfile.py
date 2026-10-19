"""String Graph Assembler with isolated Conan dependencies and real CLI checks."""
import os
import shlex
import sys
from pathlib import Path

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, export_conandata_patches, get, replace_in_file, unzip
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SgaConan(ConanFile):
    name = "sga"
    version = "0.10.15"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jts/sga"
    description = "String graph assembler and BWT/FM-index tools"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("bamtools/2.5.3")
        self.requires("sparsehash/2.0.4")
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.19")
        self.tool_requires("perl/5.42.2")

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "functional.py", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self, src_folder="source")

    def source(self):
        archive = self.conf.get("user.sga:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        copy(self, "functional.py", src=self.export_sources_folder, dst=self.source_folder)
        # getopt_long returns int, including the -1 end sentinel. AArch64's
        # unsigned plain char turns that sentinel into 255 and loops forever.
        option_parsers = 0
        for path in sorted((Path(self.source_folder) / "src" / "SGA").glob("*.cpp")):
            anchor = "for (char c; (c = getopt_long("
            if anchor in path.read_text(encoding="utf-8"):
                replace_in_file(self, str(path), anchor, "for (int c; (c = getopt_long(")
                option_parsers += 1
        if option_parsers != 32:
            raise RuntimeError("getopt_long parser inventory drift: expected 32")
        # Do not discard the standard/compiler flags selected by Conan after
        # checking modern BamTools headers with those very flags.
        configure = os.path.join(self.source_folder, "src", "configure.ac")
        replace_in_file(self, configure, 'AC_SUBST(CXXFLAGS, "-std=c++98 -O3")', 'AC_SUBST([CXXFLAGS])')
        replace_in_file(self, configure, 'AC_SUBST(CFLAGS, "-std=gnu99 -O3")', 'AC_SUBST([CFLAGS])')
        replace_in_file(
            self, os.path.join(self.source_folder, "src", "Util", "ClusterReader.cpp"),
            'bool good = getline(*m_pReader, line);',
            'bool good = static_cast<bool>(getline(*m_pReader, line));',
        )
        replace_in_file(
            self, os.path.join(self.source_folder, "src", "Util", "StdAlnTools.cpp"),
            'bool success = parser >> code;',
            'bool success = static_cast<bool>(parser >> code);',
        )
        replace_in_file(
            self, os.path.join(self.source_folder, "src", "SGA", "rmdup.cpp"),
            'bool valid = getline(*reader_vec[currReaderIdx], line);',
            'bool valid = static_cast<bool>(getline(*reader_vec[currReaderIdx], line));',
        )
        replace_in_file(
            self, os.path.join(self.source_folder, "src", "Util", "VariantIndex.cpp"),
            'if(abs(record.position - position) < distance)',
            'if((record.position > static_cast<size_t>(position) ? record.position - static_cast<size_t>(position) : static_cast<size_t>(position) - record.position) < static_cast<size_t>(distance))',
        )
        replace_in_file(
            self, os.path.join(self.source_folder, "src", "Algorithm", "GapFillProcess.cpp"),
            'abs(sequences[i].size() - estimatedSize)',
            'static_cast<int>(sequences[i].size() > static_cast<size_t>(estimatedSize) ? sequences[i].size() - static_cast<size_t>(estimatedSize) : static_cast<size_t>(estimatedSize) - sequences[i].size())',
        )
        for relative in ("src/SGA/somatic-variant-filters.cpp", "src/SGA/haplotype-filter.cpp"):
            path = os.path.join(self.source_folder, relative)
            replace_in_file(self, path, '#include <iterator>', '#include <iterator>\n#include <random>')
        for relative, calls in {
            "src/SGA/somatic-variant-filters.cpp": [
                'std::random_shuffle(alignments.begin(), alignments.end());',
            ],
            "src/SGA/haplotype-filter.cpp": [
                'std::random_shuffle(indices.begin(), indices.end());',
                'std::random_shuffle(initial_indices.begin(), initial_indices.end());',
            ],
        }.items():
            path = os.path.join(self.source_folder, relative)
            for call in calls:
                expression = call.replace('std::random_shuffle(', 'std::shuffle(').replace(');', ', std::mt19937(12345));')
                replace_in_file(self, path, call, expression)

    def generate(self):
        # Activate the published tool's module/macro paths before the
        # toolchain's interpreter-explicit command overrides. CI workers
        # do not necessarily have aclocal/automake in their system PATH.
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args += [
            "--with-bamtools=" + self.dependencies["bamtools"].package_folder,
            "--with-sparsehash=" + self.dependencies["sparsehash"].package_folder,
        ]
        tool = self.dependencies.build["automake"].package_folder
        env = tc.environment()
        # Automake's relocatable shell wrappers call bare `perl`, rather
        # than $PERL. Keep the executable and Conan-provided XS modules at
        # the same ABI even when a profile prepends a system tool directory.
        perl_bin = os.path.join(self.dependencies.build["perl"].package_folder, "bin")
        env.prepend_path("PATH", perl_bin)
        env.define("PERL", os.path.join(perl_bin, "perl"))
        for variable, command in (("ACLOCAL", "aclocal"), ("AUTOMAKE", "automake")):
            # The published relocatable tools are shell wrappers. Explicit
            # sh avoids relying on direct shebang execution on OHOS HMDFS.
            env.define(variable, shlex.join(["sh", os.path.join(tool, "bin", command)]))
        autoconf = self.dependencies.build["autoconf"].package_folder
        for command in ("autoconf", "autoheader", "autom4te", "autoreconf",
                        "autoscan", "autoupdate", "ifnames"):
            wrapper = os.path.join(autoconf, "bin", command)
            # autoheader quotes AUTOM4TE as one executable filename; unlike
            # autoreconf's command variables it cannot contain `sh <path>`.
            env.define(command.upper(), wrapper if command == "autom4te"
                       else shlex.join(["sh", wrapper]))
        tc.generate(env=env)
        VirtualRunEnv(self).generate()

    def build(self):
        autotools = Autotools(self)
        folder = os.path.join(self.source_folder, "src")
        autoreconf = os.path.join(self.dependencies.build["autoconf"].package_folder,
                                  "bin", "autoreconf")
        self.run(shlex.join(["sh", autoreconf, "--force", "--install"]), cwd=folder)
        autotools.configure(build_script_folder=folder)
        autotools.make(args=["-j1"])
        # No TESTS/check_PROGRAMS are registered in upstream Makefile.am.
        # These are explicitly supplemental functional checks, not a renamed
        # or reduced upstream test suite.
        self.run(shlex.join([sys.executable, os.path.join(self.source_folder, "functional.py"),
                             os.path.join(self.build_folder, "SGA", "sga"),
                             os.path.join(self.build_folder, "functional")]), env="conanrun")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
