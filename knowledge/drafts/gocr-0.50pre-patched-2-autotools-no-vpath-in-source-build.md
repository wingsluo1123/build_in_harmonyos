# conan 默认 out-of-source 会打爆不支持 VPATH 的老式手写 Makefile.in

> Draft: `DRAFT-GOCR-050PRE-AUTOTOOLS-NO-VPATH-IN-SOURCE-BUILD`
> Stem: `gocr-0.50pre-patched-2-autotools-no-vpath-in-source-build` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-GOCR-050PRE-AUTOTOOLS-NO-VPATH-IN-SOURCE-BUILD
- **严重度**: 2
- **类别**: build|autotools|conan-recipe
- **触发工具**: conan
- **阶段**: build

## 错误特征

```
gocr/0.50pre-patched-2: RUN: make -j1
make: *** No rule to make target 'Makefile.in', needed by 'Makefile'.  Stop.
ERROR: gocr/0.50pre-patched-2: Error in build() method, line 106
	autotools.make(args=["-j1"])
	ConanException: Error 2 while executing
```

注意 `configure` 已经成功（Makefile/config.status/config.h 都生成了），失败只发生在 `make`。

## 根因分析

Conan 2 的 `basic_layout()` 默认 `folders.build = "build-<build_type>"`（本包为 `build-release`）。
Autotools helper 用**绝对路径**执行 `.../b/configure`，但 configure 生成 Makefile 时落在**当前目录**（即 `build-release/`），
而源目录里的 `Makefile.in` 并不会被复制过去。

gocr 的 `Makefile.in` 是手工维护的（2009 年），规则写作：

```make
Makefile: Makefile.in configure
	./configure
```

前提 `Makefile.in` 是**相对构建目录**的，没有 `$(srcdir)/` 前缀 → 在 `build-release/` 下不存在该文件，
make 无法为其找到规则，立即报 `No rule to make target 'Makefile.in', needed by 'Makefile'`。

## 推荐方案

**方法**: `build-in-source-for-non-vpath-makefiles`

1. 先判定 VPATH 友好性：
   ```bash
   grep -n 'srcdir\|top_srcdir\|VPATH' Makefile.in src/Makefile.in
   ```
   若前提全为不带 `$(srcdir)` 的相对路径 → 不能 out-of-source。
2. 配方改用 in-source：
   ```python
   def layout(self):
       # 上游手写 Makefile.in 无 VPATH 支持，规则引用相对构建目录的 Makefile.in
       basic_layout(self, build_folder=".")
   ```
3. 其余保持标准写法（`autotools.configure()` / `autotools.make()`）；不要改上游 Makefile.in，也不要用 `make -C` 绕过
   （package()/patch 阶段依赖 source_folder 与构建目录一致）。
4. notes.md 记录「不支持 out-of-source」，避免后续被建议改回默认值。

## 验证

```bash
$ conan create archives/g/gocr/0.50pre-patched-2 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
...
gocr/0.50pre-patched-2: RUN: make -j1
make -C src all
...
libPgm2asc consumer test: PASSED
```

修复后 conan-verify G0–G4 + L2/L4/L5 全通过。
