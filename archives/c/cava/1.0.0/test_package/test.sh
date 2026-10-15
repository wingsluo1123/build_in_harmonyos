#!/bin/bash
# test_package 消费者测试 — cava 1.0.0
# 以真实使用者身份调用已安装的 `cava` 二进制，逐项断言（任一不符即 exit 1）。
#
# 断言口径：
#   1) -v/--version 输出必须恰为 "cava 1.0.0"（cava.c:379 printf(PACKAGE " " VERSION)）
#   2) -h/--help 必须给出用法与关键行，且退出码 0
#   3) 非法选项必须非零退出 + 打印可识别的错误信息与 --help 提示（错误路径契约）
set -u

echo "--- cava 1.0.0 consumer verification ---"

CAVA="$(command -v cava)"
if [ -z "${CAVA}" ]; then
  echo "FAIL: 未在 PATH 中找到 cava 二进制"
  exit 1
fi
echo "PASS 1: 二进制定位 -> ${CAVA}"

# 1. 版本契约
out_v="$("${CAVA}" -v)"
rc_v=$?
if [ "${rc_v}" -ne 0 ]; then
  echo "FAIL: cava -v 退出码 ${rc_v}"
  exit 1
fi
if [ "${out_v}" != "cava 1.0.0" ]; then
  echo "FAIL: cava -v 输出 [${out_v}] != [cava 1.0.0]"
  exit 1
fi
echo "PASS 2: -v -> ${out_v}"

# 2. 帮助契约（长选项同样生效）
out_h="$("${CAVA}" --help)"
rc_h=$?
if [ "${rc_h}" -ne 0 ]; then
  echo "FAIL: cava --help 退出码 ${rc_h}"
  exit 1
fi
echo "${out_h}" | grep -q "^Usage: cava \[options\]" || {
  echo "FAIL: --help 缺少 Usage 行"
  exit 1
}
echo "${out_h}" | grep -q "Visualize audio input in terminal" || {
  echo "FAIL: --help 缺少功能描述"
  exit 1
}
echo "${out_h}" | grep -q -- "-p, --config" || {
  echo "FAIL: --help 缺少 -p/--config 选项"
  exit 1
}
echo "PASS 3: --help 用法/描述/选项齐全"

# 3. 错误路径：未知选项必须非零退出，且必须给出错误信息
#
# ⚠ 判定改用 bash 内建模式匹配，⛔ 不再用 grep：
#   实际错误输出是**两行**（cava 自带解析器）：
#     第 1 行 "cava: error: invalid option"
#     第 2 行 "Try 'cava --help' for more information."
#   旧写法 `grep -qi "unknown argument\|invalid option"` 依赖 GNU 扩展的 BRE 交替
#   `\|`；CI 里的 grep 是 toybox（POSIX BRE，不支持 `\|`）⇒ 恒不匹配，把
#   「已经打印了错误」误判成 FAIL（build #91286 的假红）。
#   改成对整段捕获输出做 glob 匹配 ⇒ 不依赖 grep 实现/正则方言，且天然跨多行。
out_x="$("${CAVA}" --definitely-not-an-option 2>&1)"
rc_x=$?
if [ "${rc_x}" -eq 0 ]; then
  echo "FAIL: 非法选项应当非零退出，实得 0"
  exit 1
fi
# ① 错误关键词（第一行）
case "${out_x}" in
  *"invalid option"*|*"unknown argument"*) ;;
  *)
    echo "FAIL: 非法选项未给出错误信息 [${out_x}]"
    exit 1
    ;;
esac
# ② --help 提示行（第二行，多行输出必须完整送达）
case "${out_x}" in
  *"Try"*"--help"*) ;;
  *)
    echo "FAIL: 非法选项错误缺少 --help 提示行 [${out_x}]"
    exit 1
    ;;
esac
echo "PASS 4: 非法选项 -> exit ${rc_x} + 错误信息 + --help 提示行"

echo "test cava 1.0.0: 4/4 checks PASS"
exit 0
