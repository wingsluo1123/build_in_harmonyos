#!/usr/bin/env python3
"""Conan recipe — vkd3d 1.19 (autotools).

vkd3d is the Wine project's Direct3D 12 to Vulkan translation library. The
package ships three libraries (``libvkd3d``, ``libvkd3d-shader``,
``libvkd3d-utils``) and two CLI tools (``vkd3d-compiler``, ``vkd3d-dxbc``).

Source choice
-------------
Built from the *official WineHQ release tarball*
(``https://dl.winehq.org/vkd3d/source/vkd3d-1.19.tar.xz``) rather than the
GitLab git-archive. The release tarball is a ``make dist`` artefact and ships the
files a bare git checkout does not have:

* a pre-generated ``configure`` (so no autoreconf/automake/libtool is needed), and
* everything upstream generates with **widl** (Wine's IDL compiler):
  ``include/vkd3d_d3d12.h`` plus the other eleven public headers,
  ``tests/dxcompiler.h`` and ``include/private/spirv_grammar.h``.

``widl`` belongs to Wine and is not available for OHOS, so the git-archive cannot
be built as-is. Equivalence with the git archive at tag ``vkd3d-1.19`` was
verified byte-for-byte: all 14 ``*.idl`` and all 287 ``*.shader_test`` files are
identical, i.e. upstream's widl 9.16 output is generated from exactly the same IDL
sources. Full evidence in ``notes.md``.

Vulkan
------
vkd3d does **not** link the Vulkan loader; it ``dlopen()``s ``SONAME_LIBVULKAN``
at runtime (``VULKAN_LIBS`` is not referenced by the build system at all).
``SONAME_LIBVULKAN`` is therefore pinned to the production value
``libvulkan.so.1``, so that the link-time ``AC_CHECK_LIB`` auto-detection cannot
pick up the test-only software Vulkan substrate (see below) and bake a wrong
runtime name into the shipped library. Upstream provides
``AC_ARG_VAR([SONAME_LIBVULKAN])`` for exactly this purpose.

Tests
-----
``make check`` runs the full upstream suite (three ``vkd3d_*`` programs, three
cross-test programs and the 287 ``*.shader_test`` files driven by
``tests/shader_runner``). Those tests need a real Vulkan device. The build worker
has no GPU, no ``libvulkan`` and no ICD, so the recipe provisions a *test-time*
software Vulkan 1.3 substrate from the ``swiftshader`` package (CPU
implementation) and points the runtime loader name at it. This keeps the shipped
artefact unchanged while letting the upstream suite genuinely execute instead of
silently reporting zero executed tests as passes.
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


# Build-time compatibility shim (see the class docstring and notes.md).
#
# vkd3d's pre-generated ./configure probes for the CPAN distribution "JSON" with
# `$PERL -e "use JSON;"` and aborts when it is missing. "JSON" is not core Perl;
# "JSON::PP" is core since 5.14 and offers the same interface the JSON
# distribution itself falls back to. Shipping this shim on PERL5LIB satisfies the
# probe without editing ./configure, which is a generated file.
_JSON_PM_CONTENT = '''\
package JSON;
use strict;
use warnings;
use JSON::PP ();
use Exporter 'import';
our @ISA = ('JSON::PP');
our @EXPORT = qw(decode_json encode_json);
sub new { my $class = shift; return JSON::PP->new(@_); }
sub decode_json { return JSON::PP::decode_json(@_); }
sub encode_json { return JSON::PP::encode_json(@_); }
1;
'''


class Vkd3dConan(ConanFile):
    name = "vkd3d"
    version = "1.19"
    description = ("vkd3d: Direct3D 12 to Vulkan translation library (Wine project), "
                   "including its own DXBC/DXIL to SPIR-V shader compiler")
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.winehq.org/wine/vkd3d"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_spirv_tools": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        # Upstream default is disabled (configure --with-spirv-tools default:
        # disabled); SPIRV-Tools is only used for extra validation.
        "with_spirv_tools": False,
    }

    # --- post-`make check` zero-execution guard -------------------------------
    # Upstream's test main prints the per-program counter line
    # UNCONDITIONALLY (include/private/vkd3d_test.h:316, right after
    # vkd3d_test_main() returns) and only fails on `failure_count`
    # (:328 return). A run with no usable device therefore still logs
    # `<runner>: 0 tests executed (0 failures, ...)` and exits 0, which automake
    # records as PASS. Only `N > 0` proves the tests really executed.
    _TEST_PROGRAMS = ("d3d12", "d3d12_invalid_usage", "hlsl_d3d12",
                      "vkd3d_api", "vkd3d_common", "vkd3d_shader_api")
    _COUNTER_LINE_RE = re.compile(
        r"^[ \t]*([A-Za-z0-9_.+-]+):[ \t]+([0-9]+) tests executed\b", re.M)
    _VKD3D_API_SKIP = "D3D12 device cannot be created"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: os check must use "in (...)", never "== Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("vkd3d is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # vkd3d only dlopen()s the Vulkan loader at runtime, but it needs the
        # Vulkan and SPIR-V *headers* at build time (configure hard-errors
        # without vulkan/vulkan.h and spirv/unified1/spirv.h).
        self.requires("vulkan-headers/vulkan-sdk-1.4.357.0")
        self.requires("spirv-headers/vulkan-sdk-1.3.290.0")
        if self.options.with_spirv_tools:
            self.requires("spirv-tools/vulkan-sdk-1.3.290.0")

    def build_requirements(self):
        # Test-only substrate: software Vulkan 1.3 (CPU) so that `make check`
        # really executes on a worker with no GPU / no Vulkan loader / no ICD.
        # tool_requires keeps it out of the consumer-facing dependency graph.
        self.tool_requires("swiftshader/0_git20260921")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _neutralise_config_status_umask(configure_path):
        """E114 / E1016(b): make configure's temp directory usable on HMDFS.

        The generated ``configure`` creates its scratch directory with
        ``(umask 077 && mktemp -d ./confXXXXXX)``. On HMDFS that directory lands
        as ``drwx--S---`` owned by the shared uid, so ``config.status`` cannot
        write ``./confXXXXXX/subs1.awk`` and configuration dies with
        ``config.status: error: could not setup config files machinery``.
        Dropping the ``umask 077`` prefixes is the minimal fix. Both replacement
        targets are asserted so the workaround cannot rot silently.
        """
        with open(configure_path, encoding="utf-8") as fh:
            text = fh.read()
        mktemp_old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
        mkdir_old = '(umask 077 && mkdir "$tmp")'
        for pattern in (mktemp_old, mkdir_old):
            if pattern not in text:
                raise ConanException(
                    "vkd3d: E114 `umask 077` workaround pattern not found in "
                    "./configure (%r); upstream changed - re-check HMDFS "
                    "temporary-directory permissions" % pattern)
        text = text.replace(mktemp_old,
                            'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
        text = text.replace(mkdir_old, 'mkdir "$tmp"')
        with open(configure_path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _swiftshader_package_folder(self):
        for deps in (getattr(self.dependencies, "build", None), self.dependencies):
            if deps is None:
                continue
            try:
                ref = deps["swiftshader"]
            except (KeyError, ConanException):
                continue
            folder = getattr(ref, "package_folder", None)
            if folder and os.path.isdir(folder):
                return folder
        return None

    def _stage_vulkan_substrate(self):
        """Create a directory holding a drop-in ``libvulkan.so.1``.

        SwiftShader's ``libvk_swiftshader.so`` is a complete Vulkan 1.3
        implementation that exports the global entry points (``vkCreateInstance``,
        ``vkGetInstanceProcAddr``, ``vkEnumeratePhysicalDevices``, ...), so vkd3d's
        ``dlopen("libvulkan.so.1")`` can load it directly - no Khronos loader
        required.
        """
        pkg = self._swiftshader_package_folder()
        if not pkg:
            raise ConanException(
                "vkd3d: swiftshader package folder not found; refusing to run "
                "`make check` without a Vulkan device (that would report zero "
                "executed tests as passes)")
        src = os.path.join(pkg, "lib", "libvk_swiftshader.so")
        if not os.path.exists(src):
            raise ConanException("vkd3d: missing {}".format(src))

        substrate = os.path.join(self.build_folder, "vk-substrate")
        os.makedirs(substrate, exist_ok=True)
        for name in ("libvulkan.so.1", "libvulkan.so"):
            dst = os.path.join(substrate, name)
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copy2(src, dst)

        icd = None
        icd_src = os.path.join(pkg, "res", "vk_swiftshader_icd.json")
        if os.path.exists(icd_src):
            icd = os.path.join(substrate, "vk_swiftshader_icd.json")
            shutil.copy2(icd_src, icd)
        return substrate, icd

    def _assert_tests_really_executed(self):
        """Hard post-`make check` guard against a zero-execution false green.

        Staging the substrate in ``generate()`` closes the "no device on the
        worker" channel, but *not* the residual one: a substrate that is present
        yet fails to load at run time (ABI / dependency mismatch, ICD rejected)
        still makes all 287 ``shader_runner`` logs report ``0 tests executed``
        and exit 0, so ``make check`` still summarises 293 PASS. Claiming that
        zero execution is structurally excluded therefore needs this second,
        independent assertion.

        Requirements (all of them, else ``ConanException``):

        a. each of the 6 upstream test programs has a counter line and ``N > 0``
           - ``vkd3d_api`` is the sole allowed exception: ``N == 0`` is accepted
             only when its log carries upstream's
             ``D3D12 device cannot be created`` skip message;
        b. the 287 ``shader_runner`` logs exist and sum to ``> 0``;
        c. if not a single log reports ``N > 0`` the check raises (never a
           silent pass).

        Support readings (log count, per-program hit count, ``shader_runner``
        sum) are always printed, pass or fail.
        """
        tests_dir = os.path.join(self.build_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "vkd3d: no tests/ directory at %r after `make check`; cannot "
                "verify that the upstream suite really executed" % tests_dir)

        log_count = 0
        positive_lines = 0
        zero_lines = 0
        shader_runner_logs = 0
        shader_runner_sum = 0
        programs = {}          # program name -> max N seen in its log
        api_zero_skipped = False

        for root, _dirs, files in os.walk(tests_dir):
            for name in sorted(files):
                if not name.endswith(".log"):
                    continue
                log_count += 1
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                for runner, count in self._COUNTER_LINE_RE.findall(text):
                    count = int(count)
                    if count > 0:
                        positive_lines += 1
                    else:
                        zero_lines += 1
                    if runner == "shader_runner":
                        shader_runner_logs += 1
                        shader_runner_sum += count
                    elif runner in self._TEST_PROGRAMS:
                        programs[runner] = max(count, programs.get(runner, -1))
                        if (runner == "vkd3d_api" and count == 0
                                and self._VKD3D_API_SKIP in text):
                            api_zero_skipped = True

        self.output.info(
            "vkd3d zero-execution guard: parsed %d *.log; counter lines=%d "
            "(N>0: %d, N=0: %d); programs hit=%d/6 %s; shader_runner: %d logs, "
            "sum(N)=%d"
            % (log_count, positive_lines + zero_lines, positive_lines,
               zero_lines, len(programs), sorted(programs),
               shader_runner_logs, shader_runner_sum))

        problems = []
        for runner in self._TEST_PROGRAMS:
            if runner not in programs:
                problems.append(
                    "program %r has no `N tests executed` line in tests/**/*.log"
                    % runner)
            elif programs[runner] <= 0 and not (
                    runner == "vkd3d_api" and api_zero_skipped):
                problems.append(
                    "program %r executed 0 tests (N=%d)%s"
                    % (runner, programs[runner],
                       "" if runner != "vkd3d_api"
                       else " and its log lacks the %r skip message"
                            % self._VKD3D_API_SKIP))
        if shader_runner_logs == 0:
            problems.append("no `shader_runner` test log found")
        elif shader_runner_sum <= 0:
            problems.append(
                "shader_runner executed 0 tests across %d logs (N>0 required)"
                % shader_runner_logs)
        if positive_lines == 0:
            problems.append(
                "no log reports N>0 tests executed at all: `make check` passed "
                "without executing any test (zero-execution false green)")
        if problems:
            raise ConanException(
                "vkd3d: post-`make check` zero-execution assertion FAILED - %s "
                "| readings: %d *.log parsed, %d counter lines, %d with N>0, "
                "%d with N=0, %d programs hit, shader_runner %d logs sum=%d"
                % ("; ".join(problems), log_count, positive_lines + zero_lines,
                   positive_lines, zero_lines, len(programs),
                   shader_runner_logs, shader_runner_sum))
        self.output.info(
            "vkd3d zero-execution guard: PASS (6/6 programs with N>0 except "
            "vkd3d_api N=0+skip, shader_runner sum=%d)" % shader_runner_sum)

    # ----------------------------------------------------------------- generate
    def generate(self):
        # AutotoolsToolchain does not translate dependency cpp_info into
        # -I/-L/-l; AutotoolsDeps does. Without it configure cannot see
        # spirv/unified1/spirv.h and aborts with "configure: error: spirv.h not
        # found." (vulkan/vulkan.h happens to be satisfied by the OHOS SDK
        # sysroot, which masked the missing -I on the first attempt.)
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-maintainer-mode")
        # Optional integrations that are not part of the shader/D3D12 core and
        # whose dependencies are not available here.
        tc.configure_args.append("--without-ncurses")
        tc.configure_args.append("--without-xcb")
        tc.configure_args.append("--without-opengl")
        if self.options.with_spirv_tools:
            tc.configure_args.append("--with-spirv-tools")
        else:
            tc.configure_args.append("--without-spirv-tools")
        if not self.options.shared:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        if str(self.settings.os) == "OHOS":
            # Explicit triplets so configure never needs config.guess, whose
            # 2024-07-27 copy does not recognise HarmonyOS (E007); config.sub
            # already accepts aarch64-linux-ohos. Both values are supplied so
            # the cross-compile detection is deterministic.
            triplet = "aarch64-linux-ohos"
            tc.configure_args.append("--host=%s" % triplet)
            tc.configure_args.append("--build=%s" % triplet)

        env = tc.environment()
        # Keep the production dlopen() name regardless of what is installed on
        # the build machine (upstream AC_ARG_VAR).
        env.define("SONAME_LIBVULKAN", "libvulkan.so.1")

        # JSON.pm shim so the pre-generated ./configure probe passes.
        shim = os.path.join(self.build_folder, "perl-shim")
        os.makedirs(shim, exist_ok=True)
        save(self, os.path.join(shim, "JSON.pm"), _JSON_PM_CONTENT)
        env.prepend_path("PERL5LIB", shim)

        # Vulkan substrate for `make check`.
        substrate, icd = self._stage_vulkan_substrate()
        env.prepend_path("LD_LIBRARY_PATH", substrate)
        if icd:
            env.define("VK_ICD_FILENAMES", icd)
            env.define("VK_DRIVER_FILES", icd)

        tc.generate(env)

    # -------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        self._neutralise_config_status_umask(
            os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # The upstream suite must genuinely execute; the substrate staged in
        # generate() provides the Vulkan device it needs.
        autotools.make(target="check")
        # ... and the logs must prove it: assert N>0 per program / per
        # shader_runner log set (upstream prints the counter line even when it
        # executed nothing, so "a log exists" is not evidence - see the guard).
        self._assert_tests_really_executed()

    # ------------------------------------------------------------------ package
    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la wrappers contain absolute build paths; drop them.
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                if name.endswith(".la"):
                    os.remove(os.path.join(root, name))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["vkd3d", "vkd3d-shader", "vkd3d-utils"]
        # automake installs the public headers through pkginclude_HEADERS, whose
        # default destination is $(includedir)/$(PACKAGE), i.e.
        # <prefix>/include/vkd3d/. Upstream's own pkg-config file confirms this
        # contract: "Cflags: -I${includedir}/vkd3d".
        self.cpp_info.includedirs = ["include/vkd3d"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
        if not self.options.shared:
            self.cpp_info.defines = ["VKD3D_STATIC"]
