# perm

- **上游**：`code.google.com/p/perm/`（**Google Code 已关站**）→ 源取 Debian 源包 orig
- **版本**：**0.4.0**（与平台清单一致）
- **形态**：C++ / 上游自带 makefile（43 个 .cpp，含 OpenMP）
- **许可证**：GPL-3.0-or-later（**上游 orig 未附许可证文件**，按 Debian control 标注）
- **依赖**：**零外部依赖**（makefile 只链 `-lm -lstdc++`）

## 归档内容

```
perm/
  commands.json            软件级命令声明（R38：本包产出真编译的 ELF 可执行文件）
  0.4.0/
    conandata.yml          源（Debian orig，两层目录结构已在 note 里写明）
    conanfile.py           配方（makefile + 自动探测 Source/ + 两处最小修正 + 自带测试真跑）
    manifest.yaml          版本级 manifest（dependencies / upstream_tests / knowledge_gained）
    notes.md               适配要点（两层目录 / 覆盖 CC / 两处过时写法 / 测试真实语义）
    test_package/          消费者校验（5 项，全部离线）
```

## 构建要点（详见 notes.md）

1. **两层目录**：orig 解开是 `perm_0.4.0/Source/…`，`strip_root` 只剥一层 → 配方自动探测
   `Source/makefile` 作为构建目录
2. **覆盖 `CC`**：上游 `CC = g++ -O2 $(CFLAGS)` 且 `CFLAGS` 带 `-static` → 传
   `CC="<clang++> -O2 -Wall"` 一并覆盖（换编译器 + 去掉 `-static`），不改上游 makefile
3. **两处过时写法最小修正**：`MappingResult.h` 的 `char* == '\0'` → `(!p || p[0] == '\0')`；
   `PerMTest.cpp` 的过时零参调用 → 上游自己的零参入口 `testLongBases2ColorsCases()`

## 上游测试

上游自带 **3 个用例入口**（`Source/ColorSpaceRead.h` 声明：`testShift64Bit`、`testLongBases2Colors`（两参）、
`testLongBases2ColorsCases`（零参））→ 配方**真编、真跑** `PerMTest`（rc=0；`main()` 调用 `Cases()`
覆盖 2 个，第 3 个上游自己注释掉）。
**如实披露**：其 `main()` 固定 `return 0`、无输出 → 本项证明"可编、可跑通"，不代表断言全过。

## 消费者校验

`test_package/check_perm.py` **5 项，全部离线**：产物齐备（`bin/perm` 11,241,472 字节）/ ELF 头自检
（ELF64、machine=0xB7）/ `perm`（无参）真跑有输出（打印自身 banner）/ 许可证（上游未附 → 如实记录）/
证据。实测 `checks=5 fails=0` / `RESULT: PASS`。
