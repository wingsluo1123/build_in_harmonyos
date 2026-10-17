#!/usr/bin/env python3
"""installation-report 2.98 — Debian 安装报告工具集（纯 shell 脚本，Debian native 包）。

上游是 Debian **native** 包：没有独立上游仓库，源码 = 顶层脚本 + `debian/`（含 `debian/po/`），
`debian/rules` 只有 `%: dh $@`。OHOS 环境没有 dh/debhelper，故本配方**不跑 dh**，而是按
`debian/installation-report.install`、`debian/save-logs.install`、`debian/*.manpages`、
`debian/*.links` 声明的映射直接安装产物（与同族 `archives/i/init-system-helpers` 同一做法）。

产物映射（照抄 debian/*.install）：
    report-hw                  -> bin/report-hw              （installation-report.install）
    httpd, usb-list            -> bin/                       （save-logs.install 的
                                  「report-hw httpd usb-list usr/bin」）
    install-report.template    -> share/installation-report/ （debconf 模板数据）
                               -> share/save-logs/            （同一文件两处引用）
    bug/                       -> share/bug/                 （installation-report.install: 「bug usr/share」）
    pre-pkgsel.d/              -> lib/pre-pkgsel.d/
    finish-install.d/          -> lib/finish-install.d/
    report-hw.1                -> share/man/man1/            （debian/*.manpages，文件已随源码提供）
    debian/…README.Debian      -> share/doc/installation-report/
    debian/*.links 声明的软链  -> share/doc/installation-report/install-report.template

依赖：**无 Conan requires**。`debian/control` 的 Build-Depends 仅 `debhelper-compat (= 13)`、
Depends 仅 `${misc:Depends}`；脚本运行时只用 `/bin/sh`，`lspci`/`lsusb`/`dmidecode` 是脚本内
**可选**调用（`report-hw` 注释明确「behaving robustly if commands are missing」）。

上游测试：**无**（无 `Makefile`/`t/`/`debian/tests`，`debian/rules` 只有 `%: dh $@`）
→ 上游通过率记 N/A（如实披露）；构建期只做 shell 语法检查，验证主要放在 test_package。
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

# (源内相对路径, 包内相对路径, 是否可执行)
PAYLOAD = (
    ("report-hw", "bin/report-hw", True),
    ("httpd", "bin/httpd", True),
    ("usb-list", "bin/usb-list", True),
    ("install-report.template", "share/installation-report/install-report.template", False),
    ("install-report.template", "share/save-logs/install-report.template", False),
    ("pre-pkgsel.d/50save-logs", "lib/pre-pkgsel.d/50save-logs", True),
    ("finish-install.d/94save-logs", "lib/finish-install.d/94save-logs", True),
    ("report-hw.1", "share/man/man1/report-hw.1", False),
    ("debian/installation-report.README.Debian",
     "share/doc/installation-report/README.Debian", False),
)
# 参与 build() 语法检查与消费者校验的脚本
SCRIPTS = ("bin/report-hw", "bin/httpd", "bin/usb-list",
           "lib/pre-pkgsel.d/50save-logs", "lib/finish-install.d/94save-logs")


class InstallationReportConan(ConanFile):
    name = "installation-report"
    version = "2.98"
    description = ("Debian installation report tools (report-hw, usb-list, httpd, "
                   "bug report helpers, save-logs hooks) — pure POSIX shell")
    license = "GPL-2.0-or-later"          # debian/copyright: GPL v2 or later
    homepage = "https://salsa.debian.org/installer-team/installation-report"
    url = "https://salsa.debian.org/installer-team/installation-report"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        """无编译、无上游测试 → 只做 shell 语法检查作为构建期证据。"""
        checked = 0
        for rel, _target, executable in PAYLOAD:
            if not executable:
                continue
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration("源码缺少脚本: %s" % rel)
            self.run('sh -n "%s"' % path)
            checked += 1
        self.output.info("[build] shell 语法检查通过：%d 个脚本（上游无测试，通过率 N/A）"
                         % checked)

    def package(self):
        src = self.source_folder
        for rel, target, executable in PAYLOAD:
            source = os.path.join(src, rel)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration("缺少产物源文件: %s" % rel)
            dest = os.path.join(self.package_folder, *target.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(source, dest)
            os.chmod(dest, 0o755 if executable else 0o644)

        # bug/ 子树 → share/bug/（debian/installation-report.install: 「bug usr/share」）
        shutil.copytree(os.path.join(src, "bug"),
                        os.path.join(self.package_folder, "share", "bug"),
                        dirs_exist_ok=True)

        # debian/installation-report.links 声明的软链：
        #   usr/share/installation-report/install-report.template
        #     -> usr/share/doc/installation-report/install-report.template
        link = os.path.join(self.package_folder, "share", "doc",
                            "installation-report", "install-report.template")
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if not os.path.lexists(link):
            os.symlink("../../installation-report/install-report.template", link)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]      # 承载 lib/pre-pkgsel.d 与 lib/finish-install.d
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libs = []
