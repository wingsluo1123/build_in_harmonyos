# -*- coding: utf-8 -*-
"""detect-libc-symbol-clash.py 自测套件（知识库拓展 B 类交付物）

全部使用仓库内合成 fixture：不依赖真实 sysroot、不联网、不读本地缓存，
因此在干净机器 / CI / OHOS aarch64 上行为一致（确定性输出）。

运行:
    python3 knowledge/tools/libc-symbol-clash/test_libc_symbol_clash.py
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # knowledge/tools/libc-symbol-clash → repo root
TOOL = HERE / "detect-libc-symbol-clash.py"
FIX = HERE / "fixtures"

# 剥离可能影响 sysroot 自动推断的环境变量，保证结果确定
_STRIP = ("OHOS_SYSROOT", "OHC_SYSROOT", "OHOS_SDK", "OHOS_SDK_ROOT", "OHOS_SDK_NATIVE",
          "OHC_OHOS_SDK", "CPPFLAGS", "CFLAGS", "CXXFLAGS")
ENV = {k: v for k, v in os.environ.items() if k not in _STRIP}

RESULTS = []


def run(args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, env=ENV, cwd=str(REPO))


def payload(p):
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - 失败时给出可诊断信息
        raise AssertionError(f"JSON 解析失败: {exc}\nstdout={p.stdout[:400]}\nstderr={p.stderr[:400]}")


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


def main():
    # 1) includes：kea 形态（libc net/if.h + UAPI linux/rtnetlink.h，后者经项目头间接/直接引入）
    p = run(["includes", "--src", str(FIX / "src"), "--json"])
    d = payload(p)
    hits = {f["id"]: f for f in d["findings"]}
    check("includes 命中 CLASH-001(sockaddr_storage, HIGH)",
          hits.get("CLASH-001", {}).get("severity") == "HIGH", str(d["summary"]))
    check("includes 位置指向 iface_mgr_linux.cc",
          hits.get("CLASH-001", {}).get("where", "").endswith("iface_mgr_linux.cc"),
          hits.get("CLASH-001", {}).get("where", ""))
    check("includes 证据同时给出 libc 与 UAPI 两侧来源",
          len(hits.get("CLASH-001", {}).get("evidence_lines", [])) >= 2,
          str(hits.get("CLASH-001", {}).get("evidence_lines")))
    check("includes 退出码 1（存在 HIGH/MEDIUM）", p.returncode == 1, f"rc={p.returncode}")

    # 2) 对照组：只有 libc 头的 TU 应零命中
    p2 = run(["includes", "--src", str(FIX / "src_clean"), "--json"])
    d2 = payload(p2)
    check("干净 TU 无命中且 rc=0",
          p2.returncode == 0 and d2["summary"]["total"] == 0, str(d2["summary"]))

    # 3) sysroot 实测模式（合成 sysroot：两侧同名声明）
    p3 = run(["sysroot", "--sysroot", str(FIX / "sysroot"), "--json"])
    d3 = payload(p3)
    idents = {f["ident"] for f in d3["findings"]}
    check("sysroot 实测发现两侧同现的 sockaddr_storage/in_addr",
          {"sockaddr_storage", "in_addr"} <= idents, str(sorted(idents)))
    check("sysroot 只报两侧同现（libc 独有的 sockaddr/msghdr 不入册）",
          not ({"sockaddr", "msghdr"} & idents), str(sorted(idents)))
    check("sysroot 扫描头文件数 >= 6", d3["scanned"] >= 6, str(d3["scanned"]))
    check("sysroot 报告两侧证据行",
          all(f["evidence_lines"] for f in d3["findings"]))

    # 3b) includes + --sysroot：用实测把候选收敛为权威口径
    p3b = run(["includes", "--src", str(FIX / "src"), "--sysroot", str(FIX / "sysroot"), "--json"])
    d3b = payload(p3b)
    ids3b = [f["id"] for f in d3b["findings"]]
    check("includes --sysroot 剔除未复现候选（CLASH-006 ifreq 消失）",
          "CLASH-001" in ids3b and "CLASH-006" not in ids3b, str(ids3b))
    check("includes --sysroot 命中标记 verified",
          all(f["confidence"] == "verified" for f in d3b["findings"]), str(d3b["summary"]))

    # 3c) 已 guard 的 TU（kea 修复形态）自动降级 → 默认阈值不报红
    p3c = run(["includes", "--src", str(FIX / "src_patched"),
               "--sysroot", str(FIX / "sysroot"), "--json"])
    d3c = payload(p3c)
    check("已 guard 的 TU 降级为 LOW 且 rc=0",
          p3c.returncode == 0 and d3c["summary"]["total"] == 0, str(d3c["summary"]))
    p3d = run(["includes", "--src", str(FIX / "src_patched"), "--sysroot", str(FIX / "sysroot"),
               "--min-severity", "LOW", "--json"])
    d3d = payload(p3d)
    check("--min-severity LOW 可见 guarded 记录（审计留痕）",
          any(f.get("confidence") == "guarded" for f in d3d["findings"]) and p3d.returncode == 0,
          str(d3d["summary"]))

    # 4) source 模式：项目自身重定义 libc 名字
    p4 = run(["source", "--src", str(FIX / "src_selfdefs"), "--json"])
    d4 = payload(p4)
    check("source 命中项目侧 sockaddr_storage 重定义",
          p4.returncode == 1 and any(f["ident"] == "sockaddr_storage" for f in d4["findings"]),
          str(d4["summary"]))

    # 5) lint：平台宏命中，libc 鉴别探针不误报
    p5 = run(["lint", "--patches", str(FIX / "patch-samples"), "--json"])
    d5 = payload(p5)
    check("lint 命中 GUARD-001 且仅 1 条",
          d5["summary"]["total"] == 1 and d5["findings"][0]["id"] == "GUARD-001", str(d5["summary"]))
    check("lint 指向 0001（__OHOS__）而非 0002（libc 探针）",
          "0001" in d5["findings"][0]["where"], d5["findings"][0]["where"])
    check("lint 对真实 kea 补丁（libc 探针）零误报",
          not any("0003-real-kea" in f["where"] for f in d5["findings"]))

    # 5b) 真实样例补丁与归档逐字节一致（防样例被改写后失去"真实世界正例"意义）
    real = FIX / "patch-samples" / "0003-real-kea-3.0.3-sockaddr-storage.patch"
    check("真实样例补丁 sha256 与归档一致",
          real.is_file() and hashlib.sha256(real.read_bytes()).hexdigest()
          == "a19a64b5556510e15c3d8ce488841375afe258f4d728bb35293a9f6ace1ae8b0",
          "样例补丁缺失或被改写")

    # 6) 阈值 / 忽略 / 基线开关
    p6 = run(["includes", "--src", str(FIX / "src"), "--min-severity", "HIGH", "--json"])
    check("--min-severity HIGH 只保留 HIGH", payload(p6)["summary"]["total"] == 1,
          str(payload(p6)["summary"]))
    p7 = run(["includes", "--src", str(FIX / "src"),
              "--ignore", "CLASH-001,CLASH-002,CLASH-003,CLASH-006", "--json"])
    check("--ignore 屏蔽后 rc=0", p7.returncode == 0 and payload(p7)["summary"]["total"] == 0,
          str(payload(p7)["summary"]))
    p8 = run(["includes", "--src", str(FIX / "src"), "--no-baseline", "--json"])
    check("--no-baseline 无规则 → 无命中",
          p8.returncode == 0 and payload(p8)["summary"]["total"] == 0)

    # 7) --out 落盘 + 确定性
    tmp = Path(os.environ.get("OHC_TEST_TMP") or (Path.home() / "tmp"))
    tmp.mkdir(parents=True, exist_ok=True)
    out = tmp / "libc-symbol-clash-selftest.json"
    if out.exists():
        out.unlink()
    run(["includes", "--src", str(FIX / "src"), "--json", "--out", str(out)])
    check("--out 落盘为合法 JSON 且 mode 正确",
          out.is_file() and json.loads(out.read_text(encoding="utf-8"))["mode"] == "includes")
    p9 = run(["includes", "--src", str(FIX / "src"), "--json"])
    check("输出确定性（两次运行一致）", p9.stdout == p.stdout)

    # 8) 用法错误 → rc=2
    check("无 mode → rc=2", run([]).returncode == 2)
    check("includes 缺 --src → rc=2", run(["includes"]).returncode == 2)
    check("lint 缺 --patches → rc=2", run(["lint"]).returncode == 2)

    # 8b) --sysroot 不存在 → rc=2（三种模式口径一致；防 sysroot 读空被误判为"无命中/判绿"）
    missing = FIX / "sysroot_missing"
    check("sysroot --sysroot 不存在 → rc=2",
          run(["sysroot", "--sysroot", str(missing), "--json"]).returncode == 2)
    check("source --sysroot 不存在 → rc=2",
          run(["source", "--src", str(FIX / "src"), "--sysroot", str(missing), "--json"]).returncode == 2)
    check("includes --sysroot 不存在 → rc=2",
          run(["includes", "--src", str(FIX / "src"), "--sysroot", str(missing), "--json"]).returncode == 2)

    # 9) 模板输出
    p10 = run(["--print-template"])
    check("--print-template 给出 libc 鉴别探针模板",
          p10.returncode == 0 and "!defined(__GLIBC__)" in p10.stdout
          and "__linux_uapi_" in p10.stdout)

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if not ok and detail:
            line += f"  ({detail})"
        print(line)
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} 断言通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
