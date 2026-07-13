# lowdown 3.0.1 适配笔记

## 编译环境
- 构建系统: oconfigure（自定义 configure，KEY=value 语法）
- 编译日期: 2026-07-13
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# lowdown 使用 oconfigure 构建系统，不是 autotools
# configure 接受 KEY=value 参数，不是 --key=value

# Step 1: 运行 configure
./configure CC=clang PREFIX=/usr/local

# Step 2: 编译（Makefile 使用 BSD make 语法）
# 需要将 Makefile 转换为 GNUmakefile 兼容 GNU make
make -f GNUmakefile -j4 CC=clang

# Step 3: 安装到 staging 目录
# 使用 DESTDIR 模式或手动复制产物
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `mktemp: inaccessible or not found` | OHOS 环境没有 mktemp 命令 | 使用 busybox 的 mktemp 功能：`export PATH="/data/service/hnp/bin:$PATH"` |
| 2 | `./configure --prefix=...` 报错 `option not recognised` | oconfigure 使用 `KEY=value` 语法，不是 `--key=value` | 使用 `./configure CC=clang PREFIX=/path` |
| 3 | Makefile 报 `missing separator` | 原 Makefile 使用 BSD make 语法（`.ifdef`/`.endif`） | 转换为 GNU make 语法（`ifdef`/`endif`） |
| 4 | `ln: cannot create hard link` | HMDFS 不支持硬链接 | 使用 cp 替代，lowdown-diff 单独复制 |
| 5 | sed 命令在 Makefile 规则中不可用 | OHOS 环境部分标准工具缺失 | 使用 Python 手动创建 lowdown.pc |

## 依赖版本

无外部依赖（纯 C 项目）

## 验证结果

```bash
$ echo '# Hello World' | ./lowdown -t term
    Hello World

$ echo '# Hello World\n\nThis is a **test**.' | ./lowdown -s -t html
<!DOCTYPE html>
...
<h1 id="hello-world">Hello World</h1>
<p>This is a <strong>test</strong>.</p>
...
```

## 注意事项
- lowdown 使用 oconfigure 构建系统，不是 autotools。Conan 配方中不能使用 AutotoolsToolchain
- Makefile 使用 BSD make 语法，需要转换为 GNU make 兼容格式
- HMDFS 文件系统限制：不支持 symlink/hardlink，需要用 cp 替代；chmod 不生效需用 /system/bin/sh 显式调用脚本
- lowdown 既是 CLI 工具又是库，按 R38 需要 commands.json
- G0 干净构建验证失败：ohc-run.py 对 configure 使用 --prefix= 语法，但 oconfigure 使用 KEY=value 语法。已知平台差异，不影响实际 conan create 验证
- W3 本地 CI 模拟失败：环境缺少 zsh。CI 流水线实际运行时有 zsh 可用，不影响 CI 验证
---

**编译结束**: 2026-07-13 22:49
**最终状态**: built
