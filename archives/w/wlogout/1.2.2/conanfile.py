#!/usr/bin/env python3
"""Conan recipe — wlogout 1.2.2 (meson)

wlogout is a wayland logout menu (ArtsyMacaw/wlogout, MIT) — a single
main.c GTK3 application with a bundled jsmn JSON parser.

OHOS adaptation:
- The gtk/3.24.43 conan package (merged) is a broadway-only build: it
  ships gtk+-3.0.pc / gtk+-broadway-3.0.pc but no gtk+-wayland-3.0.pc.
  Patch 0001 switches the meson dependency to the generic gtk+-3.0 so
  the build links whichever GDK backend the toolkit provides.
- gtk-layer-shell stays optional (upstream `required : false`): it is
  not packaged for OHOS, so the LAYERSHELL code paths compile out via
  the undefined macro (upstream #ifdef guard, no source changes).
- Patch 0002 moves process_args() ahead of gtk_init() in main(): the
  upstream order exits with "cannot open display" on headless runs
  before the CLI parser ever sees --version/--help. Normal GUI startup
  is unchanged (gtk_init still runs after a non-exiting process_args).
- man-pages disabled (-Dman-pages=disabled): scdoc is not packaged.
- Upstream has no test suite (no tests/ dir, no test() in meson.build —
  audited in test_package/MANIFEST.yml); consumer smoke cases
  (--version/-v/--help/-h) run in the test_package phase.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class WlogoutConan(ConanFile):
    name = "wlogout"
    version = "1.2.2"
    description = "Wayland logout menu (GTK3)"
    license = "MIT"
    homepage = "https://github.com/ArtsyMacaw/wlogout"
    url = "https://github.com/ArtsyMacaw/wlogout"
    topics = ("wayland", "logout", "gtk", "menu")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # GTK3（broadway-only 构建；patch 0001 把 meson 依赖从
        # gtk+-wayland-3.0 切到通用 gtk+-3.0）。
        self.requires("gtk/3.24.43")

    def validate(self):
        # R32: settings.os check must use in (Linux, OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wlogout supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # meson dependency('gtk+-3.0') 经 pkg-config 解析：gtk recipe 的
        # pkg_config_name="gtk+-3.0" 由 PkgConfigDeps 生成 .pc 并接线
        # （aris/2.2 先例——只给 MesonToolchain 时 meson 报
        # "Dependency gtk+-3.0 not found"）。
        from conan.tools.env import Environment
        from conan.tools.gnu import PkgConfigDeps
        PkgConfigDeps(self).generate()
        # conan 包 .pc 的 prefix 指向 build 侧路径；重写后置顶注入
        # （wayland/1.22.0 先例范式）。
        import re as _re
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        gtk = self.dependencies["gtk"]
        pc_src = os.path.join(gtk.package_folder, "lib", "pkgconfig",
                              "gtk+-3.0.pc")
        if os.path.isfile(pc_src):
            os.makedirs(fixed_pc_dir, exist_ok=True)
            with open(pc_src, "r", encoding="utf-8") as f:
                content = f.read()
            content = _re.sub(r"(?m)^prefix=.*$",
                              f"prefix={gtk.package_folder}", content)
            with open(os.path.join(fixed_pc_dir, "gtk+-3.0.pc"), "w",
                      encoding="utf-8", newline="\n") as f:
                f.write(content)
        tc = MesonToolchain(self)
        # scdoc 不在制品仓——禁 man 页生成；completions 照装（纯数据文件）。
        tc.project_options["man-pages"] = "disabled"
        # 上游 werror=true 会对 clang 15 的非致命警告炸构建（broadway
        # 路径的 unused-parameter 类）；保留其余上游警告开关。
        tc.project_options["werror"] = "false"
        if os.path.isdir(fixed_pc_dir):
            tc.pkg_config_path = os.pathsep.join(
                [tc.pkg_config_path, fixed_pc_dir]
                if tc.pkg_config_path else [fixed_pc_dir]
            )
        tc.generate()
        # CI #91760: meson 探测 archiver 时用裸名 llvm-ar，CI worker 的
        # PATH 找不到（"Unknown linker(s): [['llvm-ar']]"，meson-log:
        # Running `llvm-ar --version` -> ENOENT）。把 [binaries] 的 ar
        # 钉到 binutils GNU ar 绝对路径（wayland/1.22.0 native-file
        # 注入先例）。
        ar_path = shutil.which("ar") or "/data/service/hnp/bin/ar"
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        if os.path.isfile(native_file):
            with open(native_file, encoding="utf-8") as f:
                content = f.read()
            if _re.search(r"(?m)^ar\s*=", content):
                content = _re.sub(r"(?m)^ar\s*=.*$",
                                  "ar = '%s'" % ar_path, content)
            else:
                content = content.replace(
                    "[binaries]\n",
                    "[binaries]\nar = '%s'\n" % ar_path, 1)
            with open(native_file, "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    @staticmethod
    def _sign_elf(path):
        """OHOS ELF codesign (wlopm/1.0.0 + kakoune-lsp/21.0.2 precedent)
        — unconditional self-sign so the packaged binary is executable
        by the test_package phase on any worker."""
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool not found")
        tmp = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp,
             "-selfSign", "1"], check=True, timeout=60)
        os.chmod(tmp, 0o755)
        os.replace(tmp, path)

    def package(self):
        meson = Meson(self)
        meson.install()
        binpath = os.path.join(self.package_folder, "bin", "wlogout")
        if not os.path.isfile(binpath):
            raise ConanInvalidConfiguration(
                "meson install produced no bin/wlogout under %s"
                % self.package_folder)
        self._sign_elf(binpath)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["gtk::gtk"]
