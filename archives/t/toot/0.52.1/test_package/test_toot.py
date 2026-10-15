#!/usr/bin/env python3
"""toot 0.52.1 消费者测试 —— 含 HarmonyOS PC 适配专项断言。

用法::

    python3 test_toot.py <package_folder> <version>

``package_folder`` 是 ``conan create`` 产出的包（已由 conan 安装就位），
本脚本**只依赖该包 + PYTHONPATH**（由 ``conanrun`` 注入），不接触源码树，
因此能真实反映最终用户的运行条件。

通用消费者断言
--------------
  G1 ``importlib.metadata.version("toot")`` 等于包版本
  G2 包内子模块可导入：``toot``、``toot.api``、``toot.config``、
     ``toot.settings``、``toot.utils``、``toot.cli``
  G3 控制台入口 ``toot.cli:cli`` 可被驱动（CliRunner 跑 ``--version``）
  G4 ``bin/toot --version`` / ``--help`` 真实可执行
  G5 缺失设置项时 ``toot.settings.get_setting`` 返回给定默认值

鸿蒙特有断言（本任务新增，上游测试未覆盖）
------------------------------------------
  H1 **平铺安装布局**：``toot/`` 与 ``toot-<版本>.dist-info/`` 同处包根，
     仅把包根加入 PYTHONPATH 即可解析 —— 本适配用 ``pip --target`` 平铺
     安装而非 ``lib/pythonX.Y/site-packages`` 嵌套布局；若布局被改回嵌套，
     这一条立即失败（上游测试跑在源码树里，查不出布局回归）。
  H2 **动态版本落定**：toot 的版本来自 setuptools_scm，PyPI sdist 不含 git
     元数据，直接构建会得到 ``toot-0.0.0.dist-info`` / ``__version__ ==
     "0.0.0"``。G1 与本条一起守住配方里的 ``SETUPTOOLS_SCM_PRETEND_VERSION``
     修正：这是本次适配最容易被静默破坏的点。
  H3 **平台指纹**：在 HarmonyOS 上运行，且 ``sys.platform`` 为 ``linux`` 或
     ``ohos``。鸿蒙 PC 的两种 Python 运行时会分别如此上报（设备自带
     ``/data/service/hnp/bin/python3`` 报 ``ohos``，python.org 构建报
     ``linux``），因此配方里任何 ``settings.os`` 判断都必须同时接受
     ``Linux`` 与 ``OHOS``（R32）—— 这条把该前提固化成断言。
  H4 **wrapper shebang 有效**：``bin/toot`` 首行解释器路径真实存在且可执行，
     避免生成一个指向不存在解释器的入口。
  H5 **剥离 LD_LIBRARY_PATH 仍可运行**：保留 PYTHONPATH、剥掉
     LD_LIBRARY_PATH 运行 ``bin/toot``；依赖一律是纯 Python 包，不应依赖
     任何外部 .so 路径（R49：不写共享前缀）。
  H6 **无 site-packages 的隔离解释器仍可运行**：用 ``python -S`` 再跑一次
     ``bin/toot``，依赖只能来自 ``conanrun`` 注入的 PYTHONPATH。开发机自带
     click/urwid/PIL，会把"依赖路径没传下去"这一缺陷掩盖成绿灯；CI worker
     的解释器没有它们，同一缺陷就表现为 Traceback（即 0.52.1 首轮 CI 的
     G4a/G4b/H5 三项同时 rc=1）。这条断言把该判别条件固化，防止回归。
"""

import importlib.metadata
import os
import platform
import subprocess
import sys
import tempfile

# 隔离宿主配置：toot 从 XDG 配置目录读 settings.toml。必须在 import toot
# 之前设置，避免宿主机上真实的 toot 配置干扰断言。
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="toot-consumer-xdg-")


class Checker:
    """收集断言结果，最后统一给出退出码（非 0 即测试失败）。"""

    def __init__(self):
        self.total = 0
        self.failures = []

    def check(self, name, ok, detail=""):
        self.total += 1
        line = f"[{'ok' if ok else 'FAIL'}] {name}"
        if detail:
            line += f" -- {detail}"
        print(line)
        if not ok:
            self.failures.append(name)
        return bool(ok)

    @property
    def failed(self):
        return bool(self.failures)


def _run(cmd, env, cwd=None):
    proc = subprocess.run(cmd, env=env, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode(errors="replace")


def _consumer_env(pkg, without=()):
    """子进程运行环境：包根 + ``conanrun`` 注入的全部依赖路径。

    ``test()`` 以 ``env="conanrun"`` 启动本脚本，所以 ``os.environ`` 里已经有
    VirtualRunEnv 写好的 ``PYTHONPATH``（本包 + 每个依赖的 site 目录）。包根
    必须排第一位，但依赖条目必须保留：一旦把它们覆盖掉，``bin/toot`` 在
    "解释器里没装 click" 的机器上（CI worker）就会 ``ModuleNotFoundError``，
    而开发机因为自带 click/urwid 会把这一缺陷掩盖成绿灯 —— 0.52.1 首轮 CI 的
    G4a/G4b/H5 三项同时 rc=1 就是这个原因。
    """
    env = {k: v for k, v in os.environ.items() if k not in without}
    inherited = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env["PYTHONPATH"] = os.pathsep.join([pkg] + [p for p in inherited if p != pkg])
    return env


def main(argv):
    if len(argv) < 2:
        print("usage: test_toot.py <package_folder> [version]")
        return 2
    pkg = os.path.abspath(argv[1])
    version = argv[2] if len(argv) > 2 else None
    c = Checker()

    # 本进程内的 import / importlib.metadata 也要能解析到该包（解释器早于本行
    # 就已启动，sys.path 不会自动跟随 PYTHONPATH）。
    sys.path.insert(0, pkg)

    exe = os.path.join(pkg, "bin", "toot")
    env = _consumer_env(pkg)

    # ---- G1: 元数据版本 ----
    try:
        found = importlib.metadata.version("toot")
    except importlib.metadata.PackageNotFoundError:
        found = None
    c.check("G1 toot 元数据版本",
            bool(found) and (version is None or found == version),
            f"importlib.metadata -> {found!r}, 期望 {version!r}")

    # ---- G2: 子模块导入 ----
    modules = ("toot", "toot.api", "toot.config", "toot.settings",
               "toot.utils", "toot.cli")
    imported, errors = [], []
    for mod in modules:
        try:
            __import__(mod)
            imported.append(mod)
        except Exception as exc:  # noqa: BLE001 - 断言需要任何失败原因
            errors.append(f"{mod}: {exc.__class__.__name__}: {exc}")
    c.check("G2 包内子模块导入", not errors,
            f"{len(imported)}/{len(modules)} 成功"
            + (f"; 失败: {'; '.join(errors)}" if errors else ""))

    # ---- H2: 动态版本落定（setuptools_scm 未生效会退化为 0.0.0）----
    c.check("H2 setuptools_scm 版本已落定（非 0.0.0）",
            bool(found) and not found.startswith("0.0"),
            f"实际 {found!r} — 0.0.x 说明构建时未注入 "
            "SETUPTOOLS_SCM_PRETEND_VERSION")

    # toot.__version__ 与元数据同源，一并核对
    try:
        import toot as _toot
        attr_version = getattr(_toot, "__version__", None)
    except Exception as exc:  # noqa: BLE001
        attr_version = f"<import 失败: {exc}>"
    c.check("H2b toot.__version__ 与元数据一致",
            attr_version == found and bool(attr_version),
            f"__version__={attr_version!r} vs metadata={found!r}")

    # ---- G3: 控制台入口可被驱动 ----
    try:
        from click.testing import CliRunner
        from toot.cli import cli
        result = CliRunner().invoke(cli, ["--version"])
        ok = result.exit_code == 0 and (version is None or version in result.output)
        c.check("G3 入口 toot.cli:cli 可驱动", ok,
                f"exit={result.exit_code}, output={result.output.strip()[:80]!r}")
    except Exception as exc:  # noqa: BLE001
        c.check("G3 入口 toot.cli:cli 可驱动", False,
                f"{exc.__class__.__name__}: {exc}")

    # ---- G5: settings 公共 API ----
    try:
        from toot import settings as _settings
        marker = "toot-consumer-default"
        got = _settings.get_setting("commands.post.editor.nonexistent",
                                    str, marker)
        path = _settings.get_settings_path()
        c.check("G5 settings 公共 API", got == marker and isinstance(path, str),
                f"get_setting 默认值 -> {got!r}; settings 路径 -> {path!r}")
    except Exception as exc:  # noqa: BLE001
        c.check("G5 settings 公共 API", False, f"{exc.__class__.__name__}: {exc}")

    # ---- G4 / H4 / H5: bin/toot ----
    c.check("G4 bin/toot 存在且可执行",
            os.path.isfile(exe) and os.access(exe, os.X_OK), exe)

    shebang = ""
    if os.path.isfile(exe):
        with open(exe, encoding="utf-8", errors="replace") as fh:
            shebang = fh.readline().strip()
    interp = shebang[2:].split()[0] if shebang.startswith("#!") else ""
    c.check("H4 bin/toot shebang 解释器有效",
            bool(interp) and os.path.isfile(interp) and os.access(interp, os.X_OK),
            f"shebang={shebang!r}")

    if os.path.isfile(exe) and os.access(exe, os.X_OK):
        rc, out = _run([exe, "--version"], env)
        c.check("G4a bin/toot --version", rc == 0 and bool(out.strip()),
                f"rc={rc}, 输出={out.strip()[:80]!r}")
        rc2, out2 = _run([exe, "--help"], env)
        c.check("G4b bin/toot --help", rc2 == 0 and "Usage" in out2,
                f"rc={rc2}, 输出={out2.strip().splitlines()[0][:80] if out2.strip() else ''!r}")

        # H5: 保留 PYTHONPATH、剥掉 LD_LIBRARY_PATH —— 依赖一律是纯 Python
        # 包，不应需要任何外部 .so 搜索路径（R49：不写共享前缀）。
        clean = _consumer_env(pkg, without=("LD_LIBRARY_PATH",))
        rc3, out3 = _run([exe, "--version"], clean)
        c.check("H5 剥离 LD_LIBRARY_PATH 后仍可运行",
                rc3 == 0 and bool(out3.strip()) and "Traceback" not in out3,
                f"rc={rc3}, 输出={out3.strip()[:120]!r}")

        # H6: 隔离解释器（-S，不加载 site-packages）—— 依赖只能来自 conanrun
        # 注入的 PYTHONPATH。这正是 CI worker 与开发机的判别条件：开发机自带
        # click/urwid/PIL，会把"依赖路径没传下去"掩盖成绿灯；CI worker 没有，
        # 同一缺陷立刻表现为 Traceback。
        rc4, out4 = _run([sys.executable, "-S", exe, "--version"], clean)
        c.check("H6 无 site-packages 的隔离解释器仍可运行",
                rc4 == 0 and bool(out4.strip()) and "Traceback" not in out4,
                f"rc={rc4}, 输出={out4.strip()[:120]!r}")
    else:
        for name in ("G4a bin/toot --version", "G4b bin/toot --help",
                     "H5 剥离 LD_LIBRARY_PATH 后仍可运行",
                     "H6 无 site-packages 的隔离解释器仍可运行"):
            c.check(name, False, "bin/toot 不可执行，跳过")

    # ---- H1: 平铺布局 ----
    flat_pkg = os.path.isdir(os.path.join(pkg, "toot"))
    flat_dist = any(d.startswith("toot-") and d.endswith(".dist-info")
                    for d in os.listdir(pkg))
    nested = os.path.isdir(os.path.join(pkg, "lib"))
    c.check("H1 平铺安装布局（包根即可 import）",
            flat_pkg and flat_dist and not nested,
            f"toot/={flat_pkg}, dist-info={flat_dist}, lib/={nested}")

    # ---- H3: 平台指纹 ----
    system = platform.system()
    c.check("H3 平台指纹（HarmonyOS，sys.platform 为 linux 或 ohos）",
            system == "HarmonyOS" and sys.platform in ("linux", "ohos"),
            f"platform.system()={system!r}, sys.platform={sys.platform!r}, "
            f"machine={platform.machine()!r}, release={platform.release()!r}")

    print("")
    if c.failed:
        print(f"结果: {c.total - len(c.failures)}/{c.total} 通过；"
              f"失败项: {', '.join(c.failures)}")
        return 1
    print(f"结果: {c.total}/{c.total} 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
