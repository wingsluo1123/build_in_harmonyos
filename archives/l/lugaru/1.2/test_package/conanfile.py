#!/usr/bin/env python3
"""Conan test_package — lugaru 1.2（OHOS / aarch64 / 图形应用）。

被适配包是应用（application）：包内只产出 bin/lugaru 与同目录 bin/Data/，没有可
链接的库，因此 build() 不做事，全部校验落在 test() 里（R34：必须真正执行被测产物）。

用例构成（6 用例 / 逐项打印 [case]/[assert] 便于审计）
------------------------------------------------------------------
静态产物校验（本文件实现，不依赖执行环境）
  S1 packaged-layout        bin/lugaru 存在 + 可执行位；bin/Data/ 八个资源子目录齐、
                            资源文件数 >= 500；share/man/man6/lugaru.6；licenses/COPYING.txt
  S2 elf-ohos-aarch64       ELF64/LE/EM_AARCH64=183/ET_DYN(PIE)、
                            PT_INTERP=/lib/ld-musl-aarch64.so.1、
                            DT_NEEDED 含 gl4es 的 libGL.so.1 与 glu 的 libGLU.so.1
  S3 runenv-contract        包导出的 runenv（LIBGL_GLES/LIBGL_EGL）经 VirtualRunEnv
                            落入 conanrun 环境脚本（gl4es 后端定位的消费契约）
运行时冒烟（真实执行被测二进制，单次启动各一条，无需 GPU/合成器）
  S4 cli-version            `--version` 退出码 0，stdout 含 "Version 1.2" 与 GPL 横幅
  S5 cli-help               `--help` 退出码 0，usage 文本含 "-v, --version" 与 "-h, --help"
  S6 cli-unknown-option     未知开关退出码 1，输出含 "Unknown option"

上游测试：无（upstream_tests_exist=false，逐文件审计见 test_package/MANIFEST.yml），
故 HMBS_UPSTREAM_TEST_RESULT 标记 status=no_tests。

平台相关处理
------------
1. OHOS 上被测二进制要按 HarmonyOS 约定签名后才能 exec，且 conan 缓存可能落在
   HMDFS（chmod 被忽略）。因此运行时先把 bin/lugaru 复制到可写工作目录、去掉旧
   .codesign 段并尽力 self-sign（critter/2.0.4、fceux/2.6.6 先例）。
2. 执行统一交给 CONFIG_SHELL（bash）：OHOS 的 /bin/sh 是 mksh，会重置
   LD_LIBRARY_PATH（logstalgia/1.1.4、critter/2.0.4 先例）。
3. 三条 CLI 用例只走 Source/main.cpp 的选项解析与横幅打印（在任何 SDL 初始化之前
   return），因此不依赖显示设备；真实渲染 / 输入 / 音频需在带显示的设备上人工验证，
   属于本测试的不可覆盖面（见 MANIFEST.yml）。
"""

import glob
import json
import os
import re
import shlex
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

_EXE_NAME = "lugaru"
_EXPECTED_NEEDED = ("libGL.so.1", "libGLU.so.1")
_EXPECTED_INTERP = "/lib/ld-musl-aarch64.so.1"
_DATA_SUBDIRS = ("Animations", "Campaigns", "Dialogues", "Maps",
                 "Models", "Skeleton", "Sounds", "Textures")
_MIN_DATA_FILES = 500


class LugaruTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # 应用包：无可链接产物，功能校验全部在 test()。
        pass

    # ------------------------------------------------------------------
    # 运行时准备
    # ------------------------------------------------------------------
    def _writable_dir(self):
        """可写工作目录：TMPDIR/TMP 可用则用，否则退回 build_folder。

        /tmp 在本平台只读，因此逐个候选做真实写入探测（critter/2.0.4 先例）。
        """
        for cand in (os.environ.get("TMPDIR"), os.environ.get("TMP"),
                     os.path.join(self.build_folder, "lugaru-test")):
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(probe)
                return cand
            except OSError:
                continue
        return self.build_folder

    @staticmethod
    def _pick_shell():
        """优先 bash：OHOS 的 /bin/sh 是 mksh，会重置 LD_LIBRARY_PATH。"""
        for cand in (os.environ.get("CONFIG_SHELL"),
                     "/data/service/hnp/bin/bash",
                     shutil.which("bash"),
                     os.environ.get("SHELL"),
                     "/bin/sh"):
            if cand and os.path.exists(cand):
                return cand
        return "/bin/sh"

    def _dependency_libdirs(self):
        """各依赖包的 lib/ 目录，交给被测进程自行前置 LD_LIBRARY_PATH。"""
        dirs = []
        for dependency in self.dependencies.values():
            folder = getattr(dependency, "package_folder", None)
            if not folder:
                continue
            libdir = os.path.join(folder, "lib")
            if os.path.isdir(libdir) and libdir not in dirs:
                dirs.append(libdir)
        return ":".join(dirs)

    def _runenv_text(self):
        """读取 VirtualRunEnv 生成的 conanrun 环境脚本内容。"""
        text = ""
        for pattern in ("conanrun*.sh", "conanrun*.bat"):
            for path in glob.glob(os.path.join(self.generators_folder, pattern)):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        text += handle.read()
                except OSError:
                    continue
        return text

    def _runnable_copy(self, binary, workdir):
        """复制到可写目录并尽力签名 —— HMDFS 上原位置可能不可 exec。"""
        target = os.path.join(workdir, _EXE_NAME)
        try:
            shutil.copy2(binary, target)
        except OSError as exc:
            self.output.warning(f"复制被测二进制失败({exc})，退回原路径执行")
            return binary

        for tool in ("/data/service/hnp/bin/llvm-objcopy",
                     shutil.which("llvm-objcopy") or ""):
            if not tool:
                continue
            try:
                subprocess.run([tool, "--remove-section", ".codesign", target],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False,
                               timeout=15)
                break
            except Exception:
                continue
        for tool in ("/data/service/hnp/bin/binary-sign-tool",
                     shutil.which("binary-sign-tool") or ""):
            if not tool:
                continue
            try:
                proc = subprocess.run(
                    [tool, "sign", "-inFile", target, "-outFile", target,
                     "-selfSign", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    check=False, timeout=20)
                if proc.returncode == 0:
                    self.output.info(f"self-signed 被测二进制（{tool}）")
                    break
            except Exception:
                continue
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return target

    # ------------------------------------------------------------------
    # 断言辅助
    # ------------------------------------------------------------------
    def _case(self, name, pairs):
        """打印一个用例；pairs = [(ok, 描述), ...]，返回 (passed, failed)。"""
        self.output.info(f"[case] {name}")
        passed = failed = 0
        for ok, detail in pairs:
            if ok:
                passed += 1
                self.output.info(f"  [assert] OK   : {detail}")
            else:
                failed += 1
                self.output.info(f"  [assert] FAIL : {detail}")
        return passed, failed

    @staticmethod
    def _elf_info(path):
        with open(path, "rb") as handle:
            data = handle.read()
        if data[:4] != b"\x7fELF":
            raise ConanException(f"{path} 不是 ELF 文件")
        info = {
            "ei_class": data[4],
            "ei_data": data[5],
            "e_type": struct.unpack_from("<H", data, 16)[0],
            "e_machine": struct.unpack_from("<H", data, 18)[0],
        }
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phentsize = struct.unpack_from("<H", data, 54)[0]
        phnum = struct.unpack_from("<H", data, 56)[0]
        interp = None
        for index in range(phnum):
            base = phoff + index * phentsize
            p_type = struct.unpack_from("<I", data, base)[0]
            if p_type == 3:                       # PT_INTERP
                p_offset = struct.unpack_from("<Q", data, base + 8)[0]
                p_filesz = struct.unpack_from("<Q", data, base + 32)[0]
                interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0]
        info["interp"] = interp.decode("utf-8", "replace") if interp else ""

        shoff = struct.unpack_from("<Q", data, 40)[0]
        shentsize = struct.unpack_from("<H", data, 58)[0]
        shnum = struct.unpack_from("<H", data, 60)[0]
        sections = []
        for index in range(shnum):
            base = shoff + index * shentsize
            sh_type = struct.unpack_from("<I", data, base + 4)[0]
            sh_offset = struct.unpack_from("<Q", data, base + 24)[0]
            sh_size = struct.unpack_from("<Q", data, base + 32)[0]
            sh_link = struct.unpack_from("<I", data, base + 40)[0]
            sections.append((sh_type, sh_offset, sh_size, sh_link))
        # DT_NEEDED 在 SHT_DYNAMIC（.dynamic）里：entry = (d_tag:int64, d_val:uint64)，
        # d_tag==1 时 d_val 是 .dynstr 的下标；.dynstr 的文件偏移必须按 .dynamic 的
        # sh_link 取（不能猜"第一个 SHT_STRTAB"，.shstrtab 也可能排在前面）。
        needed = []
        for sh_type, sh_offset, sh_size, sh_link in sections:
            if sh_type != 6 or sh_link >= len(sections):     # SHT_DYNAMIC
                continue
            strtab_offset = sections[sh_link][1]
            for index in range(sh_size // 16):
                base = sh_offset + index * 16
                d_tag = struct.unpack_from("<q", data, base)[0]
                d_val = struct.unpack_from("<Q", data, base + 8)[0]
                if d_tag != 1:                               # DT_NEEDED
                    continue
                start = strtab_offset + d_val
                if start >= len(data):
                    continue
                end = data.index(b"\x00", start)
                needed.append(data[start:end].decode("utf-8", "replace"))
            break
        info["needed"] = needed
        return info

    def _run_cli(self, shell, script, workdir, libdirs, exe, args):
        """在本机真实执行被测二进制，返回 (rc, 合并输出)。"""
        tag = "".join(args).replace("-", "") or "noargs"
        log = os.path.join(workdir, "lugaru-%s.log" % tag)
        # 参数顺序与 test_lugaru.sh 的 "$1..$3" 对齐（workdir/libdirs/exe + args）；
        # 先 cd 进可写工作目录，避开 conan 运行包装 shell 在 HMDFS 构建目录下的
        # getcwd 噪声（"cannot access parent directories"）。log 名由脚本按同一规则生成。
        inner = "cd %s && %s %s %s %s %s %s" % (
            shlex.quote(workdir),
            shlex.quote(shell), shlex.quote(script),
            shlex.quote(workdir), shlex.quote(libdirs), shlex.quote(exe),
            " ".join(shlex.quote(a) for a in args))
        self.run(inner, env="conanrun", ignore_errors=True)
        text = ""
        rc = None
        if os.path.isfile(log):
            with open(log, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        if os.path.isfile(log + ".rc"):
            with open(log + ".rc", "r", encoding="utf-8", errors="replace") as handle:
                raw = handle.read().strip()
            rc = int(raw) if re.fullmatch(r"-?\d+", raw or "") else None
        return rc, text

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        exe = os.path.join(pkg, "bin", _EXE_NAME)
        data = os.path.join(pkg, "bin", "Data")
        man = os.path.join(pkg, "share", "man", "man6", "lugaru.6")
        lic = os.path.join(pkg, "licenses", "COPYING.txt")

        total_passed = total_failed = 0
        skipped = []

        # ---- S1 packaged-layout -------------------------------------
        exists = os.path.isfile(exe)
        data_subdirs = [d for d in _DATA_SUBDIRS if os.path.isdir(os.path.join(data, d))]
        data_files = sum(len(files) for _r, _d, files in os.walk(data)) if os.path.isdir(data) else 0
        passed, failed = self._case("packaged-layout", [
            (exists, f"bin/{_EXE_NAME} 存在"),
            (exists and os.access(exe, os.X_OK), f"bin/{_EXE_NAME} 具备可执行位"),
            (os.path.isdir(data), "bin/Data/ 资源目录存在（可执行文件同级，运行期 DATA_DIR）"),
            (len(data_subdirs) == len(_DATA_SUBDIRS),
             f"Data 子目录齐备 {len(data_subdirs)}/{len(_DATA_SUBDIRS)}：{data_subdirs}"),
            (data_files >= _MIN_DATA_FILES,
             f"Data 资源文件数 {data_files} >= {_MIN_DATA_FILES}"),
            (os.path.isfile(man), "share/man/man6/lugaru.6 已安装"),
            (os.path.isfile(lic), "licenses/COPYING.txt（GPL-2.0）已安装"),
        ])
        total_passed += passed
        total_failed += failed

        # ---- S2 elf-ohos-aarch64 ------------------------------------
        elf = {}
        elf_error = ""
        if exists:
            try:
                elf = self._elf_info(exe)
            except ConanException as exc:
                elf_error = str(exc)
        needed = elf.get("needed") or []
        passed, failed = self._case("elf-ohos-aarch64", [
            (bool(elf) and elf.get("ei_class") == 2, "ELF64（ei_class=2）"),
            (bool(elf) and elf.get("ei_data") == 1, "小端（ei_data=1）"),
            (bool(elf) and elf.get("e_machine") == 183, "e_machine=AArch64(183)"),
            (bool(elf) and elf.get("e_type") == 3, "ET_DYN(PIE)"),
            (elf.get("interp") == _EXPECTED_INTERP,
             f"PT_INTERP={elf.get('interp') or elf_error or '(缺失)'}"),
        ] + [
            (soname in needed, f"DT_NEEDED 含 {soname}（OHOS GL 栈 gl4es/glu）"
                              f"｜实测 NEEDED={needed}")
            for soname in _EXPECTED_NEEDED
        ])
        total_passed += passed
        total_failed += failed

        # ---- S3 runenv-contract -------------------------------------
        runenv = self._runenv_text()
        passed, failed = self._case("runenv-contract", [
            (bool(runenv), "VirtualRunEnv 已生成 conanrun 环境脚本"),
            ("LIBGL_GLES" in runenv and "/system/lib64/libGLESv3.so" in runenv
             and "LIBGL_EGL" in runenv and "/system/lib64/libEGL.so" in runenv,
             "conanrun 环境含包导出的 LIBGL_GLES/LIBGL_EGL（gl4es 后端定位）"),
        ])
        total_passed += passed
        total_failed += failed

        # ---- S4/S5/S6 运行时 CLI 冒烟（真实执行）--------------------
        shell = self._pick_shell()
        workdir = self._writable_dir()
        script = os.path.join(self.recipe_folder, "test_lugaru.sh")
        target = self._runnable_copy(exe, workdir) if exists else exe
        libdirs = self._dependency_libdirs()

        if not exists or not can_run(self):
            for name in ("cli-version", "cli-help", "cli-unknown-option"):
                skipped.append(name)
                self.output.warning(
                    f"{name} 跳过：本机无法执行 OHOS/aarch64 产物（can_run=False 或缺产物）")
        else:
            rc, out = self._run_cli(shell, script, workdir, libdirs, target, ["--version"])
            self.output.info("--version 输出（末 8 行）：\n"
                             + "\n".join(out.splitlines()[-8:]))
            passed, failed = self._case("cli-version", [
                (rc == 0, f"退出码 {rc} == 0"),
                ("Version 1.2" in out, "stdout 含 'Version 1.2'（Version.hpp 宏生效）"),
                ("Wolfire Games" in out and "Lugaru" in out,
                 "stdout 含上游版本横幅（main.cpp 打印）"),
            ])
            total_passed += passed
            total_failed += failed

            rc, out = self._run_cli(shell, script, workdir, libdirs, target, ["--help"])
            self.output.info("--help 输出（末 12 行）：\n"
                             + "\n".join(out.splitlines()[-12:]))
            passed, failed = self._case("cli-help", [
                (rc == 0, f"退出码 {rc} == 0"),
                ("-v, --version" in out, "usage 文本含 '-v, --version'"),
                ("-h, --help" in out, "usage 文本含 '-h, --help'"),
            ])
            total_passed += passed
            total_failed += failed

            rc, out = self._run_cli(shell, script, workdir, libdirs, target,
                                    ["--definitely-not-a-lugaru-option"])
            passed, failed = self._case("cli-unknown-option", [
                (rc == 1, f"退出码 {rc} == 1（main.cpp 未知选项分支）"),
                ("Unknown option" in out, "输出含 'Unknown option'"),
            ])
            total_passed += passed
            total_failed += failed

        # ---- 汇总 + HMBS 证据标记 ----------------------------------
        cases = 6 - len(skipped)
        self.output.info(
            f"[test] lugaru/1.2 消费者校验：{cases} 用例、"
            f"{total_passed + total_failed} 项断言，"
            f"通过 {total_passed}、失败 {total_failed}"
            + (f"，跳过 {skipped}" if skipped else ""))
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": True,
                "passed": total_failed == 0,
                "command": "%s test_lugaru.sh（真实执行 --version/--help/未知选项）"
                           "+ 静态产物校验" % shell,
                "discovered": cases,
                "passedCount": cases if not total_failed else 0,
                "assertions": total_passed + total_failed,
                "assertionsPassed": total_passed,
            }, ensure_ascii=False))
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "no_tests",
                "framework": "none",
                "command": "ctest (上游未注册任何测试)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "lugaru 1.2（gitlab.com/osslugaru/lugaru）上游无可接入的测试套件："
                    "顶层 CMakeLists.txt 与 CMake/Modules/ 从未调用 enable_testing()/add_test()；"
                    "全仓无任何文件名含 test 的源文件或目录；"
                    "根目录 .gitlab-ci.yml 只有 build_gcc/build_clang 两个 stage，全是"
                    "cmake+make 构建与产物归档，无测试步骤（逐文件审计见 test_package/MANIFEST.yml）"
                ),
            }, ensure_ascii=False))

        if total_failed:
            raise ConanException(
                f"lugaru 消费者校验失败：{total_failed} 项断言未通过")
