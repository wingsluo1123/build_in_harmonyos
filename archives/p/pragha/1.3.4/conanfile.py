#!/usr/bin/env python3
"""Conan recipe — pragha 1.3.4 (Autotools GTK3 music player, HarmonyOS PC aarch64).

- 上游: https://github.com/pragha-music-player/pragha (tag v1.3.4)
- 构建: 上游随附生成的 autotools 文件（configure/Makefile.in 齐备，无需 autoreconf）
- 硬依赖 (configure.ac XDT_CHECK_PACKAGE): gstreamer-1.0 / gstreamer-base-1.0 /
  gio-2.0 / gtk+-3.0 / sqlite3 / taglib_c
- 可选依赖 (XDT_CHECK_OPTIONAL_PACKAGE, 全部 --disable): libpeas/插件子系统、
  libnotify、keybinder、libglyr、gudev、libmtp、libsoup、rygel、grilo、
  libclastfm、libcdio 系、gstreamer-audio、libxfce4ui、totem-plparser

OHOS 适配要点:
  * config.guess/config.sub 补丁识别 aarch64-unknown-linux-ohos（2018 年版本）。
  * configure 临时目录 umask 077→022（HMDFS setgid 语义拒绝 0700 目录）。
  * intltool/gettext 探针用 recipe 内 shim 应答（configure 硬性要求 intltool 三件套，
    但 --disable-nls 后构建期唯一真实调用是 data/ 的 INTLTOOL_DESKTOP_RULE ——
    intltool-merge shim 真实产出 pragha.desktop，非空壳 exit 0）。
  * glib 为 musl proxy-libintl 构建，glib-2.0.pc 追加 -lintl（sound-juicer 同模式）。
  * gstreamer 包 pc 名为 gstreamer（无 -1.0 后缀），生成 gstreamer-1.0.pc /
    gstreamer-base-1.0.pc 重定向（sound-juicer 同模式）。
  * gtk 图(glib/2.84.0.1) 与 gstreamer 图(glib2/2.88.0) 的 zlib 需求以 force 对齐。
  * 无 X 服务：完整编译安装应用 + 自签名，运行期验证走无头路径
    （--version / --help / --selftest，selftest 在 GTK 窗口激活前执行）。
  * 上游无自动化测试（全仓无 check_PROGRAMS/TESTS，见 notes.md 清点证据），
    --selftest 为本适配新增的鸿蒙消费者用例。
"""
import os
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class PraghaConan(ConanFile):
    name = "pragha"
    version = "1.3.4"
    description = "Pragha — a lightweight GTK+ music player (headless-validated OHOS port)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/pragha-music-player/pragha"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pragha supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def requirements(self):
        # 硬依赖：configure.ac XDT_CHECK_PACKAGE 必需集
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("gstreamer/1.28.3", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite3/3.53.4", transitive_headers=True, transitive_libs=True)
        self.requires("taglib/1.13.1", transitive_headers=True, transitive_libs=True)
        # gtk 钉 glib/2.84.0.1(zlib 1.3.1.1)，gstreamer 钉 glib2/2.88.0(zlib 1.3.1)
        # —— force 对齐 zlib 使依赖图可解（sound-juicer 同模式）。
        self.requires("zlib/1.3.1.1", force=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── intltool/gettext 探针 shim（activity-log 同模式） ──────────────────

    def _write_i18n_tool_shims(self):
        """configure 的 IT_PROG_INTLTOOL/XDT_I18N 宏即使 --disable-nls 也硬性
        探测 intltool-update/merge/extract 与 gettext 工具。OHOS worker 无
        Perl/ gettext，用 shim 应答版本探针；intltool-merge 按真实语义产出
        .desktop 文件（INTLTOOL_DESKTOP_RULE 是构建期唯一真实调用）。"""
        shim_dir = os.path.join(self.build_folder, "ohos-build-tools")
        os.makedirs(shim_dir, exist_ok=True)
        scripts = {
            "intltool-update": (
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "  --version) echo 'intltool-update (intltool) 0.51.0' ;;\n"
                "esac\n"
                "exit 0\n"
            ),
            "intltool-extract": "#!/bin/sh\nexit 0\n",
            "intltool-merge": (
                "#!/bin/sh\n"
                "# Real semantics for INTLTOOL_DESKTOP_RULE: the last two args\n"
                "# are <input(.desktop.in)> <output(.desktop)>; the merge with an\n"
                "# empty translation set is the input with _-prefixed keys stripped.\n"
                "prev=\"\"\n"
                "for arg in \"$@\"; do input=\"$prev\"; output=\"$arg\"; prev=\"$arg\"; done\n"
                "if [ -z \"$output\" ] || [ \"$input\" = \"$output\" ] || [ ! -f \"$input\" ]; then\n"
                "  exit 0\n"
                "fi\n"
                "sed 's/^_//' \"$input\" > \"$output\"\n"
                "exit 0\n"
            ),
            "msgmerge": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgmerge (GNU gettext-tools) 0.22'\n"
                "fi\n"
                "exit 0\n"
            ),
            "xgettext": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'xgettext (GNU gettext-tools) 0.22'\n"
                "fi\n"
                "exit 0\n"
            ),
            "msgfmt": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgfmt (GNU gettext-tools) 0.22'\n"
                "fi\n"
                "exit 0\n"
            ),
            "gmsgfmt": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgfmt (GNU gettext-tools) 0.22'\n"
                "fi\n"
                "exit 0\n"
            ),
        }
        for name, content in scripts.items():
            path = os.path.join(shim_dir, name)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return shim_dir

    def _write_redirect_pkgconfig(self, alias_name, source_name):
        """PkgConfigDeps 生成 gstreamer.pc（conan 包名），而 configure 探测
        gstreamer-1.0 / gstreamer-base-1.0 —— 写入指向 gstreamer.pc 的重定向
        （gstreamer 包 cpp_info.libs 已含 -lgstbase-1.0 等全部核心库）。"""
        alias_pc = os.path.join(self.generators_folder, f"{alias_name}.pc")
        if os.path.isfile(alias_pc):
            return
        source_pc = os.path.join(self.generators_folder, f"{source_name}.pc")
        if not os.path.isfile(source_pc):
            raise ConanException(f"expected generated pc file: {source_pc}")
        with open(alias_pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"Name: {alias_name}\n"
                f"Description: {alias_name} (OHOS redirect to conan package pc: {source_name})\n"
                f"Version: {self.dependencies['gstreamer'].ref.version}\n"
                f"Requires: {source_name}\n"
            )

    def _augment_glib_pkgconfig_lintl(self):
        """glib 以 proxy-libintl 构建：g_libintl_* 符号在 libintl.so，生成的
        glib-2.0.pc 不传播，消费者链接 gettext 助手时需 -lintl（sound-juicer /
        gtk 配方同模式）。"""
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        with open(glib_pc, encoding="utf-8") as handle:
            lines = handle.read().splitlines(keepends=True)
        out = []
        for line in lines:
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            out.append(line)
        with open(glib_pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(out))

    def _augment_taglibc_pkgconfig(self):
        """pragha 源码 `#include <tag_c.h>`，上游真实 taglib_c.pc 的
        Cflags 为 `-I${includedir}/taglib`；conan 包头文件布局为
        include/taglib/tag_c.h，PkgConfigDeps 生成的 pc 只有 include 根。
        按上游语义把 taglib 子目录并入既有 Cflags 行（pc 不允许重复
        Cflags 关键字，pkg-config 解析失败会使整个包"not found"）。"""
        taglib_c_pc = os.path.join(self.generators_folder, "taglib_c.pc")
        if not os.path.isfile(taglib_c_pc):
            return
        taglib = self.dependencies["taglib"]
        taglib_sub = None
        for inc in taglib.cpp_info.aggregated_components().includedirs:
            inc_dir = inc if os.path.isabs(inc) else os.path.join(taglib.package_folder, inc)
            candidate = os.path.join(inc_dir, "taglib")
            if os.path.isfile(os.path.join(candidate, "tag_c.h")):
                taglib_sub = candidate.replace(os.sep, "/")
                break
        if taglib_sub is None:
            raise ConanException("tag_c.h not found under taglib package include dirs")
        with open(taglib_c_pc, encoding="utf-8") as handle:
            lines = handle.read().splitlines(keepends=True)
        out = []
        for line in lines:
            if line.startswith("Cflags:") and taglib_sub not in line:
                line = line.rstrip("\r\n") + f" -I{taglib_sub}\n"
            out.append(line)
        with open(taglib_c_pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(out))

    # ── E236：.la 元数据隔离（activity-log 同模式，扩展为全依赖镜像） ──────

    def _stage_dependency_libraries(self):
        """把全部宿主依赖库镜像进 la-free 目录（只复制 lib*.a / lib*.so*，
        排除 .la 元数据）。pragha 经 LT_INIT 链接，依赖包 .la 的 stale
        dependency_libs（'//lib/libpcre2-8.la' 等）会毒化 libtool 解析；
        同时本图存在 glib(shared) 与 glib2(static) 双提供者，目录顺序
        会让 ld 优先拾取 glib2 的静态 libglib-2.0.a，与 gtk 运行期加载的
        共享 libglib-2.0.so 形成双 glib 实例（GObject 启动即 abort）。
        全量镜像后所有 pc libdir 指向同一目录：ld 在同目录内 .so 优先
        于 .a，共享 glib 必然胜出，静态 gstreamer/sqlite3/taglib 照常解析。"""
        stage_dir = os.path.join(self.build_folder, "dependency-libs")
        os.makedirs(stage_dir, exist_ok=True)

        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for name in sorted(os.listdir(lib_dir)):
                if not name.startswith("lib") or name.endswith(".la"):
                    continue
                if not (name.endswith(".a") or ".so" in name):
                    continue
                source = os.path.join(lib_dir, name)
                if not os.path.isfile(source):
                    continue
                target = os.path.join(stage_dir, name)
                if os.path.exists(target):
                    continue
                shutil.copy2(source, target)

        return stage_dir

    def _rewrite_generated_pkgconfig_libdirs(self, stage_dir):
        """Point every generated pkg-config file's libdir at the la-free
        staging directory (same-name .so preferred over .a by ld)."""
        stage_posix = stage_dir.replace(os.sep, "/")
        for name in os.listdir(self.generators_folder):
            if not name.endswith(".pc"):
                continue
            path = os.path.join(self.generators_folder, name)
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                for line in lines:
                    if line.startswith("libdir="):
                        line = "libdir=%s\n" % stage_posix
                    handle.write(line)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_redirect_pkgconfig("gstreamer-1.0", "gstreamer")
        self._write_redirect_pkgconfig("gstreamer-base-1.0", "gstreamer")
        self._augment_glib_pkgconfig_lintl()
        self._augment_taglibc_pkgconfig()
        shim_dir = self._write_i18n_tool_shims()
        # E236 + 双 glib 提供者对齐：全部依赖库镜像进 la-free staging，
        # 所有生成 pc 的 libdir 指向 staging（详见 _stage_dependency_libraries）。
        stage_dir = self._stage_dependency_libraries()
        self._rewrite_generated_pkgconfig_libdirs(stage_dir)

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        environment.prepend_path("PATH", shim_dir)
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        toolchain.generate(env=environment)

    # ── 构建与安装 ────────────────────────────────────────────────────────

    def _restore_autotools_script_modes(self):
        """E490：部分 HMDFS 适配路径保存源码内容时不保留 +x 位，
        autotools 助手脚本需要可执行权限才能被 configure/make 调用。"""
        for name in ("configure", "config.guess", "config.sub",
                     "install-sh", "missing", "compile", "depcomp"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _configure_options(self):
        return [
            "--prefix=/",
            "--disable-nls",
            "--disable-libpeas-1.0",
            "--disable-libnotify",
            "--disable-keybinder",
            "--disable-libglyr",
            "--disable-gudev-1.0",
            "--disable-libmtp",
            "--disable-libsoup-2.4",
            "--disable-rygel-server-2.6",
            "--disable-grilo-0.3",
            "--disable-grilo-0.2",
            "--disable-libclastfm",
            "--disable-libcdio",
            "--disable-libcdio_paranoia",
            "--disable-libcddb",
            "--disable-gstreamer-audio",
            "--disable-libxfce4ui",
            "--disable-totem-plparser",
        ]

    def _run_ohos_configure(self):
        """HMDFS 上 getcwd()/权限语义使 configure 探测不可靠（bluefish 同模式）：
        用 /system/bin/sh 内联执行，CONFIG_SHELL/SHELL 显式固定。"""
        configure_script = os.path.join(self.source_folder, "configure")
        options = self._configure_options()
        command = (
            "CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
            + shlex.join(["/system/bin/sh", configure_script] + options)
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        # E490 预防：HMDFS 适配路径可能丢失 autotools 脚本可执行位
        self._restore_autotools_script_modes()
        # HNP bash 在 conan 切换 cwd 后调用 getcwd() 会失败（HMDFS）；
        # 导出真实构建路径让 autoconf 保持 cwd（activity-log 同模式）。
        os.environ["PWD"] = str(self.build_folder)
        if self.settings.os == "OHOS":
            self._run_ohos_configure()
        else:
            Autotools(self).configure()
        Autotools(self).make(args=["-j1"])
        # 上游无 check_PROGRAMS/TESTS（notes.md 清点证据）；automake 的
        # check-recursive 仅为空跑。仍执行以留存真实上游测试入口证据。
        Autotools(self).make(target="check", args=["-j1"])

    def package(self):
        destination = shlex.quote(self.package_folder)
        self.run(
            f"make -j1 install DESTDIR={destination}",
            cwd=self.build_folder,
            env="conanbuild",
        )
        self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "pragha"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # 应用包：无库文件供下游链接，仅 bin 目录
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ── OHOS ELF 自签名（bluefish 同模式） ────────────────────────────────

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing executable to sign: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
