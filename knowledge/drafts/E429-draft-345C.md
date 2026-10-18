# E429 — Debian orig 两层目录 / 上游 makefile 硬编码编译器 / 老 C++ 的过时写法与过时的自带测试

## 错误特征
```
1) make: *** No targets specified and no makefile found.  Stop.        （在源码根跑；源码在 Source/ 下）
2) MappingResult.h:275:23: error: comparison between pointer and integer ('char *' and 'char')
3) PerMTest.cpp:10:5: error: no matching function for call to 'testLongBases2Colors'
```

## 触发条件
- 源: Debian 源包 orig（可能是两层目录）
- 构建: 上游手写 makefile（硬编码 `g++`/带 `-static`）
- 阶段: build（编译上游主程序与上游自带测试程序）

## 根因分析
1. **两层目录**：`perm_0.4.0.orig.tar.gz` 解开是 `perm_0.4.0/Source/…`；conan 的 `strip_root=True`
   只剥掉**一层** → makefile 还在 `<source>/Source`。
2. **上游 makefile 硬编码**：`CC = g++ -O2 $(CFLAGS)`、`CFLAGS = -ggdb -Wall -fopenmp -static`。
3. **过时写法**：老 MSVC 风格的 `char* == '\0'` 在现代 clang 是硬错误；上游自带的 `PerMTest.cpp`
   调用零参 `testLongBases2Colors()`，而该函数早已变成两参，只有 `testLongBases2ColorsCases()` 是零参入口
   ——**上游自带的测试自己没跟上 API 演变**（Debian 的打包也从不编它）。

## 解决方案
```python
# ① 自动探测真正的构建目录（比写死路径稳）
sub = os.path.join(self.source_folder, "Source")
src = sub if os.path.isfile(os.path.join(sub, "makefile")) else self.source_folder

# ② 命令行覆盖 CC（make 命令行变量优先级最高）——换编译器 + 摘掉平台不合适的开关，不改上游 makefile
self.run('make -j1 CC="%s -O2 -Wall"' % clangxx, cwd=src)

# ③ 过时写法做**等价最小修正**
t = t.replace("m1.QScores == '\\0'", "(!m1.QScores || m1.QScores[0] == '\\0')")   # 与上游自己的 caRef[0] 写法一致
t = t.replace("testLongBases2Colors();", "testLongBases2ColorsCases();")           # 换成上游自己的零参入口
```
> ⚠️ 把过时的自带测试改成"能跑"之后，**必须如实披露它的语义**：`PerMTest.cpp` 的 `main()`
> 固定 `return 0`、无输出 → 只能证明"可编、可跑通"，**不能**说成"N 条断言全过"。

### 禁止做法
- ❌ 写死 `Source/` 路径（换一个包就崩；自动探测一行就够）
- ❌ 为了换编译器去改上游 makefile（命令行覆盖 `CC` 即可，且能顺手摘掉 `-static`）
- ❌ 把"过时的自带测试改成能跑"包装成"测试全过"（要看它的 main 到底断言了什么）
- ❌ 直接跳过自带测试（先把过时调用改成上游自己的零参入口，让它真跑）

## 验证
```bash
ls <source>/Source/makefile        # 确认构建目录
grep -nE '^(CC|CFLAGS|LIBS)' makefile
<build>`make test` 类目标 / 自带测试程序的 rc 与输出
```

## 关联条目
- 相关: E429（同一草稿 id 下的其它适配条目：conan out-of-source 接入上游 autotools 测试 / conan 下 CMake
  工程四处目标名/路径不匹配 / meson 在 CI 下 Unknown linker / musl 与内核 uapi 头冲突 / libelf 的
  HAVE_ELF_H 未定义导致 elf_repl.h 与系统 elf.h 撞 / 脚本式工具入口打包三坑 等）
