#!/bin/bash
# 消费者视角验证脚本：
#   1) 运行链接了本包静态库的 libshaderc C API 消费者程序
#   2) 调用本包交付的 glslc 命令行，把 GLSL 编译为 SPIR-V 并检查产物
# OHOS 上 /system/bin/sh 无法直接执行 ELF，故统一由 bash 驱动。
set -euo pipefail

TEST_EXE="$1"
GLSLC="$2"

if [ ! -x "$TEST_EXE" ]; then
  echo "consumer binary not found or not executable: $TEST_EXE" >&2
  exit 1
fi
if [ ! -x "$GLSLC" ]; then
  echo "glslc not found or not executable: $GLSLC" >&2
  exit 1
fi

echo "== libshaderc C API consumer test =="
"$TEST_EXE"

echo "== glslc command line test =="
"$GLSLC" --version

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cat > "$tmpdir/shader.vert" <<'EOF'
#version 450
layout(location = 0) in vec3 inPosition;
layout(location = 0) out vec4 outColor;
void main() {
  gl_Position = vec4(inPosition, 1.0);
  outColor = vec4(0.1, 0.2, 0.3, 1.0);
}
EOF

"$GLSLC" -fshader-stage=vert -o "$tmpdir/shader.vert.spv" "$tmpdir/shader.vert"
[ -s "$tmpdir/shader.vert.spv" ] || {
  echo "glslc 未产出 SPIR-V 文件" >&2
  exit 1
}

magic="$(od -An -tx1 -N4 "$tmpdir/shader.vert.spv" | tr -d ' \n')"
if [ "$magic" != "03022307" ]; then
  echo "SPIR-V magic 不正确: $magic" >&2
  exit 1
fi

echo "shaderc test_package PASSED"
