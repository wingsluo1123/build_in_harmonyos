#!/usr/bin/env python3
"""portio 扩展模块消费者测试（test_package 层，非上游测试）。

直接 import 被测包安装出来的 portio 扩展模块并调用其 API（R34：禁止空壳
测试）。分两类用例：
  * scope "portio"      —— 上游 API 契约（导出符号、参数解析、异常类型）
  * scope "portio-ohos" —— 鸿蒙/aarch64 平台特有行为（x86 端口 I/O 不可用时的
                            显式失败语义：18 个 I/O 入口抛 portio.error，
                            ioperm/iopl 返回 ENOSYS）

输出（供 CI / HMBS 解析）：
  CASE [scope] name ... PASS|FAIL
  SUMMARY total=N passed=N failed=N skipped=0 ohos_cases=N
退出码：全部 PASS 为 0，否则 1。
"""
import errno
import sys
import traceback

import portio

# 上游 0.6.2 的 20 个入口（README "Module reference"）
OUT_ENTRY_POINTS = ["outb", "outw", "outl", "outsb", "outsw", "outsl",
                    "outb_p", "outw_p", "outl_p"]
IN_ENTRY_POINTS = ["inb", "inw", "inl", "insb", "insw", "insl",
                   "inb_p", "inw_p", "inl_p"]
PERM_ENTRY_POINTS = ["ioperm", "iopl"]
ALL_ENTRY_POINTS = OUT_ENTRY_POINTS + IN_ENTRY_POINTS + PERM_ENTRY_POINTS
# 非 x86 上走 pio_unsupported() 抛异常的入口（ioperm/iopl 返回 errno）
RAISING_ENTRY_POINTS = OUT_ENTRY_POINTS + IN_ENTRY_POINTS

_CASES = []


def case(scope, name):
    def deco(fn):
        _CASES.append((scope, name, fn))
        return fn
    return deco


# --------------------------------------------------------------------------
# 上游 API 契约
# --------------------------------------------------------------------------
@case("portio", "test_module_exports_all_20_upstream_entry_points")
def _():
    missing = [n for n in ALL_ENTRY_POINTS if not hasattr(portio, n)]
    assert not missing, "missing entry points: %s" % missing
    for name in ALL_ENTRY_POINTS:
        assert callable(getattr(portio, name)), "%s not callable" % name


@case("portio", "test_module_exposes_error_exception")
def _():
    exc = getattr(portio, "error", None)
    assert exc is not None, "portio.error missing"
    assert isinstance(exc, type) and issubclass(exc, Exception), \
        "portio.error is not an exception class: %r" % (exc,)
    assert exc.__name__ == "error", "unexpected exception name: %s" % exc.__name__


@case("portio", "test_outb_rejects_bad_arguments")
def _():
    try:
        portio.outb("not-an-int", 0x378)
    except TypeError:
        return
    raise AssertionError("outb accepted a non-integer data argument")


@case("portio", "test_ioperm_rejects_bad_arguments")
def _():
    try:
        portio.ioperm("x", 1, 1)
    except TypeError:
        return
    raise AssertionError("ioperm accepted a non-integer 'from' argument")


@case("portio", "test_entry_points_require_arguments")
def _():
    for name in ALL_ENTRY_POINTS:
        fn = getattr(portio, name)
        try:
            fn()
        except TypeError:
            continue
        raise AssertionError("%s accepted a call with no arguments" % name)


# --------------------------------------------------------------------------
# 鸿蒙 / aarch64 平台特有语义（x86 端口指令不存在）
# --------------------------------------------------------------------------
@case("portio-ohos", "test_ohos_outb_raises_port_io_error")
def _():
    try:
        portio.outb(0, 0x378)
    except portio.error as exc:
        msg = str(exc)
        assert "outb" in msg, "error message does not name outb: %s" % msg
        assert "not available on this architecture" in msg, \
            "unexpected message: %s" % msg
        # 消息中的架构名随构建目标变化（aarch64/arm/riscv），不在此硬绑定
        assert "(" in msg and ")" in msg, \
            "architecture not reported in message: %s" % msg
        return
    raise AssertionError("outb silently succeeded on a non-x86 platform")


@case("portio-ohos", "test_ohos_inb_raises_port_io_error")
def _():
    try:
        portio.inb(0x378)
    except portio.error as exc:
        assert "inb" in str(exc), "error message does not name inb: %s" % exc
        return
    raise AssertionError("inb returned a value instead of failing on OHOS")


@case("portio-ohos", "test_ohos_ioperm_returns_enosys")
def _():
    status = portio.ioperm(0x378, 1, 1)
    assert status == errno.ENOSYS, \
        "ioperm returned %r, expected ENOSYS(%d)" % (status, errno.ENOSYS)


@case("portio-ohos", "test_ohos_iopl_returns_enosys")
def _():
    status = portio.iopl(3)
    assert status == errno.ENOSYS, \
        "iopl returned %r, expected ENOSYS(%d)" % (status, errno.ENOSYS)


@case("portio-ohos", "test_ohos_all_io_entry_points_fail_loud")
def _():
    # 逐个调用 18 个 I/O 入口：必须全部抛 portio.error，不允许任何“静默成功”
    # （静默成功会向调用者返回 0/None 的假数据）。
    sample_args = {
        "outb": (0, 0x378), "outw": (0, 0x378), "outl": (0, 0x378),
        "outb_p": (0, 0x378), "outw_p": (0, 0x378), "outl_p": (0, 0x378),
        "outsb": (0x378, b"\x00", 1), "outsw": (0x378, b"\x00\x00", 1),
        "outsl": (0x378, b"\x00" * 4, 1),
        "inb": (0x378,), "inw": (0x378,), "inl": (0x378,),
        "inb_p": (0x378,), "inw_p": (0x378,), "inl_p": (0x378,),
        "insb": (0x378, b"\x00", 1), "insw": (0x378, b"\x00\x00", 1),
        "insl": (0x378, b"\x00" * 4, 1),
    }
    silently_succeeded = []
    for name in RAISING_ENTRY_POINTS:
        fn = getattr(portio, name)
        try:
            fn(*sample_args[name])
        except portio.error:
            continue
        except Exception as exc:  # noqa: BLE001 - 记录意外异常类型
            raise AssertionError(
                "%s raised %s instead of portio.error: %s"
                % (name, type(exc).__name__, exc))
        silently_succeeded.append(name)
    assert not silently_succeeded, \
        "entry points silently succeeded on OHOS: %s" % silently_succeeded


def main():
    json_out = None
    argv = sys.argv[1:]
    if "--json-out" in argv:
        json_out = argv[argv.index("--json-out") + 1]

    total = passed = failed = 0
    ohos_total = 0
    cases = []
    failures = []
    for scope, name, fn in _CASES:
        total += 1
        if scope == "portio-ohos":
            ohos_total += 1
        try:
            fn()
        except Exception:
            failed += 1
            cases.append({"scope": scope, "name": name, "result": "FAIL"})
            print("CASE [%s] %s ... FAIL" % (scope, name))
            traceback.print_exc()
            failures.append(name)
        else:
            passed += 1
            cases.append({"scope": scope, "name": name, "result": "PASS"})
            print("CASE [%s] %s ... PASS" % (scope, name))
    print("SUMMARY total=%d passed=%d failed=%d skipped=0 ohos_cases=%d"
          % (total, passed, failed, ohos_total))
    if failures:
        print("FAILED_CASES %s" % ",".join(failures))

    rc = 0 if not failures and ohos_total >= 1 else 1
    if ohos_total < 1:
        print("ERROR: no OHOS-specific case executed")
    if json_out:
        import json
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump({"total": total, "passed": passed, "failed": failed,
                       "skipped": 0, "ohos_cases": ohos_total,
                       "cases": cases, "exit_code": rc}, f,
                      ensure_ascii=False, indent=2)
    return rc


if __name__ == "__main__":
    sys.exit(main())
