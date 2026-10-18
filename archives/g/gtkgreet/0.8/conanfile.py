#!/usr/bin/env python3
"""Conan recipe — gtkgreet 0.8 (GTK greeter client for greetd, Meson).

OHOS 适配要点（本地实测，详见 notes.md）：
  - 构建系统: meson（上游 meson.build，c_std=c11 + werror=true）
  - 依赖: gtk/3.24.43（broadway 后端 OHOS binary）、json-c/0.18；
    gettext/0.22.5.1 仅提供构建期 msgfmt（po/ 的 i18n.gettext）
  - gtk-layer-shell 与 scdoc 制品仓未发布 ⇒ 显式 -Dlayershell=disabled、
    -Dman-pages=disabled（上游 auto 语义：找不到即跳过，配方显式化）
  - 制品仓 gtk/3.24.43 的 glib-2.0.pc 缺 -lintl，链接期 undefined
    symbol（glib 2.84 的 g_libintl_* 在 libintl.so）⇒ 在 generate()
    里把 -lintl 补进 PkgConfigDeps 生成的 glib-2.0.pc（gtk/glade 同款）
  - OHOS 下对 bin/ ELF 自签（HMFS 未签名 ELF 不可执行）
  - 上游无测试套件（无 test/ 目录），test_package 做可执行性冒烟
"""
import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")


class GtkgreetConan(ConanFile):
    name = "gtkgreet"
    version = "0.8"
    description = "GTK based greeter for greetd (greeter client speaking the greetd IPC protocol)"
    license = "GPL-3.0-or-later"
    homepage = "https://sr.ht/~kennylevinsen/gtkgreet"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # gtk/3.24.43 已发布 OHOS binary（broadway 后端）；json-c 上游
        # gtkgreet/meson.build 直接 dependency('json-c')。
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("json-c/0.18", transitive_headers=True, transitive_libs=True)
        # po/ 的 i18n.gettext 需要构建期 msgfmt（制品仓 gettext 提供 bin/msgfmt）
        self.requires("gettext/0.22.5.1")

    def build_requirements(self):
        # meson 从 ohpcd 工具包取（glade 同款），避免依赖 worker 全局 meson；
        # 本机实测 meson 不在 PATH 上（rc=127），remote 上 meson/1.11.0 已发布。
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._patch_libintl()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "layershell": "disabled",
            "man-pages": "disabled",
        })
        tc.generate()
        self._inject_meson_tools()
        env = Environment()
        # msgfmt（i18n.gettext）：host requires 的 bin 不进 build PATH，显式前置
        env.prepend_path("PATH", os.path.join(
            self.dependencies["gettext"].package_folder, "bin"))
        env.vars(self).save_script("conanbuildenv-gtkgreet-tools")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ──────────────────────────────────────────────────────────────
    def _patch_libintl(self):
        """glib 2.84 的 g_libintl_* 符号在 libintl.so；PkgConfigDeps 生成的
        glib-2.0.pc 的 Libs 缺 -lintl ⇒ 链接 undefined symbol（glade 同款）。"""
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        content = open(pc, encoding="utf-8").read()
        if "-lintl" in content:
            return
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        open(pc, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _inject_meson_tools(self):
        """裸名 subprocess 在部分 worker 上 ENOENT ⇒ 显式写 ar/ranlib/
        pkg-config/ninja 绝对路径进 machine file（gtk/glade 同款守则）。"""
        import shutil
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = ce.get("ar") or (os.path.join(cdir, "llvm-ar") if cdir else None)
        ranlib = ce.get("ranlib") or (os.path.join(cdir, "llvm-ranlib") if cdir else None)
        if ar and not os.path.isfile(ar):
            ar = None
        if ranlib and not os.path.isfile(ranlib):
            ranlib = None
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        ninja = shutil.which("ninja")
        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf):
                continue
            content = open(nf, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            add = []
            if ar and "\nar =" not in content:
                add.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                add.append(f"ranlib = '{ranlib}'")
            if pkg_config and ("\npkg-config =" not in content
                               and "\npkgconfig =" not in content):
                add.append(f"pkg-config = '{pkg_config}'")
            if ninja and "\nninja = " not in content:
                add.append(f"ninja = '{ninja}'")
            if not add:
                continue
            content = content.replace("[binaries]\n",
                                      "[binaries]\n" + "\n".join(add) + "\n", 1)
            open(nf, "w", encoding="utf-8", newline="\n").write(content)

    def _sign_installed_elfs(self):
        """OHOS 签名（HMFS 上未签名 ELF 不可执行）。单次 selfSign 对刚安装
        的文件可能无效，故对每个 ELF 做两轮 remove-section + selfSign。"""
        if not os.path.isfile(SIGN_TOOL):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        targets = []
        for pattern in (os.path.join(self.package_folder, "bin", "*"),
                        os.path.join(self.package_folder, "lib", "**", "*.so*")):
            targets.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(targets)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            for _round in (1, 2):
                if os.path.isfile(OBJCOPY):
                    self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                             f"{shlex.quote(binary)} 2>/dev/null || true")
                self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                     "-outFile", binary, "-selfSign", "1"]))
