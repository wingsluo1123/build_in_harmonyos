#!/usr/bin/env python3
"""Conan test_package — forensics-colorize 1.1（OHOS 消费者端到端测试）

本包是「可执行文件型」三方库（package_type=application），因此 test_package
验证的不是链接 API，而是**把 conan 装进包里的两个真实二进制当成黑盒跑通**：

* ``colorize``    —— 把字节流渲染成 24 位 BMP，逐像素对照上游 write_byte 映射；
* ``filecompare`` —— 按块比对两个文件，逐块核对 0x80 / 0xFE / 0xFF 块类型字节。

全部断言写在同级 ``test_forensics_colorize.c``（L0c 测试源，767 行，5 个
测试组），它通过 ``system()`` 以**消费者真实命令行**驱动 ``<package>/bin/``
下的可执行文件，断言退出码 / stdout / stderr / 上游写出的 BMP 字节，最后
打印一行契约汇总：

    RESULT: PASS|FAIL (N checks, M failures)

``test()`` 解析这一行拿到 **实测** 的 N/M（绝不硬编码数字 —— 否则上游行为
一变，marker 就会继续谎报通过），M != 0 即让 conan create 失败（fail-closed）。

执行环境：
* WSL 交叉构建时由 ``ohos-aarch64-run`` profile 注入的 emulator
  （``tools.cmake.cmaketoolchain:extra_variables`` 里的
  CMAKE_CROSSCOMPILING_EMULATOR）运行 aarch64 产物；
* 鸿蒙 PC 原生构建时直接跑本机 clang 15 产物。
  本机 ``/tmp`` 是只读 tmpfs，故用 ``TMPDIR``/``HOME`` 兜底（见测试源 main()）。
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException


# C 端汇总行契约："RESULT: PASS (412 checks, 0 failures)"
_RESULT_RE = re.compile(r"RESULT:\s*(PASS|FAIL)\s*\((\d+)\s+checks,\s*(\d+)\s+failures\)")


def _parse_result(out):
    """解析测试程序真实打印的 (verdict, checks, failures)；解析不到就返回 None。

    解析失败必须抛错而不是回退到默认值：没有实测数字的「通过」不可信。
    """
    m = _RESULT_RE.search(out or "")
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3))


class ForensicsColorizeTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "profile 缺少 tools.build:compiler_executables.c（test_package 需用同一编译器）"
            )
        return cc

    def build(self):
        cc = self._cc()
        src = os.path.join(self.source_folder, "test_forensics_colorize.c")
        exe = os.path.join(self.build_folder, "test_forensics_colorize")
        # 消费者视角：一个普通 C99 程序，不链接本包（本包只提供可执行文件）
        self.run(f'"{cc}" -O2 -Wall -Wextra -std=c99 -D_DEFAULT_SOURCE '
                 f'-o "{exe}" "{src}"', cwd=self.build_folder)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        bin_dir = os.path.join(dep.package_folder, "bin")
        for prog in ("colorize", "filecompare"):
            if not os.path.isfile(os.path.join(bin_dir, prog)):
                raise ConanException(f"包内缺少可执行文件：{bin_dir}/{prog}")

        exe = os.path.join(self.build_folder, "test_forensics_colorize")
        self.run(f'"{exe}" "{bin_dir}"', cwd=self.build_folder)

        # 二次确认：从 conan 捕获的输出里解析实测数字，写进构建日志便于审计
        outfile = os.path.join(self.build_folder, "tp_stdout.txt")
        self.run(f'"{exe}" "{bin_dir}" > "{outfile}" 2>&1', cwd=self.build_folder)
        with open(outfile, encoding="utf-8", errors="replace") as fh:
            out = fh.read()
        parsed = _parse_result(out)
        print(out)
        if parsed is None:
            raise ConanException("test_forensics_colorize 未输出可解析的 RESULT 汇总行")
        verdict, checks, failures = parsed
        self.output.info(
            f"FORENSICS_COLORIZE_TP_RESULT verdict={verdict} "
            f"checks={checks} failures={failures}"
        )
        if verdict != "PASS" or failures != 0:
            raise ConanException(
                f"消费者端到端测试失败：{checks} checks, {failures} failures"
            )
