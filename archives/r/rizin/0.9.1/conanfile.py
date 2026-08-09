#!/usr/bin/env python3
"""Conan recipe — Rizin v0.9.1 (Meson build system).

Rizin is a fork of radare2, a reverse engineering framework with command-line
tooling (rizin, rz-asm, rz-bin, rz-diff, rz-find, rz-gg, rz-hash, rz-run,
rz-sign, rz-test). Adapted to OpenHarmony PC (aarch64).

Adaptation notes (see notes.md for full details):
  1. librz/util/thread.c: guard pthread_setcancelstate/type with
     HAVE_PTHREAD_SETCANCELSTATE feature probe (R8-compliant; see patch 0003/0004;
     HarmonyOS bionic libc does not implement POSIX thread cancel API).
  2. librz/debug/meson.build: extend linux/android branch with 'harmonyos' so
     linux_debug.c/linux_coredump.c are compiled in.
     HarmonyOS native build reports host_machine.system()=='harmonyos'.
  3. OpenSSL include path injected via CPPFLAGS (rz_util.h includes
     <openssl/bn.h>, consumed by sibling librz/* targets).
  4. v0.9.1 official release tarball (rizin-src-v0.9.1.tar.xz) already vendors
     subproject sources (capstone-next, pcre2-10.47, libdemangle, zydis, ...),
     so no git pre-clone is needed — meson resolves them from subprojects/ dirs.

Deps strategy ("only enable published" per W0/R36):
  use_sys_pcre2/libmagic/zlib/lz4/libzstd/openssl enabled (ohpcd published);
  use_sys_capstone/libzip/xxhash/libmspack/tree_sitter/softfloat/liblzma
  disabled (use Rizin vendored Meson subprojects).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
import os


class RizinConan(ConanFile):
    name = "rizin"
    version = "0.9.1"
    description = "Rizin is a fork of radare2, a reverse engineering framework with command-line tooling"
    license = "LGPL-3.0-only"
    homepage = "https://rizin.re"
    url = "https://github.com/rizinorg/rizin/releases/tag/v0.9.1"

    package_type = "application"
    build_system = "meson"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0/R36: only require ohpcd-published recipes.
        self.requires("pcre2/10.45.1")
        self.requires("file/5.48")        # provides libmagic.a / magic
        self.requires("zlib/1.3.1.1")     # PIC-enabled
        self.requires("lz4/1.10.0")
        self.requires("zstd/1.5.7")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # v0.9.1 release tarball vendors subproject sources under subprojects/
        # (capstone-next, pcre2-10.47, libdemangle, zydis, softfloat, ...).
        # sigdb.wrap is a git-form wrap but is only installed when present;
        # meson does not resolve it as a build dependency, so no pre-clone.

    def generate(self):
        tc = MesonToolchain(self)
        # R26: non-system-name libs default dynamic; Conan manages dep chain.
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Only enable use_sys_* for published deps; vendored for the rest.
        tc.project_options["use_sys_pcre2"] = "enabled"
        tc.project_options["use_sys_magic"] = "enabled"
        tc.project_options["use_sys_zlib"] = "enabled"
        tc.project_options["use_sys_lz4"] = "enabled"
        tc.project_options["use_sys_libzstd"] = "enabled"
        tc.project_options["use_sys_openssl"] = "enabled"
        tc.project_options["use_sys_capstone"] = "disabled"
        tc.project_options["use_sys_libzip"] = "disabled"
        tc.project_options["use_sys_lzma"] = "disabled"
        tc.project_options["use_sys_xxhash"] = "disabled"
        tc.project_options["use_sys_libmspack"] = "disabled"
        tc.project_options["use_sys_tree_sitter"] = "disabled"
        tc.project_options["use_sys_softfloat"] = "disabled"
        tc.generate()
        # OHOS conan lacks MesonDeps; use PkgConfigDeps so meson's dependency('libpcre2-8')
        # etc. resolve via pkg-config. PkgConfigDeps writes .pc into generators_folder.
        PkgConfigDeps(self).generate()
        # meson.build looks up deps by names Conan doesn't emit: create alias .pc files.
        import re
        pc_dir = self.generators_folder
        if pc_dir and os.path.isdir(pc_dir):
            aliases = {
                "libpcre2-8": "pcre2",    # meson: dependency('libpcre2-8')
                "libmagic":   "file",     # meson: dependency('libmagic')
                "liblz4":     "lz4",      # meson: dependency('liblz4')
            }
            for alias, real in aliases.items():
                real_pc = os.path.join(pc_dir, real + ".pc")
                alias_pc = os.path.join(pc_dir, alias + ".pc")
                if os.path.isfile(real_pc) and not os.path.isfile(alias_pc):
                    with open(real_pc) as fr:
                        body = fr.read()
                    body = re.sub(r"^Name:.*$", "Name: " + alias, body, count=1, flags=re.MULTILINE)
                    with open(alias_pc, "w") as fw:
                        fw.write(body)
        # Locate OpenSSL package_folder via self.dependencies (Conan 2.x standard API) so
        # we can inject -I<inc> into [built-in options] c_args/cpp_args in build().
        openssl_inc = None
        deps = getattr(self, "dependencies", None)
        dep_items = list(deps.values()) if deps else []
        for dep in dep_items:
            if dep.ref.name == "openssl":
                pf = dep.package_folder
                openssl_inc = os.path.join(pf, "include") if pf else None
        self._openssl_inc = openssl_inc  # stash for build() INI patching

    def build(self):
        apply_conandata_patches(self)
        # Inject wrap_mode into native.ini [built-in options] section.
        # wrap_mode is a meson built-in (not project) option; use 'default' so meson
        # auto-falls back to vendored subprojects (has_buildfile() returns early).
        native_ini = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_ini):
            with open(native_ini) as f:
                content = f.read()
            import re
            content = re.sub(r"^wrap_mode\s*=.*\n", "", content, flags=re.MULTILINE)
            marker = "[built-in options]\n"
            inject = "wrap_mode = 'default'\n"
            if "wrap_mode = 'default'" not in content:
                if marker in content:
                    content = content.replace(marker, marker + inject, 1)
                else:
                    content = marker + inject + "\n" + content
            oi = self._openssl_inc
            if oi and os.path.isdir(oi):
                iarg = "['-I" + oi + "']"
                content = re.sub(r"^(c_args\s*=).*?(\s*\+ preprocessor_definitions)?$", r"\1 " + iarg + r"\2", content, count=1, flags=re.MULTILINE)
                content = re.sub(r"^(cpp_args\s*=).*?(\s*\+ preprocessor_definitions)?$", r"\1 " + iarg + r"\2", content, count=1, flags=re.MULTILINE)
            with open(native_ini, "w") as f:
                f.write(content)
        # Conan's MesonToolchain omits ar/ranlib/strip/ld from [binaries]; register an
        # EXTRA machine file via Conan's conf mechanism (extra_machine_files) so meson
        # finds the absolute HNP tool paths.
        extra_ini_path = os.path.join(self.generators_folder, "ohos_extra_binaries.ini")
        hnp_bin = os.environ.get("HNP_BIN_DIR", "/data/service/hnp/bin")
        extra_ini_content = (
            "[binaries]\n"
            "ar = '" + hnp_bin + "/llvm-ar'\n"
            "ranlib = '" + hnp_bin + "/llvm-ranlib'\n"
            "strip = '" + hnp_bin + "/llvm-strip'\n"
            "ld = '" + hnp_bin + "/ld.lld'\n"
        )
        os.makedirs(os.path.dirname(extra_ini_path), exist_ok=True)
        with open(extra_ini_path, "w") as f:
            f.write(extra_ini_content)
        conf_key = "tools.meson.mesontoolchain:extra_machine_files"
        existing = self.conf.get(conf_key, default=[], check_type=list)
        if extra_ini_path not in existing:
            existing.append(extra_ini_path)
        self.conf.define(conf_key, existing)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = [
            "rz_core", "rz_main", "rz_config", "rz_cons", "rz_util",
            "rz_io", "rz_socket", "rz_bin", "rz_lang", "rz_asm", "rz_analysis",
            "rz_arch", "rz_bp", "rz_crypto", "rz_debug", "rz_egg", "rz_flag",
            "rz_hash", "rz_magic", "rz_reg", "rz_sign", "rz_syscall", "rz_type",
        ]
        self.cpp_info.includedirs = ["include/librz"]  # rz_core.h etc. live under p/include/librz/
        self.cpp_info.bindirs = ["bin"]
        # Command-line tools (R38 declared in archives/r/rizin/commands.json)
        self.cpp_info.exes = [
            "rizin", "rz-asm", "rz-ax", "rz-bin", "rz-diff", "rz-find",
            "rz-gg", "rz-hash", "rz-run", "rz-sign", "rz-test",
        ]
