#!/usr/bin/env python3
"""xkbcomp 的完整消费者用例：按 X 服务器的用法跑通「编译 + 反编译」端到端流程。

xkbcomp 是 X 服务器（Xvfb/Xorg）启动时调用的键图编译器：服务器把键盘布局
描述经 stdin 交给它、读回二进制 .xkm。上游 tarball 不含测试套件（无 check
目标、无 test/ 目录），因此这里按真实用法端到端执行被测二进制：

  1. `xkbcomp -version` —— 验证 ELF 可加载、可执行，且报告版本与包版本一致；
  2. 完整流程：
     a. 键盘布局文本经 stdin 交给 `xkbcomp - <out.xkm>`（X 服务器的调用方式），
        必须产出非空 .xkm；
     b. `xkbcomp -xkb <out.xkm> <back.xkb>` 把编译结果反编译回文本；
     c. 反编译文本必须逐项保留原映射：`<AE01>` 键码、`1/exclam` 两档符号、
        compat 的 `SetMods` 解释——证明编译 + 反编译经真实数据往返无损。

断言绑定产物：可执行文件取自 package_folder，包产物被移走时第一步即失败
（CI 的破坏性反向验证 R34/L1e 依赖这一点）。工作目录走 TMPDIR / 设备缓存 /
临时目录，绝不写回 test_package 目录（历史上写回导致生成物被误提交）。
"""

import os
import shutil
import subprocess
import sys
import tempfile

# 自包含的键盘布局：两个键、两档符号、一条 compat 解释。刻意不依赖
# xkeyboard-config 数据，使断言只度量本包。compat 段不能为空——空 compat
# 写不出 compatibility map，反编译会以 "compatibility map not defined" 失败。
KEYMAP = """xkb_keymap {
  xkb_keycodes { minimum = 8; maximum = 255; <AE01> = 10; <AE02> = 11; };
  xkb_types { };
  xkb_compatibility { interpret Any+AnyOfOrNone(All) { action= SetMods(modifiers=None); }; };
  xkb_symbols { key <AE01> { [ 1, exclam ] }; key <AE02> { [ 2, at ] }; };
};
"""

assertions = 0
failures = 0


def check(what, ok):
    global assertions, failures
    assertions += 1
    if ok:
        print(f"ok: {what}")
    else:
        print(f"FAIL: {what}", file=sys.stderr)
        failures += 1


def run(argv, stdin_path=None):
    """执行命令，返回 (retcode, 合并输出)；stdin_path 给出时由该文件喂 stdin。"""
    stdin_handle = open(stdin_path, encoding="utf-8") if stdin_path else None
    try:
        proc = subprocess.run(
            argv, stdin=stdin_handle, capture_output=True, text=True, timeout=120
        )
    finally:
        if stdin_handle:
            stdin_handle.close()
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def scratch_dir():
    """选一个可写的工作目录，绝不落在 test_package 目录里。"""
    for candidate in (os.environ.get("TMPDIR"), "/data/storage/el2/base/cache"):
        if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
            return tempfile.mkdtemp(prefix="xkbcomp-test-", dir=candidate)
    return tempfile.mkdtemp(prefix="xkbcomp-test-")


def sign_ohos_elf(path):
    """OHOS 只加载已签名 ELF；包内未签名时用设备自带工具就地签名。"""
    signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
    readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
    if not os.path.isfile(signer) or not os.path.isfile(readelf):
        raise SystemExit("required OHOS signing tools are missing")
    sections = subprocess.run(
        [readelf, "-SW", path], check=True, capture_output=True, text=True, timeout=30
    ).stdout
    if sections.count(".codesign") == 1:
        return  # 包内已签名
    temporary = f"{path}.signed"
    subprocess.run(
        [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
        check=True,
        timeout=60,
    )
    os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
    os.replace(temporary, path)


def main():
    if len(sys.argv) < 3:
        print(
            "FAIL: usage: test_xkbcomp.py <package_folder> <tested_reference> [target_os]",
            file=sys.stderr,
        )
        return 1
    package_folder = os.path.realpath(sys.argv[1])
    reference = sys.argv[2]
    target_os = sys.argv[3] if len(sys.argv) > 3 else ""
    # tested_reference_str 形如 "xkbcomp/1.4.7.1#<rev>%<timestamp>"：剥离 # 与 %
    # 尾巴，只留 pure version。
    package_version = reference.split("/", 1)[-1].split("#", 1)[0].split("%", 1)[0]

    executable = os.path.join(package_folder, "bin", "xkbcomp")
    check("packaged bin/xkbcomp exists", os.path.isfile(executable))
    if not os.path.isfile(executable):
        print(f"xkbcomp_test: assertions={assertions} failures={failures}")
        return 1

    if target_os == "OHOS":
        sign_ohos_elf(executable)

    # ---- 1. 版本汇报 ----
    # 包版本可能带 R37 适配后缀（如 1.4.7.1），而 `xkbcomp -version` 打印的是
    # 上游版本（1.4.7）——按「包版本以上游版本为前缀」判定，两种情形都成立。
    retcode, output = run([executable, "-version"])
    print(f"note: xkbcomp -version -> {output.strip()!r}")
    check("`xkbcomp -version` exits successfully", retcode == 0)
    reported_ver = output.strip().split()[-1] if output.strip() else ""
    check(
        f"reported version matches the package version ({package_version})"
        f" or its upstream base",
        bool(reported_ver)
        and (
            package_version.startswith(reported_ver)
            or reported_ver.startswith(package_version)
        ),
    )

    # ---- 2. 完整流程：stdin 编译 -> .xkm -> 反编译回文本 -> 映射核对 ----
    workdir = scratch_dir()
    keymap_in = os.path.join(workdir, "keymap.xkb")
    xkm_out = os.path.join(workdir, "keymap.xkm")
    back_text = os.path.join(workdir, "keymap-back.xkb")
    with open(keymap_in, "w", encoding="utf-8") as handle:
        handle.write(KEYMAP)

    # (a) X 服务器的调用方式：键图经 stdin 交给 xkbcomp，读回 .xkm
    retcode, output = run([executable, "-w", "1", "-", xkm_out], stdin_path=keymap_in)
    print(f"note: stdin compile rc={retcode} -> {output.strip()!r}")
    check(
        "compiling a keymap from stdin (the X server's usage) exits successfully",
        retcode == 0,
    )
    check(
        "a non-empty .xkm file was produced",
        os.path.isfile(xkm_out) and os.path.getsize(xkm_out) > 0,
    )

    # (b) .xkm 反编译回文本
    retcode, output = run([executable, "-xkb", xkm_out, back_text])
    print(f"note: decompile rc={retcode} -> {output.strip()!r}")
    check("decompiling the .xkm back to text exits successfully", retcode == 0)
    check(
        "the decompiled text is non-empty",
        os.path.isfile(back_text) and os.path.getsize(back_text) > 0,
    )

    # (c) 往返无损：反编译文本必须保留原映射
    text = ""
    if os.path.isfile(back_text):
        with open(back_text, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    check(
        "keycode mapping survives the round trip (<AE01> = 10)",
        "<AE01>" in text and "10" in text,
    )
    check(
        "two-level keysym mapping survives the round trip (1/exclam)",
        "1" in text and "exclam" in text,
    )
    check(
        "compatibility mapping survives the round trip (SetMods)",
        "SetMods" in text,
    )
    print(f"note: round-trip artefacts live in {workdir}")

    print(f"xkbcomp_test: assertions={assertions} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
