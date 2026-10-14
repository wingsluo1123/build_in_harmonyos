#!/usr/bin/env python3
"""Conan recipe for SoX NG 14.7.1.2.

The package contains the sox_ng CLI and static libsox_ng.  The upstream
Autotools check target runs the three-channel conversion matrix and the
security regression suite.  Additional invocations cover the mono/stereo
matrices and installcheck's testall.sh format round trips.
"""

import os
import re
import shlex
import shutil
import tarfile
from pathlib import PurePosixPath

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class SoxNgConan(ConanFile):
    name = "sox-ng"
    version = "14.7.1.2"
    description = "Audio file format conversion, effects, and libSoX NG"
    license = ["GPL-2.0-only", "LGPL-2.1-or-later"]
    homepage = "https://codeberg.org/sox_ng/sox_ng"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    # This recipe intentionally ships a static libsox_ng so its statically
    # linked format handlers and codec dependencies remain self-contained.
    options = {"fPIC": [True, False]}
    default_options = {
        "fPIC": True,
        "*:shared": False,
        # Use the registry's published shared OHOS variants where the static
        # package is absent.
        "fftw/3.3.11:shared": True,
        "libogg/1.3.6.2:shared": True,
        "libpng/1.6.58.3:shared": True,
        "libvorbis/1.3.7:shared": True,
        "wavpack/5.9.0:shared": True,
        # opusfile's published shared binary requires libogg/1.3.5 static,
        # which conflicts with libvorbis' published libogg/1.3.6.2 shared
        # binary. Keep opusfile static and build only that dependency from source.
        # CI failed in CMake's libopus.a static-archive link step with a
        # missing link command. Keep Opus enabled, but avoid that archive step
        # by building this one codec as a shared library.
        "opus/*:shared": True,
        "*:fPIC": True,
    }

    _codec_requirements = (
        "flac/1.5.0",
        "fftw/3.3.11",
        "libid3tag/0.16.3",
        "libmad/0.15.1b",
        "libmagic/5.48",
        "libmp3lame/3.100",
        "libpng/1.6.58.3",
        "libsndfile/1.2.2",
        "libspeexdsp/1.2.1",
        "speex/1.2.1",
        "libvorbis/1.3.7",
        "opencore-amr/0.1.6",
        "opusfile/0.12",
        "twolame/0.4.0",
        "vo-amrwbenc/0.1.3",
        "wavpack/5.9.0",
    )

    _expected_regression_cases = 71
    _expected_multichannel_cases = 99
    _expected_stereo_cases = 106
    _expected_mono_cases = 168
    _expected_testall_formats = 23

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        for reference in self._codec_requirements:
            self.requires(reference, transitive_headers=True, transitive_libs=True)

        # Keep libvorbis on its published libogg/1.3.6.2 shared binary. The
        # opusfile shared binary pins libogg/1.3.5 static, so it must be rebuilt
        # from source against the ABI-compatible newer package.
        self.requires("libogg/1.3.6.2", override=True)
        # Match the zlib version used by libpng's published binary; it remains
        # within libid3tag's supported zlib range.
        self.requires("zlib/1.3.2", override=True)

    def build_requirements(self):
        # The CI HNP image has the autoconf/Perl base but not aclocal,
        # automake, or libtoolize. Match merged Autotools recipes by supplying
        # those three bootstrap helpers as pinned build requirements.
        self.tool_requires("pkgconf/3.0.6")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def _autotools_bin(self):
        """Find the system autoconf/Perl base used for autoreconf."""
        # Keep the production HNP path as the default while allowing a private
        # HNP-shaped directory for CI-path validation on the device.
        system_bin = os.environ.get(
            "SOXNG_AUTOTOOLS_BASE", "/data/service/hnp/bin"
        )
        required_base = (
            "autoreconf",
            "autoconf",
            "autoheader",
            "autom4te",
            "m4",
            "perl",
        )
        complete = required_base + ("aclocal", "automake", "libtoolize")

        if all(os.path.isfile(os.path.join(system_bin, name)) for name in complete):
            return system_bin

        # This user-managed fallback is device-only and is accepted only as a
        # complete toolchain. CI must use the stable HNP base plus pinned
        # Conan automake/libtool helpers below.
        if not os.environ.get("CI_REPO_ROOT"):
            harmonybrew_bin = os.path.join(
                os.path.expanduser("~"), ".harmonybrew", "bin"
            )
            if all(os.path.isfile(os.path.join(harmonybrew_bin, name)) for name in complete):
                return harmonybrew_bin

        missing = [
            name
            for name in required_base
            if not os.path.isfile(os.path.join(system_bin, name))
        ]
        if not missing:
            return system_bin
        raise ConanException(
            "Missing system Autoconf/Perl tools under {}: {}".format(
                system_bin, ", ".join(missing)
            )
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        git = Git(self)
        git.clone(
            url=source["url"],
            target=".",
            args=["--depth=1", "--branch", source["tag"]],
        )
        actual_commit = git.run("rev-parse HEAD").strip()
        if actual_commit != source["commit"]:
            raise ConanException(
                "SoX NG mirror tag resolved to {}, expected {}".format(
                    actual_commit, source["commit"]
                )
            )
        shutil.rmtree(os.path.join(self.source_folder, ".git"))

        test_tool_source = self.conan_data["test_tools"]["bc"]
        bc_archive = os.path.join(self.source_folder, "bc-test-tool-source.tar.gz")
        download(
            self,
            url=test_tool_source["url"],
            filename=bc_archive,
            sha256=test_tool_source["sha256"],
        )
        bc_source_root = os.path.join(self.source_folder, ".sox-ng-test-tools")
        os.makedirs(bc_source_root, exist_ok=True)
        with tarfile.open(bc_archive, "r:gz") as tar:
            members = tar.getmembers()
            roots = set()
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise ConanException("Unsafe path in the verified bc test-tool archive")
                if not (member.isdir() or member.isfile()):
                    raise ConanException("Unsupported link or special file in the bc test-tool archive")
                if path.parts:
                    roots.add(path.parts[0])
            if roots != {"bc-1.08.2"}:
                raise ConanException("Expected bc-1.08.2 as the test-tool archive root")
            tar.extractall(path=bc_source_root)
        os.remove(bc_archive)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--build=aarch64-unknown-linux-ohos",
                "--enable-static",
                "--disable-shared",
                "--without-libltdl",
                "--without-alsa",
                "--without-ao",
                "--without-coreaudio",
                "--without-ffmpeg",
                "--without-ladspa",
                "--without-oss",
                "--without-pulseaudio",
                "--without-sndio",
                "--without-sun-audio",
                "--without-waveaudio",
                "--with-flac=yes",
                "--with-fftw=yes",
                "--with-id3tag=yes",
                "--with-lame=yes",
                "--with-mad=yes",
                "--with-magic=yes",
                "--with-opus=yes",
                "--with-oggvorbis=yes",
                "--with-png=yes",
                "--with-sndfile=yes",
                "--with-speexdsp=yes",
                "--with-twolame=yes",
                "--with-wavpack=yes",
                "--with-amrnb=yes",
                "--with-amrwb=yes",
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools_bin = self._autotools_bin()
        tool_names = (
            "autoreconf",
            "aclocal",
            "autoconf",
            "autoheader",
            "automake",
            "autom4te",
            "libtoolize",
            "m4",
            "perl",
        )
        missing_helpers = [
            name
            for name in tool_names
            if not os.path.isfile(os.path.join(autotools_bin, name))
        ]
        sed = os.environ.get("SED") or shutil.which("sed")
        if not sed:
            raise ConanException("Could not locate sed for the Autotools bootstrap")

        path_entries = [autotools_bin]
        tool_paths = {
            "AUTOCONF": os.path.join(autotools_bin, "autoconf"),
            "AUTOHEADER": os.path.join(autotools_bin, "autoheader"),
            "AUTOM4TE": os.path.join(autotools_bin, "autom4te"),
            "M4": os.path.join(autotools_bin, "m4"),
            "PERL": os.path.join(autotools_bin, "perl"),
            "SED": sed,
        }
        perl5lib = None
        if missing_helpers:
            build_dependencies = self.dependencies.build
            automake = build_dependencies.get("automake")
            libtool = build_dependencies.get("libtool")
            missing_tool_requirements = [
                name
                for name, dependency in (
                    ("automake", automake),
                    ("libtool", libtool),
                )
                if dependency is None
            ]
            if missing_tool_requirements:
                raise ConanException(
                    "Autotools fallback requires declared build tool(s): {}".format(
                        ", ".join(missing_tool_requirements)
                    )
                )
            automake_folder = automake.package_folder
            libtool_folder = libtool.package_folder
            automake_bin = os.path.join(automake_folder, "bin")
            libtool_bin = os.path.join(libtool_folder, "bin")
            helper_sources = {
                "ACLOCAL": os.path.join(automake_bin, ".aclocal-real"),
                "AUTOMAKE": os.path.join(automake_bin, ".automake-real"),
                "LIBTOOLIZE": os.path.join(libtool_bin, "libtoolize"),
            }
            missing_paths = [
                path
                for path in list(tool_paths.values()) + list(helper_sources.values())
                if not os.path.isfile(path)
            ]
            if missing_paths:
                raise ConanException(
                    "Autotools bootstrap executables are missing: {}".format(
                        ", ".join(missing_paths)
                    )
                )
            # automake/1.18 needs its own pure-Perl modules on @INC. Do not
            # inherit PERL5LIB from Conan's perl/5.42.2 tool package: system
            # Perl must load only its matching XS modules from HNP.
            perl5lib = os.path.join(
                automake_folder, "share", "automake-1.18"
            )
            if not os.path.isdir(perl5lib):
                raise ConanException(
                    "Automake Perl modules are missing: {}".format(perl5lib)
                )
            # Conan's automake scripts carry an absolute HNP Perl shebang. Use
            # the selected system Perl explicitly so the same helper packages
            # work on CI and devices without loading Conan's Perl/XS modules.
            wrapper_dir = os.path.join(
                self.build_folder, ".sox-ng-autotools-wrappers"
            )
            os.makedirs(wrapper_dir, exist_ok=True)
            wrappers = {
                "ACLOCAL": (
                    "#!/bin/sh\nexec {perl} {script} "
                    "--automake-acdir={automake_acdir} "
                    "--system-acdir={system_acdir} \"$@\"\n"
                ).format(
                    perl=shlex.quote(tool_paths["PERL"]),
                    script=shlex.quote(helper_sources["ACLOCAL"]),
                    automake_acdir=shlex.quote(
                        os.path.join(automake_folder, "share", "aclocal-1.18")
                    ),
                    system_acdir=shlex.quote(
                        os.path.join(automake_folder, "share", "aclocal")
                    ),
                ),
                "AUTOMAKE": (
                    "#!/bin/sh\nexec {perl} {script} "
                    "--libdir={libdir} \"$@\"\n"
                ).format(
                    perl=shlex.quote(tool_paths["PERL"]),
                    script=shlex.quote(helper_sources["AUTOMAKE"]),
                    libdir=shlex.quote(perl5lib),
                ),
                "LIBTOOLIZE": (
                    "#!/bin/sh\nexec /bin/sh {script} \"$@\"\n"
                ).format(script=shlex.quote(helper_sources["LIBTOOLIZE"])),
            }
            for name, contents in wrappers.items():
                wrapper_path = os.path.join(wrapper_dir, name.lower())
                with open(wrapper_path, "w", encoding="utf-8") as stream:
                    stream.write(contents)
                os.chmod(wrapper_path, 0o755)
                tool_paths[name] = wrapper_path
            path_entries.extend((automake_bin, libtool_bin))
            self.output.info(
                "HNP Autotools helpers missing: {}; using automake/1.18 and libtool/2.5.4".format(
                    ", ".join(missing_helpers)
                )
            )
        else:
            tool_paths.update(
                {
                    "ACLOCAL": os.path.join(autotools_bin, "aclocal"),
                    "AUTOMAKE": os.path.join(autotools_bin, "automake"),
                    "LIBTOOLIZE": os.path.join(autotools_bin, "libtoolize"),
                }
            )
            self.output.info(
                "Autotools bootstrap: complete system toolchain at {}".format(
                    autotools_bin
                )
            )

        command = "unset PERL5LIB; export PATH={}:$PATH; ".format(
            shlex.quote(os.pathsep.join(path_entries))
        )
        if perl5lib:
            command += "export PERL5LIB={}; ".format(shlex.quote(perl5lib))
        for variable, executable in tool_paths.items():
            command += "export {}={}; ".format(variable, shlex.quote(executable))
        command += "{} --force --install".format(
            shlex.quote(os.path.join(autotools_bin, "autoreconf"))
        )
        self.run(command, cwd=self.source_folder, env="conanbuild")

        # Autoconf's generated config.status uses a restrictive umask that
        # produces unwritable temporary directories on the HarmonyOS HMDFS.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8") as stream:
            configure_text = stream.read()
        if "umask 077" in configure_text:
            with open(configure, "w", encoding="utf-8") as stream:
                stream.write(configure_text.replace("umask 077", "umask 022"))

        # The CI log does not identify the missing executable, but the error
        # occurs in CMake's static libopus.a link step. Opus is shared here;
        # make host libraries visible to Autoconf's linked probe and tests.
        self._add_host_library_paths_to_environment()
        autotools.configure()
        autotools.make(args=["-j2"])

        # The upstream scripts are written for an in-source tree.  Conan
        # builds out of source, so supply the reference vectors and regression
        # case directories in the build tree without changing upstream files.
        self._stage_upstream_test_data()
        test_tools_bin = self._prepare_test_tools()
        test_env = self._test_environment(test_tools_bin)

        check_log = self._run_checked(
            test_env + " make -j2 check",
            cwd=self.build_folder,
            label="upstream make check",
        )
        self._verify_make_check(check_log)

        for mode, expected in (("-1", self._expected_mono_cases),
                               ("-2", self._expected_stereo_cases)):
            log = self._run_checked(
                test_env + ' sh "{}" {} --bindir=. --libdir=.libs --builddir="." --srcdir="{}"'.format(
                    os.path.join(self.build_folder, "src", "tests.sh"),
                    mode,
                    os.path.join(self.source_folder, "src"),
                ),
                cwd=os.path.join(self.build_folder, "src"),
                label="upstream tests.sh " + mode,
            )
            self._verify_conversion_matrix(log, expected, mode)

        testall_log = self._run_checked(
            test_env + ' sh "{}" --bindir=. --libdir=.libs --srcdir="{}"'.format(
                os.path.join(self.build_folder, "src", "testall.sh"),
                os.path.join(self.source_folder, "src"),
            ),
            cwd=os.path.join(self.build_folder, "src"),
            label="upstream testall.sh",
        )
        self._verify_testall(testall_log)

    def _stage_upstream_test_data(self):
        build_src = os.path.join(self.build_folder, "src")
        source_src = os.path.join(self.source_folder, "src")
        vectors = os.path.join(source_src, "vectors")
        if os.path.isdir(vectors):
            shutil.copytree(
                vectors,
                os.path.join(build_src, "vectors"),
                dirs_exist_ok=True,
            )
        monkey = os.path.join(source_src, "monkey.wav")
        if os.path.isfile(monkey):
            shutil.copy2(monkey, build_src)

        source_test = os.path.join(self.source_folder, "test")
        build_test = os.path.join(self.build_folder, "test")
        # The out-of-source check target also needs root helpers such as
        # samples.c and check.sh, in addition to all 71 regression directories.
        check_script = os.path.join(source_test, "check.sh")
        with open(check_script, "r", encoding="utf-8") as stream:
            check_lines = stream.read().splitlines()
        temp_lines = [i for i, line in enumerate(check_lines) if line.startswith("errs=")]
        if len(temp_lines) != 1:
            raise ConanException("Expected exactly one regression temp-file setting in test/check.sh")
        check_lines[temp_lines[0]] = 'errs="{}"'.format(
            os.path.join(build_test, ".check$$")
        )
        # HarmonyOS exposes /tmp read-only. Keep the upstream per-case output
        # capture in this writable build directory so all 71 cases can run.
        remove_lines = [i for i, line in enumerate(check_lines) if line.strip() == "rm $errs"]
        if len(remove_lines) != 1:
            raise ConanException("Expected exactly one regression output cleanup in test/check.sh")
        check_lines.insert(
            remove_lines[0],
            '\tif [ "$status" -ne 0 ]; then cat "$errs"; fi',
        )
        with open(check_script, "w", encoding="utf-8") as stream:
            stream.write("\n".join(check_lines) + "\n")
        shutil.copytree(source_test, build_test, dirs_exist_ok=True)

        # Toybox grep on HarmonyOS does not search binary AIFC files, even
        # though BUG-345 intentionally checks the binary MARK and INST chunks.
        # Keep the upstream round-trip test intact and make those two byte
        # checks binary-safe in the staged build-tree copy only.
        bug345_script = os.path.join(build_test, "BUG-345", "run")
        with open(bug345_script, "r", encoding="utf-8") as stream:
            bug345_text = stream.read()
        input_marker_check = "(grep -q MARK alaw.aifc && grep -q INST alaw.aifc)"
        output_marker_check = "grep -q MARK out.aifc && grep -q INST out.aifc"
        if bug345_text.count(input_marker_check) != 1:
            raise ConanException("Expected the BUG-345 input marker check")
        if bug345_text.count(output_marker_check) != 1:
            raise ConanException("Expected the BUG-345 output marker check")
        marker_helper = (
            "has_mark_and_inst() {\n"
            "    python3 - \"$1\" <<'PY'\n"
            "import sys\n"
            "with open(sys.argv[1], \"rb\") as stream:\n"
            "    data = stream.read()\n"
            "sys.exit(0 if b\"MARK\" in data and b\"INST\" in data else 1)\n"
            "PY\n"
            "}\n\n"
        )
        if bug345_text.count("rm -f out.aifc\n") != 2:
            raise ConanException("Expected both BUG-345 output cleanup lines")
        bug345_text = bug345_text.replace(
            "rm -f out.aifc\n",
            "rm -f out.aifc\n\n" + marker_helper,
            1,
        )
        bug345_text = bug345_text.replace(
            input_marker_check,
            "has_mark_and_inst alaw.aifc",
        )
        bug345_text = bug345_text.replace(
            output_marker_check,
            "has_mark_and_inst out.aifc",
        )
        with open(bug345_script, "w", encoding="utf-8") as stream:
            stream.write(bug345_text)

        # tests.sh's execute() replaces LD_LIBRARY_PATH with only libdir,
        # dropping shared host dependencies needed by the test executable.
        tests_source = os.path.join(source_src, "tests.sh")
        with open(tests_source, "r", encoding="utf-8") as stream:
            tests_text = stream.read()
        old_test_library_path = 'LD_LIBRARY_PATH="${libdir}"'
        if tests_text.count(old_test_library_path) != 1:
            raise ConanException("Expected one tests.sh library-path assignment")
        tests_text = tests_text.replace(
            old_test_library_path,
            'LD_LIBRARY_PATH="${libdir}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"',
        )
        old_format_probe_library_path = "LD_LIBRARY_PATH=${libdir}"
        if tests_text.count(old_format_probe_library_path) != 1:
            raise ConanException("Expected one tests.sh format-probe library-path assignment")
        tests_text = tests_text.replace(
            old_format_probe_library_path,
            "LD_LIBRARY_PATH=${libdir}:${LD_LIBRARY_PATH:-}",
        )
        with open(tests_source, "w", encoding="utf-8") as stream:
            stream.write(tests_text)
        with open(os.path.join(build_src, "tests.sh"), "w", encoding="utf-8") as stream:
            stream.write(tests_text)

        # testall.sh writes fixed /tmp/monkey.* paths. /tmp is read-only on
        # HarmonyOS; run the same script from build/src with local outputs.
        testall_source = os.path.join(source_src, "testall.sh")
        with open(testall_source, "r", encoding="utf-8") as stream:
            testall_text = stream.read()
        if (
            testall_text.count("/tmp/monkey.") != 2
            or testall_text.count("/tmp/monkey1.wav") != 1
        ):
            raise ConanException("Expected the three fixed /tmp outputs in upstream src/testall.sh")
        testall_text = testall_text.replace("/tmp/monkey.", "./.sox-ng-monkey.")
        testall_text = testall_text.replace("/tmp/monkey1.wav", "./.sox-ng-monkey-1.wav")
        old_testall_library_path = "LD_LIBRARY_PATH=${libdir}"
        if testall_text.count(old_testall_library_path) != 2:
            raise ConanException("Expected two testall.sh library-path assignments")
        testall_text = testall_text.replace(
            old_testall_library_path,
            "LD_LIBRARY_PATH=${libdir}:${LD_LIBRARY_PATH:-}",
        )
        with open(os.path.join(build_src, "testall.sh"), "w", encoding="utf-8") as stream:
            stream.write(testall_text)

    def _prepare_test_tools(self):
        tool_root = os.path.join(self.build_folder, ".sox-ng-test-tools")
        tool_bin = os.path.join(tool_root, "bin")
        bc_source = os.path.join(self.source_folder, ".sox-ng-test-tools", "bc-1.08.2")
        bc_build = os.path.join(tool_root, "bc-build")
        os.makedirs(tool_bin, exist_ok=True)
        os.makedirs(bc_build, exist_ok=True)

        # The upstream regression tests require bc, which is absent on the
        # device. Build the verified GNU bc source as a test-only executable.
        bc_configure = os.path.join(bc_source, "configure")
        with open(bc_configure, "r", encoding="utf-8") as stream:
            bc_configure_text = stream.read()
        if "umask 077" not in bc_configure_text:
            raise ConanException("Expected GNU bc configure's private temporary-directory umask")
        # Autoconf creates a private confXXXXXX directory with mode 0700.
        # HMDFS does not honor that mode consistently for the subsequent
        # config.status writes, so use ordinary owner-writable permissions.
        with open(bc_configure, "w", encoding="utf-8") as stream:
            stream.write(bc_configure_text.replace("umask 077", "umask 022"))
        self.run(
            '"{}" --without-readline --prefix="{}"'.format(
                os.path.join(bc_source, "configure"),
                os.path.join(tool_root, "bc-install"),
            ),
            cwd=bc_build,
            env="conanbuild",
        )
        # The regression scripts need bc's library and executable only; the
        # full recursive build also invokes absent makeinfo for documentation.
        self.run(
            "make -j2 -C lib && make -j2 -C bc",
            cwd=bc_build,
            env="conanbuild",
        )
        bc_binary = os.path.join(bc_build, "bc", "bc")
        if not os.path.isfile(bc_binary):
            raise ConanException("GNU bc test utility did not produce bc/bc")
        shutil.copy2(bc_binary, os.path.join(tool_bin, "bc"))

        # Toybox df returns only a header for HarmonyOS HMDFS paths even though
        # statvfs reports their real capacity. Report the actual values for
        # the exact path requested by the upstream 4GB WAV test.
        df_script = os.path.join(tool_bin, "df")
        with open(df_script, "w", encoding="utf-8") as stream:
            stream.write(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "paths = [arg for arg in sys.argv[1:] if not arg.startswith('-')]\n"
                "path = paths[-1] if paths else '.'\n"
                "s = os.statvfs(path)\n"
                "unit = s.f_frsize or s.f_bsize\n"
                "scale = lambda blocks: (blocks * unit + 1023) // 1024\n"
                "total = scale(s.f_blocks)\n"
                "used = scale(s.f_blocks - s.f_bfree)\n"
                "available = s.f_bavail * unit // 1024\n"
                "denominator = max(1, used + available)\n"
                "capacity = (100 * used + denominator - 1) // denominator\n"
                "print('Filesystem 1K-blocks Used Available Use% Mounted on')\n"
                "print('{} {} {} {} {}% {}'.format(path, total, used, available, capacity, path))\n"
            )
        os.chmod(df_script, 0o755)
        return tool_bin

    def _test_environment(self, tool_bin):
        sox_temp = "--temp {}".format(self.build_folder)
        library_path = os.pathsep.join(self._host_library_paths())
        return "LD_LIBRARY_PATH={}:${{LD_LIBRARY_PATH:-}} PATH={}:$PATH SOX_OPTS={}".format(
            shlex.quote(library_path),
            shlex.quote(tool_bin),
            shlex.quote(sox_temp),
        )

    def _host_library_paths(self):
        library_paths = []
        for dependency in self.dependencies.host.values():
            package_folder = dependency.package_folder
            for library_dir in dependency.cpp_info.libdirs:
                path = os.path.normpath(os.path.join(package_folder, library_dir))
                if os.path.isdir(path) and path not in library_paths:
                    library_paths.append(path)
        return library_paths

    def _add_host_library_paths_to_environment(self):
        library_paths = self._host_library_paths()
        if not library_paths:
            return

        current = os.environ.get("LD_LIBRARY_PATH", "")
        current_paths = [path for path in current.split(os.pathsep) if path]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            library_paths + [path for path in current_paths if path not in library_paths]
        )
        self.output.info(
            "Added {} Conan host library directories to LD_LIBRARY_PATH".format(
                len(library_paths)
            )
        )

    def _run_checked(self, command, cwd, label):
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
        log_path = os.path.join(cwd, ".sox-ng-{}.log".format(safe_label))
        try:
            self.run(
                '{} > "{}" 2>&1'.format(command, log_path),
                cwd=cwd,
                env="conanbuild",
            )
        except Exception as exc:
            log = self._read_log(log_path)
            if log:
                self.output.error(log)
            raise ConanException("{} failed: {}".format(label, exc)) from exc
        log = self._read_log(log_path)
        self.output.info(log)
        return log

    @staticmethod
    def _read_log(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as stream:
                return stream.read()
        except OSError:
            return ""

    def _verify_make_check(self, log):
        statuses = re.findall(
            r"^([^:\r\n]+):\s+(OK|VOID|FAIL|SUCC|ABRT|SEGV|FPE|LOOP|EXEC|ASAN|[0-9]+)\s*$",
            log,
            re.MULTILINE,
        )
        if len(statuses) != self._expected_regression_cases:
            raise ConanException(
                "make check ran {} regression cases; expected {}".format(
                    len(statuses), self._expected_regression_cases
                )
            )
        failed = [(name, result) for name, result in statuses if result != "OK"]
        if failed:
            raise ConanException("Regression failures or skips: {}".format(failed))
        self._verify_conversion_matrix(
            log,
            self._expected_multichannel_cases,
            "make check (three-channel)",
        )

    @staticmethod
    def _verify_conversion_matrix(log, expected, label):
        count = len(re.findall(r"^ok\s+channels=", log, re.MULTILINE))
        synth_size_passes = len(
            re.findall(r"^ok\s+synth size\s*$", log, re.MULTILINE)
        )
        synth_size_failures = re.findall(
            r"^\*FAIL\*\s+synth size\s*$", log, re.MULTILINE
        )
        skipped = re.findall(r"^Skipped:\s*(.*)$", log, re.MULTILINE)
        if (
            count != expected
            or synth_size_passes != 1
            or synth_size_failures
            or any(item.strip() for item in skipped)
        ):
            raise ConanException(
                "{} ran {} conversion cases (expected {}), synth-size checks {}; skipped formats: {}".format(
                    label,
                    count,
                    expected,
                    synth_size_passes,
                    [item.strip() for item in skipped if item.strip()],
                )
            )

    def _verify_testall(self, log):
        formats = re.findall(r"^Format:\s+", log, re.MULTILINE)
        failures = re.findall(r"^Test (?:to|from) .* failed\.", log, re.MULTILINE)
        if len(formats) != self._expected_testall_formats or failures:
            raise ConanException(
                "testall.sh ran {} format cases (expected {}); failures: {}".format(
                    len(formats), self._expected_testall_formats, failures
                )
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["sox_ng"]
        # OHOS clang enables OpenMP for the upstream effects by default. The
        # static archive leaves its runtime symbols for consumers to resolve.
        self.cpp_info.system_libs = ["m", "omp"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "sox-ng")
        self.cpp_info.set_property("cmake_target_name", "sox-ng::sox-ng")
        self.cpp_info.set_property("pkg_config_name", "sox-ng")
