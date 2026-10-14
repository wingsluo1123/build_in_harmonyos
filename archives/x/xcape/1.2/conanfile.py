#!/usr/bin/env python3
"""Conan recipe for xcape 1.2 -- make a modifier key act as another key when tapped.

Upstream ships one translation unit (xcape.c) plus a Makefile whose only way of
locating X11 is host pkg-config:

    CFLAGS  += `pkg-config --cflags xtst x11`
    LDFLAGS += `pkg-config --libs   xtst x11`

Neither `xtst` nor `x11` exists on an OHOS device (there is no host X11 dev
tree), so the upstream `make` stops at

    xcape.c:29:10: fatal error: 'X11/Xlib.h' file not found

This recipe therefore does not run the upstream Makefile: it issues the same
single-TU compile directly against the X11 packages published in the OHOS conan
repository (clipnotify/1.0.2 and xbanish/1.8 precedent), with every -I/-L taken
from the dependency packages' private folders (R49: no shared-prefix injection).

xcape.c compiles unmodified against the packaged X11 headers -- 0 source patches
are required (verified by the real compile recorded in notes.md).

E549: the produced ELF is self-signed with binary-sign-tool before packaging.
OHOS has no X server, so the consumer tests execute the signed ELF and check the
deterministic no-X diagnostic plus the recorded DT_NEEDED X libraries (see
test_package/).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XcapeConan(ConanFile):
    name = "xcape"
    version = "1.2"
    description = (
        "Use a modifier key as another key when pressed and released on its own "
        "(e.g. tap Left Control -> Escape)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/alols/xcape"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 本版无补丁（xcape.c 对打包的 X11 头文件零改动编译通过）；保留标准
        # 钩子以与同族 X11 配方（clipnotify/1.0.2、xbanish/1.8）一致，
        # 后续若需补丁无需改动配方骨架。
        export_conandata_patches(self)

    def requirements(self):
        # 上游 Makefile 的 `pkg-config --cflags/--libs xtst x11`，逐条映射到制品仓
        # 已发布的 libx11/6.4.0 版本线（W0 实测见 notes.md）。
        # xcape.c 使用 XTestFakeKeyEvent（XTest）与 XRecord*（XRecord）——两者都由
        # libXtst 提供；libxtst/6.1.0 自身 requires libx11/6.4.0 / libxext/6.4.0 /
        # libxi/6.1.0 / libxfixes/6.1.0 / libxau/1.0.11，与 libx11/6.4.0 同线，不冲突。
        self.requires("libxtst/6.1.0", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        # X11/X.h、X11/keysym.h 等协议头
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # conanbuild 环境提供 $CC/$CFLAGS/$CPPFLAGS（R33：不依赖 shell 预置变量）
        AutotoolsToolchain(self).generate()

    # ── E549 ELF 自签名（clipnotify / xbanish 同款实现） ────────────────

    def _find_tool(self, name):
        import glob as g

        for d in sorted(
            g.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")
        ):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        for d in ("/data/service/hnp/bin",):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        return shutil.which(name)

    def _sign_elf(self, binary_path):
        from conan.errors import ConanException

        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not sign_tool or not objcopy:
            raise ConanException("binary-sign-tool/llvm-objcopy not found (E549)")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", binary_path],
            capture_output=True,
            timeout=30,
        )
        tmp = binary_path + ".signed.tmp"
        for _ in range(3):
            r = subprocess.run(
                [
                    sign_tool,
                    "sign",
                    "-inFile",
                    binary_path,
                    "-outFile",
                    tmp,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary_path)
                os.chmod(binary_path, 0o775)
                return
        if os.path.exists(tmp):
            os.remove(tmp)
        raise ConanException(f"signing failed for {binary_path}")

    def build(self):
        apply_conandata_patches(self)  # 本版 conandata 的 patches 为空，等价 no-op
        src = self.source_folder
        dep_incs = " ".join(
            f"-I{os.path.join(dep.package_folder, inc)}"
            for dep in self.dependencies.host.values()
            for inc in dep.cpp_info.includedirs
        )
        dep_libs = " ".join(
            f"-L{os.path.join(dep.package_folder, libdir)}"
            for dep in self.dependencies.host.values()
            for libdir in dep.cpp_info.libdirs
        )
        out = os.path.join(self.build_folder, "xcape")
        # 上游 Makefile 同一编译式（$CC $(CFLAGS) -o xcape xcape.c $(LDFLAGS)），
        # 仅把其 pkg-config 取到的 include/lib 换成 conan 依赖包私有目录（R49）。
        self.run(
            f'$CC $CPPFLAGS $CFLAGS -Wall {dep_incs} "{src}/xcape.c" -o "{out}" '
            f'{dep_libs} -lXtst -lX11 -pthread',
            env="conanbuild",
        )
        self._sign_elf(out)

    def package(self):
        copy(
            self,
            "xcape",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "xcape.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
