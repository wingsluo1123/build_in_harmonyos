import os
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, check_sha256, copy, get, load, replace_in_file, save, unzip
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class UcgConan(ConanFile):
    name = "ucg"
    version = "0.3.3"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gvansickle/ucg"
    description = "Concurrent source-code search with PCRE2"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "pty_script.py", "arg_and_rc_handling.at", "testsuite", "corpus.py"

    def requirements(self):
        self.requires("pcre2/10.48")
        if self.settings.os == "OHOS":
            self.requires("argp-standalone/1.4.1")

    def build_requirements(self):
        self.tool_requires("bash/5.3")
        self.tool_requires("coreutils/9.10")
        # Original performance_tests.at compares matched lines with git diff.
        self.tool_requires("git/2.45.2")
        # The release omits its googletest checkout, not its two unit tests.
        self.test_requires("gtest/1.17.0.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Supported targets: Linux and OHOS")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        archive = self.conf.get("user.ucg:source_archive", default=None)
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        if self.source_folder != self.export_sources_folder:
            copy(self, "pty_script.py", self.export_sources_folder, self.source_folder)
            copy(self, "corpus.py", self.export_sources_folder, self.source_folder)
        # Rebuilt by Autom4te from the handwritten .at input with equivalent
        # POSIX grep -i assertions. Keep every original test group and regex.
        copy(self, "arg_and_rc_handling.at", self.export_sources_folder,
             os.path.join(self.source_folder, "tests"))
        copy(self, "testsuite", self.export_sources_folder,
             os.path.join(self.source_folder, "tests"))
        # Toybox prints "is not GNU grep". The old configure substring probe
        # mistakes that for GNU grep, registering the same slow comparator
        # twice. Correct its role in the handwritten configuration template;
        # retain the mandatory system grep, all groups, inputs and iterations.
        replace_in_file(self, os.path.join(self.source_folder, "tests", "atlocal.in"),
                        'export PROG_GNU_GREP="@PROG_GNU_GREP@"', '''PROG_GNU_GREP="@PROG_GNU_GREP@"
if test -n "$PROG_GNU_GREP"; then
    case "$("$PROG_GNU_GREP" --version 2>/dev/null | sed -n '1p')" in
        *' (GNU grep) '*) ;;
        *) PROG_GNU_GREP= ;;
    esac
fi
export PROG_GNU_GREP''')
        # Handwritten GNU helper must recognize the compiler-proven OS pair.
        replace_in_file(self, os.path.join(self.source_folder, "build-aux", "config.sub"),
                        "linux-musl* | linux-uclibc*", "linux-musl* | linux-ohos* | linux-uclibc*")
        replace_in_file(self, os.path.join(self.source_folder, "build-aux", "config.sub"),
                        "-linux-musl* | -linux-uclibc*", "-linux-musl* | -linux-ohos* | -linux-uclibc*")
        # Only x86 can include Intel intrinsics. Preserve its optimized path.
        header = os.path.join(self.source_folder, "src", "libext", "memory.hpp")
        replace_in_file(self, header, '#include "immintrin.h"',
                        '#if defined(__i386__) || defined(__x86_64__)\n#include "immintrin.h"\n#endif\n#include <cstring>')
        fallback = '''#else
template <uint8_t VecSizeBytes>
inline const void* memmem_short_pattern(const void *memory, size_t size,
                                      const void *pattern, size_t length) noexcept
{
    static_assert(VecSizeBytes == 16, "Only 128-bit search interface supported");
    if (!size || !length || length > size) return nullptr;
    const unsigned char *bytes = static_cast<const unsigned char *>(memory);
    for (size_t offset = 0; offset <= size - length; ++offset)
        if (std::memcmp(bytes + offset, pattern, length) == 0) return bytes + offset;
    return nullptr;
}
#endif // __SSE4_2__'''
        replace_in_file(self, header, '#endif // __SSE4_2__', fallback)
        # The existing non-x86 CPUID path keeps the registers zero. Guard its
        # x86-only header too; feature bit positions do not assert CPU support.
        replace_in_file(self, os.path.join(self.source_folder, "src", "libext", "cpuidex.cpp"),
                        '#include <cpuid.h>', '''#if defined(__i386__) || defined(__x86_64__)
#include <cpuid.h>
#else
#define bit_SSE2 (1u << 26)
#define bit_SSE4_2 (1u << 20)
#define bit_POPCNT (1u << 23)
#endif''')
        # C++17 makes noexcept part of the function type; std::function has
        # no noexcept specialization. Keep the actual callbacks noexcept.
        replace_in_file(self, os.path.join(self.source_folder, "src", "libext", "DirTree.h"),
                        'std::function<bool (const std::string& name) noexcept>',
                        'std::function<bool (const std::string& name)>')
        replace_in_file(self, os.path.join(self.source_folder, "src", "FileScanner.h"),
                        'std::function<int (FileScanner *obj, const char *file_data, size_t file_size, size_t start_offset, size_t *ovector) noexcept>',
                        'std::function<int (FileScanner *obj, const char *file_data, size_t file_size, size_t start_offset, size_t *ovector)>')
        # Clang accepts but ignores x86 -m flags on AArch64. The upstream
        # positive flag probe must never make x86 intrinsic code portable.
        sse = os.path.join(self.source_folder, "src", "FileScanner_sse4_2.cpp")
        save(self, sse, '#if defined(__i386__) || defined(__x86_64__)\n'
             + load(self, sse) + '\n#endif\n')
        scanner = os.path.join(self.source_folder, "src", "FileScanner.cpp")
        replace_in_file(self, scanner, '\tif(sys_has_sse4_2() && sys_has_popcnt())',
                        '#if defined(__i386__) || defined(__x86_64__)\n'
                        '\tif(sys_has_sse4_2() && sys_has_popcnt())')
        replace_in_file(self, scanner, '\telse\n\t{\n\t\tretval = reinterpret_cast<void*>(&FileScanner::CountLinesSinceLastMatch_default);',
                        '\telse\n#endif\n\t{\n\t\tretval = reinterpret_cast<void*>(&FileScanner::CountLinesSinceLastMatch_default);')
        replace_in_file(self, scanner, '\tif(sys_has_sse4_2())',
                        '#if defined(__i386__) || defined(__x86_64__)\n\tif(sys_has_sse4_2())')
        replace_in_file(self, scanner, '\telse\n\t{\n\t\tretval = &FileScanner::LiteralMatch_default;',
                        '\telse\n#endif\n\t{\n\t\tretval = &FileScanner::LiteralMatch_default;')
        # Use the already implemented standard algorithms on non-x86; keep
        # the x86 versions for architectures which really implement them.
        replace_in_file(self, scanner, '#if 0\n\t\tfirst_possible_cu = std::',
                        '#if !defined(__i386__) && !defined(__x86_64__)\n\t\tfirst_possible_cu = std::')

    def generate(self):
        tc = AutotoolsToolchain(self)
        # This is a target-native build; no invented --host/--build tuple.
        tc.configure_args = [arg for arg in tc.configure_args
                             if not arg.startswith(("--host=", "--build=", "--target="))]
        tc.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        bash = os.path.join(self.dependencies.build["bash"].package_folder, "bin", "bash")
        dep = self.dependencies["pcre2"]
        env = Environment()
        env.define("CONFIG_SHELL", bash)
        env.define("SHELL", bash)
        for variable, commands in (("AR", ("ar", "llvm-ar")),
                                   ("RANLIB", ("ranlib", "llvm-ranlib")),
                                   ("NM", ("nm", "llvm-nm")),
                                   ("LD", ("ld.lld", "ld"))):
            tool = next((shutil.which(name) for name in commands if shutil.which(name)), None)
            if not tool:
                raise ConanInvalidConfiguration("Required native tool missing: " + variable)
            env.define(variable, tool)
        coreutils_bin = os.path.join(self.dependencies.build["coreutils"].package_folder, "bin")
        if not os.path.isfile(os.path.join(coreutils_bin, "stty")):
            raise ConanInvalidConfiguration("Published coreutils has no stty")
        env.prepend_path("PATH", coreutils_bin)
        # Configure runs its original invocation probe against a real PTY.
        # Do not modify or pretend that the ambient invalid script is usable.
        env.define("PROG_SCRIPT", sys.executable + " " + os.path.join(self.source_folder, "pty_script.py"))
        env.define("PCRE2_CFLAGS", '-I"{}" -DPCRE2_STATIC'.format(os.path.join(dep.package_folder, "include")))
        env.define("PCRE2_LIBS", '-L"{}" -lpcre2-8'.format(os.path.join(dep.package_folder, "lib")))
        if self.settings.os == "OHOS":
            argp = self.dependencies["argp-standalone"].package_folder
            env.append("CPPFLAGS", '-I"{}"'.format(os.path.join(argp, "include")))
            env.append("LDFLAGS", '-L"{}"'.format(os.path.join(argp, "lib")))
        env.vars(self).save_script("ucg_environment")

    def _configure_tmpdir(self):
        # Change both temporary-directory branches, preserving upstream cleanup.
        # HMDFS permissions must be compatible at creation, not chmod later.
        configure = os.path.join(self.source_folder, "configure")
        original_stat = os.stat(configure)
        replacements = (
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 022 && mkdir "$tmp") &&'),
            ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        )
        for original, replacement in replacements:
            replace_in_file(self, configure, original, replacement, strict=True)
        # Only execution policy changed, not configure.ac or capability data.
        os.utime(configure, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        scratch = os.path.join(self.build_folder, ".autoconf-tmp")
        previous_umask = os.umask(0o022)
        try:
            os.mkdir(scratch, mode=0o755)
        finally:
            os.umask(previous_umask)
        return scratch

    def build(self):
        apply_conandata_patches(self)
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("cpp", "c++")
        if self.settings.os == "OHOS":
            triplet = subprocess.check_output([compiler, "-dumpmachine"], text=True).strip()
            if not re.fullmatch(r"aarch64-(?:unknown-)?linux-ohos", triplet) or self.settings.arch != "armv8":
                raise ConanInvalidConfiguration("Native compiler target mismatch: " + triplet)
            guess = os.path.join(self.source_folder, "build-aux", "config.guess")
            save(self, guess + ".original", load(self, guess))
            save(self, guess, "#!/bin/sh\nprintf '%s\\n' " + shlex.quote(triplet) + "\n")
        bash = os.path.join(self.dependencies.build["bash"].package_folder, "bin", "bash")
        environment = ["conanbuild", "conanrun", "ucg_environment"]
        configure_prefix = ""
        if self.settings.os == "OHOS":
            configure_prefix = "TMPDIR=" + shlex.quote(self._configure_tmpdir()) + " "
        self.run(configure_prefix + shlex.quote(bash) + ' ./configure --prefix=/ --bindir=/bin --libdir=/lib --includedir=/include', env=environment)
        self.run('make -j1', env=environment)
        if can_run(self):
            import importlib.util
            spec = importlib.util.spec_from_file_location("ucg_corpus", os.path.join(self.source_folder, "corpus.py"))
            corpus = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(corpus)
            corpus.prepare_corpora(self)
            # Run both distributed unit cases independently of the corpus-
            # dependent benchmarks, so a missing corpus cannot hide them.
            gtest = self.dependencies["gtest"].package_folder
            unit = os.path.join(self.build_folder, "upstream-unit-tests")
            args = [compiler, "-std=c++17", "-I" + self.source_folder,
                    "-I" + os.path.join(gtest, "include"),
                    os.path.join(self.source_folder, "tests", "unittests.cpp"),
                    "-L" + os.path.join(gtest, "lib"), "-lgtest", "-pthread", "-o", unit]
            self.run(shlex.join(args), env=environment)
            unit_xml = os.path.join(self.build_folder, "upstream-unit-tests.xml")
            self.run(shlex.quote(unit) + ' --gtest_output=xml:' + shlex.quote(unit_xml), env=environment)
            result = ET.parse(unit_xml).getroot()
            if (result.get("tests") != "2" or result.get("failures") != "0"
                    or result.get("disabled") != "0"
                    or result.get("errors", "0") != "0"):
                raise ConanInvalidConfiguration("Full upstream unit inventory did not pass")
            self.output.info("UCG_UPSTREAM_UNIT_RESULT=2/2")
            # All 61 distributed Autotest groups, including the benchmarks.
            suite = load(self, os.path.join(self.source_folder, "tests", "testsuite"))
            ids = re.findall(r'(?:^|=")(\d+);[^\n]+', suite, re.M)
            if ids != [str(i) for i in range(1, 62)]:
                raise ConanInvalidConfiguration("Upstream Autotest inventory changed")
            self.run('make -j1 check', env=environment)
            summary = load(self, os.path.join(self.build_folder, "tests", "testsuite.log"))
            # Autotest's successful aggregate log omits XFAIL details. Their
            # real group logs remain available even when the suite exits 0.
            for number in (28, 30):
                detail = load(self, os.path.join(self.build_folder, "tests", "testsuite.dir", str(number), "testsuite.log"))
                summary += "\n./testsuite.dir/{}/testsuite.log\n".format(number) + detail
            corpus.validate_autotest(summary)
            self.output.info("UCG_UPSTREAM_AUTOTEST=59 PASS + 2 original XFAIL (28,30); 0 SKIP/FAIL/XPASS")
            self.output.info("UCG_UPSTREAM_RESULT=63/63 PASS expected-outcome checks (61 ordinary PASS + 2 original XFAIL)")

    def package(self):
        self.run('make -j1 DESTDIR=' + shlex.quote(self.package_folder) + ' install',
                 env=["conanbuild", "conanrun", "ucg_environment"])
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
