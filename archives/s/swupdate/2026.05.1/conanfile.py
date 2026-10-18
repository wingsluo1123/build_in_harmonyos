#!/usr/bin/env python3
"""Conan recipe for SWUpdate 2026.05.1 on OpenHarmony / HarmonyOS PC (aarch64).

Upstream is a Kbuild (kernel-style make + Kconfig) project, not
configure/cmake, so the recipe drives the upstream Makefile directly:

  make ohos_defconfig      -> .config from configs/ohos_defconfig (patch 0004)
  <inject conan flags>     -> CONFIG_EXTRA_CFLAGS / CONFIG_EXTRA_LDLIBS
  make -jN                 -> swupdate + tools/* + libswupdate.so

Dependency detection is *not* automatic upstream: Makefile.deps only
supplies defaults (`export HAVE_XXX = y`) which the Kconfig `option env=`
symbols read, so the recipe must declare HAVE_* explicitly (n for every
library OHOS does not ship, see _HAVE_ENV below).

Upstream unit tests (test/ cmocka binaries) are built and executed from
build(); acceptance tests need a writable /tmp and are reported separately.

Two OHOS specific post-link steps are needed:
  * lld's build time `.codesign` self signature is invalid for this link
    (embedded "file size" field 0x53740 != real size) -> execve EPERM
    ("Operation not permitted"); every produced ELF is re-signed with
    llvm-objcopy --remove-section .codesign + binary-sign-tool -selfSign.
  * the test binaries are relinked on every `make test` invocation
    (test/Makefile's %.lnk stamp is never created), so the re-signing is
    hooked into EXECUTE_TEST, immediately before each binary runs.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Availability of the optional libraries upstream probes.  Makefile.deps
# defaults every HAVE_* to "y" and Kconfig reads it through `option env=`;
# that is the only thing gating the corresponding faces, so the recipe has
# to declare each one (libraries absent from OHOS are "n").
_HAVE_ENV = {
    "HAVE_LIBUBOOTENV": "n",   # no libubootenv anywhere on OHOS
    "HAVE_LIBMTD": "y",        # libmtd/2.3.1-3 (OHOS package repo)
    "HAVE_LIBUBI": "y",        # libubi/2.3.1-3 (OHOS package repo)
    "HAVE_LIBEBGENV": "n",
    "HAVE_LIBTEGRABOOT_TOOLS": "n",
    "HAVE_LIBZEROMQ": "n",
    "HAVE_GPGME": "n",
    "HAVE_LIBRSYNC": "n",
    "HAVE_URIPARSER": "n",
    "HAVE_ZCK": "n",
    "HAVE_MBEDTLS": "n",
    "HAVE_WOLFSSL": "n",
    "HAVE_LIBWEBSOCKETS": "n",
    "HAVE_LIBBTRFS": "n",
}

# pkg-config modules that the upstream Makefile resolves itself
# (Makefile.flags: LUABUILD / P11BUILD). libconfig/json-c/... are linked by
# bare -l name and are covered by CONFIG_EXTRA_LDLIBS.
_PC_MODULES = "openssl libarchive libconfig json-c libcurl zlib lua-5.4 cmocka"


class SwupdateConan(ConanFile):
    name = "swupdate"
    version = "2026.05.1"
    description = ("SWUpdate - software update agent for embedded Linux "
                   "(local/OTA update, signed images, hawkBit client)")
    license = "GPL-2.0-only"
    homepage = "https://github.com/sbabic/swupdate"
    url = "https://github.com/sbabic/swupdate"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    # Kbuild is an in-tree build (swupdate builds next to its sources) and
    # apply_conandata_patches() patches the source tree, so source and build
    # folder are the same directory.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("libconfig/1.8.2")
        self.requires("json-c/0.18")
        self.requires("libcurl/8.5.0")
        self.requires("libarchive/3.8.7")
        self.requires("lua/5.4.8")
        self.requires("zlib/1.3.1.1")
        # MTD / UBI faces (CONFIG_MTD, CONFIG_CFI, CONFIG_UBIVOL)
        self.requires("libmtd/2.3.1-3")
        self.requires("libubi/2.3.1-3")
        # cmocka is only needed to build/run the upstream unit tests.
        self.test_requires("cmocka/2.0.2")

    def validate(self):
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                f"swupdate supports OHOS and Linux, got {self.settings.os}")

    def source(self):
        # tar_format is archive metadata only (ARCHIVE-SPEC), get() rejects it.
        source_data = dict(self.conan_data["sources"])
        source_data.pop("tar_format", None)
        get(self, **source_data, strip_root=True)

    # ---------------------------------------------------------------- helpers
    def _compilers(self):
        return self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict)

    def _cc(self):
        return self._compilers().get("c") or "clang"

    def _cxx(self):
        return self._compilers().get("cpp") or self._cc()

    def _static_shadow_dir(self, libdirs):
        """Directory holding only the static archives of static dependencies.

        Several OHOS packages are declared static (shared=False) yet install
        a shared object next to the static archive; the linker then prefers
        the .so and the binary gains a DT_NEEDED entry whose directory Conan
        never exports into the runtime environment (for a static package
        require.run is False).  Putting a directory that contains only the
        .a files first on the library search path makes the linker honour
        the declared static build (verified: the resulting binary has no
        DT_NEEDED for libarchive any more).
        """
        shadow = os.path.join(self.generators_folder, "conan-static-libs")
        if os.path.isdir(shadow):
            shutil.rmtree(shadow)
        os.makedirs(shadow)
        for require, dep in self.dependencies.host.items():
            # VirtualRunEnv only exports the libdirs of requires with
            # run=True; those are exactly the ones whose .so may be used.
            if require.run:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs or []:
                if not os.path.isdir(libdir):
                    continue
                for name in os.listdir(libdir):
                    if name.startswith("lib") and name.endswith(".a"):
                        dst = os.path.join(shadow, name)
                        if not os.path.exists(dst):
                            shutil.copy2(os.path.join(libdir, name), dst)
        return shadow

    def _dep_flags(self):
        """include dirs / lib dirs / lib names of the whole host dependency graph."""
        incs, libdirs, libs = [], [], []
        deps = list(self.dependencies.host.values())
        # test_requires (cmocka) live in their own bucket
        deps += list(self.dependencies.test.values())
        for dep in deps:
            cpp = dep.cpp_info.aggregated_components()
            incs += list(cpp.includedirs or [])
            libdirs += list(cpp.libdirs or [])
            libs += list(cpp.libs or [])
            libs += list(cpp.system_libs or [])
        def _dedup(seq):
            seen, out = set(), []
            for item in seq:
                if item and item not in seen:
                    seen.add(item)
                    out.append(item)
            return out
        return _dedup(incs), _dedup(libdirs), _dedup(libs)

    def _sign_script(self):
        """Write the OHOS ELF re-signing helper and return its path."""
        path = os.path.join(self.build_folder, "ohos-sign-elf.sh")
        save(self, path, r'''#!/bin/sh
# Re-create a valid OHOS .codesign for one ELF executable.
# lld's link-time self signature is not usable for this project's link
# (its embedded size field does not match the file), and any post-link
# modification invalidates it anyway.  binary-sign-tool refuses to
# overwrite an existing section, so drop it first.
set -e
f="$1"
[ -f "$f" ] || { echo "sign: no such file: $f" >&2; exit 1; }
magic=$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')
[ "$magic" = "7f454c46" ] || exit 0
/data/service/hnp/bin/llvm-objcopy --remove-section .codesign "$f" 2>/dev/null || true
/data/service/hnp/bin/binary-sign-tool sign -selfSign 1 -inFile "$f" \
    -outFile "$f.signed" -signAlg SHA256withECDSA >/dev/null
mv -f "$f.signed" "$f"
chmod 755 "$f"
''')
        os.chmod(path, 0o755)
        return path

    def _sign_elfs(self, paths):
        script = self._sign_script()
        for path in paths:
            self.run(f'sh "{script}" "{path}"')

    def _built_elfs(self, root):
        """ELF executables / shared objects produced by the main build."""
        out = [os.path.join(root, "swupdate")]
        for name in os.listdir(os.path.join(root, "tools")):
            if name.startswith("swupdate-") and os.path.isfile(
                    os.path.join(root, "tools", name)):
                out.append(os.path.join(root, "tools", name))
        for name in os.listdir(root):
            if ".so" in name and (name.endswith(".so") or ".so." in name):
                out.append(os.path.join(root, name))
        return [p for p in out if os.path.isfile(p) and not p.endswith(".map")]

    # ---------------------------------------------------------------- generate
    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        incs, libdirs, libs = self._dep_flags()
        shadow = self._static_shadow_dir(libdirs)
        libdirs = [shadow] + libdirs
        cc = self._cc()
        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.define("CC", cc)
        env.define("CXX", self._cxx())
        # Kbuild sets LD/CC to "$(CROSS_COMPILE)cc" by default and only keeps
        # values that are not the builtin default, so LD must be given too.
        env.define("LD", cc)
        env.define("HOSTCC", cc)
        # OHOS: strip would invalidate .codesign, and the binary is installed
        # as-is anyway -> skip the strip step of the upstream Makefile.
        env.define("SKIP_STRIP", "y")
        env.define("LDFLAGS", " ".join(f"-L{d}" for d in libdirs))
        # Test binaries are started with LD_LIBRARY_PATH=$(objtree) upstream;
        # patch 0003 makes that append instead of replace, so the conan
        # dependency directories must be present here.
        env.define("LD_LIBRARY_PATH", ":".join(libdirs))
        for key, value in _HAVE_ENV.items():
            env.define(key, value)
        env.vars(self).save_script("ohos-swupdate-env")

    # ---------------------------------------------------------------- build
    def _inject_config(self, incs, libs):
        config = os.path.join(self.source_folder, ".config")
        with open(config, "r", encoding="utf-8") as handle:
            text = handle.read()

        def setkv(text, key, value):
            line = f'{key}="{value}"'
            out, replaced = [], False
            for row in text.splitlines():
                if row.startswith(key + "="):
                    out.append(line)
                    replaced = True
                else:
                    out.append(row)
            if not replaced:
                out.append(line)
            return "\n".join(out) + "\n"

        text = setkv(text, "CONFIG_EXTRA_CFLAGS",
                     "-Os " + " ".join(f"-I{d}" for d in incs))
        text = setkv(text, "CONFIG_EXTRA_LDLIBS", " ".join(libs))
        text = setkv(text, "CONFIG_LUAPKG", "lua-5.4")
        with open(config, "w", encoding="utf-8") as handle:
            handle.write(text)

    def build(self):
        # Kbuild is an in-tree build: everything happens in the source tree
        # (that is also where apply_conandata_patches() applies the patches).
        root = self.source_folder
        apply_conandata_patches(self)
        incs, _libdirs, libs = self._dep_flags()
        env = ["conanbuild", "ohos-swupdate-env"]
        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int)
        jobs = max(1, min(jobs, 4))
        make = f"make HOSTCC={self._cc()}"

        self.run(f"{make} ohos_defconfig", env=env, cwd=root)
        self._inject_config(incs, libs)
        self.run(f"{make} -j{jobs}", env=env, cwd=root)
        # The produced ELF objects carry an unusable link-time .codesign
        # (see notes.md): without re-signing, execve() fails with EPERM and
        # the OHOS loader refuses to dlopen libswupdate.so.0.1, which the
        # unit test binaries link against.  Sign them before running tests.
        self._sign_elfs(self._built_elfs(root))

        # Upstream unit tests.  test/Makefile never creates the %.lnk stamps,
        # so `make test` relinks every test binary on each invocation and the
        # re-signing has to happen right before each binary is executed.
        # EXECUTE_TEST is overridden with the upstream command plus one
        # signing step; the upstream runner itself is untouched.
        sign = self._sign_script()
        execute = (
            'echo "RUN $(subst $(obj)/,,$(var))"; '
            f'sh "{sign}" "$(var)"; '
            'LD_LIBRARY_PATH=$(objtree)$${LD_LIBRARY_PATH:+:$$LD_LIBRARY_PATH} '
            'CMOCKA_MESSAGE_OUTPUT=TAP '
            'SOFTHSM2_CONF=$(DATADIR)/token/softhsm.conf $(var)'
        )
        self.run(f"{make} test EXECUTE_TEST='{execute}'", env=env, cwd=root)

        # Upstream acceptance suite (scripts/acceptance-tests/CheckImage.mk:
        # six `swupdate -c` expectations for this configuration).  Two
        # OHOS specifics:
        #  * SWU_CLEAN is `rm -f /tmp/sw-description`; /tmp is read-only on
        #    OHOS and nothing ever creates that file (check-only runs), so
        #    the cleanup is neutralised - otherwise the target aborts.
        #  * the acceptance target depends on `swupdate`, which make may
        #    relink (invalidating .codesign), so the binary is re-signed
        #    after the first invocation and the suite runs again against the
        #    fresh, signed binary.  All but one acceptance expectation are
        #    "must fail", so a non-runnable binary would pass them for the
        #    wrong reason - hence the explicit `--version` guard.
        accept = f"{make} acceptance-tests SWU_CLEAN=true"
        self.run(accept, env=env, cwd=root)
        self._sign_elfs([os.path.join(root, "swupdate")])
        self.run("./swupdate --version", env=env, cwd=root)
        self.run(accept, env=env, cwd=root)

    # ---------------------------------------------------------------- package
    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "swupdate", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        for tool in ("swupdate-client", "swupdate-progress", "swupdate-ipc"):
            copy(self, tool, src=os.path.join(self.source_folder, "tools"),
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libswupdate.so*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "lua_swupdate.so*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        for header in ("network_ipc.h", "swupdate_status.h", "progress_ipc.h"):
            copy(self, header, src=os.path.join(self.source_folder, "include"),
                 dst=os.path.join(self.package_folder, "include"))

        binaries = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if name.endswith(".so") or ".so." in name:
                    binaries.append(path)
        binaries.append(os.path.join(self.package_folder, "bin", "swupdate"))
        for tool in ("swupdate-client", "swupdate-progress", "swupdate-ipc"):
            binaries.append(os.path.join(self.package_folder, "bin", tool))
        self._sign_elfs(sorted(set(os.path.normpath(p) for p in binaries)))

        # libswupdate.so is installed as a plain copy of the versioned file
        # (OHOS forbids symlinks).
        versioned = os.path.join(self.package_folder, "lib", "libswupdate.so.0.1")
        plain = os.path.join(self.package_folder, "lib", "libswupdate.so")
        if os.path.isfile(versioned) and not os.path.isfile(plain):
            shutil.copy2(versioned, plain)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["swupdate"]
