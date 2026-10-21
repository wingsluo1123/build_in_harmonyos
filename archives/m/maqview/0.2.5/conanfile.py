#!/usr/bin/env python3
"""Conan recipe — maqview 0.2.5（MAQ 比对结果可视化查看器，OpenHarmony/HarmonyOS 适配）。

上游：maqview 0.2.5（Jue Ruan / Heng Li / Mengyao Zhao，GPL-2.0）。
C++/OpenGL/GLUT：`maqview`（GUI 查看器）与 `maqindex_socks`（socket 前端）链接
GL/GLUT；`maqindex`、`zrio` 是无 GL 的命令行工具。构建系统为 autotools
（configure.ac + Makefile.am；tarball 不含生成的 configure，需 autoreconf）。

OHOS 适配要点
-------------
1. **GL 栈**：OHOS 只提供 OpenGL ES（`libGLESv2.so`），且导出的立即模式入口
   （`glBegin`/`glVertex3f`/`glMatrixMode`/`glOrtho`/选择模式…）在 ES 里不存在。
   maqview 的渲染层（gl_gui.c / MainFrame.c / view_panel.c）通篇是桌面 GL 立即
   模式 + 选择模式拾取，故本配方链接制品仓的 **mesa/24.3.4.1**：它交付
   `libOSMesa.so` + `libglapi.so`（实测联合导出上述全部桌面 GL 入口）与桌面
   `GL/gl.h`。该版本包**没有独立 `libGL.so`**（`conan list mesa/24.3.4.1`
   的 lib 目录只有 libOSMesa/libglapi），而带 libGL 的 `mesa/24.3.4.1.1.1`
   会与 `glu/9.0.3` 的 `mesa/24.3.4.1` pin 直接版本冲突
   （实测 `Version conflict`），故 GLLIBS 用 `-lOSMesa -lglapi`。
   `glu/9.0.3` 提供 `gluPickMatrix`；`freeglut/3.6.0` 提供 GLUT
   （OHOS 制品为 EGL/GLES 版 `libfreeglut-gles.so`）。三个依赖版本相互一致
   （glu/9.0.3 自身 pin 的正是 mesa/24.3.4.1）。
2. **无 X 显示**：构建只做编译+链接，不创建真实窗口。运行期验证走无头路线
   （mesa 的 OSMesa 离屏上下文跑立即模式渲染 + 直接执行打包出的二进制），
   不需要 X server/display。
3. **configure.ac 补丁**（见 conandata.yml）：取消“任何 --prefix 即静态链接
   libglut 并覆盖 CPPFLAGS/LDFLAGS”的分支（conan 必传 --prefix，会清空依赖
   路径）、`AM_CONFIG_HEADER` → `AC_CONFIG_HEADERS`、GLUT 探测/链接改用
   `libfreeglut-gles` 并补 `-lGLU`。
4. **OHOS autotools 落地**：tarball 只有 configure.ac，构建前在源目录
   `autoreconf -fi`；生成的 configure 里的 `umask 077` 在 hmdfs 上会让临时
   目录不可遍历（chmod 在 hmdfs 上是 no-op），改回 022。
5. **签名**：`os == "OHOS"` 时对打包出的每个实体 ELF 用 `binary-sign-tool`
   自签（先 `llvm-objcopy --remove-section .codesign` 清旧段），随后 `readelf -S`
   断言恰好 1 个 `.codesign` 段，fail-closed；`os.chmod` 恢复 0755。
"""
import glob
import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")

# 设备 hnp 工具链目录：clang/make/bash/autoconf/m4/perl(5.42.0) 都在这里
DEVICE_TOOLCHAIN_BIN = "/data/service/hnp/bin"

# 桌面 GL 栈（版本相互一致：glu/9.0.3 pin mesa/24.3.4.1）
GL_DEPS = ("mesa", "glu", "freeglut")

# 打包产出的可执行文件（Makefile.am: bin_PROGRAMS）
BIN_PROGRAMS = ("maqview", "maqindex", "zrio", "maqindex_socks")


class MaqviewConan(ConanFile):
    name = "maqview"
    version = "0.2.5"
    description = ("maqview 0.2.5 — MAQ 比对结果查看器（OpenGL/GLUT GUI + "
                   "maqindex/zrio 命令行工具），OpenHarmony/HarmonyOS 适配")
    license = "GPL-2.0-only"
    homepage = "https://maq.sourceforge.net/maqview.shtml"
    url = "https://deb.debian.org/debian/pool/main/m/maqview/maqview_0.2.5.orig.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"maqview is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # 桌面 GL（libGL.so + GL/gl.h，含立即模式/选择模式）与 OSMesa
        self.requires("mesa/24.3.4.1")
        # GLU（gluPickMatrix）
        self.requires("glu/9.0.3")
        # GLUT（OHOS 制品 libfreeglut-gles.so）
        self.requires("freeglut/3.6.0")

    def build_requirements(self):
        # tarball 只带 configure.ac / Makefile.am，构建前必须 autoreconf。
        # 只从制品仓取 automake：设备自带 autoconf 2.72 / m4 / perl 5.42.0（hnp
        # 工具链，与 clang/make/bash 同源），而 conan 的 autoconf 制品脚本 shebang
        # 指向 **conan perl 5.42.2**，与设备上 automake 脚本用的系统 perl 5.42.0
        # 的 XS 模块 ABI 不兼容（实测 `strict.pm` / `Perl_my_cxt_init` 报错）。
        # 详见 notes.md §3.6。
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 构建 ────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        self._relax_umask_in_configure()
        self._configure()
        self._make()

    def package(self):
        self._make_install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._fix_bin_permissions()
        self._sign_and_assert_elfs()

    def package_info(self):
        # 应用包：制品是 bin/ 下的可执行文件
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []

    # ── OHOS autotools 落地 ─────────────────────────────────────────────

    def _bootstrap_autotools(self):
        """在源目录生成 configure/Makefile.in。

        tarball 只有 configure.ac，autoreconf 需要 automake（tool_require）。
        tool_require 的 bin 由 conan 注入 PATH（conanbuild），这里再显式前置一次
        以防聚合环境缺失（R33：工具来自声明来源，而非碰巧在 PATH 上）。

        PERL5LIB 必须重写：automake/autoconf 是 perl 脚本，conan 的 perl
        tool_require 会把**它自己**（5.42.2）的 lib 目录塞进 PERL5LIB，而设备上
        automake 脚本的 shebang 指向系统 perl（5.42.0），两者 XS 模块 ABI 不兼容
        （`Perl_my_cxt_init: symbol not found`，实测 aclocal 直接 255 退出）。
        这里只保留 automake/autoconf 自己的 perl 模块目录（Automake::Config 等），
        核心模块由系统 perl 自带。
        """
        env = self._autotools_env()
        assigns = " ".join('%s="%s"' % (k, v) for k, v in env.items())
        self.run(f'{assigns} AUTOPOINT=true autoreconf -fi < /dev/null',
                 cwd=self.source_folder, env="conanbuild")
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(
                "autoreconf finished but produced no configure script")
        self.output.info("autoreconf produced: %s" % configure)

    def _autotools_env(self):
        """autoreconf 的显式环境（PATH / PERL5LIB / ACLOCAL_PATH）。

        PATH 前置 conan automake 的 bin 与设备 hnp 工具链目录：
        - conan automake 提供 aclocal/automake（设备无 automake）；
        - 设备目录提供 autoconf/autoheader/autoreconf/m4/perl（系统 perl），
          且必须排在 conan 注入的 perl tool_require bin **之前**，否则
          `perl` 会解析到 conan perl 5.42.2，与 automake 脚本 shebang 用的
          系统 perl 5.42.0 ABI 不兼容。
        PERL5LIB 只保留 automake 自己的 perl 模块目录（`Automake::Config` 等），
        核心模块由系统 perl 自带（conan perl 的 lib 目录会覆盖成 5.42.2 版本）。
        """
        env = {}
        bins = []
        try:
            automake_folder = self.dependencies.build["automake"].package_folder
        except KeyError:
            automake_folder = None
        if automake_folder:
            automake_bin = os.path.join(automake_folder, "bin")
            if os.path.isdir(automake_bin):
                bins.append(automake_bin)
        if os.path.isdir(DEVICE_TOOLCHAIN_BIN):
            bins.append(DEVICE_TOOLCHAIN_BIN)
        if bins:
            env["PATH"] = os.pathsep.join(bins) + os.pathsep + "$PATH"

        if automake_folder:
            perl5lib = sorted(glob.glob(
                os.path.join(automake_folder, "share", "automake-*")))
            if perl5lib:
                env["PERL5LIB"] = os.pathsep.join(perl5lib)
            aclocal = os.path.join(automake_folder, "share", "aclocal")
            if os.path.isdir(aclocal):
                env["ACLOCAL_PATH"] = aclocal
        return env

    def _relax_umask_in_configure(self):
        """把生成的 configure 里的 `umask 077` 改回 022。

        设备实测（ncrack/libcaca/libabw 系列）：configure 用 umask 077 建临时
        目录得到 2700，而 hmdfs 按组位判定遍历权限、chmod 又是 no-op，导致目录
        不可遍历（EACCES）。022 得到 drwxr-s--x。
        """
        path = Path(self.source_folder, "configure")
        content = path.read_text(encoding="utf-8")
        count = content.count("umask 077")
        if count == 0:
            self.output.info(
                "no 'umask 077' in generated configure (nothing to relax)")
            return
        path.write_text(content.replace("umask 077", "umask 022"),
                        encoding="utf-8", newline="\n")
        self.output.info("relaxed umask 077 -> 022 (%d occurrence(s))" % count)

    def _configure_args(self):
        return [
            # 设备 config.sub 不保证认识 "ohos"；该三元组被普遍接受，
            # host_os 解析为 linux，命中上游 configure.ac 的 linux 分支。
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=%s" % self.package_folder,
            "--disable-dependency-tracking",
        ]

    def _compiler_env_items(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        mapping = {"c": "CC", "cpp": "CXX"}
        return {env: compilers[key]
                for key, env in mapping.items() if compilers.get(key)}

    def _gl_include_flags(self):
        return " ".join("-I%s" % os.path.join(
            self.dependencies[dep].package_folder, "include") for dep in GL_DEPS)

    def _gl_library_flags(self):
        return " ".join("-L%s" % os.path.join(
            self.dependencies[dep].package_folder, "lib") for dep in GL_DEPS)

    def _tmpdir(self):
        tmp = Path(self.build_folder, ".tmp")
        tmp.mkdir(parents=True, exist_ok=True)
        return str(tmp)

    def _configure(self):
        """在源目录就地 configure（in-source build，避开 VPATH 组合风险）。

        CC/CXX 从 profile 的 tools.build:compiler_executables 取（R33），
        GL 头/库路径显式传入：configure.ac 的 AC_CHECK_HEADER(GL/glut.h) 只看
        CPPFLAGS，AC_CHECK_LIB 只看 LDFLAGS。
        """
        env = self._compiler_env_items()
        assigns = [
            "CC=%s" % shlex.quote(env.get("CC", "clang")),
            "CXX=%s" % shlex.quote(env.get("CXX", "clang++")),
            "CPPFLAGS=%s" % shlex.quote(self._gl_include_flags()),
            "CFLAGS=%s" % shlex.quote("-g -O2 -Wall"),
            "CXXFLAGS=%s" % shlex.quote("-g -O2 -Wall -DMAQ_LONGREADS"),
            "LDFLAGS=%s" % shlex.quote(self._gl_library_flags()),
            "TMPDIR=%s" % shlex.quote(self._tmpdir()),
        ]
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(shlex.quote(a) for a in self._configure_args())
        self.run(" ".join(assigns) + " %s %s" % (shlex.quote(configure), args),
                 cwd=self.source_folder, env="conanbuild")

    def _make(self):
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def _make_install(self):
        self.run("make -j1 install", cwd=self.source_folder, env="conanbuild")

    # ── 权限 / 签名 ─────────────────────────────────────────────────────

    def _fix_bin_permissions(self):
        bindir = Path(self.package_folder, "bin")
        if not bindir.is_dir():
            return
        for entry in bindir.iterdir():
            if entry.is_file() and not entry.is_symlink():
                entry.chmod(0o755)

    def _packaged_elfs(self):
        out = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                try:
                    with open(path, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                out.append(path)
        return sorted(out)

    def _find_tool(self, *names):
        candidates = []
        for name in names:
            candidates += ["/data/service/hnp/bin/%s" % name,
                           "/storage/Users/currentUser/usr/local/bin/%s" % name]
        return next((p for p in candidates if os.path.isfile(p)), None)

    def _sign_and_assert_elfs(self):
        elfs = self._packaged_elfs()
        if str(self.settings.os) != "OHOS":
            self.output.info("non-OHOS host: skipping ELF signing (%d ELF)"
                             % len(elfs))
            return
        signer = self._find_tool("binary-sign-tool")
        objcopy = self._find_tool("llvm-objcopy")
        readelf = self._find_tool("readelf")
        if not signer or not objcopy or not readelf:
            raise ConanException(
                "OHOS ELF signing tools missing (binary-sign-tool/llvm-objcopy/"
                "readelf); refusing to ship unsigned ELF")
        if not elfs:
            raise ConanException("no ELF packaged — nothing to sign")
        for elf in elfs:
            # 安装会改写 RUNPATH 使链接期写入的 .codesign 失效；先清段再自签
            self.run('%s --remove-section .codesign %s 2>/dev/null || true'
                     % (shlex.quote(objcopy), shlex.quote(elf)),
                     ignore_errors=True)
            self.run('%s sign -inFile %s -outFile %s -selfSign 1'
                     % (shlex.quote(signer), shlex.quote(elf), shlex.quote(elf)))
            os.chmod(elf, 0o755)
            count = self._codesign_section_count(readelf, elf)
            if count != 1:
                raise ConanException(
                    "expected exactly 1 .codesign section in %s, found %d"
                    % (elf, count))
        self.output.info("signed + verified %d ELF(s) for OHOS" % len(elfs))

    def _codesign_section_count(self, readelf, elf):
        import subprocess
        proc = subprocess.run([readelf, "-SW", elf], capture_output=True,
                              text=True)
        if proc.returncode != 0:
            raise ConanException("readelf -SW failed for %s: %s"
                                 % (elf, proc.stderr.strip()))
        return sum(1 for line in proc.stdout.splitlines() if ".codesign" in line)
