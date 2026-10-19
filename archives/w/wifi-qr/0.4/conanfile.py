#!/usr/bin/env python3
"""Conan recipe for wifi-qr 0.4 — bash CLI tool to create/scan WiFi QR codes.

Upstream: https://github.com/kokoye2007/wifi-qr (GPL-3.0)
Packaging family: 解释型脚本工具（v12.21 §12 变体 C）——只装不编。
Runtime dependencies (executed via PATH): bash, qrencode, zbarimg, nmcli;
  zenity/kdialog/fzf/tput are optional and degrade gracefully.
nmcli (NetworkManager) is not packaged for OHOS; wifi scan/connect features
require a system NetworkManager — QR create (-t/-c via qrencode) and file
scan (-f via zbarimg) work without it.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


class WifiQrConan(ConanFile):
    name = "wifi-qr"
    version = "0.4"
    description = "Create WiFi QR codes and scan/connect them from the terminal"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/kokoye2007/wifi-qr"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qrencode: QR PNG/UTF8 encoder used by create modes
        self.requires("qrencode/4.1.1")
        # zbar: zbarimg QR decoder used by scan modes
        self.requires("zbar/0.23.93")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # 无编译阶段：上游为单一 bash 脚本（不伪造编译——R34）。
    # 语法/功能校验由 test_package 真实执行 wifi-qr 覆盖（R34）。
    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # 上游源为单一 bash 脚本，稳健定位（source_folder 随 layout 可能在 src/ 或 build/）
        candidates = [self.source_folder, os.path.join(self.source_folder, "src"),
                      self.build_folder, self.export_folder]
        src = next((c for c in candidates
                    if c and os.path.isfile(os.path.join(c, "wifi-qr"))), self.source_folder)
        # bin/wifi-qr — copy 保留可执行位，再显式 chmod 0o755 兜底（HMDFS 权限语义）
        copy(self, "wifi-qr", src=src, dst=os.path.join(self.package_folder, "bin"))
        script = os.path.join(self.package_folder, "bin", "wifi-qr")
        # 平台适配：鸿蒙PC 无 /bin/bash，改写为 env 解析（OHOS 必要转换，非上游缺陷修复）
        replace_in_file(self, script, "#!/bin/bash\n", "#!/usr/bin/env bash\n")
        os.chmod(script, 0o755)
        copy(self, "wifi-qr.1", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "wifi-qr.desktop", src=src,
             dst=os.path.join(self.package_folder, "share", "applications"), keep_path=False)
        copy(self, "wifi-qr.svg", src=src,
             dst=os.path.join(self.package_folder, "share", "icons", "hicolor", "scalable", "apps"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # pure script, no compiled artifacts

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # Keep bash shebang scripts working with the bundled interpreter path
        bindir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bindir)
