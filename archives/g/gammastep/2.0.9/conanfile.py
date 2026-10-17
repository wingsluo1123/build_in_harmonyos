#!/usr/bin/env python3
"""Conan recipe — gammastep 2.0.9 (色温调节 CLI) for OHOS (HarmonyOS PC / aarch64).

上游 https://gitlab.com/chinstrap/gammastep （redshift 的 Wayland 活跃分支）。
产物是 CLI `bin/gammastep`（application 包，无库、无头文件）。

## 一、源码形态与 bootstrap

下载件是上游 **git tag archive**（`-/archive/v2.0.9/...tar.gz`，R39 合规），
**不含 `configure`/`Makefile.in`/`m4/`** ⇒ build() 先 `autoreconf -fi`。
configure.ac 同时用到两套 i18n 宏，两者都由 autoreconf 触发：

* `AC_PROG_INTLTOOL([0.50])` — aclocal 期要 `intltool.m4`，autoreconf 期会调
  `intltoolize`；`AC_PROG_INTLTOOL` 是 intltool 0.51.0 提供的旧名别名。
* `AM_GNU_GETTEXT([external])` — autoreconf 内部调 `autopoint`，装 `po/Makefile.in.in`
  与 gettext m4；configure/make 期要 `msgfmt`/`msgmerge`/`xgettext`。

（intltool/gettext 的工具化前缀问题与 ddccontrol/1.0.3、l3afpad 同款：两个包都把
`prefix=/` 烧进脚本，故 (a) **intltoolize 要 prefix shim**、(b) **autopoint 要
`gettext_datadir`**。两处处置逐字沿用 ddccontrol/1.0.3 的已验证写法。）

## 二、后端选择（configure.ac 的 4 个可选调节后端）

| 后端 | 依赖 | 本配方 | 运行期可用性（见 notes.md） |
|---|---|---|---|
| DRM | libdrm | `--enable-drm` | ✗ `/dev/dri` ENOENT |
| Wayland | wayland-client + wayland-scanner | `--enable-wayland` | ✗ 无 Wayland compositor |
| RANDR | xcb + xcb-randr | `--enable-randr` | ✗ 无 X 服务器 |
| VidMode | x11 + xxf86vm | `--enable-vidmode` | ✗ 无 X 服务器 |

四个都**显式 `--enable-*`**（而非默认 `maybe`）：任一依赖缺失时 configure 直接
`AC_MSG_ERROR` 硬失败，避免"静默少编一个后端却宣称四后端齐全"的假绿。
Geoclue2（需 gio ≥2.26）与 GUI（Python + GTK3 托盘）显式 `--disable-*`：前者引入
glib 全图而本机无定位服务，后者依赖未打包的 GTK3 运行期。

## 三、wayland-scanner：制品仓工具在本机**不可执行** ⇒ 源码静态重建

`src/Makefile.am` 用 `$(WAYLAND_SCANNER) private-code` 生成
`gamma-control-protocol.c` / `orbital-authorizer-protocol.c`，而 configure.ac 用
`PKG_CHECK_VAR(WAYLAND_SCANNER, wayland-scanner, wayland_scanner)` 从制品仓
`wayland` 包的 `wayland-scanner.pc` 取路径。本机一手实测该二进制**不可执行**：

```
$ <wayland>/bin/wayland-scanner --version
Operation not permitted                       # ① 未签名的制品仓 ELF
$ binary-sign-tool sign -inFile … -outFile … -selfSign 1     # ② 重签后
$ ./wayland-scanner --version
Error loading shared library /…/.cache/conan2/p/expat…/p/lib/libexpat.so  # ③ NEEDED 是
Error relocating …: xmlNewValidCtxt: symbol not found                     #    绝对路径
```

③ 的 `LD_LIBRARY_PATH` 无效（NEEDED 里不是 soname），且该绝对路径在本机不存在。
处方 = 按 `knowledge/drafts/DRAFT-ohos-static-tool-bypass-dlopen-limit` **从 wayland
源码静态编译 scanner**，并写一份指向自编译工具的 `wayland-scanner.pc` 顶到
`PKG_CONFIG_PATH` 最前（机制与 archives/l/lavalauncher/2.1.1 同款，本包为第二个
实证包：**该草稿原文只记了 dlopen 失败这一种签名，"未签名 → EPERM"这段是本包新增**）。
"""
import os
import re
import shlex
import shutil
from pathlib import Path, PurePosixPath

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GammastepConan(ConanFile):
    name = "gammastep"
    version = "2.0.9"
    description = "Adjust the color temperature of the display (CLI, multi-backend)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/chinstrap/gammastep"
    url = "https://gitlab.com/chinstrap/gammastep"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 必须用 `in ("Linux", "OHOS")` 写法判断。
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # configure.ac 的 PKG_CHECK_MODULES 逐条对应（全部显式 --enable-*，缺一即
        # configure 硬失败）。
        self.requires("wayland/1.24.0")        # WAYLAND: wayland-client >= 1.15.0
        self.requires("libdrm/2.4.133")        # DRM:     libdrm
        # RANDR: xcb + xcb-randr（libxcb 以组件暴露 xcb-randr.pc）。
        # ⚠ 版本必须与 libx11 那条链同源：本仓存在两条互斥的 X11 世代——
        #   libx11/1.8.13.x 钉 libxcb/1.17.0.x + libxau/1.0.12，
        #   libx11/6.4.0   钉 libxcb/1.16     + libxau/1.0.11；
        #   而 libxxf86vm/1.1.5 钉 libx11/6.4.0 + libxext/6.4.0。
        #   混用会直接 `Version conflict: libxau/1.0.11 vs 1.0.12`（首轮实测首错）。
        #   故整条栈按 xgamma/1.0.8（同域先例、同为 X11 gamma 工具）取 6.4.0 世代。
        self.requires("libxcb/1.16")           # RANDR:   xcb + xcb-randr
        # xorgproto 是本包**直接 include 的头**（src/gamma-vidmode.c: <X11/Xlib.h>）
        # 的来源：libx11 的传递依赖是 package_type=HEADER，conan 2 的
        # transform_downstream 对它置 headers=False ⇒ 不安装、聚合不到 ⇒
        # 编译期 'X11/X.h' file not found（lisgd/0.3.7 同款，全仓 113 份配方同写法）。
        self.requires("xorgproto/2025.1")
        self.requires("libx11/6.4.0")          # VIDMODE: x11
        self.requires("libxxf86vm/1.1.5")      # VIDMODE: xxf86vm
        # AM_GNU_GETTEXT([external]) 在 musl 上**没有 libc 内建 gettext** ⇒
        # gammastep_LDADD=@LIBINTL@ 需要真 libintl（pmount/0.9.23 先例）。
        self.requires("gettext/0.22.5.1")

    def build_requirements(self):
        # 设备自带 aclocal 是 1.17 driver + 1.16 share dir（"Can't locate
        # Automake/Config.pm"）⇒ bootstrap 必须走 tool_requires（l3afpad/ddccontrol 先例）。
        self.tool_requires("automake/1.18")
        # LT_INIT 需要健康的 ltmain.sh ⇒ libtoolize 来自 tool_requires。
        self.tool_requires("libtool/2.5.4.1")
        # AC_PROG_INTLTOOL：aclocal 期要 intltool.m4，autoreconf 期调 intltoolize。
        self.tool_requires("intltool/0.51.0")
        # AM_GNU_GETTEXT：autopoint（autoreconf 内）+ configure/make 期的 msgfmt 家族。
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # wayland-scanner 的源码（静态重建用）；与 host 侧 wayland 包同版本 1.24.0。
        get(
            self,
            **self.conan_data["scanner_sources"],
            strip_root=True,
            destination="wayland-scanner-src",
        )

    # ── generate ────────────────────────────────────────────────────────────
    def generate(self):
        # wayland 包的 cpp_info.libs = ["wayland-client", "wayland-server", "wayland-cursor"]，
        # 而 PkgConfigDeps 会把它们**全部**写进生成的 wayland-client.pc 的 `Libs:` 行 ⇒
        # configure.ac 的 PKG_CHECK_MODULES([WAYLAND], [wayland-client wayland-scanner])
        # 会让 gammastep 平白链上 server 与 cursor。后果不只是"多链两个库"：
        # 本机一手实测 libwayland-cursor.so.0.24.0 的 `.codesign` 在本设备校验不过 ⇒
        # dlopen 报 EACCES（`Error loading shared library libwayland-cursor.so.0: Permission
        # denied`），**整个二进制连 -V 都跑不起来（rc=127）**；同目录 libwayland-client.so.0
        # 正常加载、把 cursor 复制一份 binary-sign-tool -selfSign 1 重签后也能加载 ⇒ 证实是
        # 「制品仓预编译 .so 的签名与本设备绑定」这一类（B草稿库
        # DRAFT-PKG-VER-remote-prebuilt-so-codesign-is-device-bound 同族）。
        # gammastep 源码里没有任何 cursor/server 符号（`grep -rn cursor src/*.c` = 0）⇒
        # 按**真实依赖面**把该 dep 的 libs 收窄为仅 wayland-client（消费方覆盖，
        # 不改制品仓、不改上游），比"给依赖的每个 .so 重签"更小、更准。
        self.dependencies["wayland"].cpp_info.libs = ["wayland-client"]
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                # 四个后端全部强制开启（缺依赖即硬失败，防"静默少编"）。
                "--enable-drm",
                "--enable-wayland",
                "--enable-randr",
                "--enable-vidmode",
                # Geoclue2 需 gio≥2.26 且本机无定位服务；GUI 托盘是 GTK3 Python 脚本，
                # GTK3 未打包 ⇒ 两者显式关闭（关闭后树内零 xml.in 消费者）。
                "--disable-geoclue2",
                "--disable-gui",
                # 显式等值 build/host triplet：完全跳过 config.guess/config.sub
                # （其 HarmonyOS 支持取决于 autoreconf 恰好装到哪份 automake），
                # 同时保持 cross_compiling=no 语义（ddccontrol/klavaro 先例）。
                "--build=aarch64-linux",
                "--host=aarch64-linux",
            ]
        )

        env = tc.environment()

        # (1) aclocal 必须找到 configure.ac 用到的宏：git archive 的 m4/ 是空的 ⇒
        #     收集整图（host + build 上下文，intltool.m4 在 tool_requires 里）所有
        #     aclocal/m4 目录顶到 ACLOCAL_PATH。
        aclocal_dirs = []
        for ctx in (self.dependencies, self.dependencies.build):
            for dep in ctx.values():
                root = getattr(dep, "package_folder", None)
                if not root or not os.path.isdir(root):
                    continue
                for dirpath, dirnames, _ in os.walk(root):
                    if dirpath[len(root):].count(os.sep) > 3:
                        dirnames[:] = []
                        continue
                    if os.path.basename(dirpath) in ("aclocal", "m4"):
                        if dirpath not in aclocal_dirs:
                            aclocal_dirs.append(dirpath)
        own_m4 = os.path.join(self.source_folder, "m4")
        if os.path.isdir(own_m4):
            aclocal_dirs.append(own_m4)
        if aclocal_dirs:
            env.prepend_path("ACLOCAL_PATH", os.pathsep.join(aclocal_dirs))

        # (2) conan gettext 包把 prefix="/" 烧进 autopoint 且把 relocation 分支编掉
        #     ⇒ autoreconf 内的 autopoint 会去 "//share/gettext/archive.dir.tar.xz"
        #     找数据、报 "infrastructure files for version 0.18.1 not found"。
        #     脚本用 `: ${gettext_datadir=...}` 留了环境变量入口 ⇒ 导出真实数据目录。
        for dep in self.dependencies.build.values():
            if dep.ref.name != "gettext" or not dep.package_folder:
                continue
            data = os.path.join(dep.package_folder, "share", "gettext")
            if os.path.isfile(os.path.join(data, "archive.dir.tar.xz")):
                env.define("gettext_datadir", data)
                break

        # (3) configure 用 AC_CHECK_* 探 libintl（无 .pc），把 gettext 的 -I/-L 灌进
        #     CPPFLAGS/LDFLAGS；LIBS 补 -lintl（musl 无内建 gettext；ddccontrol 同款）。
        dep = self.dependencies["gettext"]
        agg = dep.cpp_info.aggregated_components()
        for inc in agg.includedirs:
            env.append("CPPFLAGS", "-I%s" % os.path.join(dep.package_folder, inc))
        for libdir in agg.libdirs:
            env.append("LDFLAGS", "-L%s" % os.path.join(dep.package_folder, libdir))
        env.append("LIBS", "-lintl")

        # (4) 自编译 wayland-scanner 的 .pc 顶到 PKG_CONFIG_PATH 最前：configure 的
        #     PKG_CHECK_VAR(WAYLAND_SCANNER, wayland-scanner, wayland_scanner) 必须
        #     解析到本配方静态重建的工具，而不是制品仓里那个不可执行的同名二进制。
        self._write_scanner_pc()
        env.prepend_path("PKG_CONFIG_PATH", self._scanner_pc_dir())
        #     PKG_CHECK_MODULES([WAYLAND], [wayland-client …]) 也要能解析到 wayland 包
        #     的 .pc ⇒ PkgConfigDeps 已覆盖（其 .pc 由 conan 生成）。

        # (5) 任务局部 libtool 递归 shadow（E522/E331）：制品仓的 .la 元数据里留了
        #     构建机的 stale 路径（libxcb-randr.la 的 dependency_libs 含
        #     `//lib/libxcb.la` 与 `/…/.conan2/p/…/libXau.la`，libdir 也指向别处的
        #     .conan2 缓存）⇒ libtool 在最终链接时会去 open 一个不存在的 .la。
        #     修法 = 把依赖的 .la（含其声明的库产物）拷进 build 内 shadow 目录并重写
        #     整条 dependency_libs 闭包 + libdir，再把 shadow 放到 -L 最前。
        shadow = self._prepare_libtool_shadow()
        if shadow:
            env.prepend("LDFLAGS", "-L%s" % shadow, separator=" ")
        tc.generate(env=env)

    # ── 任务局部 libtool shadow（E522 / E331）────────────────────────────────
    def _prepare_libtool_shadow(self):
        """把依赖的 `.la` 元数据重建成 build 内自洽闭包；返回 shadow 目录（str）或 None。

        为什么必须整条闭包而不是只补直接那一层：libtool 会**递归**打开
        `dependency_libs` 里每个 `.la`（forbid_2 反例：只修直接 .la ⇒ configure 与编译
        全过、最后链接才炸）。为什么不能就地改依赖包里的 .la：那是共享缓存状态，
        改了会污染别的构建（forbid_1）。

        本包实测的坏元数据形态（30 份 .la）：`libxcb-randr.la` 等 25 份 libxcb 家族
        + gettext 的 4 份，`libdir`/`dependency_libs` 里是 `//lib/...`（prefix=/ 的产物）
        与 `/storage/Users/currentUser/.conan2/p/...`（构建机的默认 conan home）。
        """
        libtool_archives = {}
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                d = Path(libdir)
                if not d.is_absolute():
                    d = Path(dep.package_folder, libdir)
                if not d.is_dir():
                    continue
                for archive in d.glob("*.la"):
                    libtool_archives.setdefault(archive.name, []).append(archive)
        if not libtool_archives:
            self.output.info("gammastep: 依赖里没有 .la，跳过 libtool shadow")
            return None

        ambiguous = sorted(n for n, ps in libtool_archives.items() if len(ps) != 1)
        if ambiguous:
            raise ConanException(
                "libtool archive basenames are ambiguous: %s" % ambiguous)
        archives_by_name = {n: ps[0] for n, ps in libtool_archives.items()}

        shadow = Path(self.build_folder, "libtool-shadow")
        shadow.mkdir(parents=True, exist_ok=True)
        shadow_str = str(shadow)
        known_libdirs = {str(a.parent) for a in archives_by_name.values()}

        # 1) 复制每个 .la 声明的库产物（libdir 会被改写到 shadow，libtool 得在这里
        #    找到 .so/.a；symbolic link 由 copy2 跟随复制成实体文件）。
        artifact_sources = {}
        for archive in archives_by_name.values():
            content = archive.read_text(encoding="utf-8")
            for field in ("library_names", "old_library"):
                m = re.search(r"^%s='(.*)'$" % field, content, flags=re.MULTILINE)
                if m is None:
                    raise ConanException(
                        "%s has no %s field" % (archive.name, field))
                for libname in shlex.split(m.group(1)):
                    src = archive.parent / libname
                    if not src.is_file():
                        raise ConanException(
                            "%s references a missing library: %s"
                            % (archive.name, src))
                    prev = artifact_sources.get(libname)
                    if prev is not None and prev != src:
                        raise ConanException(
                            "library basename is ambiguous: %s" % libname)
                    if prev is None:
                        shutil.copy2(src, shadow / libname)
                        artifact_sources[libname] = src

        # 2) 重写整条 dependency_libs 闭包 + libdir。
        total = 0
        dropped = []
        for name, archive in archives_by_name.items():
            content = archive.read_text(encoding="utf-8")
            m = re.search(r"^dependency_libs='(.*)'$", content, flags=re.MULTILINE)
            if m is None:
                raise ConanException("%s has no dependency_libs field" % name)
            tokens, added = [], False
            for token in shlex.split(m.group(1)):
                if token.startswith("-L"):
                    d = Path(token[2:])
                    if (str(d) in known_libdirs or self._is_stale_libdir(d)
                            or not d.is_dir()):
                        if not added:
                            tokens.append("-L" + shadow_str)
                            added = True
                        total += 1
                    else:
                        tokens.append(token)
                    continue
                if token.endswith(".la"):
                    dep_name = (PurePosixPath(token).name if token.startswith("/")
                                else Path(token).name)
                    if dep_name not in archives_by_name:
                        # 目标 .la 在本图里根本不存在（gettext 的 `//lib/libintl.la`
                        # 属此类：包只装了 libintl.so/.a，没装 libintl.la）⇒ 丢掉这个
                        # 已死的引用；真实库仍由 -L<dep libdir> + -l<name> 解析。
                        # ⛔ 不静默：逐条记进 shadow 的审计行与构建日志。
                        dropped.append("%s -> %s" % (name, token))
                        continue
                    tokens.append(str(shadow / dep_name))
                    total += 1
                    continue
                tokens.append(token)
            content = (content[:m.start(1)]
                       + " ".join(shlex.quote(t) for t in tokens)
                       + content[m.end(1):])
            content, n = re.subn(
                r"^libdir='.*'$",
                lambda _m: "libdir='%s'" % shadow_str,
                content, count=1, flags=re.MULTILINE)
            if n != 1:
                raise ConanException("%s has no unique libdir field" % name)
            (shadow / name).write_text(content, encoding="utf-8", newline="\n")

        # 3) 自检：sanitized 闭包里的 .la 必须真实存在（否则等于把坏元数据搬家）。
        for sh in shadow.glob("*.la"):
            content = sh.read_text(encoding="utf-8")
            m = re.search(r"^dependency_libs='(.*)'$", content, flags=re.MULTILINE)
            for token in shlex.split(m.group(1)):
                if token.endswith(".la") and not Path(token).is_file():
                    raise ConanException(
                        "sanitized %s has a missing archive: %s" % (sh.name, token))
        self.output.info(
            "gammastep: libtool shadow = %d archives, %d path replacements, "
            "%d dead .la refs dropped -> %s"
            % (len(archives_by_name), total, len(dropped), shadow_str))
        for d in dropped:
            self.output.info("gammastep: dropped dead .la ref: %s" % d)
        return shadow_str

    @staticmethod
    def _is_stale_libdir(path):
        """判断 -L 目标是否指向别的构建机的 conan 缓存（含 prefix=/ 的 `//lib`）。"""
        s = path.as_posix()
        return ("/.conan2/" in s or s.startswith("//lib")
                or "/conan2/p/" in s or s.startswith("/lib"))


    def _scanner_pc_dir(self):
        return os.path.join(self.generators_folder, "fixed_pkgconfig")

    def _scanner_bin(self):
        return os.path.join(self.build_folder, "scanner-bin", "wayland-scanner")

    def _write_scanner_pc(self):
        pc_dir = self._scanner_pc_dir()
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "wayland-scanner.pc"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(
                "bindir=%s\n"
                "wayland_scanner=${bindir}/wayland-scanner\n"
                "\n"
                "Name: wayland-scanner\n"
                "Description: Wayland scanner (static, OHOS)\n"
                "Version: 1.24.0\n"
                % os.path.dirname(self._scanner_bin())
            )

    # ── wayland-scanner 静态重建 ────────────────────────────────────────────
    def _find_expat_static(self):
        """按序查找 libexpat.a（依赖包内 → OHOS SDK），找不到显式报错。"""
        candidates = []
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(
                    os.path.join(dep.package_folder, "lib", "libexpat.a"))
        candidates.append(
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a")
        for c in candidates:
            if os.path.isfile(c):
                return c
        raise ConanException(
            "gammastep: libexpat.a not found for the static wayland-scanner")

    def _find_expat_include(self):
        for c in ["/data/service/hnp/expat.org/expat_2.7.3/include"]:
            if os.path.isfile(os.path.join(c, "expat.h")):
                return c
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                p = os.path.join(dep.package_folder, "include")
                if os.path.isfile(os.path.join(p, "expat.h")):
                    return p
        raise ConanException(
            "gammastep: expat.h not found for the static wayland-scanner")

    def _build_static_scanner(self):
        """静态编译 wayland-scanner（脱离 wayland 的 meson 构建系统，手工命令行）。

        只编 `scanner.c` + `wayland-util.c`（scanner 只用 expat；libxml2 只被上游
        测试的 DTD 校验用）。`wayland-version.h` 由 `.h.in` 模板手工补齐。
        """
        src = os.path.join(self.source_folder, "wayland-scanner-src")
        scanner_bin = self._scanner_bin()
        if os.path.isfile(scanner_bin):
            self.output.info("gammastep: static wayland-scanner already built, skip")
            return
        os.makedirs(os.path.dirname(scanner_bin), exist_ok=True)
        ver = "1.24.0"
        major, minor, micro = ver.split(".")
        h_in = os.path.join(src, "src", "wayland-version.h.in")
        if os.path.isfile(h_in):
            with open(h_in, "r", encoding="utf-8") as f:
                content = f.read()
            for key, val in [("@WAYLAND_VERSION@", ver),
                             ("@WAYLAND_VERSION_MAJOR@", major),
                             ("@WAYLAND_VERSION_MINOR@", minor),
                             ("@WAYLAND_VERSION_MICRO@", micro)]:
                content = content.replace(key, val)
            with open(os.path.join(src, "src", "wayland-version.h"), "w",
                      encoding="utf-8") as f:
                f.write(content)
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        self.run(
            f'"{cc}" -o "{scanner_bin}" '
            f'-I"{src}/src" '
            f'"{src}/src/scanner.c" "{src}/src/wayland-util.c" '
            f'-I"{expat_inc}" "{expat_lib}" -lm -lpthread -static',
            env="conanbuild",
        )
        self.output.info("gammastep: static wayland-scanner built -> %s" % scanner_bin)

    # ── autotools bootstrap ────────────────────────────────────────────────
    def _intltool_shim_dir(self):
        """返回一个含改写后 `intltoolize` 的目录（前缀指向 intltool 包）。

        `autoreconf -fi` 会执行 `intltoolize`，而 conan intltool 包的脚本把
        `prefix=/` 烧死 ⇒ 去找 `//share/intltool/Makefile.in.in` 并报
        "intltoolize: cannot copy …"。intltoolize 不依赖 $0 推导路径 ⇒ PATH wrapper
        无用，必须**复制脚本并改写那一个常量**（l3afpad/ddccontrol 同款 shim）。
        """
        intltool_bin = None
        intltool_root = None
        for dep in self.dependencies.build.values():
            if dep.ref.name != "intltool" or not dep.package_folder:
                continue
            cand = os.path.join(dep.package_folder, "bin", "intltoolize")
            if os.path.isfile(cand):
                intltool_bin = cand
                intltool_root = dep.package_folder
                break
        if not intltool_bin:
            raise ConanException("intltoolize not found in the intltool package")
        shim_dir = os.path.join(self.build_folder, "toolshim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "intltoolize")
        with open(intltool_bin, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        if "prefix=/" not in text:
            raise ConanException(
                "unexpected intltoolize layout: no 'prefix=/' constant to rewrite")
        text = re.sub(r"^prefix=/", "prefix=%s" % intltool_root, text,
                      count=1, flags=re.M)
        with open(shim, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)
        os.chmod(shim, 0o755)
        self.output.info("intltoolize shim prefix -> %s" % intltool_root)
        return shim_dir

    def _bootstrap_configure(self):
        """运行 `autoreconf -fi` —— git tag archive 不含 configure。"""
        if os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("configure already present, skipping autoreconf")
            return
        shim_dir = self._intltool_shim_dir()
        self.run('PATH="%s:$PATH" autoreconf -fi' % shim_dir,
                 cwd=self.source_folder, env="conanbuild")

    def _patch_configure_generated(self):
        """对刚生成的 configure 做两处幂等补丁（都是构建产物、不改上游源码）。

        (a) `umask 077` → `022`：config.status 用
        `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录，在 setgid 的 hmdfs 卷上
        建出 0700 目录后**连创建者自己都写不进去** ⇒
        `can't create ./confXXXXXX/subs1.awk: Permission denied`（E110/E112；
        l3afpad/appres/pmount/ddccontrol 先例）。

        (b) 绕过 intltool.m4 的 XML::Parser 探测：intltool.m4 以
        `if test "x$2" != "xno-xml"` 守卫该块（intltool 官方 off-switch 是第二参数
        `no-xml`），生成的 configure 里该字面量恰好出现一次 ⇒ 反转为 `=` 即跳过。
        跳过在本包是正确的：本机 perl 完全没有 XML::Parser（`perl -MXML::Parser`
        → rc=2），且 `--disable-gui` 后树内**零 xml.in 消费者**（klavaro 另需 `-x`
        merge shim 是因为它有 klavaro.appdata.xml.in，本包没有）。同 klavaro/3.14
        的 patch0001 逐字同款做法。
        """
        path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(path):
            raise ConanException("configure not found after autoreconf")
        with open(path, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()

        if "umask 077" in text:
            text, n = re.subn(r"umask 077", "umask 022", text)
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(text)
            self.output.info("patched %d umask 077 occurrence(s) in configure" % n)
        else:
            self.output.info("configure has no umask 077 (nothing to patch)")

        guard = 'if test "x" != "xno-xml"; then'
        if guard in text:
            text = text.replace(guard, 'if test "x" = "xno-xml"; then')
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(text)
            self.output.info("bypassed XML::Parser probe (intltool.m4 no-xml off-switch)")
        elif 'if test "x" = "xno-xml"; then' in text:
            self.output.info("XML::Parser probe already bypassed")
        else:
            raise ConanException(
                "intltool no-xml guard not found in generated configure — "
                "unexpected intltool.m4 layout, refusing to configure blindly")

    # ── build / package ────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        # scanner 必须在 configure 之前就位：configure 只读 .pc 里的路径变量，
        # 真正的生成动作在 make 期，但先建好可让首错落在确定的位置。
        self._build_static_scanner()
        self._bootstrap_configure()
        self._patch_configure_generated()
        autotools = Autotools(self)
        autotools.configure()
        # -j1：hmdfs 的 jobserver fifo 报 EPERM（E074），并行构建失败。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # CLI 包：产物 bin/gammastep（+ 翻译 catalog 与 man page）。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
