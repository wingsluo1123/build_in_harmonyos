#!/usr/bin/env python3
"""Conan recipe for imv 5.0.1 — Meson (C99) on HarmonyOS PC (OHOS / aarch64 / musl / libc++).

imv 是一个 X11/Wayland 图像查看器（C + Meson），产出 bin/imv（窗口客户端）、
bin/imv-msg（IPC 电容）与 contrib 的 bin/imv-dir，并安装 etc/imv_config 与
share/applications/*.desktop。

OHOS 适配要点
-------------
1. **窗口系统 = wayland-only（`-Dwindows=wayland`）**。上游 meson_options.txt 只有
   `windows`（combo: all|wayland|x11），**没有 `x11` 布尔选项**（源码为准）：
   `-Dx11=disabled` 会直接 "Unknown option"。选 wayland 的依据是两条实测：
   (a) 本机（HarmonyOS PC）`/system/lib64` 无 libX11/libxcb/libwayland-client，
       即 X11 与 Wayland 运行环境都不存在，而只有 libEGL.so + libGLESv3.so；
   (b) X11 路在本仓**结构性不可行**：libxkbcommon/1.6.0 配方显式禁用 x11 模块
       （无 xkbcommon-x11.pc），而 meson.build 的 deps_for_x11 硬需
       `dependency('xkbcommon-x11')`。wayland-only 同时使 target_single_ws=true，
       因此可执行名就是 `imv`（不是 imv-wayland）。
   运行期无 Wayland compositor ⇒ GUI 面不可测，按 R51 逐条披露（见 notes.md）。

2. **GL：`dependency('gl')` → gl4es/1.1.6**。ohpcd 无 `opengl/4.6`（W0 实测
   `conan download --only-recipe opengl/4.6` MISS），本仓既定替代是 gl4es。
   imv 的画布是**桌面 GL 1.x 固定管线**（canvas.c 用 glBegin/glVertex2i/
   glTexCoord2f/glOrtho/glPushMatrix），GLES2 头里没有这些符号 ⇒ 必须走 gl4es
   （它把固定管线翻译到 GLES2/EGL），不能用 gles2/2.0.25。gl4es 只装 libGL.so +
   include/GL，不装 .pc，所以配方自建 `gl.pc` 指向 gl4es 包并在
   PKG_CONFIG_PATH 置顶 —— 上游 meson.build 零改动。

3. **EGL：`dependency('egl')` → egl/1.0.5**。实测 gl4es 的 libGL.so **不导出 EGL
   API**（`llvm-nm -D --defined-only` 里 `T egl*` 命中 0 个，只有数据符号 egl），
   故 EGL 必须由 egl/1.0.5（静态 libEGL.a，dlopen 转发系统 /system/lib64/libEGL.so）
   提供；同样自建 `egl.pc`。gl4es 与 egl/1.0.5 都不带 pkg-config 文件。

4. **wayland-scanner 必须静态重建**。制品仓 wayland/1.24.0 包自带
   bin/wayland-scanner 在本机不可执行：实测 rc=126 / `Operation not permitted`，
   `llvm-readelf -d` 显示其 DT_NEEDED 是构建机 conan 缓存绝对路径
   （…/.cache/conan2/p/expat*/p/lib/libexpat.so）且缺 libxml2.so.16。
   按 DRAFT-ohos-static-tool-bypass-dlopen-limit（chayang/0.1.0、gammastep/2.0.9
   两个先例）从 wayland 1.24.0 源码静态编译（仅依赖 libc），并自建
   wayland-scanner.pc 顶到最前。

5. **.pc prefix 修正**：ohpcd 的 .pc prefix 是 `/`、`/usr/local`、
   `/opt/libjpeg-turbo` 或构建机缓存路径（实测 libpng.pc=/, libwebpdecoder.pc=
   /usr/local, libturbojpeg.pc=/opt/libjpeg-turbo, wayland*.pc=/）。全部复制到
   fixed_pkgconfig 并改写 prefix/exec_prefix/libdir/includedir 指向真实包目录，
   置顶 PKG_CONFIG_PATH。wayland-protocols.pc 另作（pkgdatadir 决定协议 XML 路径）。

6. **上游测试真实执行**：`-Dtest=enabled` → cmocka/2.0.2 + xxd（/usr/bin/xxd 实测存在）；
   meson.build 注册 3 个测试目标（test_list / test_navigator / test_backends），
   内含 6 条 cmocka_unit_test 声明（其中 test_navigator.c 的
   test_navigator_add_remove 在上游源码里被注释掉 ⇒ live 5 条）。
   build() 内 `meson.test()` 真实执行，失败即抛出（不吞错误）。
   本机 build==host（同 profile）⇒ conan 判为非 cross，meson 原生跑測試。

7. **后端取舍（显式，不静默）**：
   - 启用：farbfeld / libtiff / libpng / libjpeg / librsvg / libnsgif /
     libnsbmp / libheif / libwebp（全部显式 =enabled，缺依赖即 configure 硬失败）；
   - `libjxl=disabled`：W0 实测 ohpcd 未发布 libjxl/0.11.2（`conan download
     --only-recipe libjxl/0.11.2` 与 `libjxl/0.11.2@ohpcd/stable` 双形态均 MISS）；
   - `qoi=disabled`：上游用 `cc.has_header('qoi.h')` 探测**系统头**（不认 pkg-config），
     OHOS sysroot 无 qoi.h。

8. **E077 签名**：meson install 会就地改写 ELF 的 RUNPATH（构建机绝对路径→占位符），
   这使链接器写入的 `.codesign` 失效 ⇒ 内核拒绝 execve（报错不含 codesign 字样）。
   package() 末尾对 bin/imv、bin/imv-msg 重新 `binary-sign-tool sign -selfSign 1`。

9. **版本 pin / override**（全部为消解图冲突或对齐已发布 binary，W0/W2 实测）：
   pango/1.50.14.1.1（librsvg 定点）、libwebp/1.6.0 与 libtiff/4.7.2
   （libtiff/gdk-pixbuf 定点）、libtiff/4.7.2（gdk-pixbuf/2.44.6.1 定点，避免
   与 libtiff/4.7.2.2 冲突）；override：expat/2.8.2.1（wayland 定 2.8.2 vs
   libxml2 定 2.8.2.1）、libxml2/2.15.3.1（wayland 定 2.15.3 vs librsvg 定
   2.15.3.1）、libxrender/0.9.12.1（cairo-gobject override libx11→6.4.0 后，
   libxrender/0.9.12 的已发布 binary 因 package_id 变化缺失，`--build=never`
   硬失败；0.9.12.1 的已发布 binary 正是 libx11/6.4.0 世代）。
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# wayland release used to build the embedded static wayland-scanner.
# Must equal the `wayland/...` requirement (protocol code and runtime library
# have to come from the same release).
SCANNER_WAYLAND_VERSION = "1.24.0"

# Backends explicitly switched on (missing dependency => configure hard error,
# so a shrinking backend set can never be silent).
_ENABLED_BACKENDS = (
    "farbfeld",
    "libtiff",
    "libpng",
    "libjpeg",
    "librsvg",
    "libnsgif",
    "libnsbmp",
    "libheif",
    "libwebp",
)

# ── OHOS pthread-cancellation compatibility layer ────────────────────────
# imv's shutdown path is a real cancel->join pair (src/imv.c:1242
# `pthread_cancel(pipe_stdin_thread)` immediately followed by `pthread_join`).
# OHOS misses the POSIX cancellation API on three levels at once. The handling
# follows the formal knowledge entry **E513** (rec_approach
# "guarded-signal-thread-exit": install a narrowly scoped thread-exit handler,
# then pthread_kill(thread, SIGUSR1) and join); this package differs from E513
# only in delivery form - E513 is a source patch, here it is injected from the
# recipe with zero upstream edits - and in keeping real cancel semantics by
# exiting with PTHREAD_CANCELED. Per 手册/03 §6.2 note 2 that makes this a
# `create` (an extra可选路径 + its适用面), documented as
# knowledge/drafts/DRAFT-imv-5.0.1-pthread-cancel-ohos-nonRT-signal-shim.{kv,md}.
# See notes.md §12b for the dedup record.
#   ① the SDK sysroot <pthread.h> does not declare pthread_cancel at all
#      (measured: `grep -c pthread_cancel <sysroot>/usr/include/pthread.h` = 0),
#      so with c_std=c99 clang reports "call to undeclared function" and the
#      first real error only shows up at link time;
#   ② the sysroot's dyn-stub libc.so does not export it either
#      -> `ld.lld: error: undefined symbol: pthread_cancel`;
#   ③ the runtime /system/lib64/libc.so *does* export it, but as an empty
#      shell: pthread_cancel() returns ENOSYS(38) and the following
#      pthread_join() never returns - i.e. letting the dynamic linker resolve
#      it, or supplying a "return 0" stub, upgrades a link failure into a
#      silent hang.
# The fix is a self-hosted TU (no upstream source patch) that restores the
# contract with a *non-RT* signal: RT signals (SIGRTMIN..MAX) are silently
# swallowed on OHOS (handler never runs), SIGUSR1 works. Its handler calls
# pthread_exit(PTHREAD_CANCELED), so the cancelled thread really unblocks and
# join() returns. imv itself uses no signals at all (measured: no SIGUSR1 /
# sigaction / signal() in src/), so taking SIGUSR1 over is safe.
_CANCEL_HEADER = "pthread_cancel_compat.h"
_CANCEL_SOURCE = "pthread_cancel_compat.c"
_CANCEL_OBJECT = "pthread_cancel_compat.o"

_CANCEL_HEADER_TEXT = """\
/* OHOS pthread-cancellation declarations missing from the SDK <pthread.h>.
 * Forced into every translation unit with `-include` (see conanfile.py). */
#ifndef IMV_PTHREAD_CANCEL_COMPAT_H
#define IMV_PTHREAD_CANCEL_COMPAT_H

#include <pthread.h>

#ifdef __cplusplus
extern "C" {
#endif

int pthread_cancel(pthread_t thread);
int pthread_setcancelstate(int state, int *oldstate);
int pthread_setcanceltype(int type, int *oldtype);
void pthread_testcancel(void);

#ifdef __cplusplus
}
#endif

#endif /* IMV_PTHREAD_CANCEL_COMPAT_H */
"""

_CANCEL_SOURCE_TEXT = """\
/* OHOS pthread-cancellation compatibility layer (see conanfile.py docstring).
 * pthread_cancel() installs a SIGUSR1 handler on first use and delivers that
 * signal to the target thread; the handler calls pthread_exit(PTHREAD_CANCELED)
 * so the thread really terminates and a following pthread_join() returns.
 * SIGRTMIN..MAX cannot be used: RT signals are silently swallowed on OHOS. */
#include <pthread.h>
#include <signal.h>
#include <string.h>

#include "pthread_cancel_compat.h"

static void imv_pthread_cancel_handler(int signo)
{
  (void)signo;
  pthread_exit(PTHREAD_CANCELED);
}

int pthread_cancel(pthread_t thread)
{
  static int installed = 0;

  if (!installed) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = imv_pthread_cancel_handler;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGUSR1, &sa, NULL) != 0) {
      return -1;
    }
    installed = 1;
  }

  return pthread_kill(thread, SIGUSR1);
}

int pthread_setcancelstate(int state, int *oldstate)
{
  (void)state;
  if (oldstate) {
    *oldstate = PTHREAD_CANCEL_ENABLE;
  }
  return 0;
}

int pthread_setcanceltype(int type, int *oldtype)
{
  (void)type;
  if (oldtype) {
    *oldtype = PTHREAD_CANCEL_DEFERRED;
  }
  return 0;
}

void pthread_testcancel(void)
{
}
"""


class ImvConan(ConanFile):
    name = "imv"
    version = "5.0.1"
    description = ("imv - X11/Wayland image viewer (wayland-only build for OHOS; "
                   "gl4es desktop-GL + OHOS system EGL)")
    license = "MIT"
    homepage = "https://sr.ht/~exec64/imv/"
    url = "https://git.sr.ht/~exec64/imv"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    # ── metadata / source ────────────────────────────────────────────────

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS builds on the device itself (build == host here); Linux is
        # kept so the recipe can be sanity-checked natively.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports OHOS/Linux only (gl4es + OHOS system EGL)")

    def requirements(self):
        # meson.build deps_for_imv
        self.requires("pango/1.50.14.1.1")        # dependency('pangocairo')
        self.requires("gl4es/1.1.6")              # dependency('gl')  -> self-authored gl.pc
        self.requires("libxkbcommon/1.6.0")       # dependency('xkbcommon')
        self.requires("icu4c/77")                 # dependency('icu-uc') (unicode=icu)
        self.requires("inih/r58")                 # dependency('inih', fallback subproject)
        # deps_for_wayland
        self.requires("wayland/1.24.0")           # wayland-client / -cursor / -egl + .pc
        self.requires("wayland-protocols/1.36")   # xdg-shell + pointer-gestures XML
        self.requires("egl/1.0.5")                # dependency('egl') -> self-authored egl.pc
        # wayland-client.pc declares `Requires.private: libffi`; pkg-config
        # resolves private requires for --cflags while conan marks a pure
        # transitive dependency as "skipped binary" and never installs its .pc
        # -> promote it to a direct requirement (chayang/gammastep precedent).
        # The same "Skipped binaries" mechanism (conan 2 transform_downstream
        # sets headers=False for pure transitive nodes) hides four more .pc
        # files that the pkg-config closure of pango/librsvg/libheif requires:
        #   glib-2.0.pc  Requires.private: libpcre2-8      -> pcre2
        #   harfbuzz.pc  Requires.private: graphite2       -> graphite2
        #   libtiff-4.pc Requires.private: liblzma         -> xz
        #   libx11/libxrender/libxext.pc Requires: xproto/kbproto/renderproto/
        #   xextproto                                      -> xorgproto
        # All five are promoted to direct requirements for that reason only
        # (measured 2026-10-18: configure failed with
        #  "Package 'libpcre2-8', required by 'glib-2.0', not found").
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.45")
        self.requires("graphite2/1.3.14")
        self.requires("xz/5.6.2")
        self.requires("xorgproto/2025.1")
        # image backends (all explicitly enabled above)
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("librsvg/2.62.3.1.1")
        self.requires("libnsgif/1.0.0")
        self.requires("libnsbmp/0.1.7")
        self.requires("libheif/1.22.2")
        self.requires("libwebp/1.6.0")
        # upstream test suite (-Dtest=enabled): cmocka + xxd
        self.requires("cmocka/2.0.2")
        # version-conflict resolvers (see module docstring, point 9)
        self.requires("expat/2.8.2.1", override=True)
        self.requires("libxml2/2.15.3.1", override=True)
        self.requires("libxrender/0.9.12.1", override=True)

    def build_requirements(self):
        # the device has no system meson (measured: `command -v meson` empty);
        # the packaged one is the repo convention.
        self.tool_requires("meson/1.11.0")
        # /usr/bin/xxd on OHOS is a toybox applet: it has neither `-n` nor a
        # vim-compatible `-i` (measured: "xxd: Unknown option 'n'"), while
        # upstream meson.build embeds the two test images with
        # `xxd -n NAME -i IN OUT`. Use the packaged vim-xxd-compatible
        # tinyxxd/1.3.16, exposed under the name `xxd` (see generate()).
        self.tool_requires("tinyxxd/1.3.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # wayland sources, used only to build the static wayland-scanner
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")

    # ── toolchain helpers ────────────────────────────────────────────────

    def _c_compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if cc and os.path.isfile(cc):
            return cc
        return shutil.which("clang") or "/data/service/hnp/bin/clang"

    def _llvm_tool(self, name):
        tool_dir = os.path.dirname(self._c_compiler())
        candidate = os.path.join(tool_dir, name)
        if os.path.isfile(candidate):
            return candidate
        return shutil.which(name) or f"/data/service/hnp/bin/{name}"

    def _tinyxxd_binary(self):
        """Path of the packaged tinyxxd ELF (build context), or None."""
        try:
            folder = self.dependencies.build["tinyxxd"].package_folder
        except Exception:
            folder = None
        if folder:
            candidate = os.path.join(folder, "bin", "tinyxxd")
            if os.path.isfile(candidate):
                return candidate
        return shutil.which("tinyxxd")

    @staticmethod
    def _write_text(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    @staticmethod
    def _author_pc(path, body):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)

    # ── generate ─────────────────────────────────────────────────────────

    def generate(self):
        tc = MesonToolchain(self)
        # window system / features (upstream has no `x11` option, only `windows`)
        tc.project_options["windows"] = "wayland"
        tc.project_options["unicode"] = "icu"
        tc.project_options["test"] = "enabled"
        tc.project_options["man"] = "disabled"          # no a2x in the sandbox
        tc.project_options["contrib-commands"] = "true"
        for backend in _ENABLED_BACKENDS:
            tc.project_options[backend] = "enabled"
        tc.project_options["libjxl"] = "disabled"        # ohpcd: unpublished (W0 MISS)
        tc.project_options["qoi"] = "disabled"           # no system qoi.h on OHOS

        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)

        # PkgConfigDeps emits a .pc for every direct requirement that does not
        # ship one itself (inih, libnsgif, ...), using the conan cpp_info paths;
        # the generators folder therefore has to stay on PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()

        # OHOS pthread-cancellation compat: the header has to exist before
        # meson configure (it is force-included into every C TU), the object is
        # compiled at the start of build() and handed to the link line.
        compat_dir = self._cancel_compat_dir()
        self._write_text(os.path.join(compat_dir, _CANCEL_HEADER),
                         _CANCEL_HEADER_TEXT)
        self._write_text(os.path.join(compat_dir, _CANCEL_SOURCE),
                         _CANCEL_SOURCE_TEXT)
        tc.extra_cflags += ["-include", os.path.join(compat_dir, _CANCEL_HEADER)]
        tc.extra_ldflags += [os.path.join(compat_dir, _CANCEL_OBJECT)]

        gl4es_base = self.dependencies["gl4es"].package_folder
        egl_base = self.dependencies["egl"].package_folder
        wp_base = self.dependencies["wayland-protocols"].package_folder

        # 1. gl.pc -> gl4es (desktop GL fixed pipeline translated to GLES2).
        self._author_pc(os.path.join(fixed_pc_dir, "gl.pc"),
                        "prefix={0}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include\n\n"
                        "Name: gl\n"
                        "Description: OpenGL (gl4es GLES translation layer, OHOS)\n"
                        "Version: 1.1.6\n"
                        "Libs: -L${{libdir}} -lGL\n"
                        "Cflags: -I${{includedir}}\n".format(gl4es_base))

        # 2. egl.pc -> egl/1.0.5 (static libEGL.a forwarding /system/lib64/libEGL.so).
        self._author_pc(os.path.join(fixed_pc_dir, "egl.pc"),
                        "prefix={0}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include\n\n"
                        "Name: egl\n"
                        "Description: EGL 1.5 (OHOS system EGL forwarding backend)\n"
                        "Version: 1.0.5\n"
                        "Libs: -L${{libdir}} -lEGL\n"
                        "Libs.private: -ldl\n"
                        "Cflags: -I${{includedir}}\n".format(egl_base))

        # 3. wayland-scanner.pc -> the static scanner built in build().
        #    pkgdatadir is irrelevant here; `wayland_scanner` is what meson's
        #    unstable-wayland module reads (find_tool).
        self._author_pc(os.path.join(fixed_pc_dir, "wayland-scanner.pc"),
                        "prefix={0}\n"
                        "bindir=${{prefix}}\n"
                        "wayland_scanner=${{bindir}}/wayland-scanner\n\n"
                        "Name: Wayland Scanner\n"
                        "Description: Wayland scanner (static, OHOS)\n"
                        "Version: {1}\n".format(self.generators_folder,
                                               SCANNER_WAYLAND_VERSION))

        # 4. wayland-protocols.pc with a working pkgdatadir (the packaged one
        #    carries the packaging machine's cache path in `prefix`).
        self._author_pc(os.path.join(fixed_pc_dir, "wayland-protocols.pc"),
                        "prefix={0}\n"
                        "datarootdir=${{prefix}}/share\n"
                        "pkgdatadir=${{datarootdir}}/wayland-protocols\n\n"
                        "Name: Wayland Protocols\n"
                        "Description: Wayland protocol files\n"
                        "Version: 1.36\n".format(wp_base))

        # 5. every dependency .pc: prefix= is "/", "/usr/local",
        #    "/opt/libjpeg-turbo" or a packaging-machine cache path -> copy with
        #    prefix/exec_prefix/libdir/includedir rewritten to the real package
        #    folder, and put that copy first on PKG_CONFIG_PATH.
        pc_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            for pc_dir in ("lib", "share"):
                pc = os.path.join(dep.package_folder, pc_dir, "pkgconfig")
                if not os.path.isdir(pc):
                    continue
                pc_paths.append(pc)
                for pc_name in os.listdir(pc):
                    if not pc_name.endswith(".pc"):
                        continue
                    if pc_name in ("wayland-scanner.pc",
                                   "wayland-protocols.pc"):
                        continue  # the two self-authored files must win
                    base = dep.package_folder
                    with open(os.path.join(pc, pc_name), "r",
                              encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    # NB: several packages write "prefix = /" with spaces
                    # around '=' (measured: icu4c/77's icu-uc.pc), so the
                    # pattern has to tolerate whitespace - otherwise the file
                    # keeps prefix=/ and the link line ends up with -L//lib
                    # ("unable to find library -licuuc").
                    content = re.sub(r"(?m)^prefix\s*=.*$",
                                     f"prefix={base}", content)
                    content = re.sub(r"(?m)^exec_prefix\s*=.*$",
                                     f"exec_prefix={base}", content)
                    content = re.sub(r"(?m)^libdir\s*=.*$",
                                     f"libdir={base}/lib", content)
                    content = re.sub(r"(?m)^includedir\s*=.*$",
                                     f"includedir={base}/include", content)
                    content = re.sub(r"/[^\"\s]*/p/b/[^/\s]+/p", base, content)
                    # some packaged .pc files expand ${libdir} at their own
                    # configure time with a "/" prefix and therefore carry a
                    # literal -L//lib in Libs: (measured: freetype2/2.14.3 ->
                    # "Libs: -L//lib -lfreetype"). Point such -L flags at the
                    # package's real libdir instead.
                    content = re.sub(
                        r"-L(/[^\s\"']*)",
                        lambda m: ("-L${libdir}"
                                   if m.group(1).startswith("//")
                                   or not os.path.isdir(m.group(1))
                                   else m.group(0)),
                        content)
                    # librsvg is packaged as a **static** archive
                    # (librsvg-2.a): everything it references has to sit on the
                    # link line. Its .pc keeps the whole closure in
                    # Requires.private, which pkg-config does *not* expand for
                    # --libs, so the first attempt failed with
                    # "undefined symbol: cairo_gobject_line_join_get_type" and
                    # then "... xmlParseDocument" (libxml2). Promote the whole
                    # private closure to a public Requires: entry in this copy
                    # (no upstream source change; meson then also emits the
                    # matching -rpath entries).
                    if pc_name == "librsvg-2.0.pc":
                        pub = re.search(r"(?m)^Requires:(.*)$", content)
                        priv = re.search(r"(?m)^Requires\.private:(.*)$", content)
                        if priv:
                            extra = priv.group(1).strip()
                            if pub:
                                content = content.replace(
                                    pub.group(0),
                                    f"Requires:{pub.group(1)}, {extra}")
                            else:
                                content += f"\nRequires: {extra}\n"
                            content = re.sub(
                                r"(?m)^Requires\.private:.*$\n?", "", content)
                            self.output.info(
                                "imv: promoted librsvg-2.0.pc Requires.private "
                                "into Requires (static librsvg archive)")
                    # icu4c/77 ships only static .a files and is a C++
                    # implementation, so a C consumer has to pull in the C++
                    # runtime explicitly (same handling as cif-api/0.4.2:
                    # "ICU 是 C++ 库 ... 需 -lc++ 提供 __gxx_personality_v0").
                    if pc_name == "icu-uc.pc" and "-lc++" not in content:
                        content = re.sub(r"(?m)^Libs:(.*)$",
                                         r"Libs:\1 -lc++", content)
                        self.output.info("imv: appended -lc++ to icu-uc.pc")
                    with open(os.path.join(fixed_pc_dir, pc_name), "w",
                              encoding="utf-8", newline="\n") as f:
                        f.write(content)
        tc.pkg_config_path = os.pathsep.join(
            [fixed_pc_dir, self.generators_folder] + pc_paths)

        # fail loudly instead of letting a stale prefix surface much later as
        # "unable to find library -licuuc" / "-lfreetype" (the -L//lib shape)
        broken = []
        for pc_name in sorted(os.listdir(fixed_pc_dir)):
            with open(os.path.join(fixed_pc_dir, pc_name), "r",
                      encoding="utf-8", errors="replace") as f:
                head = f.read()
            for m in re.finditer(
                    r"(?m)^(prefix|libdir|includedir)\s*=\s*(\S+)\s*$", head):
                value = m.group(2)
                if "$" in value:
                    continue
                if not os.path.isdir(value):
                    broken.append(f"{pc_name}:{m.group(1)}={value}")
            for m in re.finditer(r"-L(/[^\s\"']*)", head):
                value = m.group(1)
                if not os.path.isdir(value):
                    broken.append(f"{pc_name}:-L{value}")
        if broken:
            raise ConanException(
                "imv: rewritten .pc files still point at non-existent "
                f"directories: {', '.join(broken)}")

        # meson derives the executables' -rpath entries from the *direct*
        # pkg-config dependencies only, so the transitive shared libraries of
        # pango/cairo/libtiff/fontconfig (libfribidi, libpixman-1, libzstd,
        # libexpat) were not reachable when the test binaries ran (measured:
        # "imv:test_backends FAIL exit status 127 - Error loading shared
        # library libfribidi.so.0 ... symbol not found"). Add one -rpath per
        # dependency libdir: the build-time equivalent of conan's runenv.
        # LD_LIBRARY_PATH cannot be used for this: conan's libintl proxy would
        # shadow the system one and break python3/meson itself (measured:
        # "libpython3.14.so.1.0: libintl_dgettext: symbol not found").
        rpath_dirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for sub in (dep.cpp_info.libdirs or ["lib"]):
                libdir = os.path.join(dep.package_folder, sub)
                if os.path.isdir(libdir) and libdir not in rpath_dirs:
                    rpath_dirs.append(libdir)
        tc.extra_ldflags += [f"-Wl,-rpath,{d}" for d in rpath_dirs]
        tc.generate()

        # OHOS sandbox: meson cannot find llvm-ar/ranlib/ninja on its own
        # (wayland/zix/serd precedent) -> inject absolute paths into the
        # generated meson machine file's [binaries] section. `xxd` is injected
        # there too: meson resolves find_program() through the machine file's
        # [binaries] entry first, which is deterministic (PATH order is not:
        # /usr/bin/xxd is a toybox applet that lacks -n/-i).
        ar_path = self._llvm_tool("llvm-ar")
        ranlib_path = self._llvm_tool("llvm-ranlib")
        ninja_path = shutil.which("ninja") or "/data/service/hnp/bin/ninja"
        tinyxxd = self._tinyxxd_binary()
        if not tinyxxd:
            raise ConanException(
                "imv: tinyxxd (build requirement) not found; the upstream test "
                "image generator needs a vim-xxd compatible `xxd -n NAME -i`")
        native_file = os.path.join(self.generators_folder,
                                   "conan_meson_native.ini")
        with open(native_file, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace(
            "[binaries]\nc =",
            f"[binaries]\nar = '{ar_path}'\nranlib = '{ranlib_path}'\n"
            f"ninja = '{ninja_path}'\nxxd = '{tinyxxd}'\nc =")
        with open(native_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        # meson 1.12+ prefers the NINJA env var over PATH
        env = Environment()
        env.define("NINJA", ninja_path)
        # second line of defence: expose the packaged tinyxxd under the name
        # upstream's generator looks up (find_program('xxd')) as well
        xxd_dir = os.path.join(self.generators_folder, "toolshim")
        os.makedirs(xxd_dir, exist_ok=True)
        link = os.path.join(xxd_dir, "xxd")
        if os.path.islink(link) or os.path.isfile(link):
            os.remove(link)
        os.symlink(tinyxxd, link)
        env.prepend_path("PATH", xxd_dir)
        # lld shipped with the OHOS SDK NEEDs libxml2.so.16 from llvm/lib;
        # without it every link step fails to start the linker.
        llvm_lib = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                    "ohos/native/llvm/lib")
        if os.path.isdir(llvm_lib):
            env.append_path("LD_LIBRARY_PATH", llvm_lib)
        env.vars(self).save_script("conanbuild_env")

    # ── pthread cancellation compat ──────────────────────────────────────

    def _cancel_compat_dir(self):
        return os.path.join(self.generators_folder, "compat")

    def _build_cancel_compat(self):
        """Compile the pthread-cancellation TU before meson configure runs.

        The object is added to the link line through MesonToolchain
        ``extra_ldflags``, so it has to exist before meson's configure-time
        sanity check links.
        """
        compat_dir = self._cancel_compat_dir()
        src = os.path.join(compat_dir, _CANCEL_SOURCE)
        obj = os.path.join(compat_dir, _CANCEL_OBJECT)
        cc = self._c_compiler()
        self.run(f"{cc} -O2 -fPIC -c {src} -o {obj} -I{compat_dir}",
                 env="conanbuild")
        if not os.path.isfile(obj):
            raise ConanException(
                f"imv: pthread-cancel compat object was not produced: {obj}")
        self.output.info(f"imv: built pthread-cancel compat {obj}")

    # ── static wayland-scanner ───────────────────────────────────────────
    def _find_expat_static(self):
        candidates = ["/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a"]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                self.output.info(f"imv: static expat -> {c}")
                return c
        raise ConanException(
            "imv: no static libexpat.a found for the static wayland-scanner "
            f"link; tried: {candidates}")

    def _find_expat_include(self):
        candidates = ["/data/service/hnp/expat.org/expat_2.7.3/include"]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat" and dep.package_folder:
                candidates.append(os.path.join(dep.package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_static_scanner(self):
        src = os.path.join(self.source_folder, "wayland-scanner-src")
        if not os.path.isdir(src):
            raise ConanException(f"imv: wayland scanner sources missing: {src}")

        # config.h / wayland-version.h are normally produced by wayland's own
        # build system; write the minimal forms by hand.
        config_h = os.path.join(src, "config.h")
        with open(config_h, "w", encoding="utf-8", newline="\n") as f:
            f.write("#define HAVE_EXPAT 1\n"
                    "#define PACKAGE \"wayland\"\n"
                    f"#define VERSION \"{SCANNER_WAYLAND_VERSION}\"\n")

        version_in = os.path.join(src, "src", "wayland-version.h.in")
        version_h = os.path.join(src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in (("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)):
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

        # the XML DTD is embedded through the upstream embed.py helper
        dtd_h = os.path.join(src, "src", "wayland.dtd.h")
        self.run(f"python3 {src}/src/embed.py {src}/protocol/wayland.dtd "
                 f"wayland_dtd > {dtd_h}", env="conanbuild")

        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = self._c_compiler()
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f"{cc} -o {scanner_bin} "
            f"-include {config_h} "
            f"-I{src} -I{src}/src -I{src}/protocol "
            f"{src}/src/scanner.c {src}/src/wayland-util.c "
            f"{inc_flag}{expat_lib} "
            f"-lm -lpthread -static",
            env="conanbuild")
        self.output.info(f"imv: built static wayland-scanner ({scanner_bin})")

    # ── build ────────────────────────────────────────────────────────────

    def build(self):
        # both must happen before meson configure(): the wayland module resolves
        # the scanner during configure, and the compat object is already on the
        # link line of the configure-time sanity check
        self._build_cancel_compat()
        self._build_static_scanner()

        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # upstream test suite: 3 meson test targets / 5 live cmocka cases.
        # Failures propagate (no swallowing) - rule4 requires real execution.
        meson.test()

    # ── packaging ────────────────────────────────────────────────────────

    def _find_sdk_tool(self, name):
        env_name = "OHOS_" + name.upper().replace("-", "_")
        for candidate in (os.environ.get(env_name), shutil.which(name),
                          f"/data/service/hnp/bin/{name}"):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign_ohos_binary(self, path):
        """Give `path` a valid `.codesign` section (OHOS exec precondition, E077).

        `meson install` rewrites every ELF in place (absolute RUNPATHs ->
        placeholders), which invalidates the `.codesign` placeholder written by
        the linker; the kernel then refuses to execve the file.
        """
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return
        signer = self._find_sdk_tool("binary-sign-tool")
        if not signer:
            raise ConanException(
                "imv: binary-sign-tool not found; an unsigned ELF cannot be "
                "executed on OHOS (E077)")
        objcopy = self._find_sdk_tool("llvm-objcopy")
        if objcopy:
            self.run(f'{objcopy} --remove-section .codesign "{path}" '
                     f"2>/dev/null || true")
        signed = path + ".signed"
        self.run(f'{signer} sign -inFile "{path}" -outFile "{signed}" '
                 f"-selfSign 1")
        if not os.path.isfile(signed):
            raise ConanException(
                f"imv: binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)
        self.output.info(f"imv: signed {path}")

    def package(self):
        meson = Meson(self)
        meson.install()
        for name in ("imv", "imv-msg"):
            binary = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(binary):
                os.chmod(binary, 0o755)
                self._sign_ohos_binary(binary)

    def package_info(self):
        # R38: command line / GUI application -> software-level commands.json
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # runtime: gl4es dlopen()s its GLES/EGL backend via these vars
        # (/system/lib64 has libEGL.so + libGLESv3.so but no libGLESv2.so)
        self.runenv_info.define("LIBGL_GLES", "/system/lib64/libGLESv3.so")
        self.runenv_info.define("LIBGL_EGL", "/system/lib64/libEGL.so")
