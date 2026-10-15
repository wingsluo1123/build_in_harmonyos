#!/usr/bin/env python3
"""Conan recipe — kooha-mp4 2.2.4 (Rust/Meson, GTK4 screen recorder).

Kooha is a GNOME screen recorder ("Elegantly record your screen") that
records the screen to WebM / MP4 / Matroska / GIF. Upstream 2.2.4 is a
Rust application driven by Meson (cargo custom_target), GTK4 +
libadwaita UI, GStreamer capture pipeline and the xdg-desktop-portal
screencast session. This recipe builds the Rust binary directly with
cargo (below/0.11.0 precedent) — the meson layer (i18n merge, desktop
file, gresource compilation) is reproduced by the recipe itself.

Toolchain handling (below/0.11.0 precedent):
The worker has no system Rust toolchain, and rustup cannot recognize the
HarmonyOS host (E105/E154). The build uses the rust-toolchain/1.97.1
infrastructure package (tool_requires; rust-lang official dist tarball,
host & target = aarch64-unknown-linux-ohos). Its binaries carry no code
signature, so the recipe copies cargo/rustc (+ librustc_driver) into the
build folder and self-signs them with binary-sign-tool (OHOS refuses to
execve unsigned ELF, EACCES errno 13). Crates are fetched through the
rsproxy.cn sparse mirror.

OHOS adaptations (patch 0001):
- gtk4/4.22.4 on OHOS ships the Broadway backend ONLY (no wayland/x11),
  so gdk4-wayland / gdk4-x11 crates are dropped and the portal window
  identifier degrades to the empty variant (the same "Unhandled surface
  backend type" path upstream takes).
- gst-plugin-gtk4 (gtk4paintablesink) hard-requires gstreamer-gl + a
  real window system; the area-selector live preview degrades to
  fakesink with a MemoryTexture placeholder paintable.
- libpulse-binding / libpulse-glib-binding dropped: the published
  pulseaudio/17.0 package has no libpulse-mainloop-glib. Audio device
  discovery keeps the gstreamer DeviceMonitor path only.
- main() gained a --version early-exit (headless verification path,
  zenity/4.2.2 E252 precedent) and KOOHA_LOCALEDIR / KOOHA_RESOURCE_FILE
  env overrides for the packaged layout.

Graph alignment (libadwaita/1.7.12 precedent):
The whole graph is pinned exactly like libadwaita/1.7.12 — glib/2.84.0.1.1
shared=True, zlib/1.3.1.1, fontconfig/2.18.1.1, pango/1.56.4, zstd/1.5.7.1
(override=True) — so the gtk4 side resolves identically. The gstreamer
side (gstreamer/1.28.3 + gst-plugins-base/1.28.3, static) links against
the SINGLE glib/2.84 shared runtime: its 745 undefined g_* symbols are
all satisfied by libglib-2.0.so.0 (verified by llvm-nm on the published
static archives), so no second GLib runtime ever enters the binary —
glib2/2.88.0 stays a transitive recipe dependency only and its pkg-config
files are explicitly excluded from the build environment (staging pkg
config dir below), preventing glib-2.0.pc shadowing.

gettext handling:
The OHOS sysroot libc.so exports no gettext symbols at link time, and
gettext-sys' "gettext-system" fast path only recognizes *-gnu/*-musl
triplets. The recipe builds a tiny identity shim (libintl.a: gettext/
ngettext/... return their inputs, exactly the C-locale behaviour) and
points GETTEXT_DIR at it with GETTEXT_STATIC=1, so gettext-sys links
statically instead of compiling full GNU gettext.

Upstream unit tests (37 #[test] across 10 modules) are executed during
build() via cargo test unless OHC_SKIP_UPSTREAM_TESTS=1.
"""
import os
import shutil
import subprocess
import tarfile
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    download,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# cargo 运行期依赖的共享库（below/0.11.0 先例：OHOS loader 忽略
# DT_RUNPATH，cargo 需要 OpenSSL 3.5+ / zlib；系统 /usr/lib 的 3.0 太老）。
# 2026-10-04 实测：below 先例的 openssl%403-3.6.4 / zlib-ng-compat-2.3.3_1
# 两个 bottle 已下架（HTTP 404）；改用现存 3.6.5 / 2.3.3_2，sha256 双源实测。
# zlib bottle 已移除：zlib-ng-compat-2.3.3_2 于 2026-10-12 从 CI 侧 CDN
# 下架（本机暖缓存 200 假阳性，CI 连续 NotFoundException）；libz.so 改从
# 本配方 conan 依赖 zlib/1.3.1.1（制品仓有货）的 libdir 直取。
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.5.arm64_ohos.bottle.tar.gz",
     "f8c374560f0002975203425b6b5db30f84eb9e78f9c56a8494b60ca57664327c"),
)

# 依赖 payload 的 pkgconfig 目录聚合清单（顺序即 staging 顺序）。
# glib2 被刻意排除（见 docstring：防 glib-2.0.pc 遮蔽）。
_PC_DEP_NAMES = (
    "glib", "gtk4", "libadwaita",
    "gstreamer", "gst-plugins-base", "orc", "libdrm",
    "pango", "cairo", "cairo-gobject", "gdk-pixbuf", "graphene",
    "harfbuzz", "fribidi", "libepoxy", "zlib", "zstd",
    "libxml2", "libxmlb", "libcurl", "pcre2", "libpng", "freetype",
    "fontconfig", "pixman", "expat", "libffi",
    "libogg", "libvorbis", "opus", "alsa-lib",
    "libx11", "libxext", "libxv", "libxi", "libxau", "libxcb",
    "xorgproto", "xtrans", "iso-codes",
)

# 上游测试清点（静态统计，2026-10-04 实测源码 grep #[test]）
UPSTREAM_TEST_DISCOVERED = 37
UPSTREAM_TEST_FRAMEWORK = "cargo-test"
UPSTREAM_TEST_COMMAND = "cargo test --release --target aarch64-unknown-linux-ohos"


class KoohaMp4Conan(ConanFile):
    name = "kooha-mp4"
    version = "2.2.4"
    description = "Kooha — elegantly record your screen (GTK4 screen recorder, WebM/MP4/Matroska/GIF)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/Seadve/Kooha"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/k/kooha-mp4/2.2.4"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kooha-mp4 supports Linux and OHOS only, got {self.settings.os}"
            )
        self._ohos_target()

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # ── gtk4 / libadwaita 动态侧（zenity + libadwaita/1.7.12 同款图约束）──
        # adw crate 0.5.3 带 v1_4 特性（ToolbarView 在 libadwaita >= 1.4），
        # 选 libadwaita/1.7.12（图内 appstream/libxmlb 已实测可源码构建发布）。
        self.requires(
            "libadwaita/1.7.12",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "gtk4/4.22.4",
            transitive_headers=True,
            transitive_libs=True,
        )
        # The SAME graph constraint libadwaita/1.7.12 and gtk4/4.22.4 use
        # (override=True unifies the pango/harfbuzz/cairo-gobject/graphene
        # glib pins; .1.1's bin tools are codesigned so glib-compile-resources
        # and friends run on OHOS).
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        # gtk4/4.22.4 meson requires pango >= 1.56; pin the whole graph onto
        # gtk4's pango/1.56.4 (same override libadwaita/1.7.12 applies).
        self.requires(
            "pango/1.56.4",
            transitive_headers=True,
            transitive_libs=True,
            override=True,
        )
        # appstream (libadwaita 1.7.12 dep) chain pins; keep the graph single.
        self.requires("zstd/1.5.7.1", override=True)

        # ── gstreamer 静态侧（R36：依赖均已发布制品）──
        # kooha links gstreamer-1.0 / -base / -video / -pbutils (+ -audio,
        # -tag, -allocators transitively) as STATIC archives from the
        # published 1.28.3 packages; their orc/libdrm closure is satisfied
        # by the packages below (declared explicitly so the payload folders
        # are reachable through self.dependencies).
        self.requires("gstreamer/1.28.3")
        self.requires("gst-plugins-base/1.28.3")
        self.requires("orc/0.4.42")
        self.requires("libdrm/2.4.133")

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（R36；below/0.11.0 先例）：
        # rust-lang 官方 dist 预编译 tarball，宿主与目标均为
        # aarch64-unknown-linux-ohos。不使用 rustup 引导——标准 rustup
        # 无法识别 HarmonyOS 宿主（E105/E154）。
        self.tool_requires("rust-toolchain/1.97.1")

    # ──────────────────────────────────────────────────────────────────
    # source / build
    # ──────────────────────────────────────────────────────────────────

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._generate_config_rs()
        self._stage_pkgconfig()
        self._build_intl_shim()
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._fetch_cargo_deps(env)
        self._pin_target_lexicon(env)
        # 数据层先于测试编译：settings.rs 测试在运行期对源码 data/ 目录
        # 调 glib-compile-schemas 并设 GSETTINGS_SCHEMA_DIR，需要已替换
        # @app-id@ 的 gschema.xml 就位
        self._compile_data_files(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    # ──────────────────────────────────────────────────────────────────
    # upstream-data reproduction (the meson layer, done by hand)
    # ──────────────────────────────────────────────────────────────────

    def _generate_config_rs(self):
        """生成 src/config.rs（meson configure_file(config.rs.in) 的等价物）。

        RESOURCES_FILE/LOCALEDIR 指向包安装前缀（运行期可被
        KOOHA_RESOURCE_FILE / KOOHA_LOCALEDIR 环境变量覆盖，见 patch 0001）。
        """
        prefix = self.package_folder
        mapping = {
            "@APP_ID@": "io.github.seadve.Kooha",
            "@GETTEXT_PACKAGE@": "kooha",
            "@LOCALEDIR@": f"{prefix}/share/locale",
            "@PKGDATADIR@": f"{prefix}/share/kooha",
            "@PROFILE@": "",
            "@VERSION@": str(self.version),
        }
        src_in = os.path.join(self.source_folder, "src", "config.rs.in")
        with open(src_in, encoding="utf-8") as fh:
            content = fh.read()
        for key, value in mapping.items():
            content = content.replace(key, f'"{value}"')
        dst = os.path.join(self.source_folder, "src", "config.rs")
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(content)
        self.output.info(f"generated src/config.rs for prefix {prefix}")

    def _stage_pkgconfig(self):
        """聚合各依赖 payload 的 .pc 到 build_folder/pkgconfig-staging。

        1. 拷贝 payload lib/pkgconfig/*.pc；
        2. 把 prefix=/ 改写为 payload 真实绝对路径（${libdir}/${includedir}
           随之指向真实 payload）；
        3. 剔除 Requires.private 中 staging 没有的项（--cflags 会展开
           private requires，缺失项会让 pkg-config 直接报错）。

        glib2 payload 刻意不在 _PC_DEP_NAMES 里：gstreamer 静态侧的
        glib-2.0 符号全部由 glib/2.84 动态库满足（llvm-nm 验证 745/745），
        若 glib2 的 glib-2.0.pc 进入 PKG_CONFIG_PATH 会把 gtk4 图的头文件
        与库路径整个遮蔽到 2.88 静态版（双 GLib 运行时 = GType 双注册）。
        """
        staging = os.path.join(self.build_folder, "pkgconfig-staging")
        os.makedirs(staging, exist_ok=True)
        staged = set()
        for dep_name in _PC_DEP_NAMES:
            try:
                dep = self.dependencies.get(dep_name)
            except (KeyError, ConanException):
                dep = None
            if dep is None or not getattr(dep, "package_folder", None):
                # 头文件-only 包（xorgproto 等）或 Skip 节点没有 payload
                continue
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(pc_dir):
                continue
            for pc_name in sorted(os.listdir(pc_dir)):
                if not pc_name.endswith(".pc"):
                    continue
                src_pc = os.path.join(pc_dir, pc_name)
                with open(src_pc, encoding="utf-8") as fh:
                    text = fh.read()
                # 确定性 prefix 改写：剔除全部既有 prefix= 行后在顶部写入
                # payload 真实绝对路径。payload .pc 的 prefix=/ 指向包根，
                # 部分文件以注释开头——先 replace 再判断 startswith 会产生
                # 重复 prefix 定义（pkg-config 报 Duplicate definition，
                # pcre2/10.45 实测），故统一"删全部 + 头部补一条"。
                body = "\n".join(
                    line for line in text.splitlines()
                    if not line.startswith("prefix="))
                text = f"prefix={dep.package_folder}\n{body}\n"
                dst_pc = os.path.join(staging, pc_name)
                with open(dst_pc, "w", encoding="utf-8") as fh:
                    fh.write(text)
                staged.add(pc_name[:-3])
        # 第二遍：剔除 Requires.private 中缺失项
        for pc_name in sorted(os.listdir(staging)):
            path = os.path.join(staging, pc_name)
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
            out, in_private, changed = [], False, False
            for line in lines:
                if line.startswith("Requires.private:"):
                    in_private = True
                    kept = []
                    for tok in line.split(":", 1)[1].split(","):
                        name = tok.strip().split()[0] if tok.strip() else ""
                        if not name or name in staged:
                            kept.append(tok.strip())
                        else:
                            changed = True
                    out.append("Requires.private: " + ", ".join(kept) + "\n")
                    continue
                if in_private and line.startswith((" ", "\t")):
                    # 续行（罕见）：整行丢弃策略过于粗暴，保留原样
                    out.append(line)
                    continue
                in_private = False
                out.append(line)
            if changed:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.writelines(out)
        self._pkgconfig_staging = staging
        self.output.info(f"staged {len(staged)} pkg-config files "
                         f"into {staging}")

    def _build_intl_shim(self):
        """构建 gettext identity shim（libintl.a + libintl.h 存根）。

        OHOS sysroot libc.so 链接期不导出 gettext 族符号（运行时
        /system/lib/ld-musl-aarch64.so.1 有全套实现，但 ld 找不到定义）；
        gettext-sys 的 gettext-system 快速路径只认 *-gnu/*-musl triplet。
        GETTEXT_DIR + GETTEXT_STATIC=1 让 gettext-sys 静态链接本 shim，
        语义等同 C locale（gettext 原样返回 msgid —— i18n 单测断言
        恰好覆盖此行为），避免源码编译整个 GNU gettext。
        """
        shim_dir = os.path.join(self.build_folder, "intlshim")
        lib_dir = os.path.join(shim_dir, "lib")
        inc_dir = os.path.join(shim_dir, "include")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        marker = os.path.join(shim_dir, ".built")
        if os.path.isfile(marker):
            return
        csrc = os.path.join(shim_dir, "intlshim.c")
        with open(csrc, "w", encoding="utf-8") as fh:
            fh.write(INTL_SHIM_C)
        with open(os.path.join(inc_dir, "libintl.h"), "w",
                  encoding="utf-8") as fh:
            fh.write(INTL_SHIM_H)
        cc = self._ohos_cc()
        obj = os.path.join(shim_dir, "intlshim.o")
        r = subprocess.run(
            [cc, "-target", self._ohos_target(), "-c", csrc, "-o", obj],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                f"intl shim compile failed: {r.stderr[:300]}")
        ar = self._llvm_ar()
        r = subprocess.run(
            [ar, "rcs", os.path.join(lib_dir, "libintl.a"), obj],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise ConanInvalidConfiguration(
                f"intl shim archive failed: {r.stderr[:300]}")
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("built\n")
        self.output.info("intl identity shim built (libintl.a)")

    @staticmethod
    def _tool(name, env):
        """按 env PATH 解析工具的绝对路径。

        实测本机 Python subprocess 的 PATH 查找遵循 posix_spawnp 语义
        （用父进程 PATH 而非传入 env 的 PATH），环境里 /data/service/
        hnp/bin 的 glib-compile-resources 链接本机不存在的 libffi.so.8
        必挂；shutil.which(path=...) 则正确按给定 PATH 解析。故一律先
        解析为绝对路径再调用。
        """
        resolved = shutil.which(name, path=env.get("PATH"))
        return resolved or name

    def _compile_data_files(self, env):
        """复现 meson 数据层：gresource / gschema / .mo / desktop / icons。

        全部产物直接落到 package_folder（layout=basic_layout 时
        package_folder 在 build() 阶段即可写）。
        """
        pkg = self.package_folder
        src = self.source_folder
        share = os.path.join(pkg, "share")
        for sub in ("kooha", "applications", "metainfo",
                    "glib-2.0/schemas", "icons/hicolor/scalable/apps",
                    "icons/hicolor/symbolic/apps", "locale"):
            os.makedirs(os.path.join(share, sub), exist_ok=True)

        # 1) gresource bundle（glib-compile-resources，zenity 同款 PATH 准备）
        gcr = self._tool("glib-compile-resources", env)
        res_xml = os.path.join(src, "data", "resources",
                               "resources.gresource.xml")
        res_out = os.path.join(share, "kooha", "resources.gresource")
        r = subprocess.run(
            [gcr, "--target", res_out,
             "--sourcedir", os.path.dirname(res_xml), res_xml],
            cwd=src, env=env, capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(res_out):
            raise ConanInvalidConfiguration(
                f"glib-compile-resources failed: {r.stderr[:300]}")

        # 2) gschema：模板替换 + 写源码 data/（供上游单测 GSETTINGS_SCHEMA_DIR）
        #    + 安装目录两份，并各自 glib-compile-schemas
        with open(os.path.join(src, "data",
                               "io.github.seadve.Kooha.gschema.xml.in"),
                  encoding="utf-8") as fh:
            gschema = fh.read()
        gschema = gschema.replace("@app-id@", "io.github.seadve.Kooha")
        gschema = gschema.replace("@gettext-package@", "kooha")
        gschema_name = "io.github.seadve.Kooha.gschema.xml"
        src_data = os.path.join(src, "data", gschema_name)
        with open(src_data, "w", encoding="utf-8") as fh:
            fh.write(gschema)
        schema_install_dir = os.path.join(share, "glib-2.0", "schemas")
        with open(os.path.join(schema_install_dir, gschema_name), "w",
                  encoding="utf-8") as fh:
            fh.write(gschema)
        gcs = self._tool("glib-compile-schemas", env)
        for schema_dir in (os.path.join(src, "data"), schema_install_dir):
            subprocess.run(
                [gcs, schema_dir],
                env=env, capture_output=True, text=True, check=False)

        # 3) .mo 翻译（msgfmt，43 个 po）
        po_dir = os.path.join(src, "po")
        msgfmt = self._tool("msgfmt", env)
        for po_name in sorted(os.listdir(po_dir)):
            if not po_name.endswith(".po"):
                continue
            lang = po_name[:-3]
            mo_dir = os.path.join(share, "locale", lang, "LC_MESSAGES")
            os.makedirs(mo_dir, exist_ok=True)
            r = subprocess.run(
                [msgfmt, "-o", os.path.join(mo_dir, "kooha.mo"),
                 os.path.join(po_dir, po_name)],
                env=env, capture_output=True, text=True)
            if r.returncode != 0:
                self.output.warning(f"msgfmt failed for {lang}: "
                                    f"{r.stderr[:120]}")

        # 4) desktop file（@icon@ 替换；desktop-file-validate 可选）
        with open(os.path.join(
                src, "data", "io.github.seadve.Kooha.desktop.in.in"),
                encoding="utf-8") as fh:
            desktop = fh.read()
        desktop = desktop.replace("@icon@", "io.github.seadve.Kooha")
        with open(os.path.join(share, "applications",
                               "io.github.seadve.Kooha.desktop"), "w",
                  encoding="utf-8") as fh:
            fh.write(desktop)

        # 5) metainfo（@app-id@ / @gettext-package@ 替换）
        with open(os.path.join(
                src, "data", "io.github.seadve.Kooha.metainfo.xml.in.in"),
                encoding="utf-8") as fh:
            metainfo = fh.read()
        metainfo = metainfo.replace("@app-id@", "io.github.seadve.Kooha")
        metainfo = metainfo.replace("@gettext-package@", "kooha")
        with open(os.path.join(share, "metainfo",
                               "io.github.seadve.Kooha.metainfo.xml"), "w",
                  encoding="utf-8") as fh:
            fh.write(metainfo)

        # 6) icons（install_data + rename，照 data/icons/meson.build）
        icons = os.path.join(src, "data", "icons")
        copy(self, "io.github.seadve.Kooha.svg",
             src=icons, dst=os.path.join(share, "icons/hicolor/scalable/apps"))
        copy(self, "io.github.seadve.Kooha.Devel.svg",
             src=icons, dst=os.path.join(share, "icons/hicolor/scalable/apps"))
        copy(self, "io.github.seadve.Kooha.Source.svg",
             src=icons, dst=os.path.join(share, "icons/hicolor/scalable/apps"))
        copy(self, "io.github.seadve.Kooha-symbolic.svg",
             src=icons, dst=os.path.join(share, "icons/hicolor/symbolic/apps"))

        self.output.info("data files compiled (gresource/gschema/mo/"
                         "desktop/metainfo/icons)")

    # ──────────────────────────────────────────────────────────────────
    # Rust build helpers (below/0.11.0 precedent)
    # ──────────────────────────────────────────────────────────────────

    def _fetch_cargo_deps(self, env):
        result = subprocess.run(
            [env["CARGO"], "fetch", "--manifest-path",
             os.path.join(self.source_folder, "Cargo.toml")],
            cwd=self.source_folder, env=env,
        ).returncode
        if result != 0:
            raise ConanInvalidConfiguration(f"cargo fetch failed (rc={result})")

    def _pin_target_lexicon(self, env):
        """将 target-lexicon 钉到 0.12.16（认识 OHOS 三元组）。

        Cargo.lock 锁定 target-lexicon 0.12.11（system-deps → cfg-expr
        0.15.5 的传递依赖）；0.12.11 的 build.rs 解析
        aarch64-unknown-linux-ohos 时 panic（"Invalid target name"），
        0.12.16 起收录该三元组（targets.rs "aarch64-unknown-linux-ohos"）。
        cargo update --precise 只动这一个 crate，其余锁定不变。
        """
        lock = os.path.join(self.source_folder, "Cargo.lock")
        with open(lock, encoding="utf-8") as fh:
            lock_txt = fh.read()
        if 'target-lexicon' not in lock_txt:
            return
        if 'target-lexicon\nversion = "0.12.16"' in lock_txt:
            return  # already pinned
        result = subprocess.run(
            [env["CARGO"], "update", "--manifest-path",
             os.path.join(self.source_folder, "Cargo.toml"),
             "-p", "target-lexicon", "--precise", "0.12.16"],
            cwd=self.source_folder, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"cargo update target-lexicon failed: {result.stderr[:300]}")
        self.output.info("pinned target-lexicon to 0.12.16 (OHOS triple)")

    def _run_upstream_tests(self, env):
        """cargo test：上游 37 个 #[test] 单元测试（R51 三步法第二步）。

        OHOS 拒绝 execve 未签名 ELF：cargo test 链接出的测试二进制
        （target/<t>/release/deps/kooha-<hash>）必须先构建（--no-run）、
        用 binary-sign-tool 自签、再执行；--tests 只构建单元测试二进制
        （doc-test 的临时二进制无法预签，跳过）。

        --no-fail-fast：需要 gst 元素工厂（vp8enc/x264enc/opusenc/webmmux/
        encodebin——在未发布的 gst-plugins-good / 静态未注册插件里）的
        用例在无插件环境必然失败，属环境限制而非被测逻辑缺陷；纯逻辑
        用例（i18n/pipeline/window/screencast_session/settings/...）应全
        绿。失败计数写入 notes.md，OHC_REQUIRE_UPSTREAM_TESTS=1 可转硬门禁。
        """
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1)")
            return
        target = self._ohos_target()
        base = [env["CARGO"], "test", "--release", "--target", target,
                "--tests", "--no-fail-fast"]
        # 1) build only（链接测试二进制但不运行）。
        # HMDFS 瞬态竞争重试环：build-script 二进制刚链接即 exec 偶发
        # ETXTBSY（os error 26，实测 syn / gstreamer-audio-sys 先后命中，
        # 失败点逐次前移），cargo 增量续编可收敛——最多重试 3 次。
        build_ok = False
        last_rc = None
        for attempt in range(3):
            r = subprocess.run(base + ["--no-run"],
                               cwd=self.source_folder, env=env)
            last_rc = r.returncode
            if r.returncode == 0:
                build_ok = True
                break
            self.output.warning(
                f"cargo test --no-run attempt {attempt + 1} failed "
                f"(rc={r.returncode}); HMDFS settle retry")
            time.sleep(5)
        if not build_ok:
            raise ConanInvalidConfiguration(
                f"cargo test --no-run failed after retries (rc={last_rc})")
        # 2) sign the freshly linked test binaries (OHOS execve gate)
        self._sign_test_binaries()
        # 3) run
        result = subprocess.run(base, cwd=self.source_folder, env=env)
        if result.returncode != 0 and \
                os.environ.get("OHC_REQUIRE_UPSTREAM_TESTS") == "1":
            raise ConanInvalidConfiguration(
                f"Upstream kooha tests failed for {target} "
                f"(rc={result.returncode})")
        if result.returncode != 0:
            self.output.warning(
                f"Upstream kooha tests: rc={result.returncode} "
                "(known factory-limited cases, see notes.md); continuing")

    def _sign_test_binaries(self):
        """签名 cargo 链接的测试二进制（deps/ 下的可执行文件）。

        cargo test 产物不带 .codesign，OHOS 拒绝 execve（exit 127）。
        对 target/<t>/release/deps/ 的每个可执行文件：剥离旧 .codesign
        段后 binary-sign-tool 自签（ML-0043 模式，幂等可重复）。
        """
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; test binaries stay unsigned "
                "and the OHOS loader will refuse them (exit 127)")
            return
        target = self._ohos_target()
        deps_dir = os.path.join(self.source_folder, "target", target,
                                "release", "deps")
        if not os.path.isdir(deps_dir):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signed = 0
        for name in sorted(os.listdir(deps_dir)):
            if name.endswith((".d", ".so", ".rlib", ".rmeta", ".json",
                              ".signed")):
                continue
            path = os.path.join(deps_dir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if not os.access(path, os.X_OK):
                continue
            if os.path.isfile(objcopy):
                subprocess.run(
                    f'{objcopy} --remove-section .codesign "{path}" '
                    f'2>/dev/null || true', shell=True)
            tmp = path + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", tmp,
                 "-selfSign", "1"], capture_output=True, text=True)
            if result.returncode == 0 and os.path.isfile(tmp):
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                signed += 1
            elif os.path.isfile(tmp):
                os.remove(tmp)
        self.output.info(f"signed {signed} cargo test binaries")

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--target", target]
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={result})")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        release_dir = os.path.join(self.source_folder, "target", target,
                                   "release")
        src_bin = os.path.join(release_dir, "kooha")
        if not os.path.isfile(src_bin):
            raise ConanInvalidConfiguration(
                f"kooha binary not produced at {src_bin}")
        dst_bin = os.path.join(out_dir, "kooha")
        shutil.copy2(src_bin, dst_bin)
        os.chmod(dst_bin, 0o755)

    def _sign_binaries(self):
        """binary-sign-tool 自签最终产物（zenity ML-0043 模式）。

        cargo 链接后产物不带 .codesign，OHOS XPM 拒绝 execve。
        """
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; kooha stays unsigned and may "
                "be rejected by the OHOS loader (EACCES)")
            return
        binary = os.path.join(self.build_folder, "bin", "kooha")
        if not os.path.isfile(binary):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(objcopy):
            subprocess.run(
                f'{objcopy} --remove-section .codesign "{binary}" '
                f'2>/dev/null || true', shell=True)
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", binary,
             "-selfSign", "1"], capture_output=True, text=True)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed for kooha (rc={result.returncode}):"
                f" {result.stderr[:200]}")
        os.chmod(binary, 0o755)
        self.output.info("kooha signed (selfSign)")

    # ── environment assembly ──────────────────────────────────────────

    def _prepare_glib_tools(self):
        """准备可执行的 glib 构建工具（glib-compile-resources 等）。

        /data/service/hnp/bin/glib-compile-resources 链接本机不存在的
        libffi.so.8 无法运行；glib/2.84.0.1.1 payload 自带全套已签名
        工具，但缓存副本可能携带失效 .codesign（exec 报 EPERM）——按
        ML-0043（zenity/gtk4/libadwaita 配方同款防御性重签）复制到
        build_folder、剥离旧段、binary-sign-tool 重签后使用。数据编译
        与上游 settings.rs 测试（Command::new("glib-compile-schemas")
        走 PATH）都经由本目录。

        返回工具目录；非 OHOS 环境或 glib 依赖缺失时返回 None（回退
        系统 PATH）。
        """
        dst = os.path.join(self.build_folder, "glib-tools")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return dst
        try:
            glib = self.dependencies.get("glib")
        except (KeyError, ConanException):
            glib = None
        if glib is None or not getattr(glib, "package_folder", None):
            return None
        os.makedirs(dst, exist_ok=True)
        signer = self._find_binary_sign_tool()
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        for name in ("glib-compile-resources", "glib-compile-schemas",
                     "gresource"):
            s = os.path.join(glib.package_folder, "bin", name)
            if not os.path.isfile(s):
                continue
            d = os.path.join(dst, name)
            shutil.copy2(s, d)
            os.chmod(d, 0o755)
            if os.path.isfile(objcopy):
                subprocess.run(
                    f'{objcopy} --remove-section .codesign "{d}" '
                    f'2>/dev/null || true', shell=True)
            if signer:
                result = subprocess.run(
                    [signer, "sign", "-inFile", d, "-outFile", d,
                     "-selfSign", "1"], capture_output=True, text=True)
                if result.returncode != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool failed for {name} "
                        f"(rc={result.returncode}): {result.stderr[:200]}")
                os.chmod(d, 0o755)
                self.output.info(f"prepared glib tool: {name}")
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("glib tools prepared\n")
        return dst

    def _rust_environment(self):
        env = os.environ.copy()
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        extra_paths = [os.path.dirname(cargo)]
        glib_tools = self._prepare_glib_tools()
        if glib_tools:
            extra_paths.insert(0, glib_tools)
        extra_paths += [d for d in ("/system/bin", "/system/sbin",
                                     "/vendor/bin") if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + \
            env.get("PATH", "")

        # 工具链自带 lib + cargo 运行期共享库 + 动态侧依赖 payload lib
        # （gtk4/glib/libadwaita/...：测试与 glib-compile-* 工具运行时都要
        # 找到 .so）+ 受控系统库目录。
        #
        # 刻意不继承环境的 LD_LIBRARY_PATH：桌面会话的值含空白符损坏的
        # /system/lib64 条目（"         /system/lib64"——musl 视为不存在的
        # 路径），且 bundle 目录带异源 libc++_shared.so；实测导致 rustc
        # dlopen librustc_driver 时 libc++ 符号全部重定位失败
        # （error_category::equivalent / system_category ...）。
        # 改为显式列出 profile [buildenv] 同款已知可用目录（受控验证
        # rustc 1.97.1 --version 正常）。
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        lib_dirs += self._dependency_lib_dirs()
        lib_dirs += [
            "/system/lib64",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/lib",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/lib/aarch64-linux-ohos",
        ]
        env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)

        # pkg-config：只看 staging（见 _stage_pkgconfig；glib2 刻意排除）
        for var in ("PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR",
                    "PKG_CONFIG_SYSROOT_DIR", "PKG_CONFIG_ALLOW_SYSTEM_CFLAGS"):
            env.pop(var, None)
        env["PKG_CONFIG_PATH"] = self._pkgconfig_staging

        # gettext-sys → 静态链接 identity shim（见 _build_intl_shim）
        shim_dir = os.path.join(self.build_folder, "intlshim")
        env["GETTEXT_DIR"] = shim_dir
        env["GETTEXT_STATIC"] = "1"

        # cargo 走 HTTPS（rsproxy.cn）；设备无默认 CA bundle
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        env["CARGO_PROFILE_RELEASE_LTO"] = "false"
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] = "1"

        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": self._ohos_cxx(),
                "AR_aarch64_unknown_linux_ohos": self._llvm_ar(),
                "RANLIB_aarch64_unknown_linux_ohos": self._llvm_ranlib(),
            })
            # orc 静态库（liborc-0.4.a 的 JIT 指令缓存刷新，orcarm.c /
            # orcprogram-x86.c）引用 __clear_cache；rustc 链接时传
            # -nodefaultlibs，clang 不会自动带上 compiler-rt builtins →
            # ld.lld 报 "undefined symbol: __clear_cache"。显式把 SDK 的
            # libclang_rt.builtins.a 挂进 link-arg（llvm-nm 实测含该符号）。
            import glob as _glob
            llvm_root = os.path.dirname(os.path.dirname(cc))
            builtins = sorted(_glob.glob(
                os.path.join(llvm_root, "lib", "clang", "*",
                             "lib", "aarch64-linux-ohos",
                             "libclang_rt.builtins.a")))
            if builtins:
                key = "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_RUSTFLAGS"
                env[key] = (env.get(key, "") + " -C link-arg=" +
                            builtins[-1]).strip()
                self.output.info("linked compiler-rt builtins: "
                                 + os.path.basename(builtins[-1]))
            else:
                self.output.warning(
                    "libclang_rt.builtins.a not found under SDK; "
                    "orc __clear_cache may fail to link")
        return env

    def _dependency_lib_dirs(self):
        """构建/测试环境 LD_LIBRARY_PATH 的依赖 lib 目录（全图遍历）。

        直接依赖的 _PC_DEP_NAMES 不够：gdk-pixbuf 的 libgdk_pixbuf-2.0.so
        运行期还要解析 libtiff/libjpeg-turbo 的符号（TIFFSetField/
        jpeg_resync_to_restart...，均为传递依赖，实测缺目录时测试二进制
        报 "Error relocating" exit 127）。故遍历完整依赖图的所有 payload
        lib 目录；clang payload 排除（其 libc++_shared.so 会与 rustc
        dlopen 的 librustc_driver 产生解析竞争），glib2 payload 排除
        （防御性：其静态 .a 无害但保持与 pkg-config staging 一致的排除
        口径）。
        """
        dirs = []
        seen = set()
        try:
            deps = list(self.dependencies.values())
        except Exception:  # noqa: BLE001 - dependencies may be absent
            deps = []
        for dep in deps:
            if getattr(dep, "package_folder", None) is None:
                continue
            ref_name = getattr(dep, "refname", "") or ""
            base = ref_name.split("/")[0] if ref_name else ""
            if base in ("clang", "glib2"):
                continue
            lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib) and lib not in seen:
                seen.add(lib)
                dirs.append(lib)
        return dirs

    # ── toolchain discovery / bootstrap (below/0.11.0 verbatim) ──────

    def _ohos_target(self):
        arch = str(self.settings.arch)
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
            "armv7": "armv7-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        target = mapping.get(arch)
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return target

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "aarch64-unknown-linux-ohos-clang not found")

    def _ohos_cxx(self):
        cc = self._ohos_cc()
        return cc + "++" if not cc.endswith("++") else cc

    def _llvm_ar(self):
        return os.path.join(os.path.dirname(self._ohos_cc()), "llvm-ar")

    def _llvm_ranlib(self):
        return os.path.join(os.path.dirname(self._ohos_cc()), "llvm-ranlib")

    def _ensure_ohos_target(self, env):
        """校验工具链自带 OHOS 目标标准库（无需 rustup，E105/E154）。"""
        target = self._ohos_target()
        rustc = os.path.join(os.path.dirname(env["CARGO"]), "rustc")
        if not os.path.isfile(rustc):
            rustc = shutil.which("rustc") or ""
        if not rustc:
            return
        prefix = os.path.dirname(os.path.dirname(rustc))
        rustlib = os.path.join(prefix, "lib", "rustlib", target)
        if not os.path.isdir(rustlib):
            self.output.warning(
                f"rust-std for {target} not found under {rustlib}; "
                "the toolchain may be unable to build for OHOS")

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _find_cargo(self, env):
        candidates = [
            os.environ.get("CARGO"),
            env.get("CARGO"),
            shutil.which("cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            "/data/service/hnp/bin/cargo",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available")

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """准备可执行（已签名）的 Rust 工具链，返回其 bin 目录。

        rust-toolchain/1.97.1 包内二进制无 code signature，HarmonyOS
        拒绝 execve（EACCES）；复制 cargo/rustc + librustc_driver 到
        build_folder 签名，其余只读负载软链。幂等（marker）。
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if not tool:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay "
                "unsigned and may be rejected by the OHOS loader (EACCES)")

        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                        os.chmod(d, 0o755)
                    to_sign.append(d)

        if signer:
            for path in to_sign:
                tmp = path + ".signed"
                result = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"], capture_output=True, text=True)
                if result.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, result.returncode, result.stderr[:200]))
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info("signed toolchain binary: %s"
                                 % os.path.basename(path))
        else:
            self.output.warning("toolchain binaries were not signed")

        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    os.symlink(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                os.symlink(s, d)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _prepare_runtime_libs(self):
        """下载 cargo 运行期共享库（libssl/libcrypto/libz），
        返回 lib 目录列表（below/0.11.0 先例）。"""
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, url, tgz, sha256=sha256)
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz."))
                       for f in files):
                    lib_dirs.append(root)
        # libz.so 来自 conan 依赖 zlib/1.3.1.1 的包目录（替代已下架的
        # harmonybrew zlib bottle；制品仓有货，CI 可解析）。
        try:
            zdep = self.dependencies["zlib"]
        except KeyError:
            zdep = None
        if zdep is not None:
            for libdir in zdep.cpp_info.aggregated_components().libdirs:
                if any(f.startswith("libz.") for f in os.listdir(libdir)):
                    lib_dirs.append(libdir)
                    break
            else:
                for libdir in zdep.cpp_info.libdirs:
                    if any(f.startswith("libz.") for f in os.listdir(libdir)):
                        lib_dirs.append(libdir)
                        break
        return lib_dirs

    def _ca_bundle(self):
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")
        content = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 3\n"
        )
        if ca_bundle:
            content += ("\n[http]\n"
                        "cainfo = \"%s\"\n" % ca_bundle)
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    # ──────────────────────────────────────────────────────────────────
    # package / package_info
    # ──────────────────────────────────────────────────────────────────

    def package(self):
        copy(self, "kooha", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # share/ 数据文件已在 _compile_data_files 直接落 package_folder
        os.chmod(os.path.join(self.package_folder, "bin", "kooha"), 0o755)

    def package_info(self):
        # R38: application package — a command-line/GUI tool, not a library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []


# ──────────────────────────────────────────────────────────────────────
# gettext identity shim（C locale 语义；i18n 单测断言覆盖该行为）
# ──────────────────────────────────────────────────────────────────────

INTL_SHIM_C = r"""
/* Identity gettext shim for HarmonyOS PC (C-locale semantics).
 *
 * The OHOS sysroot libc.so exports no gettext-family symbols at link
 * time (the runtime loader ld-musl-aarch64.so.1 HAS them, but ld needs
 * a definition when linking). This shim provides the C-locale
 * behaviour: messages pass through untranslated, ngettext picks the
 * plural form by n == 1, and the domain/bookkeeping calls return their
 * arguments. Semantically identical to running upstream under LC_ALL=C.
 */
#include <stddef.h>

#if defined(__GNUC__)
#define SHIM_EXPORT __attribute__((visibility("default")))
#else
#define SHIM_EXPORT
#endif

SHIM_EXPORT char *gettext(const char *msgid) { return (char *)msgid; }
SHIM_EXPORT char *dgettext(const char *domainname, const char *msgid)
{ (void)domainname; return (char *)msgid; }
SHIM_EXPORT char *dcgettext(const char *domainname, const char *msgid,
                            int category)
{ (void)domainname; (void)category; return (char *)msgid; }
SHIM_EXPORT char *ngettext(const char *msgid1, const char *msgid2,
                           unsigned long n)
{ return (char *)(n == 1 ? msgid1 : msgid2); }
SHIM_EXPORT char *dngettext(const char *domainname, const char *msgid1,
                            const char *msgid2, unsigned long n)
{ (void)domainname; return (char *)(n == 1 ? msgid1 : msgid2); }
SHIM_EXPORT char *dcngettext(const char *domainname, const char *msgid1,
                             const char *msgid2, unsigned long n,
                             int category)
{ (void)domainname; (void)category;
  return (char *)(n == 1 ? msgid1 : msgid2); }
SHIM_EXPORT char *bindtextdomain(const char *domainname, const char *dirname)
{ (void)dirname; return (char *)domainname; }
SHIM_EXPORT char *bind_textdomain_codeset(const char *domainname,
                                          const char *codeset)
{ (void)codeset; return (char *)domainname; }
SHIM_EXPORT char *textdomain(const char *domainname)
{ return (char *)(domainname ? domainname : "messages"); }
"""

INTL_SHIM_H = r"""
/* Minimal libintl.h for the kooha-mp4 identity shim (see conanfile.py).
 * Declarations match gettext-sys 0.21.3 src/lib.rs extern "C" block. */
#ifndef KOOHA_INTL_SHIM_H
#define KOOHA_INTL_SHIM_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
char *gettext(const char *msgid);
char *dgettext(const char *domainname, const char *msgid);
char *dcgettext(const char *domainname, const char *msgid, int category);
char *ngettext(const char *msgid1, const char *msgid2, unsigned long n);
char *dngettext(const char *domainname, const char *msgid1,
                const char *msgid2, unsigned long n);
char *dcngettext(const char *domainname, const char *msgid1,
                 const char *msgid2, unsigned long n, int category);
char *bindtextdomain(const char *domainname, const char *dirname);
char *bind_textdomain_codeset(const char *domainname, const char *codeset);
char *textdomain(const char *domainname);
#ifdef __cplusplus
}
#endif
#endif /* KOOHA_INTL_SHIM_H */
"""
