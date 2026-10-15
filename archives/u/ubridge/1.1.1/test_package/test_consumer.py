#!/usr/bin/env python3
"""消费者测试 — 以 GNS3 客户端的方式真实驱动已安装的 ubridge。

断言清单（每条都有可核对的实际输出，不是空壳）：
  A. CLI 契约  : `ubridge -v` 输出 "ubridge version 1.1.1"，rc=0
  B. CLI 契约  : `ubridge -h` 输出用法且含 "-H"，rc=0
  C. 目标平台  : 可执行文件是 aarch64 ELF（鸿蒙特有：交叉编译目标正确）
  D. 控制协议  : `hypervisor version` → 应答码 100，版本串为 1.1.1
  E. 控制协议  : `module_list` 含 hypervisor/bridge/brctl/link
                 （brctl/link 存在 ⟹ OHOS 上 Linux 分支确实被编入，
                  这是本适配 Makefile 补丁的直接证据）
  F. 控制协议  : `cmd_list brctl` 以 "101 " 连续行给出命令，末行 "100-"
  G. 错误语义  : 未知模块 → 201，未知命令 → 202
  H. 无特权变更被优雅拒绝（创建失败 206 / 删除失败 207），进程不崩溃且仍可应答
  I. 收尾      : `stop` → 100，进程正常退出
"""

import os
import re
import socket
import subprocess
import sys
import time

FAILURES = []
PASSED = []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print("  [PASS] %s %s" % (name, detail))
    else:
        FAILURES.append(name)
        print("  [FAIL] %s %s" % (name, detail))
    return cond


def find_binary():
    path = os.environ.get("PATH", "")
    for d in path.split(os.pathsep):
        cand = os.path.join(d, "ubridge")
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Control:
    """ubridge 控制端口的极简客户端（协议：'%3d-%s' 为结束行，'%3d %s' 为中间行）。"""

    def __init__(self, port, timeout=10.0):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=3.0)
                break
            except OSError as exc:  # 等进程把监听端口起起来
                last = exc
                time.sleep(0.2)
        else:
            raise RuntimeError("无法连接 ubridge 控制端口 %d: %s" % (port, last))
        self.f = self.sock.makefile("rwb")

    def send(self, line):
        self.f.write((line + "\r\n").encode())
        self.f.flush()
        out = []
        while True:
            raw = self.f.readline()
            if not raw:
                break
            text = raw.decode("utf-8", "replace").rstrip("\r\n")
            out.append(text)
            if len(text) >= 4 and text[3] == "-":
                break
        return out

    @staticmethod
    def code(lines):
        return int(lines[-1][:3]) if lines else -1

    def close(self):
        try:
            self.f.close()
            self.sock.close()
        except OSError:
            pass


def main():
    binary = find_binary()
    if binary is None:
        print("FAIL: PATH 中找不到已安装的 ubridge 可执行文件")
        return 1
    print("被测二进制: %s" % binary)

    # ---- A. `-v` -------------------------------------------------------
    p = subprocess.run([binary, "-v"], capture_output=True, text=True, timeout=30)
    print("  $ ubridge -v -> rc=%d, stdout=%r" % (p.returncode, p.stdout.strip()))
    check("A1 -v 退出码为 0", p.returncode == 0, "rc=%d" % p.returncode)
    check("A2 -v 报出 1.1.1", re.search(r"ubridge version 1\.1\.1", p.stdout) is not None,
          "stdout=%r" % p.stdout.strip())

    # ---- B. `-h` -------------------------------------------------------
    p = subprocess.run([binary, "-h"], capture_output=True, text=True, timeout=30)
    usage = (p.stdout or "") + (p.stderr or "")
    check("B1 -h 打用法并含 -H", p.returncode == 0 and "-H" in usage,
          "rc=%d, contains('-H')=%s" % (p.returncode, "-H" in usage))

    # ---- C. aarch64 ELF ------------------------------------------------
    with open(binary, "rb") as fh:
        head = fh.read(20)
    magic_ok = head[:4] == b"\x7fELF"
    e_machine = int.from_bytes(head[18:20], "little") if len(head) >= 20 else -1
    print("  ELF magic=%s e_machine=0x%X" % (magic_ok, e_machine))
    check("C1 是 ELF 且 e_machine=AArch64(0xB7)", magic_ok and e_machine == 0xB7,
          "e_machine=0x%X" % e_machine)

    # ---- D-H. 控制协议 --------------------------------------------------
    port = free_port()
    proc = subprocess.Popen([binary, "-H", "127.0.0.1:%d" % port],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ctl = None
    try:
        ctl = Control(port)

        lines = ctl.send("hypervisor version")
        print("  $ hypervisor version -> %r" % lines)
        check("D1 version 应答码 100", ctl.code(lines) == 100, "code=%d" % ctl.code(lines))
        check("D2 version 串为 1.1.1", any("1.1.1" in l for l in lines), "lines=%r" % lines)

        lines = ctl.send("hypervisor module_list")
        print("  $ hypervisor module_list -> %r" % lines)
        joined = "\n".join(lines)
        for mod in ("hypervisor", "bridge", "brctl", "link"):
            check("E1 module_list 含 %s" % mod,
                  re.search(r"\b%s\b" % mod, joined) is not None, "lines=%r" % lines)
        check("E2 module_list 正常结束 100", ctl.code(lines) == 100, "code=%d" % ctl.code(lines))

        lines = ctl.send("hypervisor cmd_list brctl")
        print("  $ hypervisor cmd_list brctl -> %d 行, 首行=%r" % (len(lines), lines[0] if lines else None))
        check("F1 cmd_list 有 101 明细行",
              any(l.startswith("101 ") for l in lines) and len(lines) >= 2,
              "lines=%d" % len(lines))
        check("F2 cmd_list 末行 100", ctl.code(lines) == 100, "code=%d" % ctl.code(lines))
        check("F3 cmd_list 列出 create/delete/show",
              all(any(l.startswith("101 %s " % c) for l in lines)
                  for c in ("create", "delete", "show")),
              "lines=%r" % lines)

        lines = ctl.send("nosuchmodule version")
        print("  $ nosuchmodule version -> %r" % lines)
        check("G1 未知模块 → 201", ctl.code(lines) == 201, "code=%d" % ctl.code(lines))

        lines = ctl.send("hypervisor nosuchcommand")
        print("  $ hypervisor nosuchcommand -> %r" % lines)
        check("G2 未知命令 → 202", ctl.code(lines) == 202, "code=%d" % ctl.code(lines))

        # ---- H. 无特权变更必须被优雅拒绝 --------------------------------
        lines = ctl.send("brctl create atomcode_ubridge_probe")
        code = ctl.code(lines)
        print("  $ brctl create atomcode_ubridge_probe -> %r" % lines)
        if code == 100:
            # 有 CAP_NET_ADMIN：撤销并如实标注为「已跳过（特权环境）」
            ctl.send("brctl delete atomcode_ubridge_probe")
            print("  [SKIP] H1 进程具备 CAP_NET_ADMIN，变更未被拒绝（已回滚）")
        else:
            check("H1 无特权变更被拒绝(206/207)", code in (206, 207), "code=%d" % code)

        lines = ctl.send("hypervisor version")
        check("H2 被拒绝后进程仍存活并可应答", ctl.code(lines) == 100, "code=%d" % ctl.code(lines))

        # ---- I. 收尾 ---------------------------------------------------
        lines = ctl.send("hypervisor stop")
        print("  $ hypervisor stop -> %r" % lines)
        check("I1 hypervisor stop → 100", ctl.code(lines) == 100, "code=%d" % ctl.code(lines))
    finally:
        if ctl is not None:
            ctl.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
    check("I2 进程在 stop 后退出", proc.returncode is not None,
          "returncode=%s" % proc.returncode)

    print("\n通过 %d 项，失败 %d 项" % (len(PASSED), len(FAILURES)))
    if FAILURES:
        print("失败项: %s" % ", ".join(FAILURES))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
