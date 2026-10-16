# DRAFT-ohos-hmdfs-umask-and-autotools-regeneration

> 维护者复审候选草稿（Path B 知识扩展材料）；**不自动作为 Path B 评级或分值依据**。

## 现象

在 HMDFS 上以 autotools 构建（本轮 `libbs2b/3.1.0`、`libcddb/1.3.2`、`libXxf86dga/1.1.5` 等都遇到）时，会连续踩到三类问题：

```
config.status: error: could not setup config files machinery

configure: error: newly created file is older than distributed files!

ConanException: Failed to apply patch …: source/target file does not exist:
  --- b'a/build-aux/config.guess'
```

## 根因（逐条实测）

### 1. umask 077 是**双重**的

`configure` 与**它生成的 `config.status`** 都用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录（2700）。
hmdfs 经 group 位中介目录访问、`chmod` 对它无效 → 目录不可遍历 → `config.status` 报
`could not setup config files machinery`。**只改 `configure` 不够**：make 期间一旦有规则重跑 `config.status`，
会按模板**重新生成**带 `umask 077` 的脚本，错误原样再现（libbs2b 实测：先只改 configure 失败 → 再补 config.status 才通过）。

### 2. 补丁改了 autotools 输入 → 触发再生规则

补丁触及 `configure.ac` / `Makefile.am` 后，它们比 `configure` 新 → make 触发
`$(srcdir)/configure: $(am__configure_deps)` 与 `config.status --recheck`，**再次生成 077 的 config.status**。
处置：把 **输入置旧、生成物置新**（`configure`/`config.status`/`Makefile`/`config.h` 用当前时间，
`configure.ac`/`aclocal.m4`/`Makefile.am`/`Makefile.in`/`config.h.in` 用 now-600）。

**坑中坑**：若图省事用“未来时间戳”（如 now+5s）让生成物更新，autoconf 的健全性检查会报
`newly created file is older than distributed files!` —— 必须用相对时间。

### 3. 自实现 `strip_root` 时被 `patches/` 干扰

`get()` 不支持 `.tar.lzma` 等格式时改用 `download()` + 标准库解包，若按“源目录里只有一个子目录就是 tarball 顶层”
判断，会因 `export_sources` 已把 `patches/` 放进源目录而**判断失效** → 补丁目标解析到 `a/...` 不存在的路径，
报 `source/target file does not exist`。正解：先解到独立 staging 子目录，再上移其唯一条目。

## 推荐处置（可直接复用）

```python
# ① configure / config.status 都放宽 umask；② 输入置旧、生成物置新（禁用未来时间戳）
def _relax_umask(self):
    import time
    from pathlib import Path
    now, old = time.time(), time.time() - 600
    patched = []
    for root in {self.source_folder, self.build_folder}:
        for dirpath, _dirs, files in os.walk(root):
            for name in ("configure", "config.status"):
                if name in files:
                    p = Path(dirpath, name)
                    c = p.read_text(encoding="utf-8", errors="replace")
                    if "umask 077" in c:
                        p.write_text(c.replace("umask 077", "umask 022"), encoding="utf-8")
                    patched.append(p)
    for p in patched:
        os.utime(p, (now, now))
    for base in {self.source_folder, self.build_folder}:
        for name in ("Makefile", "config.h"):
            f = Path(base, name)
            if f.is_file():
                os.utime(f, (now, now))
        for name in ("configure.ac", "configure.in", "aclocal.m4", "Makefile.am",
                     "Makefile.in", "config.h.in", "config.h.in~"):
            f = Path(base, name)
            if f.is_file():
                os.utime(f, (old, old))
    return [str(p) for p in patched]
```

调用点：`build()` 开头一次、`configure()` 之后再调用一次（覆盖新生成的 `config.status`）。

## 验证

- `libbs2b/3.1.0`：`conan create` rc=0；test_package 输出 `level_fcut=700 level_feed=30`、
  `cross_feed_f: left=0.754334 right=0.039345`、`libbs2b 等级编码/采样率/串扰处理 检查通过`
- `libcddb/1.3.2`：`0003-configure.patch`（umask 077→022）+ 消费者测试 3/3

## 证据

- `archives/l/libbs2b/3.1.0/notes.md`（“换源与构建踩坑”四节，含每条的实测报错）
- `archives/l/libcddb/1.3.2/patches/0003-configure.patch`、`archives/l/libXxf86dga/1.1.5/notes.md`
