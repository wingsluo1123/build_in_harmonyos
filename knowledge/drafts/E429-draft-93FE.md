# E429 — HMDFS 下 configure/config.status 的 umask 077 让配置阶段整体失败

## 错误特征

`configure` 走到生成 config files 那一步时突然失败，日志尾部形如：

```
configure: creating ./config.status
./config.status: line 873: ./confJhgpDJ/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

即 config.status 自建的临时目录/脚本**不可访问**（注意报错主体是它临时建的文件，而不是某个源码文件）。

## 触发条件

- 构建系统: **autotools**（且 `configure` 是经 `autoreconf` 自举生成的）
- 阶段: **configuration**（`./configure` 内部调用 `config.status` 时）
- 环境: 本仓库的共享文件系统（HMDFS）语义
- 前提: 生成的 `configure` 里含 `umask 077`（`grep -rn "umask 077" --include=configure` 可快速判定）

## 根因分析

`autoreconf` 生成的 `configure` 里会内嵌一段 `umask 077`，它又被写进**生成的 `config.status`**。
在 HMDFS 下，该掩码使 config.status 自建的临时目录与脚本（`confXXXX/subs1.awk` 之类）访问受限，
于是它直接放弃 "config files machinery"，整个 configure 失败。

**关键点**：只在**进程层面**放开掩码（shell `umask 022` / python `os.umask(0o022)`）**不足以**解决 ——
`config.status` 自带的那处 `umask 077` 仍会在它内部生效。

## 解决方案

### 推荐方案

在 **`autoreconf` 之后**、`configure` 之前，把 `<source>/**/configure` 里的 `umask 077` **等价替换**成
`umask 022`（只改这一处掩码，不改任何逻辑）。配方里用 python 遍历 glob 完成，例如：

```python
for cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
    txt = open(cfg, encoding="utf-8", errors="ignore").read()
    if "umask 077" in txt:
        open(cfg, "w", encoding="utf-8").write(txt.replace("umask 077", "umask 022"))
```

然后照常 `./configure --build=aarch64-unknown-linux-musl`（`--build` 用于绕开上游过旧的 config.guess）。

### 次级方案

若 `configure` 里本就没有 `umask 077`，仅放开进程掩码（`umask 022` / `os.umask(0o022)`）即可。

### 禁止做法

- ❌ 在 `autoreconf` **之前**修改 `configure` —— 自举会重新生成它，改动被覆盖，表现为"改了却没生效"。
- ❌ 因为这一条就判定"HMDFS 下 autotools 不可做"而放弃整包。

## 验证

```bash
grep -rn "umask 077" . --include=configure      # 命中 → 本模式
# 修好后：conan create 应能走到 configure 成功并进入 make
```

## 关联条目

- 相关: 同族经验「autoreconf 三件套」——①`automake`/`libtool` 需作为 `tool_requires`
  （镜像无系统 automake 时报 `Can't exec "aclocal"`）；②自举前要清 `PERL5LIB`/`PERL5OPT`；
  ③发布源常缺 `m4/` 空目录，需先建。这三条与本节同属"autoreconf 自举"族，本次在 usbauth 1.0.5
  一并踩到并已写进该版本 notes.md。
