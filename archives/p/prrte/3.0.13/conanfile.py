#!/usr/bin/env python3
"""Conan recipe — prrte 3.0.13 (Autotools).

PRRTE: PMIx Reference RunTime Environment — the process-management
runtime used by Open MPI (https://github.com/openpmix/prrte).

PRRTE is NOT a system same-name library (R26 exemption), so dynamic
linking is the default. Conan manages the full dependency chain
(pmix + hwloc + libevent).

OHOS platform adaptation (patches/, see notes.md):
- 0001/0002: config.guess/config.sub teach the 2021-01-25 autotools
  scripts about HarmonyOS (aarch64-unknown-linux-ohos) — E007/E072.
- 0003: configure/config.status umask 077 -> 022. On HMDFS a 0700 dir
  created under umask 077 is not writable even by its owner (E011),
  which broke `mktemp -d` temp files during configure.
- 0004: plm_ssh_module.c rindex -> strrchr (BSD legacy function not
  present in OHOS libc).
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.files import copy as conan_copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class PrrteConan(ConanFile):
    name = "prrte"
    version = "3.0.13"
    description = "PMIx Reference RunTime Environment"
    license = "BSD-3-Clause"
    homepage = "https://github.com/openpmix/prrte"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # 上游 git 仓库 v3.0.13 的 test/ 目录注册了 19 个测试用例
    # （test/Makefile 的 TESTS），但 release tarball 不含 test/ 目录。
    # 将上游 test 源码随配方导出，source() 时复制进源码树，build() 中
    # 编译、test_package 中运行，以满足"上游测试用例须真实执行"要求。
    exports_sources = "test-src/**"

    def export_sources(self):
        export_conandata_patches(self)
        # test-src/** 已通过 exports_sources 属性导出（见类属性声明）

    def requirements(self):
        self.requires("pmix/5.0.11")
        self.requires("hwloc/2.14.0")
        self.requires("libevent/2.1.12")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 git 仓库 v3.0.13 的 test/ 目录注册了 19 个测试用例
        # （test/Makefile 的 TESTS），release tarball 不含 test/。
        # 将导出源复制回源码树，供 build() 编译、test_package 运行。
        if os.path.isdir(os.path.join(self.recipe_folder, "test-src")):
            shutil.copytree(
                os.path.join(self.recipe_folder, "test-src"),
                os.path.join(self.source_folder, "test-src"),
                dirs_exist_ok=True,
            )

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the compiler toolchain (contains libxml2.so.16).

        The OHOS clang driver spawns `lld` for linking, and lld's RUNPATH
        ($ORIGIN/../lib) points into the SDK llvm/lib. On CI workers the
        ambient LD_LIBRARY_PATH (e.g. ~/usr/local/lib) can shadow that dir
        with an incompatible libxml2.so.16, making lld fail with
        "Error loading shared library libxml2.so.16 ... symbol not found".
        Prepend the SDK llvm/lib so the correct libxml2 is found first.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        candidates = []
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        cc_real = os.path.realpath(cc)
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib"))
        try:
            resource_dir = subprocess.check_output(
                [cc, "-print-resource-dir"], stderr=subprocess.DEVNULL, text=True
            ).strip()
            candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except (OSError, subprocess.CalledProcessError):
            pass
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def generate(self):
        # PkgConfigDeps: PRRTE configure uses pkg-config to discover pmix
        # (PRTE_CHECK_PMIX -> OAC_CHECK_PACKAGE). The conan-published
        # pmix.pc embeds prefix=/ (relocatable), so without regenerated
        # .pc files pkg-config emits -I//include and configure cannot find
        # pmix.h. Regenerate correct .pc for pmix/hwloc/libevent.
        PkgConfigDeps(self).generate()
        # pmix headers are installed under include/pmix/ (e.g.
        # include/pmix/src/util/pmix_argv.h, included by PRRTE as
        # "src/util/pmix_argv.h"). The regenerated pmix.pc only emits
        # -I<prefix>/include, so teach it additional -I<prefix>/include/pmix
        # — otherwise PRTE_CHECK_PMIX cflags miss the subdir and later
        # compilation of src/util/hostfile/hostfile.c fails to find
        # "src/class/pmix_list.h".
        pmix_pc = os.path.join(self.generators_folder, "pmix.pc")
        if os.path.isfile(pmix_pc):
            with open(pmix_pc, "r") as f:
                content = f.read()
            if "${includedir}/pmix" not in content:
                content = content.replace(
                    'Cflags: -I"${includedir}"',
                    'Cflags: -I"${includedir}" -I"${includedir}/pmix"'
                )
                with open(pmix_pc, "w") as f:
                    f.write(content)
                self.output.info(
                    "Augmented regenerated pmix.pc Cflags with ${includedir}/pmix"
                )

        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            envvars = env.vars(self)
            envvars.save_script("conanbuild_llvm")
            self.output.info(
                "Prepending OHOS SDK linker runtime path: %s" % sdk_llvm_lib
            )

        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # pmix headers live under include/pmix/ (e.g. src/util/pmix_argv.h),
        # while pmix.pc only emits -I<prefix>/include — add the pmix subdir
        # so PRTE_CHECK_PMIX's AC_CHECK_HEADER([src/util/pmix_argv.h])
        # succeeds.
        pmix_inc_pmix = os.path.join(
            self.dependencies["pmix"].package_folder, "include", "pmix"
        )
        tc.extra_cflags.append("-I" + pmix_inc_pmix)
        # PRRTE configure performs its own dependency detection and does not
        # rely solely on CPPFLAGS/LDFLAGS. Notes on --with-* handling:
        #   - do NOT pass --with-pmix=/ --with-hwloc=DIR: PRTE_CHECK_PMIX /
        #     PRTE_SETUP_HWLOC resolve the dep .pc via pkg-config; passing an
        #     explicit DIR makes OAC_CHECK_PACKAGE read the *packaged* .pc
        #     whose embedded prefix=/ yields -I//include and configure cannot
        #     find the headers. PkgConfigDeps above already regenerates
        #     prefix-correct .pc files into the generators folder, which
        #     AutotoolsToolchain exposes via PKG_CONFIG_PATH.
        #   - --with-libevent=DIR is safe: PRTE_LIBEVENT_CONFIG probes the
        #     header/library at DIR directly, not via pkg-config.
        tc.configure_args.append(
            "--with-libevent=" + self.dependencies["libevent"].package_folder
        )
        tc.generate()

        # Prrte's event-internal.h does `#include <event.h>`. On OHOS the
        # ambient CPPFLAGS usually carries -I<HOME>/usr/local/include, and
        # that dir contains a *libev* compatibility event.h (same name as
        # libevent's). When searched first, the libev header neither defines
        # the event_get_signal macro (turned into an external symbol ->
        # undefined reference) nor matches libevent's struct event layout
        # (-> redefinition when both headers meet). Prepend the dependency's
        # include dir to CPPFLAGS so <event.h> resolves to libevent's own.
        # Must be applied AFTER tc.generate() so it wins the final env.
        le_include = os.path.join(
            self.dependencies["libevent"].package_folder, "include"
        )
        env_le = Environment()
        env_le.prepend("CPPFLAGS", "-I" + le_include)
        env_le.vars(self).save_script("conanbuild_z_libevent_include")
        self.output.info(
            "Prepending libevent include to CPPFLAGS: %s" % le_include
        )

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        self._build_upstream_tests()

    def _build_upstream_tests(self):
        """Compile the 19 upstream test/ cases (test/Makefile TESTS).

        The upstream git repo v3.0.13 registers 19 tests in test/Makefile
        (TESTS), but the release tarball does not carry test/. The sources
        were copied into the source tree by source(); compile them against
        the freshly built libprrte so CI can actually build every case.
        chkfs is registered upstream but has no .c source (upstream
        omission); double-get uses pnmi_set_string() which upstream declares
        as pmi_set_string() — fix that typo here for the compile.
        """
        tdir = os.path.join(self.source_folder, "test-src")
        if not os.path.isdir(tdir):
            return
        # libprrte 由 libtool 生成在 build 目录的 src/.libs/ 下
        lib = os.path.join(self.build_folder, "src", ".libs")
        includes = [
            tdir,
            os.path.join(self.source_folder, "examples"),
            os.path.join(self.source_folder, "include"),
            os.path.join(self.dependencies["pmix"].package_folder, "include"),
            os.path.join(self.dependencies["pmix"].package_folder, "include", "pmix"),
            os.path.join(self.dependencies["hwloc"].package_folder, "include"),
            os.path.join(self.dependencies["libevent"].package_folder, "include"),
        ]
        inc_args = " ".join("-I%s" % i for i in includes)
        lib_args = (
            "-L%s -lprrte "
            "-L%s -lpmix "
            "-L%s -lhwloc "
            "-L%s -levent_core -levent_pthreads -lpthread"
            % (
                lib,
                os.path.join(self.dependencies["pmix"].package_folder, "lib"),
                os.path.join(self.dependencies["hwloc"].package_folder, "lib"),
                os.path.join(self.dependencies["libevent"].package_folder, "lib"),
            )
        )
        cases = [
            "double-get", "get-nofence", "get-immediate",
            "abort", "simple_spawn", "hello", "connect",
            "loop_child", "loop_spawn", "reinit", "cmspawn",
            "qspawn", "iostress", "filegen", "clichk",
            "spawn_timeout", "attachtest/app", "attachtest/tool",
        ]
        built = []
        failed = []
        for case in cases:
            src = os.path.join(tdir, case + ".c")
            out = os.path.join(self.build_folder, "upstream-tests",
                               case.replace("/", "_"))
            if case.startswith("attachtest/"):
                src = os.path.join(tdir, case + ".c")
            if not os.path.isfile(src):
                failed.append("%s (no source)" % case)
                continue
            # upstream typo: pnmi_set_string -> pmi_set_string (double-get)
            with open(src, "r") as f:
                content = f.read()
            content = content.replace("pnmi_set_string", "pmi_set_string")
            fixed = os.path.join(self.build_folder, "upstream-tests",
                                 "src_" + case.replace("/", "_") + ".c")
            os.makedirs(os.path.dirname(fixed), exist_ok=True)
            with open(fixed, "w") as f:
                f.write(content)
            cmd = "clang %s %s %s -o %s" % (inc_args, fixed, lib_args, out)
            rc = self.run(cmd, env="conanbuild")
            if rc == 0:
                built.append(case)
            else:
                failed.append(case)
        self.output.info(
            "upstream tests: built=%s failed=%s" % (built or "none", failed or "none")
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove .la files (libtool absolute-path issue on relocated packages)
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["prrte"]
        self.cpp_info.set_property("pkg_config_name", "prrte")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
