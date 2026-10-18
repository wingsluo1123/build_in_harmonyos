# E2296 — OHOS procfs /proc/self/fd 的 st_size 固定 64 导致 readlink 路径截断

## 错误特征

`pflash --info` 的 `Name` 字段末字符丢失，例如：

```text
Name          = /data/storage/el2/base/files/home/.tmp/.../01-info.pno
```

（实际文件名为 `01-info.pnor`，尾字符被截断。）

## 触发条件

- 平台：OHOS / HarmonyOS（procfs 实现）
- 阶段：runtime / testing
- 程序通过 `lstat("/proc/self/fd/<n>")` 取 `st_size`，再按该长度分配缓冲并 `readlink()`
- 被打开的路径长度超过 63 字节

## 根因分析

OHOS 的 procfs 对 `/proc/self/fd/<n>` 符号链接返回的 `st_size` 固定为 64
（与真实目标路径长度无关）。按 POSIX 语义用 `st_size` 作为 readlink 缓冲大小，
当目标路径长度 ≥ 64 时 readlink 只能返回 63 字节，路径被截断。

skiboot 的 `libflash/file.c:get_info_name()` 正是这种写法，因此 `pflash -F <file>
--info` 在长路径下显示的名称少一个字符；上游 shell 测试 `01-info` 依赖把完整路径
替换为 `FILE`，截断后 sed 不匹配，测试失败。

## 解决方案

### 推荐方案

- 修改程序：按 `PATH_MAX` 分配 readlink 缓冲，或 readlink 返回 `len == size` 时扩容重试
  （skiboot 已在 `libflash/file.c` 按此修复）；
- 测试/运行时把临时目录放在可写构建目录；不要假定 `/tmp` 可写（CI worker 上可能只读），
  也不要把路径长度作为规避手段。

### 禁止做法

- ❌ 不要按 `st_size` 精确分配 readlink 缓冲（OHOS 上该值不可信）。
- ❌ 不要用 `readlink -f` 之类外部工具做等价替换，测试脚本会在 CI 的 toybox 环境下产生新差异。

## 验证

```bash
python3 -c "import os; f=open(__import__('os').path.expanduser('~/tmp/x'),'w'); p='/proc/self/fd/%d'%f.fileno(); print(os.lstat(p).st_size, len(os.readlink(p)))"
# OHOS: 64 48  —— st_size 固定 64，与真实长度无关
TMPDIR="$BUILD_DIR/test-tmp" make -C external/pflash check
```

## 关联条目

- E2297（toybox coreutils 的 GNU 长选项兼容性）
