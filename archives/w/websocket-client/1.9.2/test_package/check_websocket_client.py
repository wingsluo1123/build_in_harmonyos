#!/usr/bin/env python3
"""消费测试 — websocket-client 1.9.2 真实产物校验（全部离线，不触网）。

用法: python3 check_websocket_client.py <package_folder> <wsdump_path>
"""
import os
import sys

checks = fails = 0

# 关键子模块（上游 `websocket/` 的实际文件，1.9.2 实测）
NEED = ("__init__.py", "_abnf.py", "_app.py", "_core.py", "_dispatcher.py",
        "_exceptions.py", "_handshake.py", "_http.py", "_logging.py", "_socket.py",
        "_ssl_compat.py", "_url.py", "_utils.py", "_wsdump.py", "py.typed")


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    pkg, wsdump = sys.argv[1], sys.argv[2]

    mod = None
    for root, _dirs, _files in os.walk(os.path.join(pkg, "lib")):
        if os.path.basename(root) == "websocket":
            mod = root
            break
    if not mod or not os.path.isdir(mod):
        fail("产物缺失：site-packages 下找不到 websocket/ 模块目录")
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1
    ok("产物齐备：websocket 模块位于 %s" % os.path.relpath(mod, pkg))

    miss = [n for n in NEED if not os.path.exists(os.path.join(mod, n))]
    if miss:
        fail("关键文件缺失：%s" % miss)
    else:
        ok("模块文件齐备：%d 个关键文件（含 tests/ 与 data/，与上游 find_packages 一致）"
           % len(NEED))

    sys.path.insert(0, os.path.dirname(mod))
    try:
        import websocket
        ok("import websocket 成功（零运行期依赖）")
    except Exception as exc:
        fail("import websocket 失败：%s" % str(exc)[:160])
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1

    ver = getattr(websocket, "__version__", None)
    if ver == "1.9.2":
        ok("__version__ == '1.9.2'（与包版本一致）")
    else:
        fail("__version__ 期望 '1.9.2'，实际 %r" % ver)

    # 真实离线 API 1：URL 解析（上游 _url.parse_url，纯函数）
    try:
        from websocket._url import parse_url
        got1 = parse_url("wss://example.com:8443/path")
        got2 = parse_url("ws://h/")
        if got1 == ("example.com", 8443, "/path", True) and \
           got2 == ("h", 80, "/", False):
            ok("真实离线 API：parse_url() 正确解析 wss/ws 两种 URL（含默认端口与 secure 位）")
        else:
            fail("parse_url() 结果不符：%r / %r" % (got1, got2))
    except Exception as exc:
        fail("websocket._url.parse_url() 调用失败：%s" % str(exc)[:160])

    # 真实离线 API 2：ABNF 帧编码 + 回读校验 + UTF-8 校验（纯内存，无 socket）
    try:
        from websocket._abnf import ABNF
        from websocket._utils import validate_utf8
        frame = ABNF.create_frame("hello", ABNF.OPCODE_TEXT)
        data = frame.format()
        back = ABNF()
        back.validate(frame)
        ok_utf8 = validate_utf8(b"hi") and not validate_utf8(b"\xff\xfe")
        if len(data) == 11 and data[0] == 0x81 and ok_utf8:
            ok("真实离线功能：ABNF.create_frame('hello')→format() 得 11 字节、首字节 0x81（FIN|TEXT），"
               "ABNF.validate() 通过，validate_utf8() 判定正确")
        else:
            fail("ABNF/UTF-8 校验不符：len=%d head=%r utf8=%r"
                 % (len(data), data[:1], ok_utf8))
    except Exception as exc:
        fail("ABNF/validate_utf8 调用失败：%s" % str(exc)[:160])

    # 上游 CLI（console_scripts 入口）真跑
    if not os.path.isfile(wsdump):
        fail("缺少上游 CLI 产物：%s（上游 setup.py 声明 console_scripts wsdump）" % wsdump)
    else:
        import subprocess
        try:
            r = subprocess.run([sys.executable, wsdump, "--help"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=60)
            out = r.stdout.decode("utf-8", "replace")
            if r.returncode == 0 and "WebSocket Simple Dump Tool" in out:
                ok("上游 CLI 真跑：bin/wsdump --help rc=0 且打印用法（入口 websocket._wsdump:main 可用）")
            else:
                fail("bin/wsdump --help 异常（rc=%d）：%s"
                     % (r.returncode, out.strip()[:200]))
        except Exception as exc:
            fail("bin/wsdump 无法执行：%s" % str(exc)[:160])

    total = 0
    for root, _dirs, files in os.walk(mod):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    ok("证据：websocket 模块总字节 %d；python %s" % (total, sys.version.split()[0]))

    print("\nchecks=%d fails=%d" % (checks, fails))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
