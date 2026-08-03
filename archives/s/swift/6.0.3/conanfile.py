#!/usr/bin/env python3
"""Conan package for the Swift 6.0.3 OHOS toolchain.

The default path downloads the Swift 6.0.3 source components, applies the OHOS
patch set, and runs the reviewable source-bootstrap helper to assemble a Swift
stage from source. A preassembled stage may still be used for probe replay, but
only when SWIFT_OHOS_ALLOW_STAGED_PACKAGE=1 is set; that path records a stage
identity hash so downstream recipes do not silently depend on absolute probe
paths.
"""
import os
import shutil
import stat
import tarfile
import hashlib
import json

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, unzip
from conan.tools.layout import basic_layout


class SwiftConan(ConanFile):
    name = "swift"
    version = "6.0.3"
    description = "Swift compiler and Swift Package Manager for HarmonyOS/OHOS"
    license = "Apache-2.0"
    homepage = "https://www.swift.org/"
    url = "https://www.swift.org/"
    package_type = "application"
    options = {"stage_id": ["ANY"]}
    default_options = {"stage_id": "source"}

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "scripts/*"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("This Swift package currently targets OHOS only.")
        if str(self.settings.arch) not in ("armv8", "armv8.3", "armv8.4", "aarch64"):
            raise ConanInvalidConfiguration(f"Unsupported OHOS Swift arch: {self.settings.arch}")

    def configure(self):
        self.settings.rm_safe("compiler")
        self.settings.rm_safe("build_type")
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")
        self.info.settings.rm_safe("os.version")
        self.info.options.stage_id = self._stage_identity()

    def source(self):
        for name, source in self.conan_data["sources"].items():
            local_archive = self._local_source_archive(source)
            if local_archive:
                self.output.info(f"Using cached Swift source component: {name}")
                self._verify_sha256(local_archive, source["sha256"], name)
                unzip(self, local_archive, destination=self.source_folder)
            else:
                self.output.info(f"Fetching Swift source component: {name}")
                get_args = {key: value for key, value in source.items() if key != "filename"}
                get(self, destination=self.source_folder, strip_root=False, **get_args)
        apply_conandata_patches(self)
        self._write_source_manifest()

    def build(self):
        stage_out = os.path.join(self.build_folder, "stage")
        if self._allow_staged_package() and self._has_supplied_stage():
            self._copy_supplied_stage(stage_out)
        else:
            self._build_from_source(stage_out)

        self._validate_stage(stage_out)

    def _copy_supplied_stage(self, stage_out):
        stage = os.environ.get("SWIFT_OHOS_STAGED_ROOT")
        tarball = os.environ.get("SWIFT_OHOS_STAGED_TARBALL")
        if stage and os.path.isdir(stage):
            copy(self, "*", src=stage, dst=stage_out, keep_path=True)
        elif tarball and os.path.isfile(tarball):
            os.makedirs(stage_out, exist_ok=True)
            with tarfile.open(tarball, "r:*") as archive:
                try:
                    archive.extractall(stage_out, filter="data")
                except TypeError:
                    archive.extractall(stage_out)
            self._strip_single_root(stage_out)
        else:
            raise ConanException(
                "SWIFT_OHOS_ALLOW_STAGED_PACKAGE=1 was set, but neither "
                "SWIFT_OHOS_STAGED_ROOT nor SWIFT_OHOS_STAGED_TARBALL points "
                "to a usable Swift OHOS stage."
            )
        self._write_stage_provenance(stage_out, source_mode="staged")

    def _build_from_source(self, stage_out):
        script = os.path.join(
            self.export_sources_folder, "scripts", "source-bootstrap-ohos.sh"
        )
        if not os.path.isfile(script):
            raise ConanException(f"Swift OHOS source bootstrap script is missing: {script}")
        env = {
            "SWIFT_OHOS_SOURCE_ROOT": self.source_folder,
            "SWIFT_OHOS_BUILD_ROOT": os.path.join(self.build_folder, "source-bootstrap"),
            "SWIFT_OHOS_BOOTSTRAP_ROOT": os.path.join(
                self.build_folder, "source-bootstrap", "bootstrap"
            ),
            "SWIFT_OHOS_STAGE_OUT": stage_out,
        }
        command = " ".join(f"{key}={self._quote_sh(value)}" for key, value in env.items())
        command = f"{command} sh {self._quote_sh(script)}"
        self.run(command, cwd=self.source_folder)
        self._write_stage_provenance(stage_out, source_mode="source-bootstrap")

    def _strip_single_root(self, stage_out):
        entries = os.listdir(stage_out)
        if len(entries) != 1:
            return
        root = os.path.join(stage_out, entries[0])
        if not os.path.isdir(root):
            return
        for name in os.listdir(root):
            shutil.move(os.path.join(root, name), os.path.join(stage_out, name))
        os.rmdir(root)

    def _validate_stage(self, stage):
        required = [
            os.path.join("bin", "swift"),
            os.path.join("bin", "swiftc"),
            os.path.join("bin", "swift-frontend"),
            os.path.join("bin", "swift-autolink-extract"),
            os.path.join("bin", "swift-build"),
            os.path.join("bin", "swift-package"),
            os.path.join("lib", "swift"),
        ]
        missing = [path for path in required if not os.path.exists(os.path.join(stage, path))]
        if missing:
            raise ConanException(f"Swift OHOS stage is missing required entries: {missing}")

    def _has_supplied_stage(self):
        stage = os.environ.get("SWIFT_OHOS_STAGED_ROOT")
        tarball = os.environ.get("SWIFT_OHOS_STAGED_TARBALL")
        return (stage and os.path.isdir(stage)) or (tarball and os.path.isfile(tarball))

    def _allow_staged_package(self):
        return os.environ.get("SWIFT_OHOS_ALLOW_STAGED_PACKAGE") == "1"

    def _stage_identity(self):
        if not self._allow_staged_package():
            return "source"
        stage = os.environ.get("SWIFT_OHOS_STAGED_ROOT")
        tarball = os.environ.get("SWIFT_OHOS_STAGED_TARBALL")
        if tarball and os.path.isfile(tarball):
            return "tarball-" + self._hash_file(tarball)[:32]
        if stage and os.path.isdir(stage):
            return "dir-" + self._hash_tree(stage)[:32]
        return "source"

    def _write_source_manifest(self):
        manifest = {
            "swift_version": self.version,
            "components": sorted(self.conan_data["sources"].keys()),
            "patches": [
                patch["patch_file"]
                for patch in self.conan_data.get("patches", {}).get(str(self.version), [])
            ],
            "toolchain_references": self.conan_data.get("toolchain_references", {}),
        }
        path = os.path.join(self.source_folder, "SWIFT-OHOS-SOURCE-MANIFEST.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _local_source_archive(self, source):
        mirror = os.environ.get("SWIFT_OHOS_SOURCE_TARBALL_DIR")
        if not mirror:
            return None
        for name in (source.get("filename"), os.path.basename(source["url"])):
            if not name:
                continue
            candidate = os.path.join(mirror, name)
            if os.path.isfile(candidate):
                return candidate
        return None

    def _verify_sha256(self, path, expected, name):
        actual = self._hash_file(path)
        if actual.lower() != expected.lower():
            raise ConanException(
                f"Cached Swift source component {name} has sha256 {actual}, expected {expected}"
            )

    def _write_stage_provenance(self, stage_out, source_mode):
        os.makedirs(stage_out, exist_ok=True)
        provenance = {
            "source_mode": source_mode,
            "stage_identity": self._stage_identity(),
            "source_manifest": "SWIFT-OHOS-SOURCE-MANIFEST.json",
        }
        if os.path.isdir(stage_out):
            provenance["stage_tree_sha256"] = self._hash_tree(stage_out)
        path = os.path.join(stage_out, "CONAN-STAGE-PROVENANCE.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(provenance, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def _hash_file(self, path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _hash_tree(self, root):
        digest = hashlib.sha256()
        for current, dirs, files in os.walk(root):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(current, name)
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                digest.update(rel.encode("utf-8"))
                digest.update(b"\0")
                digest.update(self._hash_file(path).encode("ascii"))
                digest.update(b"\0")
        return digest.hexdigest()

    def _quote_sh(self, value):
        return "'" + str(value).replace("'", "'\"'\"'") + "'"

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "*", src=stage, dst=self.package_folder, keep_path=True)
        self._make_bin_executable()

    def _make_bin_executable(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bin_dir):
            return
        for name in os.listdir(bin_dir):
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        swift_lib_dir = os.path.join(lib_dir, "swift", "ohos")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", lib_dir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", lib_dir)
        if os.path.isdir(swift_lib_dir):
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", swift_lib_dir)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", swift_lib_dir)
        self.buildenv_info.define("SWIFT_EXEC", os.path.join(bin_dir, "swiftc"))
        self.buildenv_info.define("SWIFT_OHOS_TOOLCHAIN_ROOT", self.package_folder)
