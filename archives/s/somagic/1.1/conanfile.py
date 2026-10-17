#!/usr/bin/env python3
"""Conan recipe — somagic 1.1 (raw Makefile, command-line tools).

somagic (upstream project `easycap-somagic-linux`) is the user-space driver
suite for the Somagic EasyCAP DC60 / EasyCAP002 USB video-capture dongles
(USB ID 1c88:0007). Upstream ships four single-file C programs plus a raw
Makefile (no configure/CMake step):

  somagic-init            uploads the chip firmware and re-enumerates the
                          dongle under a new product ID (libusb-1.0 + libgcrypt)
  somagic-capture         initializes the capture registers and streams raw
                          UYVY video (libusb-1.0)
  somagic-audio-capture   beta audio-only capture path (libusb-1.0)
  somagic-both            beta combined init + capture path (libusb-1.0)

The two beta programs are built by the Makefile's separate `beta` target; this
recipe builds and packages all four so the delivered package matches what the
README documents.

OHOS notes:
  - Raw Makefile: `make all beta` with CC/CFLAGS/LFLAGS supplied from Conan
    (R33 — the compiler comes from tools.build:compiler_executables, never
    from the ambient shell). The upstream Makefile's implicit `.c:` suffix
    rule needs only a compiler and the two library flags.
  - libusb-1.0 and libgcrypt are not system libraries on OHOS, so include
    dirs, library dirs and an rpath into the dependency packages are passed
    explicitly (dcled/uhubctl precedent).
  - The sources include <libusb-1.0/libusb.h>; libusb's Conan package exposes
    include/libusb-1.0, so the parent include/ directory is added as well.
  - `execinfo.h` is only referenced under the DEBUG macro (which upstream does
    not define), so no libexecinfo dependency is needed.
  - package() self-signs every installed ELF for HarmonyOS (XPM requirement),
    so the consumer test can execute them directly.
  - One portability patch (patches/0001-guard-libusb-init-failure.patch):
    upstream ignores the libusb_init() return value and then dereferences the
    never-initialised device handle. On the HongMeng kernel netlink sockets are
    unsupported, so libusb_init() fails and somagic-init previously died with
    SIGSEGV (exit 139) on its `--skip-check` path. The patch turns that fatal
    crash into the intended diagnostic + exit 1. It is a plain defect fix: no
    platform #ifdef, and also correct on Linux.
    The recipe also builds a small static library from two of those sources
    (somagic-init.c, -DSOMAGIC_NO_MAIN) against a mock libusb backend; its
    test_package links that library and replays somagic_init() offline, so the
    mocked path proves the guard above without touching the real package.

Upstream ships no automated test suite: the Makefile defines only
all/beta/install/install-beta/clean (no check/test target) and the tarball has
no tests/ directory. The upstream verification surface is the tools themselves
(--version/--help plus the deterministic device-free error paths), which the
test_package exercises end-to-end against the installed package.
"""

import os
import time
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SomagicConan(ConanFile):
    name = "somagic"
    version = "1.1"
    description = ("User-space driver suite for the Somagic EasyCAP DC60 / "
                   "EasyCAP002 USB video-capture dongles")
    license = "GPL-2.0-or-later"
    homepage = "https://code.google.com/archive/p/easycap-somagic-linux/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # Every executable produced by the upstream Makefile.
    _PROGRAMS = ("somagic-init", "somagic-capture")
    _BETA = ("somagic-audio-capture", "somagic-both")

    def validate(self):
        # R32: match OHOS alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"somagic supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("libusb/1.0.27")
        self.requires("libgcrypt/1.11.0")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # ── fork 压力缓解：env 激活脚本切 function 反激活模式 ──
        # conan 默认（tools.env:deactivation_mode 未设）在聚合环境脚本
        # conanbuildenv-<id>.sh / conanrunenv-<id>.sh 顶部生成一段 source 时
        # 立即执行的反激活前导块：
        #     for v in <vars>; do value=$(printenv $v) || is_defined="" || true; ...; done
        # 即对每个导出变量 fork 一次 printenv 与命令替换子 shell。该块仅为生成
        # 本配方从不使用的 deactivate_*.sh，却让每次 self.run(env="conanbuild")
        # 在目标命令执行前先 fork 十余次（profile [buildenv] 导出 SHELL/
        # CONFIG_SHELL/PATH/LD_LIBRARY_PATH，VirtualBuildEnv/VirtualRunEnv 还会
        # 聚合依赖的 libdir/bindir 等）。真机 worker 处于 fork/进程资源临界时，
        # make 启动前 mksh 执行该循环即返回 EAGAIN（CI #95906：
        # `ConanException: Error while running cmd` / `Error: [Errno 11]
        # Resource temporarily unavailable`，甚至没有进入 make 编译）。
        # `tools.env:deactivation_mode=function` 让 env 脚本只在 source 期定义
        # 反激活函数、用 ${VAR+x} 参数展开保存旧值，不再 fork printenv；仍完整
        # 导出原有环境变量（对照 conan/tools/env/environment.py 的
        # _sh_deactivate_contents 两分支）。conf 必须在 VirtualBuildEnv/
        # VirtualRunEnv 生成之前 define，故放在 generate() 顶部。
        self.conf.define("tools.env:deactivation_mode", "function")

    # ── build ────────────────────────────────────────────────────────────────
    def _dependency_search_paths(self):
        """Include and library directories contributed by the dependencies.

        For each include dir the parent directory is added too: libusb exposes
        include/libusb-1.0 while the sources include <libusb-1.0/libusb.h>, so
        the parent include/ has to be on the search path.
        """
        incdirs = []
        libdirs = []
        for dep in self.dependencies.values():
            info = dep.cpp_info.aggregated_components()
            for inc in info.includedirs:
                path = os.path.join(dep.package_folder, str(inc))
                for candidate in (path, os.path.dirname(path)):
                    if candidate and candidate not in incdirs:
                        incdirs.append(candidate)
            for lib in info.libdirs:
                path = os.path.join(dep.package_folder, str(lib))
                if path not in libdirs:
                    libdirs.append(path)
        return incdirs, libdirs

    def build(self):
        # R33: compiler from Conan conf, never from shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        incdirs, libdirs = self._dependency_search_paths()

        # Upstream CFLAGS = -s -W -Wall; keep them and add the dependency
        # include dirs.
        cflags = ["-s", "-W", "-Wall"]
        cflags.extend(f"-I{d}" for d in incdirs)

        # Upstream LFLAGS = -lusb-1.0 -lgcrypt. Add the dependency lib dirs and
        # an rpath into each so the freshly built tools resolve the shared
        # libraries even outside the Conan run environment.
        lflags = [f"-L{d}" for d in libdirs]
        lflags.append("-lusb-1.0")
        lflags.append("-lgcrypt")
        lflags.extend(f"-Wl,-rpath,{d}" for d in libdirs)

        make_command = (
            'make -j1 CC="{cc}" CFLAGS="{cflags}" LFLAGS="{lflags}" all beta'.format(
                cc=cc,
                cflags=" ".join(cflags),
                lflags=" ".join(lflags),
            )
        )
        self._make_with_fork_retry(make_command)

    def _make_with_fork_retry(self, command):
        """Run the upstream make, retrying only on real fork-pressure markers.

        The HarmonyOS worker is a shared machine whose process/thread table can
        briefly run out (fork() returns EAGAIN). In CI #95906 the failure
        surfaced before any compilation:
            ConanException: Error while running cmd
            Error: [Errno 11] Resource temporarily unavailable
        which is `subprocess.Popen` itself being refused a fork while Conan
        activated the aggregated env scripts. The deactivation_mode=function
        change in generate() removes the per-variable printenv forks, but make
        still spawns one clang per translation unit, so a transient EAGAIN
        spike can also strike the build itself. Retry a bounded number of times
        with backoff, but only when the failure really is fork pressure;
        genuine compiler/linker errors are re-raised immediately.
        """
        fork_markers = ("can't fork", "cannot fork", "try again",
                        "resource temporarily unavailable", "out of memory",
                        "errno 11")
        max_attempts = 4
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            buf = StringIO()
            try:
                self.run(command, cwd=self.source_folder, stdout=buf, stderr=buf)
                print(buf.getvalue(), end="", flush=True)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                captured = buf.getvalue()
                print(captured, end="", flush=True)
                blob = (str(exc) + "\n" + captured).lower()
                is_fork = any(marker in blob for marker in fork_markers)
                if not is_fork or attempt >= max_attempts:
                    if is_fork:
                        self.output.warning(
                            "somagic build still fork-starved after "
                            f"{attempt} attempts: {exc}")
                    raise
                wait = 15 * attempt
                self.output.warning(
                    "somagic build hit fork pressure (attempt "
                    f"{attempt}/{max_attempts}); sleeping {wait}s then "
                    f"retrying: {exc}")
                time.sleep(wait)
        if last_exc is not None:
            raise last_exc

    # ── package ──────────────────────────────────────────────────────────────
    def package(self):
        # Do not use `make install`: it writes to $(PREFIX)=/usr/local and
        # installs only the two PROGRAMS. Package all four built executables
        # plus the man pages and the upstream DEP-5 copyright file instead.
        bindir = os.path.join(self.package_folder, "bin")
        for name in self._PROGRAMS + self._BETA:
            copy(self, name, self.source_folder, bindir)
            path = os.path.join(bindir, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._sign_ohos_binary(path)

        copy(
            self,
            "*.1",
            os.path.join(self.source_folder, "man"),
            os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "copyright",
            os.path.join(self.source_folder, "debian"),
            os.path.join(self.package_folder, "licenses"),
        )

    def _sign_ohos_binary(self, path):
        """Self-sign an installed ELF (HarmonyOS refuses to execute unsigned
        binaries taken from the package cache)."""
        if str(self.settings.os) != "OHOS":
            return
        if not self._is_elf(path):
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if os.path.isfile(objcopy):
            self.run(
                f'env -u LD_LIBRARY_PATH "{objcopy}" --remove-section '
                f'.codesign "{path}" 2>/dev/null || true'
            )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool unavailable; skipping OHOS ELF signing of "
                f"{path}"
            )
            return
        self.run(
            f'env -u LD_LIBRARY_PATH "{signer}" sign -inFile "{path}" '
            f'-outFile "{path}" -selfSign 1'
        )
        os.chmod(path, 0o755)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def package_info(self):
        # Command-line tools: expose bin/, no libraries or headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
