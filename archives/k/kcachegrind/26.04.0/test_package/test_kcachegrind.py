#!/usr/bin/env python3
"""消费者测试：kcachegrind 26.04.0 (HarmonyOS PC)。

本脚本按「用例」组织，而不是一堆孤立断言（rule12 口径：鸿蒙特有测试必须包含
**至少一个完整消费者用例** —— 真正跑通功能/流程的端到端用例）：

  CASE 1（集成测试）  运行期冒烟：offscreen 运行安装后的 `--version`
  CASE 2（鸿蒙特有）  **完整消费者用例：Callgrind 剖面分析端到端流程**
                      构造输入 → 真实执行 → 产出结果 → 校验内容（见下）
  CASE 3（鸿蒙特有）  产物布局 + OHOS ELF 专项校验

CASE 2 的四段式：
  · 构造输入：内嵌**确定性** callgrind 语料（无随机）；主语料 `e1` 为
      main → parse_trace → build_model 的真实调用链；对照语料 `e2` 与 e1
      **开销结构相同、仅入口函数改名**（去掉 `main`）。
      另给每次运行一个可写的 `XDG_CONFIG_HOME`。
  · 真实执行：offscreen 启动安装后的 `bin/kcachegrind <trace>`，走完整产品链路
      —— 进程启动 → Qt6/KF6 平台与 UI 初始化 → loader/插件发现 → 解析 callgrind
      → 构建 TraceData/CostItem 模型 → 函数视图/调用图选中入口函数 → 退出时
      写回 KConfig（窗口布局）。
  · 产出结果：① stderr 的 `Selected  "<fn>"`；② `<XDG_CONFIG_HOME>/kcachegrindrc`；
      ③ 进程存活状态；④ stderr 是否有加载错误。
  · 校验内容：① 独立 Python 参考实现（自带 callgrind 文本解析）算出的入口函数
      与产品选中的函数一致；② 参考实现的总自身开销与语料自带 `summary:` 声明
      一致（交叉验证参考实现本身）；③ 对照语料（入口改名）**不**选中 `main`
      —— 证明选中由输入驱动、非硬编码；④ `kcachegrindrc` 写出且含 `[Layouts]`
      —— 证明 KConfig 读写流程真实走通；⑤ 两次运行均无 loader/symbol 错误；
      ⑥ 主语料运行期间 GUI 存活未崩。

KF6 依赖库坏 `DT_NEEDED` 的说明见 test_package/conanfile.py 的
`_reconstruct_kf6_rpaths()`；本脚本以继承的 CWD（`<cache>/recon/kcg`）运行。
所有外部工具用**绝对路径**解析（踩坑清单 #39：本宿主 posix_spawn 快路径不做裸名
PATH 查找）。
"""
import os
import shutil
import subprocess
import sys

BIN = os.environ.get("KCACHEGRIND_BIN", "")
PKG = os.environ.get("KCACHEGRIND_PKG", "")

CONVERTERS = [
    "dprof2calltree",
    "hotshot2calltree",
    "memprof2calltree",
    "op2calltree",
    "pprof2calltree",
]

# ── 确定性语料（CASE 2 的「构造输入」）────────────────────────────────────
# 自身开销：main 220（120+100）、parse_trace 900、build_model 980；summary 2100
E1_TRACE = """# callgrind format
version: 1
creator: callgrind-3.22.0
pid: 4321
cmd: ./kcg_consumer
part: 1
desc: Trigger: Program termination
positions: line
events: Ir
summary: 2100
ob=(1) /usr/bin/kcg_consumer
fl=(1) consumer.c
fn=(1) main
10 120
cfl=(1)
cfn=(2) parse_trace
calls=1 40
fn=(2) parse_trace
40 900
cfl=(1)
cfn=(3) build_model
calls=2 70
fn=(3) build_model
70 980
fn=(1) main
11 100
"""

# 对照语料：与 E1 开销结构完全相同，仅把入口函数 main → entry_point
E2_TRACE = E1_TRACE.replace("fn=(1) main", "fn=(1) entry_point")

failures = []
checks = 0


def check(cond, label, detail=""):
    global checks
    checks += 1
    if cond:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label} {detail}")
        failures.append(label)


def tool(names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for p in (
        "/data/service/hnp/bin/readelf",
        "/data/service/hnp/bin/llvm-readelf",
        "/usr/bin/readelf",
    ):
        if os.path.exists(p):
            return p
    return None


def run(cmd, timeout=180, env=None, cwd=None):
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd
    )


# ── 独立参考实现：callgrind 文本解析（不依赖产品任何代码）────────────────
def parse_callgrind(text):
    """极简 callgrind 解析：返回 (各函数自身开销 dict, 调用边 set, 声明 summary)。

    规则：`fn=(n) NAME` 切换当前函数；随后的 `<line> <cost>` 行为该函数的自身
    开销；`cfn=(n) NAME` 记录一条调用边（本语料为自开销语料，不含 call-cost 块）。
    """
    self_cost = {}
    edges = set()
    cur = None
    pending_callee = None
    declared = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("summary:"):
            declared = int(line.split(":", 1)[1].strip())
        elif line.startswith("fn="):
            cur = line.split(")", 1)[1].strip()
            self_cost.setdefault(cur, 0)
        elif line.startswith("cfn="):
            pending_callee = line.split(")", 1)[1].strip()
        elif line.startswith("calls="):
            if cur and pending_callee:
                edges.add((cur, pending_callee))
            pending_callee = None
        else:
            parts = line.split()
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                if cur:
                    self_cost[cur] = self_cost.get(cur, 0) + int(parts[1])
    return self_cost, edges, declared


def reference_entry(self_cost, edges, declared_name="main"):
    """领域规则：trace 的入口函数 = 名为 declared_name 且无调用者的函数。"""
    callees = {c for _, c in edges}
    if declared_name in self_cost and declared_name not in callees:
        return declared_name
    return None


def selected_function(output):
    """从产品 stderr 中取出最后一次 `Selected  "<fn>"` 的函数名。"""
    name = None
    for ln in output.splitlines():
        if ln.startswith("Selected"):
            rest = ln[len("Selected"):].strip()
            if rest.startswith('"') and rest.endswith('"') and len(rest) > 1:
                name = rest[1:-1]
    return name


def gui_run(binary, trace, workdir, tag, timeout=30):
    """真实执行一次产品（offscreen），返回 (out, alive, config_dir)。"""
    cfg = os.path.join(workdir, f"config-{tag}")
    os.makedirs(cfg, exist_ok=True)
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/nonexistent-ohos-bus")
    env["XDG_CONFIG_HOME"] = cfg
    env["XDG_CACHE_HOME"] = cfg
    out, alive = "", False
    try:
        r = run([binary, trace], timeout=timeout, env=env)
        out = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as exc:
        alive = True            # 超时=进程仍在运行（GUI 活着、未崩）
        for stream in (exc.stdout, exc.stderr):
            if isinstance(stream, bytes):
                stream = stream.decode("utf-8", "replace")
            out += stream or ""
    return out, alive, cfg


def main():
    print(f"== CASE 1: 运行期冒烟 (bin={BIN}) ==")
    check(bool(BIN) and os.path.isfile(BIN), "bin/kcachegrind installed")
    check(bool(BIN) and os.access(BIN, os.X_OK),
          "bin/kcachegrind is executable")
    version_out = ""
    if BIN and os.path.isfile(BIN):
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
        env.setdefault("DBUS_SESSION_BUS_ADDRESS",
                       "unix:path=/nonexistent-ohos-bus")
        try:
            r = run([BIN, "--version"], timeout=180, env=env)
            version_out = (r.stdout or "") + (r.stderr or "")
            print(f"  rc={r.returncode} out={version_out.strip()[:120]}")
            check(r.returncode == 0, "kcachegrind --version exit 0")
            check("26.04.0" in version_out or "26.4.0" in version_out,
                  "version string 26.04.0 in output")
        except subprocess.TimeoutExpired:
            check(False, "kcachegrind --version finished", "(timeout 180s)")

    print("== CASE 2: 完整消费者用例 —— Callgrind 剖面分析端到端流程 ==")
    workdir = os.path.join(os.environ.get("TMPDIR", "/data/local/tmp"),
                           "kcachegrind-e2e")
    os.makedirs(workdir, exist_ok=True)
    e1 = os.path.join(workdir, "e1.callgrind")
    e2 = os.path.join(workdir, "e2_control.callgrind")
    with open(e1, "w") as f:
        f.write(E1_TRACE)
    with open(e2, "w") as f:
        f.write(E2_TRACE)
    print(f"  cwd={os.getcwd()}")
    print(f"  构造输入: {e1} ({len(E1_TRACE)}B) + 对照 {e2}")

    # 独立参考实现：由语料文本算出入口函数与总自身开销
    self_cost, edges, declared = parse_callgrind(E1_TRACE)
    ref_total = sum(self_cost.values())
    ref_entry = reference_entry(self_cost, edges, "main")
    print(f"  参考实现: self_cost={self_cost} edges={sorted(edges)} "
          f"total={ref_total} declared_summary={declared} entry={ref_entry}")
    check(declared is not None and ref_total == declared,
          "参考实现自校：解析出的总自身开销 == 语料声明 summary",
          f"({ref_total} vs {declared})")
    check(ref_entry == "main", "参考实现的入口函数 == main", f"({ref_entry})")

    out1, alive1, cfg1 = ("", False, "")
    if BIN and os.path.isfile(BIN):
        out1, alive1, cfg1 = gui_run(BIN, e1, workdir, "e1", timeout=30)
        sel1 = selected_function(out1)
        print(f"  产出结果(e1): alive={alive1} selected={sel1!r}")
        check(alive1, "e1: GUI 存活 30s 未崩（产品真实跑起来）")
        check(sel1 == ref_entry,
              "e1: 产品选中的函数 == 独立参考实现算出的入口函数",
              f"({sel1!r} vs {ref_entry!r})")
        rc = os.path.join(cfg1, "kcachegrindrc")
        cfg_txt = open(rc).read() if os.path.isfile(rc) else ""
        print(f"  产出结果(e1): config={rc} exists={bool(cfg_txt)}")
        check(bool(cfg_txt) and "[Layouts]" in cfg_txt,
              "e1: 退出时写回 kcachegrindrc 且含 [Layouts]（KConfig 流程走通）")

        # 对照语料：结构相同、入口改名 ⇒ 选中结果必须随之改变（输入驱动）
        out2, _alive2, _cfg2 = gui_run(BIN, e2, workdir, "e2", timeout=15)
        sel2 = selected_function(out2)
        print(f"  产出结果(e2 对照): selected={sel2!r}")
        check(sel2 != "main",
              "对照语料（入口改名）不再选中 main —— 选中由输入驱动、非硬编码",
              f"(selected={sel2!r})")

        errs = [ln for ln in (out1 + "\n" + out2).splitlines()
                if "Error loading shared library" in ln
                or "symbol not found" in ln]
        check(not errs, "两次运行均无 loader/symbol 错误", str(errs[:2]))

    print("== CASE 3: 产物布局 + OHOS ELF 专项校验 ==")
    for name in CONVERTERS:
        check(os.path.isfile(os.path.join(PKG, "bin", name)),
              f"converter bin/{name} installed")
    for shared in ("share/applications/org.kde.kcachegrind.desktop",
                   "share/metainfo/org.kde.kcachegrind.appdata.xml"):
        check(os.path.isfile(os.path.join(PKG, shared)),
              f"desktop metadata {shared}")
    rf = tool(["readelf"])
    check(rf is not None, "readelf available")
    if rf and BIN and os.path.isfile(BIN):
        hdr = run([rf, "-h", BIN]).stdout
        dyn = run([rf, "-d", BIN]).stdout
        check("DYN (" in hdr or "DYN  (" in hdr, "PIE executable (ET_DYN)")
        check("GNU_STACK" in run([rf, "-l", BIN]).stdout,
              "GNU_STACK program header present")
        check("(RPATH)" in dyn or "(RUNPATH)" in dyn,
              "DT_RPATH/DT_RUNPATH present (OHOS musl 不认 LD_LIBRARY_PATH)")
        needed = sorted({ln.split("[")[-1].rstrip("]").strip()
                         for ln in dyn.splitlines() if "(NEEDED)" in ln})
        print("  DT_NEEDED:", ", ".join(needed)[:400])
        absolute = [n for n in needed if "/" in n]
        if absolute:
            print(f"  [INFO] {len(absolute)}/{len(needed)} DT_NEEDED 为绝对路径"
                  f"（E537 族，KF6 预编译库无 DT_SONAME；仓内同族包同形）")
        bases = [n.rsplit("/", 1)[-1] for n in needed]
        for want in ("libKF6KIOCore", "libKF6KIOWidgets", "libKF6KIOGui",
                     "libKF6XmlGui", "libKF6ConfigGui", "libKF6ConfigCore",
                     "libKF6DBusAddons", "libKF6CoreAddons", "libKF6I18n",
                     "libKF6WidgetsAddons", "libKF6JobWidgets",
                     "libQt6Widgets.so.6", "libQt6DBus.so.6"):
            check(any(b == want or b.startswith(want + ".so") for b in bases),
                  f"linked against {want}")

    print(f"== {checks - len(failures)}/{checks} checks passed ==")
    print("== 3 个消费者用例：CASE1 运行期冒烟 / "
          "CASE2 完整端到端剖面分析 / CASE3 产物与 ELF ==")
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("KCACHEGRIND CONSUMER CASES: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
