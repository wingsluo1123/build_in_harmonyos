# E551: OHOS head 不支持 GNU 负数字节偏移，上游回归截断输入需改 POSIX wc/dd

## 基本信息
- **严重度**: 2（中）
- **类别**: portability, testing, libc
- **作者**: pc2-7
- **来源事件**: gif 5.2.2 上游回归套件（tests/makefile 的 giffix-rebuild/giffix-regress）

## 错误特征
```
head --bytes=-20 <pic/treescap.gif   →  head: illegal byte count / 退出码 1
make: *** [makefile:110: giffix-regress] Error 1
```

## 根因分析
OHOS 默认 `head(1)`（toybox 系）只实现 POSIX 语义，不支持 GNU coreutils 的
负数字节偏移扩展 `--bytes=-N`（即 `head -c -N`：去掉文件末尾 N 字节）。
上游 giflib 回归套件用 `head --bytes=-20` 从 GIF 图片截去末尾 20 字节，
构造"尾部截断的损坏 GIF"来验证 giffix 的修复行为；该命令在 OHOS 上直接
失败（illegal byte count），导致 giffix 两个回归目标无法运行。

## 推荐方案
**方法**: portable-truncate-wc-dd

**说明**: 不改工具链，只把测试驱动中的 GNU 负数偏移替换为 POSIX 组合，
保持"去掉末尾 N 字节"语义：

```sh
bytes=$(wc -c <file); \
 test "$bytes" -gt N && \
 dd if=file bs=1 count=$((bytes - N)) 2>/dev/null | tool ...
```

实测 `dd bs=1 count=$((bytes-20))` 输出与 GNU `head -c -20` 逐字节一致
（387/387 字节）。补丁只动测试驱动（tests/makefile），不涉及库源码、
工具源码，不加平台宏。

**验证/命令**:
```bash
make -C tests   # 全量回归："No output is good news"
```

## 关键词
head --bytes, negative byte count, GNU coreutils extension, truncated input,
regression suite, POSIX head, wc -c, dd bs=1, giffix

## 适用范围 / 边界
- 适用：任何测试/构建脚本用 `head --bytes=-N` / `head -c -N` 截断输入构造
  损坏数据或夹具的 C/C++ 库；上游回归套件、shell 测试驱动、数据准备步骤。
- 反例：`head -c N`（正数，保留前 N 字节）是 POSIX 支持的标准用法，
  不需要替换；`tail -c -N` 同理属于 GNU 扩展，遇到时用同一模式处理。
- 关系：与 E010（toybox sed/expr 不完整）同族（toybox 工具链 GNU 扩展缺失），
  但 E010 针对 sed/expr/configure 阶段，本条针对 head 的测试阶段负数字节截断。
