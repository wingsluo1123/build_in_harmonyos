#!/bin/sh
# run_py_case.sh —— 上游用例执行包装（tests.xml.in 场景的依赖预检 + DBus 会话夹具）
#
# 用法: run_py_case.sh <test-script> [args...]
#
# 预检（缺失则 exit 77，ctest 记 SKIP 并打印原因）：
#   * python 用例需要 python3；
#   * 触发型用例（--trigger 触发 .desktop Exec）需要 python3 与可写 /tmp
#     （上游夹具 Exec=python3 -c ... 写 /tmp/<marker>）；
#   * DBus 用例（gallery.py / uberprogram.py 假服务）需要 python3 的
#     dbus + gi 绑定与 dbus-daemon；具备时本包装自动拉起私有会话总线。
set -u
# 无参调用保护：set -u 下 "$1" 未绑定会以中止退出（ctest 记为 FAIL 而非 SKIP），
# 显式给出用法并以 2 退出，避免与"环境预检不满足"的 77 语义混淆。
CASE="${1:-}"
if [ -z "$CASE" ]; then
  echo "usage: run_py_case.sh <case-name> [args...]" >&2
  exit 2
fi
shift
if [ $# -eq 0 ]; then
  set -- "$CASE"
fi

PY3_OK=0
command -v python3 >/dev/null 2>&1 && PY3_OK=1

# ---------------------------------------------------------------------------
# 用例间共享可变状态的隔离（LCA_PRIVATE_HOME=1 时启用）
# ---------------------------------------------------------------------------
# 上游 test-defaults.py 的 testSettingDefault / testResettingDefault 会真实写
#   $XDG_DATA_HOME/applications/mimeapps.list
# 并断言写入前/复位后的 action 顺序一致（test-defaults.py:73
# `self.assertTrue(newactions == oldactions)`）。
# 若多个用例二进制共用同一个 HOME/XDG_DATA_HOME，并发执行时彼此的
# --setmimedefault / --resetmimedefault 会交错，导致该断言假失败：
#   实测（同产物、不改代码）：ctest -j1 -> 0 failed；
#   默认并发 -> upstream-test-defaults 间歇 ***Failed；隔离重跑 6/6 全过。
# 按 ctest 的 CTEST_PARALLEL_LEVEL/唯一化目录给每个用例一份私有 HOME，
# 上游断言与用例逻辑零改动。
if [ "${LCA_PRIVATE_HOME:-}" = "1" ]; then
  _base="${XDG_DATA_HOME:-$HOME}"
  _priv="$(dirname "$_base")/priv-$(basename "$CASE")-$$"
  mkdir -p "$_priv/tests-home" 2>/dev/null || {
    echo "SKIP: 无法创建私有 HOME（$_priv 不可写）"
    exit 77
  }
  HOME="$(dirname "$_priv")"
  XDG_DATA_HOME="$_priv/tests-home"
  export HOME XDG_DATA_HOME
fi

case "$CASE" in
  *.py|gen-regexps)
    if [ "$PY3_OK" != 1 ]; then
      echo "SKIP: python3 不可用（上游 $CASE 为 python 用例）"
      exit 77
    fi
    ;;
esac

# 触发型用例：.desktop Exec 里是 python3 -c ... 写 /tmp/<marker>
NEEDS_TRIGGER=0
NEEDS_DBUS=0
case "$CASE" in
  test-mimes.py|test-desktop-launching.py|test-fixed-params.py|test-special-chars.py)
    NEEDS_TRIGGER=1 ;;
esac
case "$CASE" in
  test-mimes.py|test-fixed-params.py|test-special-chars.py|test-schemes.sh)
    NEEDS_DBUS=1 ;;
esac

if [ "$NEEDS_TRIGGER" = 1 ]; then
  if [ "$PY3_OK" != 1 ]; then
    echo "SKIP: 触发型用例需要 python3（.desktop Exec 夹具）"
    exit 77
  fi
  # 目的仅为**探测 /tmp 可写**（.desktop Exec 夹具要往 /tmp 写 marker），
  # 探测完立即释放，不留残留文件。用 mktemp 而非可预测的 /tmp/.lca_probe_$$：
  # 后者在全局可写的 /tmp 下存在符号链接攻击面，且同脚本并发时 PID 复用会撞名。
  # 探测器本身不被后续夹具消费，故"创建后即删"是刻意的（mktemp 的退出码即为判据）。
  PROBE=$(mktemp /tmp/lca-probe.XXXXXX 2>/dev/null) || {
    echo "SKIP: /tmp 不可写（.desktop Exec 夹具写 /tmp/<marker>）"
    exit 77
  }
  rm -f "$PROBE"
fi

DBUS_STARTED=""
if [ "$NEEDS_DBUS" = 1 ] && [ "${LCA_SKIP_DBUS_CHECK:-}" != "1" ]; then
  if [ "$PY3_OK" != 1 ] || ! python3 -c "import dbus, dbus.service, dbus.mainloop.glib; from gi.repository import GObject" >/dev/null 2>&1; then
    echo "SKIP: DBus 夹具需要 python3-dbus + python3-gi（gallery.py/uberprogram.py）"
    exit 77
  fi
  if ! command -v dbus-daemon >/dev/null 2>&1; then
    echo "SKIP: dbus-daemon 不可用（gallery.py/uberprogram.py 需要会话总线）"
    exit 77
  fi
  # mktemp 失败时必须按 SKIP(77) 退出：否则 ADDR_FILE/PID_FILE 为空串，
  # 3>"" 会让 shell 报错，而脚本无 set -e 会继续执行到 dbus-daemon，
  # 结果是 DBUS_STARTED 为空、trap 不 kill，留下**孤儿 dbus-daemon**。
  ADDR_FILE=$(mktemp /tmp/lca-dbus-addr.XXXXXX) || {
    echo "SKIP: 无法创建 DBus 临时文件（/tmp 不可写？）"
    exit 77
  }
  PID_FILE=$(mktemp /tmp/lca-dbus-pid.XXXXXX) || {
    rm -f "$ADDR_FILE"
    echo "SKIP: 无法创建 DBus 临时文件（/tmp 不可写？）"
    exit 77
  }
  dbus-daemon --session --print-address=3 --print-pid=4 --fork 3>"$ADDR_FILE" 4>"$PID_FILE" || {
    # 失败分支必须先清理刚创建的临时文件，否则每次启动失败都在 /tmp 泄漏两个文件
    rm -f "$ADDR_FILE" "$PID_FILE"
    echo "SKIP: 私有会话总线启动失败"
    exit 77
  }
  DBUS_SESSION_BUS_ADDRESS=$(cat "$ADDR_FILE")
  export DBUS_SESSION_BUS_ADDRESS
  DBUS_STARTED=$(cat "$PID_FILE")
  rm -f "$ADDR_FILE" "$PID_FILE"

  # ★guest 侧可达性判据（缺了它就会"假可跑、真必失败"）★
  # 上面两条只证明**宿主侧**齐备：python3-dbus 可导入 + dbus-daemon 可启动。
  # 但被测二进制是 aarch64 目标，经 qemu-user/run-guest 在 OHOS musl 运行根里执行，
  # **宿主侧齐备 ≠ guest 侧能连上**。实测（本机 ohos-aarch64-run，全部可复现）：
  #     host: python3 -c "import dbus"            -> OK
  #     host: dbus-daemon --session --fork        -> OK，ADDRESS 已导出
  #     guest: connect() 到该 unix socket          -> 成功
  #     guest: D-Bus SASL 握手 AUTH EXTERNAL        -> "REJECTED EXTERNAL"
  #     guest: QDBusConnection::sessionBus()        -> isConnected()=false
  #                                                   "Not connected to D-Bus server"
  # 原因是 EXTERNAL 认证依赖 SO_PEERCRED 的 uid 与总线属主一致，qemu-user 下不成立；
  # 改用 ANONYMOUS 总线（allow_anonymous）实测仍为 "REJECTED ANONYMOUS"。
  # 于是 lca-tool --trigger <X-Maemo-Method> 会**静默 no-op（RC=0）**，
  # gallery/uberprogram 等假服务永远收不到方法调用，用例只能等到 TIMEOUT 判 FAIL。
  # 这类"未连上总线"必须按**执行环境预检不满足**处理（SKIP 77），
  # 而不是让用例跑起来再超时失败 —— 否则失败信息完全指向不了真实原因。
  # 判据用被测方自己的库来问（与用例同一条代码路径），而非另造探针：
  #   dbus-probe 仅链接 libcontentaction 已依赖的 libQt6DBus，
  #   在 build/bin 下由 CMake 构建（见 port/CMakeLists.txt）。
  # ★必须与上面的 LCA_SKIP_DBUS_CHECK 同款地可关闭★：mimes-subset 用例
  # （test-mimes.py 的非 DBus 方法子集）显式设 LCA_SKIP_DBUS_CHECK=1，
  # 表示"我不走 DBus 夹具路径、不要因总线不可用而跳过"。若此处忽略该开关，
  # 会把本该真实执行并通过的 subset 用例误判为 SKIP（实测踩到过）。
  if [ "${LCA_SKIP_DBUS_CHECK:-}" != "1" ] \
     && [ -n "${LCA_DBUS_PROBE:-}" ] && [ -x "$LCA_DBUS_PROBE" ]; then
    if ! "$LCA_DBUS_PROBE" >/dev/null 2>&1; then
      kill "$DBUS_STARTED" 2>/dev/null
      DBUS_STARTED=""
      echo "SKIP: guest 侧无法连接 D-Bus 会话总线（qemu-user 下 SASL EXTERNAL/ANONYMOUS 均被拒），"
      echo "      X-Maemo-Method 触发型断言在本执行环境下不可满足"
      exit 77
    fi
  fi
fi

cleanup() {
  if [ -n "$DBUS_STARTED" ]; then
    kill "$DBUS_STARTED" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 末位 exec 的**两个**原生陷阱（均在本环境实测定位，缺一不可）
# ---------------------------------------------------------------------------
# 陷阱 1（CI #79942，已在下面处理）：裸相对名。
#   上游 lca-cita-test 以 `run_py_case.sh test-defaults.py` 调用，$1 是**裸名**。
#   HMOS 的 sh 不搜索 cwd、只按 PATH 查找 -> `inaccessible or not found`、RC=127。
#   修法：相对名且 cwd 下确为文件时显式补 `./`。
#
# 陷阱 2（CI #80118 复现 / #b92439 确认，**这才是 test-defaults/regexps 失败的真正原因**）：
#   上游那批 .py 的 shebang 是**绝对路径** `#!/usr/bin/python3`，而 HMOS/CI worker 上
#   python3 位于 /data/app/bin/python3（CI env 的 PATH 可见），**/usr/bin/python3 不存在**。
#   内核 exec 一个 shebang 解释器不存在的脚本会返回 ENOENT，shell 于是报
#       ./test-defaults.py: No such file or directory
#   —— **报的是脚本"不存在"，实际是解释器不存在**，极难定位。
#   实测（WSL，构造同样形态）：
#       [ -f ./broken.py ] -> TRUE          文件确实在
#       ./broken.py        -> bad interpreter: No such file or directory, RC=126
#       python3 broken.py  -> 正常
#   这也解释了为何 test-mimes.py 等"看起来没事"：它们先 exit 77 跳过，没走到 exec。
#   .sh 那批 shebang 是 #!/bin/sh（HMOS 有），所以一直正常。
#   修法：**不依赖 shebang** —— 对 .py 显式用 PATH 里的 python3 调起；
#   找不到 python3 时回退为原样执行（保持旧行为，不引入新的硬失败）。
if [ $# -gt 0 ]; then
  _first="$1"
  case "$_first" in
    */*) _target="$_first" ;;                  # 已含路径（含绝对路径），原样
    *)
      # ★只在"cwd 下确实是这个文件"时才改写 $1★
      # 若裸名不在 cwd（例如 lca-cita-test 在 testbed/bin 下调 testbed/run_py_case.sh），
      # 必须原样放行，交给 PATH/上层去解析 —— 改写反而会把它变成找不到的 ./x。
      if [ -f "./$_first" ]; then _target="./$_first"; else _target=""; fi
      ;;
  esac
  if [ -n "$_target" ]; then
    case "$_target" in
      *.py)
        # 对 .py 显式用 PATH 里的 python3，绕开 shebang 绝对路径不存在的问题。
        if command -v python3 >/dev/null 2>&1; then
          shift; set -- python3 "$_target" "$@"
        elif command -v python >/dev/null 2>&1; then
          shift; set -- python "$_target" "$@"
        else
          shift; set -- "$_target" "$@"
        fi
        ;;
      *)
        shift; set -- "$_target" "$@"
        ;;
    esac
  fi
fi

"$@"
RC=$?
exit $RC
