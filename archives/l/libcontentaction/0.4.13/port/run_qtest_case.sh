#!/bin/sh
# run_qtest_case.sh —— QTest 用例执行预检包装
#
# 用法: run_qtest_case.sh <QTest 可执行名>
#
# 预检（缺失则 exit 77，ctest 记 SKIP 并打印原因）：
#   test-info / test-action 依赖 shared-mime-info 的类型描述与内容探测
#   （"Plain text document" / "PNG image"），该数据库由构建期
#   update-mime-database 生成到 $XDG_DATA_HOME/mime。构建机没有
#   shared-mime-info 时数据库不存在，这两个用例的断言必然失败，
#   故在此按 ctest 的 SKIP_RETURN_CODE=77 约定记为 SKIP 并说明原因，
#   而不是让整包构建失败。
#   其余 QTest（test-mimedefaults / test-findhighlights）无此依赖，直接执行。
set -u
# 无参调用保护（同 run_py_case.sh）：set -u 下未绑定变量会中止退出，
# 会被 ctest 记为 FAIL 而非 SKIP。
CASE="${1:-}"
if [ -z "$CASE" ]; then
  echo "usage: run_qtest_case.sh <case-name> [args...]" >&2
  exit 2
fi
shift

case "$CASE" in
  test-info|test-action)
    if [ -z "${XDG_DATA_HOME:-}" ] || [ ! -f "${XDG_DATA_HOME}/mime/mime.cache" ]; then
      echo "SKIP: shared-mime-info 数据库不可用（构建机无 update-mime-database），"
      echo "      上游 $CASE 的类型描述/内容探测断言依赖该数据库"
      exit 77
    fi
    ;;
esac

exec "$@"
