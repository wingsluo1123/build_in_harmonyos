#!/usr/bin/env python3
"""Conan recipe — wayout 0.1.4 (Wayland desktop text widget, Meson).

wayout reads text from standard input and renders it as a layer-shell desktop
widget on wlroots-based Wayland compositors.  Adapted for OpenHarmony /
HarmonyOS PC (aarch64, clang 15, musl).

OHOS 适配要点（均本机实测）：
  - 上游 meson.build 用 `dependency.get_pkgconfig_variable()`，该 API 在
    Meson 1.6 已移除（本环境 meson 1.11/1.12）→ 补丁 0001/0002 改为
    `get_variable(pkgconfig: ...)`。
  - `dependency('wayland-cursor')` / `dependency('pangocairo')`：Conan 的
    PkgConfigDeps 只按 `pkg_config_name` 生成 .pc（wayland 包只声明
    wayland-client，pango 包只声明 pango），这两个名字缺失 → generate()
    在私有目录里补出桥接 .pc（prefix 指向真实包目录）。
  - `dependency('wayland-scanner', native: true)`：wayland 包自带的 scanner
    带构建机绝对 DT_NEEDED 且未签名，HMFS 上直接执行 EPERM → staging 后
    patchelf 改写为 soname、重签名，再用 wrapper 注入 LD_LIBRARY_PATH。
  - wayland-protocols 的 `pkgdatadir` 由 .pc 承载 → 桥接 .pc 直接给出包内
    share/wayland-protocols 路径。
  - Meson 在 OHOS 上对裸名 subprocess 查找报 ENOENT → 机器文件注入
    pkg-config / ninja / ar / ranlib 绝对路径。
  - 产物 ELF 自签名（HMFS 未签名 ELF 不可执行）。

上游测试：无（仓库无 tests/ 目录，meson.build 无 test() 注册）—— 见
notes.md 的核验证据表与 test_package/MANIFEST.yml。
"""
import glob
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

HNP_BIN = "/data/service/hnp/bin"
PATCHELF = os.path.join(HNP_BIN, "patchelf")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
READELF = os.path.join(HNP_BIN, "llvm-readelf")
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")

# name -> (bridge .pc body template, )
SCANNER_TOOL = "wayland-scanner"


class WayoutConan(ConanFile):
    name = "wayout"
    version = "0.1.4"
    description = ("Wayland desktop text widget: renders stdin (feeds) on a "
                   "layer-shell surface")
    license = "GPL-3.0-or-later"
    homepage = "https://git.sr.ht/~proycon/wayout"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wayout 0.1.4 only supports Linux/OHOS, got {self.settings.os}")

    def requirements(self):
        # meson.build: wayland-protocols, wayland-client, wayland-cursor,
        # cairo, pangocairo (+ rt/m).
        self.requires("wayland/1.24.0")
        self.requires("wayland-protocols/1.48")
        self.requires("cairo/1.18.4.2")
        self.requires("pango/1.58.2")
        # wayland/1.24.0 requires expat/2.8.2 while the pango→fontconfig chain
        # uses expat/2.8.2.1; unify on the published 2.8.2.1 binary (wayland's
        # package_id does not depend on the expat version — verified with
        # `conan install --build=never`).
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        # Worker-global meson is not guaranteed (cairo/pango precedent).
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ──────────────────────────────────────────────────────────────
    # generate
    # ──────────────────────────────────────────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._stage_wayland_scanner()
        pc_dir = self._write_bridge_pc(tools_folder)

        tc = MesonToolchain(self)
        tc.pkg_config_path = os.pathsep.join(
            [pc_dir, tc.pkg_config_path or ""])
        tc.project_options.update({
            "man-pages": "disabled",
            "wrap_mode": "nodownload",
        })
        tc.generate()
        self._inject_meson_binaries()
        self._build_environment().vars(self).save_script("wayout_build_env")

    def _pc_dir(self):
        path = os.path.join(self.generators_folder, "wayout_pkgconfig")
        os.makedirs(path, exist_ok=True)
        return path

    def _write_bridge_pc(self, tools_folder):
        """桥接 PkgConfigDeps 不生成的三个 .pc（wayland-cursor / pangocairo /
        wayland-scanner）与带 pkgdatadir 的 wayland-protocols（wdisplays 的
        gdk-3.0.pc 同款手法）。

        包内自带的 .pc 用 `prefix=/` 安装，绝对路径不可用；这里按真实包目录
        重新生成。
        """
        pc_dir = self._pc_dir()
        wayland = self.dependencies.host["wayland"]
        pango = self.dependencies.host["pango"]
        protocols = self.dependencies.host["wayland-protocols"]

        wayland_prefix = wayland.package_folder.replace(os.sep, "/")
        pango_prefix = pango.package_folder.replace(os.sep, "/")
        protocols_prefix = protocols.package_folder.replace(os.sep, "/")

        files = {
            "wayland-cursor.pc": (
                f"prefix={wayland_prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                "Name: Wayland Cursor\n"
                "Description: Wayland cursor helper library\n"
                f"Version: {wayland.ref.version}\n"
                "Requires.private: wayland-client\n"
                "Libs: -L${libdir} -lwayland-cursor\n"
                "Cflags: -I${includedir}\n"
            ),
            "pangocairo.pc": (
                f"prefix={pango_prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                "Name: Pango Cairo\n"
                "Description: Cairo rendering support for Pango\n"
                f"Version: {pango.ref.version}\n"
                "Requires: pango, cairo\n"
                "Libs: -L${libdir} -lpangocairo-1.0\n"
                "Cflags: -I${includedir}/pango-1.0\n"
            ),
            "wayland-scanner.pc": (
                f"prefix={tools_folder.replace(os.sep, '/')}\n"
                "bindir=${prefix}\n"
                "wayland_scanner=${bindir}/" + SCANNER_TOOL + "\n\n"
                "Name: Wayland Scanner\n"
                "Description: Wayland scanner\n"
                f"Version: {wayland.ref.version}\n"
            ),
            "wayland-protocols.pc": (
                f"prefix={protocols_prefix}\n"
                "datarootdir=${prefix}/share\n"
                "pkgdatadir=${datarootdir}/wayland-protocols\n\n"
                "Name: Wayland Protocols\n"
                "Description: Wayland protocol files\n"
                f"Version: {protocols.ref.version}\n"
            ),
        }
        for name, body in files.items():
            with open(os.path.join(pc_dir, name), "w",
                      encoding="utf-8", newline="\n") as handle:
                handle.write(body)
        return pc_dir

    def _tool_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _stage_wayland_scanner(self):
        """Staging wayland 包的 wayland-scanner，使其可在 HMFS 上执行。

        实测（本机 aarch64 OHOS）：包内 bin/wayland-scanner
          1. 直接执行报 EPERM（HMFS 未签名 ELF 不可执行）；
          2. DT_NEEDED 记录构建机绝对路径（.../.cache/conan2/p/expat*/p/lib/
             libexpat.so），loader 不查 LD_LIBRARY_PATH。
        顺序必须是：拷贝 → patchelf 改写绝对 NEEDED 为 soname → 重签名
        （patchelf 会破坏签名）→ wrapper 注入依赖 lib 目录。
        """
        tools_folder = self._tool_folder()
        os.makedirs(tools_folder, exist_ok=True)
        dep = self.dependencies.host["wayland"]
        src = os.path.join(dep.package_folder, "bin", SCANNER_TOOL)
        if not os.path.isfile(src):
            raise ConanInvalidConfiguration(
                f"wayland package does not ship {SCANNER_TOOL} ({src})")

        real = os.path.join(tools_folder, f"{SCANNER_TOOL}.elf")
        shutil.copyfile(src, real)
        os.chmod(real, 0o755)
        if os.path.isfile(PATCHELF):
            for entry in self._absolute_needed(real):
                self.run(
                    f"{shlex.quote(PATCHELF)} --replace-needed "
                    f"{shlex.quote(entry)} {shlex.quote(os.path.basename(entry))} "
                    f"{shlex.quote(real)}")
        if str(self.settings.os) == "OHOS":
            self._resign_elf(real)

        lib_dirs = self._dependency_lib_dirs()
        wrapper = os.path.join(tools_folder, SCANNER_TOOL)
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\n")
            if lib_dirs:
                handle.write(
                    "export LD_LIBRARY_PATH=" + ":".join(lib_dirs)
                    + "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n")
            handle.write(f"exec {shlex.quote(real)} \"$@\"\n")
        os.chmod(wrapper, 0o755)
        return tools_folder

    def _dependency_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    dirs.append(libdir)
        return dirs

    def _absolute_needed(self, binary):
        """列出 ELF 中以绝对路径记录的 DT_NEEDED（构建机缓存路径残留）。"""
        if not os.path.isfile(READELF):
            return []
        try:
            out = subprocess.run([READELF, "-d", binary], capture_output=True,
                                 text=True).stdout
        except Exception:
            return []
        return re.findall(r"NEEDED.*Shared library: \[(/[^\]]+)\]", out)

    def _resign_elf(self, binary):
        """HMFS 执行限制规避：移除 .codesign 段后 selfSign 重签。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]),
                     quiet=True)

    def _inject_meson_binaries(self):
        """meson 机器文件注入 ar/ranlib/pkg-config/ninja 绝对路径。

        OHOS 上 Python subprocess 对裸名查找报 ENOENT（wdisplays/cairo 同款）。
        """
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if cdir:
            if not ar:
                cand = os.path.join(cdir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
            if not ranlib:
                cand = os.path.join(cdir, "llvm-ranlib")
                if os.path.isfile(cand):
                    ranlib = cand
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        ninja = shutil.which("ninja") or os.path.join(HNP_BIN, "ninja")

        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            ini = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(ini):
                continue
            with open(ini, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            additions = []
            if ar and "\nar = " not in content:
                additions.append(f"ar = '{ar}'")
            if ranlib and "\nranlib = " not in content:
                additions.append(f"ranlib = '{ranlib}'")
            if pkg_config and ("\npkg-config = " not in content
                               and "\npkgconfig = " not in content):
                additions.append(f"pkg-config = '{pkg_config}'")
            if ninja and os.path.isfile(ninja) and "\nninja = " not in content:
                additions.append(f"ninja = '{ninja}'")
            if not additions:
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n" + "\n".join(additions) + "\n", 1)
            with open(ini, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)
        for libdir in self._dependency_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        # 最后 prepend ⇒ 工具目录排在 PATH 最前（覆盖 wayland 包 bin/ 里
        # 无法在 HMFS 上执行的原始 scanner）
        env.prepend_path("PATH", self._tool_folder())
        env.prepend_path("PKG_CONFIG_PATH", self._pc_dir())
        ninja = shutil.which("ninja") or os.path.join(HNP_BIN, "ninja")
        if os.path.isfile(ninja):
            env.define("NINJA", ninja)
        return env

    # ──────────────────────────────────────────────────────────────
    # build / package
    # ──────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) == "OHOS":
            for binary in sorted(glob.glob(
                    os.path.join(self.package_folder, "bin", "*"))):
                if os.path.isfile(binary) and not os.path.islink(binary):
                    self._resign_elf(binary)

    def package_info(self):
        # 应用包：只交付 bin/wayout（+ man page 目录留空，man-pages 关闭）
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
