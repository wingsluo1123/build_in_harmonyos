#!/usr/bin/env python3
"""Conan recipe — bazel-diff 18.0.0 (Kotlin/JVM project)

bazel-diff is a CLI tool for determining affected Bazel targets between
Git revisions. The deploy is a platform-independent fat JAR.

Bazel cannot run on OHOS CI (HMDFS/SELinux limitations), so we package
a pre-built deploy JAR. JVM bytecode is platform-independent, runs on
any JDK 21+.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BazelDiffConan(ConanFile):
    name = "bazel-diff"
    version = "18.0.0"
    description = "Bazel target diffing tool — determine affected targets between Git revisions"
    license = "Apache-2.0"
    homepage = "https://github.com/Tinder/bazel-diff"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Export pre-built deploy JAR (platform-independent JVM bytecode)
        # Bazel/kotlinc not available on OHOS CI, use pre-built artifact
        copy(self, "bazel-diff.jar", src=self.recipe_folder,
             dst=self.export_sources_folder)
        copy(self, "bazel-diff", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Use pre-built deploy JAR — Bazel/kotlinc not available on OHOS CI
        # JVM bytecode is platform-independent, no compilation needed
        build_dir = os.path.join(self.build_folder, "build")
        os.makedirs(build_dir, exist_ok=True)
        copy(self, "bazel-diff.jar", src=self.source_folder,
             dst=build_dir)

    def package(self):
        # Copy fat JAR and launcher script
        src_dir = self.build_folder
        copy(self, "bazel-diff.jar", src=os.path.join(src_dir, "build"),
             dst=os.path.join(self.package_folder, "bin"))
        # Launcher script
        launcher = os.path.join(self.package_folder, "bin", "bazel-diff")
        with open(launcher, 'w') as f:
            f.write('#!/bin/sh\nexec java -jar "$(dirname "$0")/bazel-diff.jar" "$@"\n')
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
