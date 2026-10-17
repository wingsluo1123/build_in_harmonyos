#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Liblzw, liblzw, 0.3, liblzw 0.3, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout
from conan.tools.files import chdir
import os


class LiblzwConan(ConanFile):
    name = "liblzw"
    version = "0.3"
    description = "liblzw 0.3"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # R02 CI L1 闭环: 上游 v0.3 tarball 不带生成的 configure, build() 必须
        # 先跑 autogen.sh (autoreconf -i -f)。CI 干净环境仅有 autoconf 2.72
        # (/data/service/hnp), 无 automake/aclocal — R01 L1 实测
        # "Can't exec aclocal", autoreconf exit 2, configure 未生成。把 automake
        # + libtool 作为 tool_requires 拉入 (制品仓已发布 1.18/2.5.4, 同
        # abiword-plugin-docbook 先例), 由 conanbuild 环境提供 aclocal/automake/
        # libtoolize, 不再依赖执行端设备本机 autotools。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv: 把 tool_requires(automake/libtool) 的 bin 目录注入
        # conanbuild 环境的 PATH——aclocal/automake/libtoolize 只存在于
        # tool_requires 包内, 不注入则 self.run(env="conanbuild") 报
        # "aclocal: not found"(CI 干净环境实测语义, 同 abiword 先例)。
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Explicit triplet: config.guess cannot write its probe temp file into
        # the executor's unwritable $HOME (/storage/Users/currentUser) on hmdfs,
        # so "cannot guess build type" fails; supply build/host explicitly.
        tc.configure_args.append("--build=aarch64-linux-ohos")
        tc.configure_args.append("--host=aarch64-linux-ohos")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Upstream v0.3 tarball ships autogen.sh + configure.ac but no generated
        # configure script; run autogen.sh (autoreconf -i -f) first so
        # autotools.configure() has a configure script to execute.  Run inside
        # the conanbuild env: aclocal/automake come from tool_requires
        # (automake/1.18 + libtool/2.5.4), not the executor's host autotools.
        # autogen.sh's trailing `git checkout -f INSTALL || true` tolerates a
        # non-git source dir (CI clean env), so the git probe is non-fatal and
        # configure generation is unaffected.
        with chdir(self, self.source_folder):
            if not os.path.exists(os.path.join(self.source_folder, "configure")):
                self.run("sh autogen.sh", cwd=self.source_folder, env="conanbuild")
        # E011 (edit-umask-in-configure): generated config.status creates its
        # temp dir with umask 077, and OHOS/HMDFS makes new 0700 dirs unwritable
        # (Permission denied), so configure dies inside config.status. Relax the
        # generated configure template so config.status uses a writable umask.
        self.run("sed -i 's/umask 077/umask 022/g' configure", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        self._patch_generated_libtool()
        autotools.make(args=["-j1"])

    def _patch_generated_libtool(self):
        # The generated libtool on this OHOS runner never assigns the lowercase
        # `echo` variable (only ECHO=), so `$echo "X$arg"` expands to running a
        # command named "X--mode=compile" and fails; also `$tool_oldlib` is never
        # set, so ranlib gets no archive argument. Patch the generated script so
        # make can drive libtool (libtool is a build artifact, not tracked).
        lt = os.path.join(self.build_folder, "build-release", "libtool")
        if not os.path.exists(lt):
            lt = os.path.join(self.build_folder, "libtool")
        if not os.path.exists(lt):
            return
        with open(lt, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        if 'echo="$ECHO"' not in txt:
            # insert AFTER the ECHO= assignment so it picks up the value
            idx = txt.find("ECHO=")
            if idx != -1:
                end = txt.find("\n", idx)
                txt = txt[: end + 1] + 'echo="$ECHO"\n' + txt[end + 1 :]
        # old_archive_cmds/old_postinstall_cmds store escaped \$tool_oldlib
        txt = txt.replace(r"\$RANLIB \$tool_oldlib", r"\$RANLIB \$oldlib")
        with open(lt, "w", encoding="utf-8") as f:
            f.write(txt)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Base library name is "lzw" (installed as liblzw.a); conan adds the
        # "lib"/suffix itself, so supplying "liblzw" would break CMakeDeps.
        self.cpp_info.libs = ["lzw"]
