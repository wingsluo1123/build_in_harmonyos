#!/usr/bin/env python3
"""Conan test_package for wayland-utils 1.2.0 — 三层消费者测试。

上游 1.2.0 无任何测试套件（tarball 无 tests/、无 test 目标），全部为
鸿蒙侧补测（R51 三层测试体系；清点证据见 MANIFEST.yml）：

层 1（源级 E2E，76 项）：复用主配方已下载的 wayland 1.24.0 源码编译静态
  wayland-scanner（主配方同款：OHOS 禁止 execve conan 缓存内二进制），
  对 wayland-protocols 1.48 安装集内上游 wayland-info 实际消费的 5 组协议
  XML（19 个接口）重新生成 client-header + private-code，编译链接
  test_wayland_info_e2e.c，运行时逐接口核对：接口名 / 版本号 / 请求计数
  （运行时解析 XML 计数）/ XML 原文包含 name 与 version 属性——
  19 用例 × 4 检查点 = 76 项，任一失败退出码 1。

层 2（消费者 CLI，20 项）：test.sh 执行安装出的 bin/wayland-info（经
  conanrun PATH），断言 --help/-h 退出码 0 与 usage 文案、未知选项与
  缺参的退出码/诊断文本、无合成器环境的优雅失败（"failed to create
  display"）、readelf 级 ELF 属性（AArch64/PIE/NX/RELRO/DT_NEEDED/
  DT_RUNPATH）、env -i 裸跑冒烟。

层 3（鸿蒙特有，31 项）：test_wayland_info_ohos.c 仅 OHOS 编译
  （#ifndef __OHOS__ #error 守卫），对安装出的二进制做 ELF 级断言：
  11 项平台属性（ELF64/AArch64/PIE/INTERP/NX/RELRO/NEEDED wayland-client
  与 libc/RUNPATH 指向 wayland 包 libdir）+ 19 项协议接口数据符号存在
  （证明 5 组协议绑定真实编译链接进了产物）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get

SCANNER_WAYLAND_VERSION = "1.24.0"
SCANNER_WAYLAND_URL = ("https://gitlab.freedesktop.org/wayland/wayland/"
                       "-/archive/1.24.0/wayland-1.24.0.tar.gz")
SCANNER_WAYLAND_SHA256 = \
    "7800858844751fc7113d7df3678dc6b58b26a056176a65c49a059763045bffd5"

# 上游 wayland-info/meson.build 的 generated_protocols 字典（5 组协议，
# 19 个接口）——全部取自 wayland-protocols 安装集
PROTOCOLS = [
    ("stable/presentation-time/presentation-time.xml",
     "presentation-time"),
    ("staging/drm-lease/drm-lease-v1.xml",
     "drm-lease-v1"),
    ("unstable/linux-dmabuf/linux-dmabuf-unstable-v1.xml",
     "linux-dmabuf-unstable-v1"),
    ("unstable/tablet/tablet-unstable-v2.xml",
     "tablet-unstable-v2"),
    ("unstable/xdg-output/xdg-output-unstable-v1.xml",
     "xdg-output-unstable-v1"),
]


class WaylandUtilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 对齐主配方与真实下游：wayland 包提供 wayland-client.h 等头文件；
        # wayland-protocols 提供 pkgdatadir（层 1 重新生成的输入）。
        self.requires("wayland/" + SCANNER_WAYLAND_VERSION)
        self.requires("wayland-protocols/1.48")

    # 注意: conan 2.29 对 in-place test_package 不调用 source()
    # （真机实测: 主配方 source() 执行而 test_package 的跳过），
    # 故 wayland scanner 源码下载放 build() 开头。

    # ── helpers（主配方同款） ────────────────────────────────────────────

    def _pkgdatadir(self):
        """Locate the wayland-protocols protocol-XML install directory.

        The published wayland-protocols package ships a .pc whose prefix is a
        *build-time staging path* from whichever conan home built it (e.g.
        prefix=/storage/.../.cache/conan2/p/b/<hash>/p) — a path that does
        not exist on the current worker, so trusting the .pc prefix makes
        pkgdatadir non-relocatable (measured: pkgdatadir invalid:
        '.../.cache/conan2/p/b/wayla3c1508aeaa1b7/p/share/wayland-protocols').
        The package layout is authoritative: the XMLs live in
        <package_folder>/share/wayland-protocols. Use that directly and only
        fall back to parsing the .pc if the layout is unexpected.
        """
        pkg = self.dependencies["wayland-protocols"].package_folder
        direct = os.path.join(pkg, "share", "wayland-protocols")
        if os.path.isdir(direct):
            return direct
        pc = None
        for sub in ("share/pkgconfig", "lib/pkgconfig"):
            candidate = os.path.join(pkg, sub, "wayland-protocols.pc")
            if os.path.isfile(candidate):
                pc = candidate
                break
        if not pc:
            raise ConanException("wayland-protocols.pc not found in package")
        vars = {}
        with open(pc, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vars[k.strip()] = v.strip()
        for _ in range(8):
            changed = False
            for k in list(vars):
                for kk, vv in vars.items():
                    nv = vars[k].replace("${" + kk + "}", vv)
                    if nv != vars[k]:
                        vars[k] = nv
                        changed = True
            if not changed:
                break
        pkgdatadir = vars.get("pkgdatadir", "")
        pkgdatadir = re.sub(r"\$\{[^}]+\}", "", pkgdatadir)
        if not pkgdatadir or not os.path.isdir(pkgdatadir):
            raise ConanException(
                f"pkgdatadir invalid: {pkgdatadir!r}")
        return pkgdatadir

    def _find_expat_static(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        if "expat" in self.dependencies:
            candidates.append(os.path.join(
                self.dependencies["expat"].package_folder, "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                return c
        raise ConanException(
            f"no static libexpat.a found for the static wayland-scanner link; "
            f"tried: {candidates}")

    def _find_expat_include(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]
        if "expat" in self.dependencies:
            candidates.append(os.path.join(
                self.dependencies["expat"].package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_scanner(self, src):
        """主配方同款：wayland 1.24.0 源码 -static 编译 wayland-scanner。"""
        config_h = os.path.join(src, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write('#define HAVE_EXPAT 1\n'
                    '#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        version_in = os.path.join(src, "src", "wayland-version.h.in")
        version_h = os.path.join(src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8") as f:
            f.write(content)

        dtd_h = os.path.join(src, "src", "wayland.dtd.h")
        self.run(
            f'python3 {src}/src/embed.py '
            f'{src}/protocol/wayland.dtd wayland_dtd > {dtd_h}',
            env="conanbuild",
        )

        scanner_bin = os.path.join(self.build_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{src} -I{src}/src -I{src}/protocol '
            f'{src}/src/scanner.c {src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild",
        )
        return scanner_bin

    def _obtain_wayland_src(self):
        """wayland 1.24.0 源码取得（source() 对 in-place test_package 不被
        调用）。优先复用主配方 source() 已下载的 scanner 源码：被测试包的
        package_folder（p/<hash>/p）与 source_folder（p/<hash>/s）是同一
        p/<hash>/ 下的兄弟目录，主配方把 scanner 源码解压在
        s/wayland-scanner-src。同一 run 内直接复制复用，避免 test_package
        对 gitlab.freedesktop.org 的第二次请求被 429 限流
        （wayland-protocols 1.48 CI#65173 实测教训）。取不到才回退 get()
        下载（sha256 校验不变）。
        """
        dst = os.path.join(self.build_folder, "wayland-src")
        dep_pkg = self.dependencies["wayland-utils"].package_folder
        sibling = os.path.join(os.path.dirname(dep_pkg), "s",
                               "wayland-scanner-src")
        if (os.path.isfile(os.path.join(sibling, "src", "scanner.c"))
                and os.path.isfile(os.path.join(sibling, "protocol",
                                                "wayland.xml"))):
            shutil.copytree(sibling, dst)
            self.output.info("wayland-scanner source reused from main "
                             "recipe source folder (no re-download)")
            return dst
        get(self, SCANNER_WAYLAND_URL, sha256=SCANNER_WAYLAND_SHA256,
            strip_root=True, destination=dst)
        return dst

    @staticmethod
    def _sign_ohos_elf(path):
        """Self-sign the freshly built OHOS test binary (wayneko precedent)."""
        if not os.path.isfile(path):
            raise ConanException(f"Missing OHOS consumer test binary: {path}")
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or \
            "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            return
        import subprocess
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True, timeout=30)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True, timeout=60)
        os.chmod(path, (os.stat(path).st_mode & 0o777) | 0o555)

    # ── build: 层 1 + 层 3 编译 ──────────────────────────────────────────

    def build(self):
        wayland_src = self._obtain_wayland_src()
        scanner = self._build_scanner(wayland_src)
        gen = os.path.join(self.build_folder, "gen")
        os.makedirs(gen, exist_ok=True)
        pkgdatadir = self._pkgdatadir()

        # 5 组协议：client-header + private-code（上游 generated_protocols
        # 字典同款；scanner 1.24.0 >= 1.14.91 走 private-code 模式）
        for xml_rel, stem in PROTOCOLS:
            xml = os.path.join(pkgdatadir, xml_rel)
            self.run(f'{scanner} client-header --strict '
                     f'"{xml}" "{gen}/{stem}-client-protocol.h"',
                     env="conanbuild")
            self.run(f'{scanner} private-code --strict '
                     f'"{xml}" "{gen}/{stem}-protocol.c"',
                     env="conanbuild")

        # wayland-util.h 等头文件优先取 wayland 包 include（真实消费者
        # 形态），回退 scanner 源码树
        wayland_inc = os.path.join(
            self.dependencies["wayland"].package_folder, "include")
        if not os.path.isdir(wayland_inc):
            wayland_inc = os.path.join(wayland_src, "src")

        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"

        # 层 1：E2E（链接重新生成的 5 组协议 private-code）
        srcs = [os.path.join(self.source_folder, "src",
                             "test_wayland_info_e2e.c")]
        srcs += [f"{gen}/{stem}-protocol.c" for _, stem in PROTOCOLS]
        # The generated protocol code references the core wl_*_interface
        # objects (wl_surface_interface / wl_output_interface /
        # wl_buffer_interface / wl_seat_interface ...), which live in
        # libwayland-client — link it explicitly, otherwise ld.lld fails with
        # "undefined symbol: wl_surface_interface".
        wayland_libdir = os.path.join(
            self.dependencies["wayland"].package_folder, "lib")
        self.run(f'{cc} -O2 -std=c99 -o '
                 f'{self.build_folder}/test_wayland_info_e2e '
                 f'-I{gen} -I{wayland_inc} -I{wayland_src}/src '
                 f'{" ".join(srcs)} '
                 f'-L{wayland_libdir} -lwayland-client',
                 env="conanbuild")
        self.output.info("wayland-utils: built layer-1 E2E test")

        # 层 3：鸿蒙特有 ELF 测试（仅 OHOS 编译）
        if str(self.settings.os) == "OHOS":
            src3 = os.path.join(self.source_folder,
                                "test_wayland_info_ohos.c")
            out3 = os.path.join(self.build_folder,
                                "test_wayland_info_ohos")
            self.run(f'{cc} -O2 -std=c11 -o "{out3}" "{src3}"',
                     env="conanbuild")
            self._sign_ohos_elf(out3)
            self.output.info("wayland-utils: built OHOS-specific test")

    # ── test: 三层执行 ───────────────────────────────────────────────────

    def test(self):
        pkg = self.dependencies["wayland-utils"].package_folder
        binary = os.path.join(pkg, "bin", "wayland-info")
        if not os.path.isfile(binary):
            raise ConanException(f"Missing installed wayland-info: {binary}")

        # 层 1：E2E（19 接口 × 4 检查点 = 76 项）
        pkgdatadir = self._pkgdatadir()
        self.run(f'{self.build_folder}/test_wayland_info_e2e '
                 f'"{pkgdatadir}"',
                 env="conanrun")

        # 层 2：消费者 CLI（20 断言）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        wayland_libdir = os.path.join(
            self.dependencies["wayland"].package_folder, "lib")
        self.run(f'{bash} "{script}" "{wayland_libdir}"', env="conanrun")

        # 层 3：鸿蒙特有 ELF 断言（11 平台 + 19 符号 = 30 项）
        if str(self.settings.os) == "OHOS":
            exe = os.path.join(self.build_folder, "test_wayland_info_ohos")
            self.run(f'"{exe}" "{binary}" "{wayland_libdir}"',
                     env="conanrun")
