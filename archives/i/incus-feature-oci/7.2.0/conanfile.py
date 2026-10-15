#!/usr/bin/env python3
"""Conan recipe for incus-feature-oci 7.2.0 — OCI image support meta-package.

``incus-feature-oci`` is the ``oci()`` sub-package of the Alpine source package
``community/incus-feature`` (APKBUILD)::

    oci() {
        pkgdesc="Install packages required to run OCI images under Incus"
        depends="$depends skopeo"
        install -d "$subpkgdir"
    }

It is a **noarch meta-package**: it installs no binary of its own and only
declares the runtime contract needed to run OCI container images under Incus.
Upstream (github.com/lxc/incus, tag v7.2.0) has no standalone ``incus-oci``
binary; OCI image handling lives inside the ``incus`` client, which shells out
to the external ``skopeo`` command at runtime (``client/oci_images.go``::

    _, err := exec.LookPath("skopeo")
    ...
    errors.New("OCI container handling requires \\"skopeo\\" be present on the system")

HarmonyOS (OHOS) adaptation — mirrors the ``archives/a/abuild-rootbld``
noarch meta-package precedent, all at recipe level, no upstream source patch:

1. ``requirements()`` declares the published dependency that provides the
   consumer of OCI images: ``incus-feature-client/7.2.0`` (the ``/usr/bin/incus``
   CLI).  ``skopeo`` is the remaining runtime requirement; it is **not yet**
   published to the ohpcd artifact repository (verified 2026-10-15 via a
   recipe listing on the ohpcd remote → 0 recipes) and OHOS builds of skopeo
   are a separate adaptation task — therefore it is NOT declared as a Conan
   requirement (PF4 forbids referencing unpublished recipes).  Instead the
   ``bin/incus-oci`` wrapper enforces the skopeo contract at runtime with the
   exact upstream error message, exactly like upstream ``exec.LookPath``.
2. ``bin/incus-oci`` thin wrapper: ``--version`` reports the meta-package;
   any other arguments re-check skopeo presence (upstream contract) and then
   ``exec incus "$@"`` so the entry point is discoverable on PATH.
3. No compilation (noarch; the Go source tarball is fetched only for the
   license file and contract documentation).

Upstream tests: the oci() sub-package has no test target of its own (it ships
no files); the Go test suite of the incus source (same tarball) is exercised
by the sibling ``incus-feature-client/7.2.0`` recipe (12 packages / 248 cases,
all passed).  test_package here verifies the meta-package contract:
wrapper execution, exact upstream skopeo error message, and real delegation
to the ``incus`` binary from the incus-feature-client dependency.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IncusFeatureOciConan(ConanFile):
    name = "incus-feature-oci"
    version = "7.2.0"
    description = ("OCI image support contract for Incus (Alpine incus-feature "
                   "noarch meta-package) adapted for HarmonyOS PC")
    license = "Apache-2.0"
    homepage = "https://github.com/lxc/incus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("incus", "oci", "containers", "meta-package", "go")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The incus CLI (provides the OCI image consumer, /usr/bin/incus).
        # Published to the ohpcd artifact repo (recipe + binary verified
        # 2026-10-15 via a full download from the ohpcd remote).
        self.requires("incus-feature-client/7.2.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"incus-feature-oci supports Linux and OHOS only, got {self.settings.os}")

    def build(self):
        # Noarch meta-package: nothing to compile. The OCI image handling
        # itself lives in the incus client (incus-feature-client dependency);
        # this package installs the PATH wrapper below and ships the license.
        apply_conandata_patches(self)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        wrapper = os.path.join(bindir, "incus-oci")
        with open(wrapper, "w", encoding="utf-8") as fh:
            fh.write(
                '#!/bin/sh\n'
                '# incus-oci — Alpine incus-feature-oci meta-package wrapper.\n'
                '# Upstream oci() sub-package installs no binary; it declares the\n'
                '# runtime contract for running OCI images under Incus: the incus\n'
                '# client (client/oci_images.go) exec.LookPath("skopeo") and fails\n'
                '# with the exact message below when it is missing.\n'
                'if [ "${1:-}" = "--version" ] || [ "${1:-}" = "-V" ]; then\n'
                '    echo "incus-feature-oci 7.2.0 (OCI image support contract for Incus)"\n'
                '    exit 0\n'
                'fi\n'
                'if ! command -v skopeo >/dev/null 2>&1; then\n'
                '    echo \'OCI container handling requires "skopeo" be present on the system\' >&2\n'
                '    exit 1\n'
                'fi\n'
                'exec incus "$@"\n'
            )
        os.chmod(wrapper, 0o755)

        # License + contract documentation from the upstream source tarball.
        src = str(self.source_folder)
        copy(self, "COPYING", src, os.path.join(self.package_folder, "licenses"))
        docdir = os.path.join(self.package_folder, "share", "incus-feature-oci")
        os.makedirs(docdir, exist_ok=True)
        readme = os.path.join(docdir, "README.md")
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write(
                "# incus-feature-oci (HarmonyOS PC)\n\n"
                "Noarch meta-package equivalent of the Alpine ``incus-feature-oci``\n"
                "sub-package: *packages required to run OCI images under Incus*.\n\n"
                "Runtime contract:\n\n"
                "1. ``incus`` (provided by incus-feature-client) — the OCI image\n"
                "   consumer (``client/oci_images.go``).\n"
                "2. ``skopeo`` — external command required at runtime; upstream\n"
                "   error when missing:\n"
                "   ``OCI container handling requires 'skopeo' be present on the system``.\n"
                "   On OHOS, skopeo is not yet available (not in the ohpcd artifact\n"
                "   repository); adapting it is a separate task.\n\n"
                "``bin/incus-oci`` enforces the contract and delegates to ``incus``.\n")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
