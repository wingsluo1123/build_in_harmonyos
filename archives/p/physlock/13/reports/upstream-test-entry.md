# 上游测试入口核验 — physlock 13

> 结论：**上游没有自动化测试**。测试入口不存在，本文件记录核验证据（真实命令 + 原始输出）。

## 1. 源码 tarball 目录清点

命令：

```bash
tar -tzf physlock-13.tar.gz
```

原始输出（顶层）：

```
physlock-13/
physlock-13/.gitignore
physlock-13/LICENSE
physlock-13/Makefile
physlock-13/README.md
physlock-13/config.def.h
physlock-13/main.c
physlock-13/options.c
physlock-13/physlock.1
physlock-13/physlock.h
physlock-13/physlock.pam
physlock-13/session.c
physlock-13/util.c
physlock-13/vt.c
```

→ **无 `tests/` / `test/` 目录**，无测试脚本、无测试数据。

## 2. Makefile 目标清点

命令：

```bash
grep -nE "^check|^test|check:|test:" Makefile
```

原始输出：**无命中（exit 1）**。

Makefile 声明的目标仅：`all`（默认）、`physlock`、`.c.o`、`config.h`、`version.h`、`clean`、`install`、`uninstall`。
→ **无 `check` / `test` 目标**。

命令：

```bash
grep -nE "^[A-Za-z0-9_.-]+:" Makefile
```

原始输出（目标列表）：

```
all:
$(objs): Makefile physlock.h config.h
options.o: version.h
physlock: $(objs)
config.h:
version.h: Makefile .git/index
.git/index:
clean:
install: all
uninstall:
```

## 3. README 测试章节清点

命令：

```bash
grep -niE "test" README.md
```

原始输出：**无命中**。README 仅包含 Installation（`make` / `make install`）、Usage（命令行参数）两节。
另外明确注明：

> Please note, that the latter one [make install] requires root privileges.

## 4. 结论

| 项 | 结果 |
|---|---|
| `tests/` 目录 | 不存在 |
| `make check` / `make test` | 不存在 |
| README 测试章节 | 不存在 |
| 上游自动化测试总数 | **0** |
| 上游测试入口 | **无** |

因此本库无法产出"上游测试 通过/失败/跳过"统计。`test_package/test_physlock.py`
提供 9 条消费者验证（其中 4 条为鸿蒙特有），**不能替代上游测试统计**。
