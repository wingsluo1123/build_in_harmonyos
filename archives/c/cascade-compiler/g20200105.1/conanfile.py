#!/usr/bin/env python3
"""Conan recipe for VMware Cascade g20200105.1 on HarmonyOS PC."""

import os
import shutil
import tarfile

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
)


class CascadeCompilerConan(ConanFile):
    name = "cascade-compiler"
    version = "g20200105.1"
    package_type = "library"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vmware-archive/cascade"
    description = "JIT compiler and software simulator for Verilog"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("ncurses/6.4")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("googletest/1.18.0")
        self.tool_requires("google-benchmark/1.9.5")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _extract_verified_tarball(archive_path, destination):
        os.makedirs(destination, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            if not members or not members[0].name.rstrip("/"):
                raise ValueError("Expected a single top-level directory in source archive")
            root = members[0].name.rstrip("/").split("/", 1)[0]
            safe_members = []
            for member in members:
                if member.name.rstrip("/") == root:
                    continue
                prefix = root + "/"
                if not member.name.startswith(prefix):
                    raise ValueError("Source archive contains an unexpected top-level path")
                relative = member.name[len(prefix):]
                components = relative.split("/")
                if not relative or relative.startswith("/") or ".." in components:
                    raise ValueError("Source archive contains an unsafe path")
                if member.issym() or member.islnk():
                    link = member.linkname
                    if member.islnk() and link.startswith(prefix):
                        link = link[len(prefix):]
                    resolved = os.path.normpath(os.path.join(os.path.dirname(relative), link))
                    if os.path.isabs(link) or resolved == ".." or resolved.startswith(".." + os.sep):
                        raise ValueError("Source archive contains a link outside its root")
                    member.linkname = link
                member.name = relative
                safe_members.append(member)
            archive.extractall(destination, members=safe_members)

    def source(self):
        cascade_archive = "cascade-source.tar.gz"
        download(
            self,
            self.conan_data["sources"]["url"],
            cascade_archive,
            sha256=self.conan_data["sources"]["sha256"],
        )
        self._extract_verified_tarball(cascade_archive, self.source_folder)
        os.remove(cascade_archive)

        verilator_archive = "verilator-source.tar.gz"
        download(
            self,
            self.conan_data["verilator"]["url"],
            verilator_archive,
            sha256=self.conan_data["verilator"]["sha256"],
        )
        self._extract_verified_tarball(
            verilator_archive, os.path.join(self.source_folder, ".verilator-src")
        )
        os.remove(verilator_archive)

    def generate(self):
        include_dirs = set()
        library_dirs = set()
        for context in (self.dependencies.host, self.dependencies.build):
            for dependency in context.values():
                if not dependency.package_folder:
                    continue
                for directory in dependency.cpp_info.includedirs:
                    include_dirs.add(os.path.join(dependency.package_folder, directory))
                for directory in dependency.cpp_info.libdirs:
                    library_dirs.add(os.path.join(dependency.package_folder, directory))

        flex_dependency = self.dependencies.build["flex"]
        flex_include_dirs = [
            os.path.join(flex_dependency.package_folder, directory)
            for directory in flex_dependency.cpp_info.includedirs
        ]
        flex_header_dir = next(
            (
                directory
                for directory in flex_include_dirs
                if os.path.isfile(os.path.join(directory, "FlexLexer.h"))
            ),
            None,
        )
        if flex_header_dir is None:
            raise RuntimeError("Flex package does not provide FlexLexer.h")

        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["BUILD_TESTING"] = True
        toolchain.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.cache_variables["FLEX_INCLUDE_DIR"] = flex_header_dir
        toolchain.cache_variables["CASCADE_EXTRA_INCLUDE_DIRS"] = ";".join(
            sorted(include_dirs)
        )
        toolchain.cache_variables["CASCADE_EXTRA_LIBRARY_DIRS"] = ";".join(
            sorted(library_dirs)
        )
        toolchain.generate()
        CMakeDeps(self).generate()
        build_env = VirtualBuildEnv(self)
        bison_data = os.path.join(
            self.dependencies.build["bison"].package_folder, "share", "bison"
        )
        m4_executable = shutil.which("m4")
        if not os.path.isfile(os.path.join(bison_data, "m4sugar", "m4sugar.m4")):
            raise RuntimeError("Bison package data directory is incomplete")
        if not m4_executable:
            raise RuntimeError("GNU M4 is required to build Verilator and Cascade")
        build_variables = build_env.environment()
        build_variables.define("BISON_PKGDATADIR", bison_data)
        build_variables.define("M4", m4_executable)
        build_variables.define(
            "CPPFLAGS",
            " ".join("-I{}".format(directory) for directory in flex_include_dirs),
        )
        build_env.generate()
        VirtualRunEnv(self).generate()

    def _build_verilator(self):
        source_dir = os.path.join(self.source_folder, ".verilator-src")
        install_prefix = os.path.join(self.build_folder, "_tools", "verilator")
        os.makedirs(install_prefix, exist_ok=True)

        bison_data = os.path.join(
            self.dependencies.build["bison"].package_folder, "share", "bison"
        )
        if not os.path.isfile(os.path.join(bison_data, "m4sugar", "m4sugar.m4")):
            raise RuntimeError("Bison package data directory is incomplete")
        os.environ["BISON_PKGDATADIR"] = bison_data

        # Bison 3.8 derives the generated header include from verilog.y, while
        # bisonpre renames the generated header to V3ParseBison.h.
        bisonpre_path = os.path.join(source_dir, "src", "bisonpre")
        with open(bisonpre_path, "r", encoding="utf-8") as bisonpre_file:
            bisonpre = bisonpre_file.read()
        include_rewrite = '        $line =~ s!$basename!$newbase!g;\n'
        if bisonpre.count(include_rewrite) != 1:
            raise RuntimeError("Unexpected Verilator bisonpre source layout")
        bisonpre = bisonpre.replace(
            include_rewrite,
            include_rewrite
            + '        $line =~ s!#include "verilog\\.h"!#include "V3ParseBison.h"! if $is_c;\n',
        )
        with open(bisonpre_path, "w", encoding="utf-8") as bisonpre_file:
            bisonpre_file.write(bisonpre)

        self.run("autoconf", cwd=source_dir, env="conanbuild")
        self.run(
            "CC=clang CXX=clang++ ./configure --no-create --prefix=\"{}\"".format(
                install_prefix
            ),
            cwd=source_dir,
            env="conanbuild",
        )
        config_status_path = os.path.join(source_dir, "config.status")
        with open(config_status_path, "r", encoding="utf-8") as config_status_file:
            config_status = config_status_file.read()
        if config_status.count("umask 077") != 2:
            raise RuntimeError("Unexpected Verilator config.status temporary-directory setup")
        config_status = config_status.replace("umask 077", "umask 007")
        with open(config_status_path, "w", encoding="utf-8") as config_status_file:
            config_status_file.write(config_status)
        self.run("./config.status", cwd=source_dir, env="conanbuild")
        self.run("make -j2", cwd=source_dir, env="conanbuild")
        install_script = os.path.join(source_dir, "install-sh")
        self.run(
            'make install INSTALL="/bin/sh {} -c"'.format(install_script),
            cwd=source_dir,
            env="conanbuild",
        )

        verilator_root = os.path.join(install_prefix, "share", "verilator")
        verilator_bin = os.path.join(install_prefix, "bin")
        os.environ["VERILATOR_ROOT"] = verilator_root
        os.environ["PATH"] = verilator_bin + os.pathsep + os.environ.get("PATH", "")

    def build(self):
        apply_conandata_patches(self)
        self._build_verilator()

        cmake = CMake(self)
        cmake.configure()
        self.run(
            'cmake --build "{}" --parallel 2'.format(self.build_folder),
            env="conanbuild",
        )

        cascade_tmp_dir = os.path.join(self.build_folder, "_cascade_tmp")
        os.makedirs(cascade_tmp_dir, exist_ok=True)
        self.run(
            'CASCADE_TMP_DIR="{}" ctest --test-dir "{}" --output-on-failure --verbose'.format(
                cascade_tmp_dir, self.build_folder
            ),
            env="conanrun",
        )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "src", "cascade"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        verilator_prefix = os.path.join(self.build_folder, "_tools", "verilator")
        package_verilator = os.path.join(self.package_folder, "tools", "verilator")
        copy(self, "*", src=verilator_prefix, dst=package_verilator, keep_path=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CascadeCompiler")
        self.cpp_info.set_property("cmake_target_name", "CascadeCompiler::Cascade")
        self.cpp_info.libs = ["cascade"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.system_libs = ["pthread", "dl"]
        verilator_prefix = os.path.join(self.package_folder, "tools", "verilator")
        self.runenv_info.prepend_path("PATH", os.path.join(verilator_prefix, "bin"))
        self.runenv_info.define(
            "VERILATOR_ROOT", os.path.join(verilator_prefix, "share", "verilator")
        )
        self.buildenv_info.prepend_path("PATH", os.path.join(verilator_prefix, "bin"))
        self.buildenv_info.define(
            "VERILATOR_ROOT", os.path.join(verilator_prefix, "share", "verilator")
        )
