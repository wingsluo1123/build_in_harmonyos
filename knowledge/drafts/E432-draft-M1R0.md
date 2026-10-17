# E432 — 新增文件补丁与 GENERATED 文件（configure）改写的正确处置

## 错误特征

两种相互牵连的失败：

1. 新增源文件的补丁在 `conan create` 中报：
   ```
   ERROR: miredo/1.2.6: Error in build() method
   patch: **** source/target file does not exist
   ```
   （`patches/*.patch` 里该文件的头部是 `--- a/include/xxx.h` 而不是 `--- /dev/null`）

2. 改用 `export_sources()` 让新增文件进源码包后，`clean-verify` 的**干净构建**又失败：
   ```
   configure: error: ...
   ```
   ——因为干净构建只用「上游 tarball + patches」，而改写预生成 `configure` 的那部分改动
   从未进入 patches。

## 触发条件

- 构建系统: 任意，但必须用 conan 的补丁机制（`refresh-patch --auto` + `conandata.yml: patches`）
- 场景: ①适配需要**新增源文件/头文件**；②适配需要改动 autotools **预生成文件**
  （`configure`、`config.guess`、`config.sub`）
- 阶段: `conan create` 的 `build()`（补丁应用）/ `clean-verify`（干净构建复验）

## 根因分析

1. **新增文件的补丁头**：补丁生成工具对新增文件固定写 `--- a/<path>`，而 Conan 的补丁
   应用要求新增文件源侧为 `/dev/null`；且工具每次重跑 `refresh-patch --auto` 都会覆盖
   手工修正过的判定行，结果反复回退。
2. **GENERATED 文件被排除**：`configure` 属 autotools 生成产物，补丁工具按 GENERATED
   排除（同 `config.h`/`Makefile`），因此 E114 那类对 `configure` 的改写**无法进 patches/**；
   本地 `conan create` 之所以能过，是因为配方 `build()` 里另有就地改写代码，
   而 `clean-verify` 的干净构建路径不跑 `build()`。

## 解决方案

### 推荐方案（rec_priority 1）

1. **新增代码内联进既有文件**（首选）：把回退实现（如 `pthread_cancel` 空操作、
   原型声明）放进已有源文件（`libteredo/debug.h` 这类），使 patches 全部是修改型，
   `clean-verify` 只用「tarball + patches」即可配置。
   miredo 1.2.6 由最初的 `include/pthread-cancel-compat.h` 改为内联进
   `libteredo/debug.h`（补丁 0006）+ `src/relayd.c`（补丁 0003）。
2. **必须新增文件时**：走 `export_sources()` 导出 + `source()` 拷贝
   （先例：`archives/a/abiword-plugin-*/` 的 `compat/`），不要塞进 `patches/`。
3. **GENERATED 文件（configure）的改写**：放配方 `build()` 内就地完成，例如
   ```python
   _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
   ```
   （先例：`archives/a/abiword-plugin-t602/3.0.8/conanfile.py` 的 `_drop_umask_077`）；
   `config.guess`/`config.sub` 不属 GENERATED（是手写脚本），可直接进 patches。

### 禁止做法

- ❌ 期望 `patches/` 承载新增文件（`--- a/...` 头部必然应用失败）
- ❌ 把 `configure` 的改写塞进 `patches/`（GENERATED 会被排除，本地看不出来、
  `clean-verify`/CI 才暴露）
- ❌ 每次 refresh-patch 后手工改补丁头（会被下一次重跑覆盖，属反复无效操作）

## 验证

```bash
# 1. 补丁全部为修改型（不应出现非 /dev/null 的新增文件头）
grep -n "^--- " archives/<l>/<pkg>/<ver>/patches/*.patch | grep -v "/dev/null"
# 2. 干净构建复验（只用 tarball + patches）
python3 scripts/ohc-run.py clean-verify <pkg> <ver>
# 3. 完整配方构建
conan create archives/<l>/<pkg>/<ver> -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 关联条目

- 相关: E114（HMDFS 下 configure 临时目录的 umask 改写）、E431（线程取消回退，本条目促成其改为内联）
