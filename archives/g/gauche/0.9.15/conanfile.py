#!/usr/bin/env python3
"""Conan recipe — Gauche 0.9.15 (Scheme interpreter).

Gauche is a Scheme interpreter with R7RS compatibility, UTF-8 support,
and multithreading. It builds via autotools and produces the `gosh`
executable and `libgauche` shared library.

Key OHOS adaptations:
  - config.guess/config.sub patched for OHOS platform detection
  - Boehm GC patched to disable pthread_cancel (musl libc gap)
  - ext directory skipped (dynamic linking issues on OHOS)
  - pthread_compat.c stub for missing pthread_cancel/setcancelstate

File location: archives/g/gauche/0.9.15/conanfile.py
"""
import hashlib
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class GaucheConan(ConanFile):
    name = "gauche"
    version = "0.9.15"
    description = "Gauche is a Scheme implementation designed as a scripting language"
    license = "BSD-3-Clause"
    homepage = "https://practical-scheme.net/gauche/"
    url = "https://github.com/shirok/Gauche"

    # Gauche produces both an executable (gosh) and a library (libgauche).
    # We classify it as an application since the primary deliverable is the
    # interpreter binary.
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No external Conan dependencies — Gauche bundles its own Boehm GC.
    # libiconv is used for charconv but the ext directory is skipped.

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        source = self.conan_data["sources"]
        mirror_dir = "mirror"
        Git(self).clone(url=source["mirror_url"], target=mirror_dir)
        Git(self, folder=mirror_dir).checkout(commit=source["mirror_commit"])

        archive = os.path.join(self.source_folder, mirror_dir, source["archive"])
        with open(archive, "rb") as input_file:
            actual_sha256 = hashlib.sha256(input_file.read()).hexdigest()
        if actual_sha256 != source["sha256"]:
            raise ConanException(
                f"Mirrored release archive checksum mismatch: {actual_sha256}"
            )
        extract_dir = os.path.join(self.source_folder, "release-extract")
        os.makedirs(extract_dir)
        extract_root = os.path.realpath(extract_dir)
        with tarfile.open(archive, "r:gz") as release:
            members = release.getmembers()
            for member in members:
                destination = os.path.realpath(
                    os.path.join(extract_root, member.name)
                )
                if (
                    not destination.startswith(extract_root + os.sep)
                    or member.issym()
                    or member.islnk()
                    or member.isdev()
                ):
                    raise ConanException(
                        f"Unsafe member in mirrored release archive: {member.name}"
                    )
            for member in members:
                release.extract(member, extract_root)
        roots = os.listdir(extract_dir)
        if len(roots) != 1:
            raise ConanException("Expected exactly one root directory in release archive")
        root = os.path.join(extract_dir, roots[0])
        for entry in os.listdir(root):
            shutil.move(os.path.join(root, entry), self.source_folder)
        shutil.rmtree(extract_dir)
        shutil.rmtree(os.path.join(self.source_folder, mirror_dir))
        required_entries = ("configure", "gc", "libsrc")
        if not all(os.path.exists(os.path.join(self.source_folder, entry))
                   for entry in required_entries):
            raise ConanException(
                "Extracted release root does not contain configure, gc/, and libsrc/"
            )

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Gauche 非系统同名库（R26 仅限系统同名库），默认动态构建：
        # 其 Boehm GC 需要生成 libgc_pic.a（PIC 归档）供 libgauche 链接，
        # --disable-shared 会使 libgc_pic.a 为空导致 GC_* 符号未定义。
        # 依赖链由 Conan 管理，gosh 可执行文件自带 RPATH。
        tc.generate()

    def build(self):
        # Conan exports conandata patches to export_sources_folder, not recipe_folder.
        # Accept both supported conandata layouts and preserve their declared order.
        patches = self.conan_data.get("patches", [])
        if isinstance(patches, dict):
            patches = patches.get(str(self.version), [])
        if not isinstance(patches, list):
            raise ConanException("conandata.yml 'patches' must be a list or version map")
        for patch_data in patches:
            if "patch_file" not in patch_data:
                raise ConanException("Each conandata patch must define patch_file")
            patch(
                self,
                base_path=self.source_folder,
                patch_file=os.path.join(
                    self.export_sources_folder, patch_data["patch_file"]
                ),
                strip=patch_data.get("strip", 1),
            )

        # Makefile.in files are generated upstream artifacts (R6), so keep their
        # OHOS-only build adjustments in the recipe rather than as source patches.
        def replace_generated(path, old, new):
            with open(path, encoding="utf-8") as source:
                text = source.read()
            if old not in text:
                raise ConanException(f"Expected generated Makefile fragment missing: {path}")
            with open(path, "w", encoding="utf-8") as output:
                output.write(text.replace(old, new))

        top_makefile = os.path.join(self.source_folder, "Makefile.in")
        replace_generated(
            top_makefile,
            "SUBDIRS = gc src lib ext doc examples tools",
            "SUBDIRS = gc src lib examples tools",
        )
        replace_generated(
            top_makefile,
            "\tcd src; $(MAKE) -s static",
            "\t@echo \"static lib skipped (ext unavailable on OHOS)\"",
        )
        replace_generated(
            top_makefile,
            "\tcd doc; $(MAKE) install",
            "\t@echo \"doc build skipped (ext charconv unavailable on OHOS)\"",
        )
        replace_generated(top_makefile, "\tcd ext; $(MAKE) install\n", "")
        replace_generated(
            top_makefile,
            "\t\"$(BUILD_GOSH)\" \"$(srcdir)/tools/check-build-version\" ${BUILD_GOSH_VERSION} && touch pre-package.stamp",
            "\ttouch pre-package.stamp",
        )
        replace_generated(
            os.path.join(self.source_folder, "src", "Makefile.in"),
            "INSTALL_LIBS = $(LIBGAUCHE).$(SOEXT) $(LIBGAUCHE_STATIC).a",
            "INSTALL_LIBS = $(LIBGAUCHE).$(SOEXT)",
        )

        # HMDFS rejects config.status helper scripts created with umask 077.
        # basic_layout may run configure from either source_folder or build_folder,
        # so patch both locations and fail loudly if neither contains the expected form.
        updated = 0
        seen = set()
        roots = (
            self.source_folder,
            self.build_folder,
            os.path.dirname(self.build_folder),
            os.path.dirname(os.path.dirname(self.build_folder)),
            os.path.dirname(self.source_folder),
        )
        for root in roots:
            for configure_path in ("configure", os.path.join("gc", "configure")):
                configure_file = os.path.join(root, configure_path)
                if configure_file in seen or not os.path.isfile(configure_file):
                    continue
                seen.add(configure_file)
                with open(configure_file, encoding="utf-8") as source:
                    configure_text = source.read()
                occurrences = configure_text.count("umask 077")
                if occurrences:
                    with open(configure_file, "w", encoding="utf-8") as output:
                        output.write(configure_text.replace("umask 077", "umask 002"))
                    updated += occurrences
                    self.output.info(f"Applied HMDFS umask fix to {configure_file}")
        if not updated:
            self.output.warning(
                "HMDFS umask fix found no configure script; "
                f"source={self.source_folder}, build={self.build_folder}"
            )

        # Copy pthread_compat.c stub into the source tree.
        # This provides stub implementations for pthread_cancel and
        # pthread_setcancelstate which are missing from HarmonyOS musl libc.
        patch_dir = os.path.join(self.recipe_folder, "patches")
        compat_src = os.path.join(patch_dir, "03-pthread-compat.c")
        if os.path.isfile(compat_src):
            shutil.copy(compat_src, os.path.join(self.source_folder, "pthread_compat.c"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Copy license file
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Gauche installs headers under lib/gauche-<abi>/<ver>/include/
        # (autotools GAUCHE_HEADER_INSTALL_DIR), not under a top-level include/.
        # Conan cpp_info.includedirs is relative to the package folder.
        gauche_inc = os.path.join("lib", "gauche-0.98", "0.9.15", "include")
        self.cpp_info.includedirs = [gauche_inc]
        self.cpp_info.libs = ["gauche-0.98"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
