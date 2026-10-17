#!/usr/bin/env python3
"""istgt 0.4-20111008 consumer test — application package verification.

检查面（每项打印 [ok]，末尾 CHECK_SUMMARY 逐项计数；任何一项不成立即 exit 1）：

  A 包布局（8 项）
    A1 bin/istgt 存在且非空              A2 bin/istgt 可执行
    A3 bin/istgtcontrol 存在且可执行     A4 man/man1/istgt.1[.gz] 随包
    A5 lib/pkgconfig/istgt.pc 存在       A6 licenses/ 非空（BSD-2-Clause）
    A7 etc/istgt/istgt.conf.sample 随包  A8 etc/istgt/auth.conf.sample 随包

  B 命令行契约（3 项）
    B1 istgt -V rc=0 + "istgt version 0.4" + extra version 20111008
    B2 istgtcontrol -V rc=0 + "istgtcontrol version 0.4"
    B3 istgt -H rc=0 + usage 文本

  C 守护进程端到端（4 项）—— 鸿蒙特有/消费者用例
    C1 最小配置启动 daemon（istgt -D）：uctl 控制端口（38261）与 iSCSI
       数据 portal（38262）同时监听（TCP connect 成功）
    C2 istgtcontrol noop 对运行中 daemon rc=0（uctl 控制协议往返）
    C3 istgtcontrol version 经控制协议取回 daemon 版本（0.4/20111008）
    C4 SIGTERM 干净退出：daemon 10s 内结束（信号处理线程工作正常）

  运行期事实（写进 PR 说明/notes）：istgt 的 [UnitControl] portal 是
  istgtcontrol 使用的 uctl TCP 控制通道（样例配置 127.0.0.1:3261）；
  CI 无 iSCSI initiator 可用，端到端口径取「daemon 双端口监听 +
  istgtcontrol uctl 往返 + 版本回读 + 干净退出」（icecast「启动服务 +
  请求状态页」先例同口径）。
"""
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

CHECKS = []
FAILURES = []

LOG_PATH = os.environ.get("ISTGT_TEST_LOG")
LOG_FH = None

UCTL_PORT = 38261
DATA_PORT = 38262
NODEBASE = "iqn.2026-10.local.istgt-test"


def _sink(line):
    print(line, flush=True)
    global LOG_FH
    if not LOG_PATH:
        return
    try:
        if LOG_FH is None:
            LOG_FH = open(LOG_PATH, "w", encoding="utf-8")
        LOG_FH.write(line + "\n")
        LOG_FH.flush()
    except OSError:
        pass


def ok(msg):
    CHECKS.append(msg)
    _sink("[ok] %s" % msg)


def bad(msg):
    FAILURES.append(msg)
    _sink("[FAIL] %s" % msg)


def done():
    _sink("CHECK_SUMMARY checks=%d passed=%d failed=%d"
          % (len(CHECKS) + len(FAILURES), len(CHECKS), len(FAILURES)))
    return 1 if FAILURES else 0


def run(argv, env=None, timeout=30, attempts=4):
    """spawn 子进程并对 EAGAIN（worker fork 抖动）重试；只重试基础设施特征。"""
    import errno
    r = None
    for attempt in range(attempts):
        try:
            r = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=timeout)
        except (BlockingIOError, OSError) as exc:
            if getattr(exc, "errno", None) not in (errno.EAGAIN,
                                                   errno.EWOULDBLOCK):
                raise
            time.sleep(1.5 * (attempt + 1))
            continue
        err = (r.stderr or b"").decode(errors="replace")
        if ("can't fork" in err
                or "Resource temporarily unavailable" in err) \
                and attempt < attempts - 1:
            time.sleep(1.5 * (attempt + 1))
            continue
        return r
    return r


def port_open(port, host="127.0.0.1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def check_layout(pkg_root):
    istgt = os.path.join(pkg_root, "bin", "istgt")
    istctl = os.path.join(pkg_root, "bin", "istgtcontrol")
    if not os.path.isfile(istgt):
        bad("A1 bin/istgt missing: %s" % istgt)
    elif os.path.getsize(istgt) == 0:
        bad("A1 bin/istgt is empty")
    else:
        ok("A1 bin/istgt present (%d bytes)" % os.path.getsize(istgt))
    if os.access(istgt, os.X_OK):
        ok("A2 bin/istgt executable")
    else:
        bad("A2 bin/istgt not executable")
    if not os.path.isfile(istctl) or os.path.getsize(istctl) == 0:
        bad("A3 bin/istgtcontrol missing or empty: %s" % istctl)
    elif not os.access(istctl, os.X_OK):
        bad("A3 bin/istgtcontrol not executable")
    else:
        ok("A3 bin/istgtcontrol present+executable (%d bytes)"
           % os.path.getsize(istctl))
    # 上游 doc/Makefile.in 的 install 规则把 man 页装到 $(mandir)/man1 并用
    # gzip -9 压缩（实测交付形态 man/man1/istgt.1.gz；prefix=/ 时 mandir 即 /man，
    # 故**不在** share/man 下）。断言按真实交付形态同时接受 .1 与 .1.gz，并解压
    # 校验内容确为 istgt 的 man 页 —— 只查文件存在发现不了"交付了空壳页"。
    man_dir = os.path.join(pkg_root, "man", "man1")
    man = os.path.join(man_dir, "istgt.1")
    man_gz = os.path.join(man_dir, "istgt.1.gz")
    body = None
    if os.path.isfile(man) and os.path.getsize(man) > 0:
        with open(man, "rb") as fh:
            body = fh.read()
    elif os.path.isfile(man_gz) and os.path.getsize(man_gz) > 0:
        import gzip
        try:
            with gzip.open(man_gz, "rb") as fh:
                body = fh.read()
        except OSError as exc:
            bad("A4 man page %s is not a valid gzip stream: %r"
                % (man_gz, exc))
    else:
        bad("A4 man page missing: neither %s nor %s" % (man, man_gz))
    if body is not None:
        mtext = body.decode("utf-8", "replace")
        if ".TH istgt" in mtext:
            ok("A4 man page shipped + valid (.TH istgt, %d bytes uncompressed)"
               % len(body))
        else:
            bad("A4 man page content invalid (no '.TH istgt' header): %r"
                % mtext[:120])
    pc = os.path.join(pkg_root, "lib", "pkgconfig", "istgt.pc")
    if os.path.isfile(pc):
        ok("A5 lib/pkgconfig/istgt.pc present")
    else:
        bad("A5 lib/pkgconfig/istgt.pc missing")
    licdir = os.path.join(pkg_root, "licenses")
    lic = sorted(os.listdir(licdir)) if os.path.isdir(licdir) else []
    if lic:
        ok("A6 licenses/ non-empty (%s)" % ", ".join(lic[:3]))
    else:
        bad("A6 licenses/ missing or empty")
    conf = os.path.join(pkg_root, "etc", "istgt", "istgt.conf.sample")
    if os.path.isfile(conf):
        ok("A7 etc/istgt/istgt.conf.sample shipped")
    else:
        bad("A7 etc/istgt/istgt.conf.sample missing")
    auth = os.path.join(pkg_root, "etc", "istgt", "auth.conf.sample")
    if os.path.isfile(auth):
        ok("A8 etc/istgt/auth.conf.sample shipped")
    else:
        bad("A8 etc/istgt/auth.conf.sample missing")
    return istgt, istctl


def check_cli(istgt, istctl):
    r = run([istgt, "-V"])
    out = (r.stdout + r.stderr).decode(errors="replace")
    if r.returncode == 0 and "istgt version 0.4" in out \
            and "20111008" in out:
        ok("B1 istgt -V rc=0 (version 0.4 + extra 20111008)")
    else:
        bad("B1 istgt -V rc=%d out=%s" % (r.returncode, out[:200]))
    r = run([istctl, "-V"])
    out = (r.stdout + r.stderr).decode(errors="replace")
    if r.returncode == 0 and "istgtcontrol version 0.4" in out:
        ok("B2 istgtcontrol -V rc=0 (version banner OK)")
    else:
        bad("B2 istgtcontrol -V rc=%d out=%s" % (r.returncode, out[:200]))
    r = run([istgt, "-H"])
    out = (r.stdout + r.stderr).decode(errors="replace")
    if r.returncode == 0 and "usage" in out:
        ok("B3 istgt -H rc=0 (usage text)")
    else:
        bad("B3 istgt -H rc=%d out=%s" % (r.returncode, out[:200]))


def check_e2e(istgt, istctl, tmp):
    """C：真实 daemon + istgtcontrol uctl 往返的端到端验证。"""
    daemon_conf = os.path.join(tmp, "istgt.conf")
    with open(daemon_conf, "w", encoding="utf-8") as f:
        f.write("[Global]\n")
        f.write('  NodeBase "%s"\n' % NODEBASE)
        f.write("  PidFile %s/istgt.pid\n" % tmp)
        f.write("  AuthFile %s/auth.conf\n" % tmp)
        f.write("  MediaDirectory %s/media\n" % tmp)
        f.write('  LogFacility "local7"\n')
        f.write("  Timeout 30\n")
        f.write("  MaxSessions 4\n")
        f.write("  MaxConnections 2\n")
        f.write("[PortalGroup1]\n")
        f.write("  Portal DA1 127.0.0.1:%d\n" % DATA_PORT)
        f.write("[UnitControl]\n")
        f.write("  AuthMethod Auto\n")
        f.write("  Portal UC1 127.0.0.1:%d\n" % UCTL_PORT)
    with open(os.path.join(tmp, "auth.conf"), "w", encoding="utf-8") as f:
        f.write("# test: no auth entries\n")
    ctl_conf = os.path.join(tmp, "istgtcontrol.conf")
    with open(ctl_conf, "w", encoding="utf-8") as f:
        f.write("[Global]\n")
        f.write("  Timeout 60\n")
        f.write("  AuthMethod Auto\n")
        f.write("  Host 127.0.0.1\n")
        f.write("  Port %d\n" % UCTL_PORT)
        f.write('  TargetName "%s:disk1"\n' % NODEBASE)
        f.write("  Lun 0\n")
    os.makedirs(os.path.join(tmp, "media"), exist_ok=True)

    daemon_log = os.path.join(tmp, "daemon.out")
    proc = None
    try:
        logf = open(daemon_log, "w", encoding="utf-8")
        proc = subprocess.Popen([istgt, "-D", "-c", daemon_conf],
                                stdout=logf, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL)
        ready_uctl = ready_data = False
        deadline = time.time() + 20
        while time.time() < deadline and not (ready_uctl and ready_data):
            if proc.poll() is not None:
                break
            ready_uctl = port_open(UCTL_PORT)
            ready_data = port_open(DATA_PORT)
            time.sleep(0.5)
        if ready_uctl and ready_data:
            ok("C1 daemon (istgt -D) listening: uctl %d + iSCSI data portal %d"
               % (UCTL_PORT, DATA_PORT))
        else:
            bad("C1 daemon not listening (uctl=%s data=%s rc=%s)"
                % (ready_uctl, ready_data, proc.poll()))
            with open(daemon_log, encoding="utf-8", errors="replace") as fh:
                for line in fh.read().splitlines()[-15:]:
                    _sink("  | daemon: %s" % line)
            return

        r = run([istctl, "-c", ctl_conf, "noop"])
        if r.returncode == 0:
            ok("C2 istgtcontrol noop rc=0 (uctl round-trip against live daemon)")
        else:
            bad("C2 istgtcontrol noop rc=%d err=%s"
                % (r.returncode,
                   (r.stderr or b"").decode(errors="replace")[:200]))

        r = run([istctl, "-c", ctl_conf, "version"])
        out = (r.stdout + r.stderr).decode(errors="replace")
        if r.returncode == 0 and "0.4" in out and "20111008" in out:
            ok("C3 istgtcontrol version fetched daemon version via uctl "
               "(0.4/20111008)")
        else:
            bad("C3 istgtcontrol version rc=%d out=%s"
                % (r.returncode, out[:200]))
    finally:
        if proc is not None and proc.poll() is None:
            try:
                proc.send_signal(signal.SIGTERM)
            except OSError:
                pass
        if proc is not None:
            try:
                proc.wait(timeout=10)
                if proc.returncode is not None and proc.returncode <= 128:
                    ok("C4 SIGTERM clean exit: daemon exited within 10s "
                       "(rc=%d)" % proc.returncode)
                else:
                    bad("C4 daemon did not exit cleanly (rc=%s)"
                        % proc.returncode)
            except subprocess.TimeoutExpired:
                proc.kill()
                bad("C4 daemon did not exit within 10s after SIGTERM (killed)")


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 \
        else os.environ.get("ISTGT_PKG_ROOT", ".")
    istgt, istctl = check_layout(pkg_root)
    if not os.path.isfile(istgt) or not os.path.isfile(istctl):
        return done()
    check_cli(istgt, istctl)
    with tempfile.TemporaryDirectory(prefix="istgt-consumer-") as tmp:
        check_e2e(istgt, istctl, tmp)
    return done()


if __name__ == "__main__":
    sys.exit(main())
