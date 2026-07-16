#!/usr/bin/env python3
"""Conan recipe — speex 1.2.1 (autotools).
"""
import os
import shutil
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpeexConan(ConanFile):
    name = "speex"
    version = "1.2.1"
    description = "Audio codec designed for voice encoding over IP networks"
    license = "BSD-3-Clause"
    homepage = "https://speex.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        # ── Fix 0: Repair new-file patch format before applying ──
        # refresh-patch generates `--- a/filename` for new files, but
        # Conan's patch_ng requires `--- /dev/null`. Fix in-place.
        export_sources = self.export_sources_folder
        if export_sources:
            for p in self.conan_data.get("patches", []):
                patch_file = p.get("patch_file", "")
                patch_path = os.path.join(export_sources, patch_file)
                if not os.path.isfile(patch_path):
                    continue
                with open(patch_path, "r") as f:
                    content = f.read()
                if "--- a/" in content and "@@ -0,0" in content:
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if line.startswith("--- a/"):
                            lines[i] = "--- /dev/null"
                    with open(patch_path, "w") as f:
                        f.write("\n".join(lines))

        apply_conandata_patches(self)

        # ── Fix 1: Patch ALL generated env scripts for local dev ──
        # The CI profile (ohos-aarch64) sets CONFIG_SHELL/SHELL/CC/CXX to
        # /data/service/hnp/bin/* which only exist on CI release workers.
        # Conan generates multiple .sh scripts (conanautotoolstoolchain.sh,
        # conanbuildenv-*.sh, etc.) that are sourced in sequence by
        # conanbuild.sh. We must patch every .sh in the generators folder
        # because the [buildenv] vars in conanbuildenv-*.sh are sourced
        # AFTER and override values set in earlier scripts.
        if not os.path.exists("/data/service/hnp/bin/bash"):
            bash_path = shutil.which("bash") or "bash"
            clang_path = shutil.which("clang") or "clang"
            clangxx_path = shutil.which("clang++") or "clang++"
            gen_folder = self.generators_folder
            if gen_folder and os.path.isdir(gen_folder):
                for name in os.listdir(gen_folder):
                    if not name.endswith(".sh"):
                        continue
                    script_path = os.path.join(gen_folder, name)
                    if not os.path.isfile(script_path):
                        continue
                    content = load(self, script_path)
                    if "/data/service/hnp/bin/" in content:
                        content = content.replace(
                            "/data/service/hnp/bin/bash", bash_path)
                        content = content.replace(
                            "/data/service/hnp/bin/clang++", clangxx_path)
                        content = content.replace(
                            "/data/service/hnp/bin/clang", clang_path)
                        save(self, script_path, content)

        # ── Fix 2: Patch configure to relax umask for HMFS ──
        # autoconf's config.status uses `umask 077` to create a secure temp
        # directory. On HMDFS (HarmonyOS), directories inherit a setgid bit
        # from their parent. With umask 077, the group loses execute (x)
        # permission, making the setgid bit uppercase 'S' (setgid without
        # execute). HMDFS then denies file creation in that directory even
        # for the owner. Changing to umask 022 preserves group execute,
        # keeping the setgid bit lowercase 's' and allowing writes.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            content = load(self, configure_path)
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                save(self, configure_path, content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["speex"]
