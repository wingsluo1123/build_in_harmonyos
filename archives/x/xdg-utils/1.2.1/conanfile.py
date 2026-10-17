#!/usr/bin/env python3
"""Conan recipe for xdg-utils 1.2.1 — freedesktop.org xdg shell-script suite.

xdg-utils ships shell scripts (xdg-open/xdg-mime/xdg-email/...), not compiled
libraries: package_type="application", no cpp_info.libs. The scripts install
to <prefix>/bin via upstream autotools install. OHOS boundary: the xdg-*
runtime dispatcher (xdg-utils-common.in) probes desktop environments
(XDG_CURRENT_DESKTOP) and falls back to "generic" mode; on OHOS there is no
X11/Wayland session so desktop-specific helpers are unreachable at runtime —
script presence + `--version` execution is the verifiable boundary
(see test_package / notes.md).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XdgutilsConan(ConanFile):
    name = "xdg-utils"
    version = "1.2.1"
    description = "Freedesktop.org xdg-* portable shell-script integration suite (xdg-open, xdg-mime, xdg-email, ...)"
    license = "MIT"
    homepage = "https://www.freedesktop.org/wiki/Software/xdg-utils/"
    url = "https://gitlab.freedesktop.org/xdg/xdg-utils"

    package_type = "application"

    # L0p 要求 OHOS profile 四项 settings 齐全；纯脚本包编译器实际不参与
    settings = "os", "compiler", "build_type", "arch"
    options = {}
    default_options = {}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E060 use-tmpfs-workaround: config.status 在 HMDFS（/storage，noexec +
        # umask 077 临时目录不可写）上 mktemp -d ./confXXXXXX + subs1.awk 被拒；
        # tmpfs 根取 /data/storage/el2/base（acpid/2.0.34 先例）。
        root = f"/data/storage/el2/base/.conan-build-xdg-utils-{self.version}"
        work = os.path.join(root, "src")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')
        install_dir = os.path.join(root, "install")
        os.makedirs(install_dir, exist_ok=True)
        # xmlto 桩：上游 scripts/Makefile 的 all 目标含 html/man，真实 xmlto
        # 需联网拉 docbook DTD（沙箱不可达）。桩离线生成最小 man/html 页。
        shim_dir = os.path.join(root, "shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "xmlto")
        with open(shim, "w") as f:
            f.write(
                '#!/bin/sh\n'
                '# offline xmlto stub: docbook DTD fetch unreachable in sandbox\n'
                'mode="$1"; src="$2"\n'
                'base=$(basename "$src" .xml)\n'
                'case "$mode" in\n'
                '  man)           printf \'.TH "%s" 1 "xdg-utils 1.2.1"\\n\' "$base" > "$base.1" ;;\n'
                '  html)          printf \'<html><body>%s</body></html>\\n\' "$base" > "$base.html" ;;\n'
                '  html-nochunks) printf \'<html><body>%s</body></html>\\n\' "$base" > "$base.html" ;;\n'
                '  txt)           printf \'%s help text (offline stub)\\n\' "$base" > "$base.txt" ;;\n'
                'esac\n'
                'exit 0\n')
        os.chmod(shim, 0o755)
        env = (f'PATH={shim_dir}:/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:'
               f'{os.environ.get("PATH", "")} CONFIG_SHELL=/data/service/hnp/bin/bash '
               # /usr/bin/awk 指向 toybox 坏符号链接（exec 被拒），config.status 的
               # subs1.awk 处理需真实 awk；显式指定 hnp GNU awk
               f'AWK=/data/service/hnp/bin/awk')
        self.run(f'bash -c \'cd "{work}" && export {env} && ./configure --prefix="{install_dir}" '
                 f'--bindir="{install_dir}/bin"\'')
        # -j1 强制：上游 %: %.in %.txt 生成链（awk|sed 重定向 + sh --help 追加
        # .txt）在并行 make 下出现 sed 自读自写死循环（单文件膨胀至 ~35GB，
        # 2026-10-14 实证；-j1 复测脚本全部正常生成）
        self.run(f'bash -c \'cd "{work}" && export {env} && make -j1\'')
        # 不跑 make install：上游 install-sh 是新建脚本文件，在 OHOS MAC 沙箱下
        # "can't execute: Permission denied"（hishell_hap 对新建可执行文件无执行权）；
        # 直接复制已生成的脚本与文档（copy2 保留脚本已有执行位）。
        scripts_src = os.path.join(work, "scripts")
        bin_dst = os.path.join(install_dir, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        for entry in os.listdir(scripts_src):
            path = os.path.join(scripts_src, entry)
            if os.path.isfile(path) and os.access(path, os.X_OK) and entry.startswith("xdg-"):
                shutil.copy2(path, os.path.join(bin_dst, entry))
        for doc_dir, dst in (("man", "share/man"), ("html", "share/doc/xdg-utils/html")):
            src_d = os.path.join(scripts_src, doc_dir)
            if os.path.isdir(src_d):
                dst_d = os.path.join(install_dir, dst)
                os.makedirs(dst_d, exist_ok=True)
                for f in os.listdir(src_d):
                    if f.endswith((".1", ".html")):
                        shutil.copy2(os.path.join(src_d, f), os.path.join(dst_d, f))

    def package(self):
        install_dir = os.path.join(
            f"/data/storage/el2/base/.conan-build-xdg-utils-{self.version}",
            "install")
        copy(self, "*", src=os.path.join(install_dir, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.1", src=os.path.join(install_dir, "share", "man"), dst=os.path.join(self.package_folder, "share", "man"))
        copy(self, "*.html", src=os.path.join(install_dir, "share", "doc", "xdg-utils", "html"), dst=os.path.join(self.package_folder, "share", "doc", "xdg-utils", "html"))

    def package_id(self):
        del self.info.settings.build_type

    def package_info(self):
        # shell scripts, no libraries to link
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
