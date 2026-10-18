#!/usr/bin/env python3
"""Conan recipe for musicpc 0.35.

"musicpc" is the name the FreeBSD ports tree gives to the mpc command-line
client of the Music Player Daemon (MPD); the upstream project is
MusicPlayerDaemon/mpc. Pure C, meson build, single runtime dependency
libmpdclient (upstream requires >= 2.18; ohpcd publishes 2.23).

Unrelated to mpc/1.3.1 (the GNU MPC multiprecision library) — same name,
different software.

Upstream test case (rule4)
--------------------------
Upstream declares exactly one test with meson's ``test()``
(``test/meson.build``): ``test_format``, a libcheck suite over
``format_song()``, gated behind the ``test`` option (default ``false``).  The
recipe builds it and runs it for real — see ``_run_upstream_tests()``.
"""

import os
import platform
import shutil
import struct

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain

# e_machine values from the ELF spec, restricted to what matters here.
_EM_AARCH64 = 0xB7
_EM_X86_64 = 0x3E

# Guest sysroots searched for the OHOS loader/libc when emulating.
_GUEST_ROOTS = ("/opt/ohos-guest",)
# Guest-side fortify shim: OHOS headers reference __fd_chk(), which the
# emulated guest libc does not provide.
_GUEST_PRELOAD = "libfdchkshim.so"


def _elf_machine(path):
    """Return the ELF e_machine of `path`, or None if it is not an ELF."""
    with open(path, "rb") as handle:
        header = handle.read(20)
    if len(header) < 20 or header[:4] != b"\x7fELF":
        return None
    little_endian = header[5] == 1
    return struct.unpack("<H" if little_endian else ">H", header[18:20])[0]


def _host_machine():
    machine = platform.machine().lower()
    if machine in ("aarch64", "arm64"):
        return _EM_AARCH64
    if machine in ("x86_64", "amd64"):
        return _EM_X86_64
    return None


class MusicpcConan(ConanFile):
    name = "musicpc"
    version = "0.35"
    description = ("mpc: minimalist command-line client for the Music Player "
                   "Daemon (MPD); upstream MusicPlayerDaemon/mpc, named "
                   "'musicpc' in the FreeBSD ports tree")
    license = "GPL-2.0-or-later"
    homepage = "https://www.musicpd.org/clients/mpc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mpd", "music", "cli", "audio")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # plain name/version: ohpcd publishes these as plain refs; the
        # "@ohpcd/stable" user/channel form does not resolve in this repo
        # (measured failure, see archives/m/mpdas/0.4.5/notes.md)
        self.requires("libmpdclient/2.23")

    def build_requirements(self):
        # Upstream's single test target links the `check` unit-testing
        # framework (test/meson.build declares `check_dep`), so building it
        # needs check for the *target* platform.  test_requires is used on
        # purpose: it is only expanded while this recipe itself is under test
        # (conan create / conan test), musicpc consumers never see it, and it
        # does not contribute to package_id (conan requires.py: "test_requires
        # never affect the binary_id").  ohpcd already publishes
        # check/0.15.2 for OHOS/armv8/clang-15/Release with fPIC=True and
        # shared=False — byte-for-byte the settings of ci/conan/profiles/
        # ohos-aarch64 — so the CI worker downloads a binary instead of
        # building check from source (CI runs conan create with
        # --build="musicpc/*", which would not rebuild it anyway).
        self.test_requires("check/0.15.2")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _has_check(self):
        """True when `check` is resolved for this graph.

        That is the case during `conan create` (test_requires is expanded);
        it is False when musicpc is consumed as a dependency, where there is
        nothing to test and meson must not be asked for -Dtest=true.
        """
        try:
            self.dependencies["check"]
        except KeyError:
            return False
        return True

    def generate(self):
        # libmpdclient is resolved through pkg-config from the conan
        # dependency graph; wrap_mode keeps meson from falling back to the
        # in-tree subprojects/ wrap file (upstream ships a libmpdclient.wrap)
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["documentation"] = "disabled"
        # Build upstream's test target only when its framework resolves,
        # so a consumer building this recipe from source is unaffected.
        tc.project_options["test"] = self._has_check()
        self._pin_meson_archiver(tc)
        tc.generate()

    def _pin_meson_archiver(self, toolchain):
        """Pin an absolute static archiver into meson's native file.

        meson probes the archiver while configuring.  A bare name is spawned
        as-is, and on the OHOS worker that probe child cannot resolve a bare
        name (it fails with ``[Errno 2] No such file or directory`` even
        though the tool sits in the same hnp bin dir as the pinned clang).
        The worker buildenv also ships ``AR=llvm-ar`` (bare), which conan
        copies verbatim into ``conan_meson_native.ini``, so configure dies
        with::

            ../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]
            Running `llvm-ar --version` gave "[Errno 2] ... 'llvm-ar'"

        (CI builds #92723 / #93102 / #93136 on workers CI-026 / CI-014 /
        CI-028; local repro with meson 1.11.1 + bare AR).  An absolute path
        bypasses the PATH lookup entirely.  Precedent:
        archives/c/coeurl/0.3.2, archives/q/qbootctl/0.2.2,
        archives/m/mpd/0.24.12, archives/m/mobile-broadband-provider-info.
        """
        executables = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        cc = executables.get("c") or ""
        # profiles pin the compiler by absolute path (/data/service/hnp/bin
        # /clang on the OHOS worker); the archiver lives in that same bin dir
        cc_bindir = os.path.dirname(cc) if os.sep in cc else ""
        candidates = [
            executables.get("ar"),
            shutil.which("llvm-ar"),
            os.path.join(cc_bindir, "llvm-ar") if cc_bindir else None,
            "/data/service/hnp/bin/llvm-ar",
            shutil.which("ar"),
            os.path.join(cc_bindir, "ar") if cc_bindir else None,
        ]
        ar = next((c for c in candidates if c and os.path.isfile(c)), None)
        if not ar:
            raise ConanException(
                "cannot resolve an absolute archiver for meson; the OHOS "
                "worker cannot spawn a bare 'llvm-ar' during 'meson setup' "
                "(Unknown linker(s)). Tried: {}".format(
                    [c for c in candidates if c]))
        toolchain.binaries["ar"] = ar

    def build(self):
        if not shutil.which("meson"):
            raise ConanInvalidConfiguration(
                "Meson is a required build tool and must be prepared by the "
                "worker")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        # conan 的 Meson.build() 只接受 target，不接受额外参数：它固定拼成
        # `meson compile -C <build> -j<jobs>`，而 <jobs> 来自 conf tools.build:jobs，
        # 默认取构建机 CPU 数（worker 上是 20）。worker 的进程预算吃紧时，
        # `-j20` 的 ninja 会直接死在 fork/spawn 上（CI #93538 与 #93684 两次都是
        # `ninja: fatal: posix_spawn: Resource temporarily unavailable`，29 秒即失败）。
        # 这里改为直接调用并把并行度钉成 -j1 —— 与仓内既有做法一致（sinfo 的
        # 「R9/E074 → make -j1」、vfu 的 -j1），只降低并行度，不影响任何正确性。
        self.run('meson compile -C "%s" -j1' % self.build_folder)
        if self._has_check():
            self._run_upstream_tests()

    def _execution_wrapper(self, binary):
        """Program prefix needed to execute `binary` on this machine.

        None when the ELF already matches the host (the CI HarmonyOS PC
        worker, where the aarch64 test binary is native).  On a cross-build
        host the test binary is foreign, so it is launched through
        qemu-aarch64 against the OHOS guest sysroot.  The decision comes from
        the ELF header, NOT from Conan's cross_building(): the OHOS profiles
        pass the same file for -pr:h and -pr:b, so Conan reports host == build
        even though the ELF is aarch64 and the host is x86_64.  Same model as
        test_package/conanfile.py (precedent: archives/t/tasksh/1.2.0,
        archives/a/array-hash/0.7.2).
        """
        if _elf_machine(binary) == _host_machine():
            return None
        qemu = shutil.which("qemu-aarch64")
        if not qemu:
            raise ConanException(
                "the upstream test binary targets a foreign architecture and "
                "qemu-aarch64 is required to execute it")
        guest = next((root for root in _GUEST_ROOTS
                      if os.path.isdir(os.path.join(root, "lib"))), None)
        if guest is None:
            raise ConanException(
                "the upstream test binary targets a foreign architecture and "
                "no OHOS guest sysroot was found in {}".format(
                    list(_GUEST_ROOTS)))
        parts = [qemu, "-L", guest]
        preload = os.path.join(guest, "lib", _GUEST_PRELOAD)
        if os.path.isfile(preload):
            # -E puts the shim in the *guest* environment, so the host loader
            # never sees the aarch64 shim.  libmpdclient links dynamically and
            # the OHOS build calls __fd_chk(), which the emulated guest libc
            # does not implement.
            parts += ["-E", "LD_PRELOAD=" + preload]
        return " ".join(parts)

    def _run_upstream_tests(self):
        """Run upstream's one and only test target, for real.

        `test/meson.build` registers exactly one meson test — ``test_format``
        — a libcheck suite holding six START_TEST cases (test_empty,
        test_basic, test_group, test_fallback, test_default, test_escape) that
        exercise ``format_song()`` on top of libmpdclient's
        ``mpd_song_begin``/``mpd_song_feed``.  It needs no MPD server and no
        network: it is pure in-process string formatting, which is why it can
        genuinely run here.  Upstream ships the test source unmodified; the
        only thing this recipe adds around it is the cross-execution wrapper
        and the signing described below.

        `meson test` is used rather than a hand-rolled exec so the upstream
        test definition is what actually drives the run, and so the log
        carries meson's own pass/fail summary ("Ok: 1" / "Fail: 0").
        """
        binary = os.path.join(self.build_folder, "test", "test_format")
        if not os.path.isfile(binary):
            raise ConanException(
                "upstream test binary not built: {} — upstream declares it "
                "with meson test() under -Dtest=true".format(binary))

        # libcheck pipes results from the forked test process back to the
        # runner through a temp file (src/check_msg.c open_tmp_file()) and
        # resolves its directory as: TEMP -> P_tmpdir -> TMPDIR -> ".".
        # P_tmpdir is a compile-time macro that glibc and musl both define as
        # "/tmp", and it wins over TMPDIR -- so pointing TMPDIR at a writable
        # directory is not enough.  The OHOS worker's /tmp is read-only (the
        # repo states this itself: "OHOS /tmp is read-only, use build
        # directory instead" in ci/conan/build_and_test.sh), so libcheck died
        # before running a single assertion:
        #
        #   check_msg.c:317: Unable to create temporary file for
        #   communication; may not have permissions to do so
        #   1/1 mpc:test_format FAIL   0.05s   exit status 2
        #
        # (CI build #94829, worker CI-023).  TEMP has the highest precedence,
        # so pin it at a directory this build owns and can write on both the
        # worker and a cross-build host.
        test_tmp = os.path.join(self.build_folder, "upstream-test-tmp")
        # The OHOS worker refuses to execute an *unsigned* ELF through HMDFS
        # (bin/mpc was rejected with exit 126 "Operation not permitted" in CI
        # #93705, which is why package() self-signs).  The test binary lives
        # in the build folder, so it gets the same treatment; on a plain
        # cross-build host there is no signer and this only warns.
        self._sign_ohos_binary(binary)

        os.makedirs(test_tmp, exist_ok=True)
        cmd = ('TEMP="%s" TMPDIR="%s" meson test -C "%s" -v --print-errorlogs'
               % (test_tmp, test_tmp, self.build_folder))
        wrapper = self._execution_wrapper(binary)
        if wrapper:
            cmd += ' --wrapper "%s"' % wrapper
        if wrapper:
            self.output.info("upstream test executed through: %s" % wrapper)
        retcode = self.run(cmd, ignore_errors=True)
        if retcode != 0:
            raise ConanException(
                "upstream test suite failed (meson test exited %d); the "
                "libcheck output and meson's Fail:/Timeout: summary are above"
                % retcode)
        self.output.info("upstream test suite passed: mpc:test_format 1/1")

    def package(self):
        meson = Meson(self)
        # build() already ran `meson compile` to completion, so the install
        # step must not rebuild: on the OHOS worker `meson install` re-entered
        # ninja and tried to relink *both* binaries even though the preceding
        # `meson compile -j1` had reported "ninja: no work to do" (CI #94968,
        # worker CI-028 -- the build folder is a FUSE/HMDFS mount whose
        # timestamps make ninja re-consider its outputs stale).  Those two
        # redundant links then died on the worker's exhausted process budget:
        #
        #   clang-15: error: unable to execute command:
        #       posix_spawn failed: Resource temporarily unavailable
        #   FAILED: [code=1] mpc / FAILED: [code=1] test/test_format
        #   ERROR: musicpc/0.35: Error in package() method, line 300
        #       ConanException: Error 255 while executing
        #
        # which is the same worker resource condition that forced `-j1` in
        # build() (CI #93538 / #93684).  `--no-rebuild` is the documented meson
        # flag for exactly this: install what has already been built.
        meson.install(cli_args=["--no-rebuild"])

        binary = os.path.join(self.package_folder, "bin", "mpc")
        if not os.path.isfile(binary):
            raise ConanException("meson install produced no bin/mpc (%s)" % binary)
        # 真机 HMDFS 会拒绝执行**未签名**的 ELF：CI #93705 的消费者测试就是死在
        #   FAIL 1: mpc nosuchcommand exit=126 out=[timeout: exec <pkg>/bin/mpc: Operation not permitted]
        # 注意本地包内该文件的权限位本来就是 -rwxr-xr-x(755)，所以不是权限位问题。
        # 仓内既有先例与同款做法：archives/t/termdebug/2.2 的 `_sign_ohos_binary()`
        # （其 docstring 记录了 cronutils 首轮 PermissionError 的同因），
        # 即 llvm-objcopy 去掉旧 .codesign 段 + binary-sign-tool -selfSign 1。
        os.chmod(binary, 0o755)
        self._sign_ohos_binary(binary)

    def _sign_ohos_binary(self, path):
        """对 OHOS 目标的自签名（非 OHOS 构建直接跳过）。

        与 archives/t/termdebug/2.2/conanfile.py 的同名方法一致：
        先 llvm-objcopy 去掉可能存在的旧 .codesign 段（失败忽略），
        再用 binary-sign-tool -selfSign 1 生成签名文件并替换回原路径。
        签名工具不存在时明确告警并跳过（交叉构建机上本来就没有它），
        绝不静默假装签过。
        """
        if str(self.settings.os) != "OHOS":
            return
        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (signer or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool unavailable; skipping OHOS ELF signing "
                "(cross build only, the consumer test on a real device needs it)")
            return
        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (objcopy or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path),
                     ignore_errors=True)
        signed = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                 % (signer, path, signed))
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool produced no output for %s" % path)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
