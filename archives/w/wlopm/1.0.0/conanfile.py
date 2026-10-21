#!/usr/bin/env python3
"""Conan recipe — wlopm 1.0.0 (make)

wlopm is a simple Wayland output power management client implementing
the zwlr-output-power-management-v1 protocol (~leon_plickat/wlopm,
GPLv3). A single C file plus scanner-generated protocol glue; upstream
Makefile drives wayland-scanner over the bundled protocol XML and
links -lwayland-client.

OHOS adaptation (0 source patches):
- tool_requires wayland/1.22.0 (merged): its package bin/ carries
  wayland-scanner (meson install), used as SCANNER for the protocol
  XML → C glue generation; libwayland-client comes from the same
  package's libs.
- The upstream Makefile hardcodes SCANNER := wayland-scanner; the
  recipe invokes make with SCANNER pointed at the dependency's
  scanner binary and CC/CFLAGS/LDFLAGS from the OHOS toolchain.
- wconversion/-Werror flag set kept as upstream (code compiles clean
  under clang 15); -j2 for HMFS concurrency limits (alacritty
  precedent).
- Upstream ships no test suite (CLI tool, no test/ dir, no #[test] —
  see test_package/MANIFEST.yml audit); consumer smoke cases
  (--version/--help/-h/--json usage) run in the test_package phase.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class WlopmConan(ConanFile):
    name = "wlopm"
    version = "1.0.0"
    description = "Wayland output power management client (zwlr-output-power-management-v1)"
    license = "GPL-3.0-only"
    homepage = "https://git.sr.ht/~leon_plickat/wlopm"
    url = "https://git.sr.ht/~leon_plickat/wlopm"
    topics = ("wayland", "output", "power-management", "cli")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # libwayland-client（运行时链接）与 wayland-scanner（构建期协议
        # 代码生成）同包提供（wayland/1.22.0 meson install 的 bin/ 含
        # wayland-scanner）。
        self.requires("wayland/1.22.0")

    def build_requirements(self):
        # wayland-scanner 自身 NEEDED libxml2.so.16（协议 XML 解析）：
        # scanner 只在构建期执行，libxml2 属构建上下文依赖（CI 的
        # -pr:b 与 -pr:h 同为 ohos-aarch64，二进制兼容）。wlopm 本体
        # 不链接 libxml2（cpp_info.requires 仅 wayland-client）。
        self.tool_requires("libxml2/2.15.3")

    def validate(self):
        # R32: settings.os check must use in (Linux, OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wlopm supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _sign_elf(path):
        """OHOS ELF codesign (kysdk-desktop 3.0.1.0 precedent).

        The dynamic linker refuses to execute (or dlopen) unsigned
        ELFs. The wayland-scanner shipped in the downloaded
        wayland/1.22.0 package is unsigned — executing it verbatim
        fails with EPERM (verified locally). Copy + self-sign before
        use; skip when a .codesign section is already present."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanInvalidConfiguration("required OHOS signing tools are missing")
        # NOTE: unconditional re-sign — the wayland/1.22.0 package from the
        # registry ships the scanner with a CI-side .codesign section that
        # is INVALID on this machine/worker (executing it verbatim fails
        # with EPERM, verified locally); binary-sign-tool replaces the old
        # section in place (file size unchanged, signature data replaced).
        temporary = path + ".signed"
        try:
            subprocess.run([signer, "sign", "-inFile", path, "-outFile", temporary,
                            "-selfSign", "1"], check=True, timeout=60)
            os.chmod(temporary, 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.unlink(temporary)

    @staticmethod
    def _dep_dir(dep, attr):
        for d in getattr(dep.cpp_info, attr):
            return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
        return None

    def build(self):
        wayland = self.dependencies["wayland"]
        # ── scanner：定位 → 拷贝到 build 目录 → 签名 ──
        # （制品仓包内的 scanner 未签名，OHOS 直接执行报 EPERM；且不能
        # 改写依赖包目录，拷贝到本包 build 目录自签后再用。）
        scanner_src = None
        for bindir in wayland.cpp_info.bindirs:
            cand = bindir if os.path.isabs(bindir) else os.path.join(
                wayland.package_folder, bindir)
            probe = os.path.join(cand, "wayland-scanner")
            if os.path.isfile(probe):
                scanner_src = probe
                break
        if not scanner_src:
            raise ConanInvalidConfiguration(
                "wayland-scanner not found in wayland/1.22.0 package"
            )
        scanner_bin = os.path.join(self.build_folder, "wayland-scanner.bin")
        shutil.copy2(scanner_src, scanner_bin)
        os.chmod(scanner_bin, 0o755)
        self._sign_elf(scanner_bin)

        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        wayland_lib = self._dep_dir(wayland, "libdirs")
        wayland_inc = self._dep_dir(wayland, "includedirs")
        xml2 = self.dependencies["libxml2"]
        xml2_lib = self._dep_dir(xml2, "libdirs")

        # scanner wrapper：libxml2 运行库路径仅注入 scanner 子进程——
        # 放全局 LD_LIBRARY_PATH 会污染 lld（其自身 NEEDED libxml2.so.16，
        # 会加载 conan 包内符号不匹配版本，CI #91520 实测
        # xmlFreeDoc: symbol not found）。
        scanner = os.path.join(self.build_folder, "wayland-scanner")
        wrapper_lines = [
            "#!/bin/sh",
            "# wlopm recipe: scanner wrapper (scoped libxml2 runtime path)",
        ]
        if xml2_lib:
            wrapper_lines.append(
                'LD_LIBRARY_PATH="%s:${LD_LIBRARY_PATH:-}" exec "%s" "$@"'
                % (xml2_lib, scanner_bin))
        else:
            wrapper_lines.append('exec "%s" "$@"' % scanner_bin)
        with open(scanner, "w", encoding="utf-8") as f:
            f.write("\n".join(wrapper_lines) + "\n")
        os.chmod(scanner, 0o755)

        env = dict(os.environ)
        env["CC"] = cc
        env["CFLAGS"] = (f"-I{wayland_inc} "
                         + os.environ.get("CFLAGS", ""))
        ldflags = f"-L{wayland_lib}" if wayland_lib else ""
        # HMFS 上并发链接偶发 Text file busy——-j2（alacritty 先例）。
        subprocess.check_call(
            ["make", "-j2", "wlopm", f"SCANNER={scanner}", f"CC={cc}",
             f"LDFLAGS={ldflags}"],
            cwd=self.source_folder,
            env=env,
        )

    def package(self):
        dst = os.path.join(self.package_folder, "bin")
        copy(self, "wlopm", src=self.source_folder, dst=dst)
        # 打包二进制签名：test_package 阶段真执行（OHOS 拒绝未签名 ELF）
        self._sign_elf(os.path.join(dst, "wlopm"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "wlopm.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 运行期依赖 libwayland-client（wayland/1.22.0 已声明）
        self.cpp_info.requires = ["wayland::wayland-client"]
