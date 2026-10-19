# DRAFT-ohos-shadow-shared-device-usrlocal-lib-quarantine-under-lock：共享真机 ~/usr/local/lib 遗留 .la/.a 被 libtool/ld 命中——持全局锁窗口整类隔离、跑完恢复、零删除

> Source: xmedcon/0.26.1-gtk3 真机 shadow CI r11–r13（2026-10-13/16）
> 对应 KV: knowledge/drafts/DRAFT-ohos-shadow-shared-device-usrlocal-lib-quarantine-under-lock.kv

## 一句话

共享真机的 `~/usr/local/lib` 里常有历史实验留下的 `.la`（dependency_libs 全绝对路径）和
静态 `.a`；autotools+libtool 包链接时 `-ltiff`、`-lglib-2.0` 等会被 libtool/ld 解析到这些
**非 conan 来源**的遗留文件上（`no such file or directory: .../libtiff.so`、`undefined
symbol: pcre2_* in archive .../libglib-2.0.a`）。处置不是删文件，而是：**在持有设备全局
锁的窗口内把这一类文件移入隔离目录，构建结束原样恢复**——零删除、不影响其它任务。

## 使用说明（runner 模板片段，可复制）

```sh
# 拿到设备全局锁（mkdir 原子锁）之后再执行：
QUAR=~/usr/local/lib/.la-quarantine-<pkg>-r<N>
mkdir -p "$QUAR"
for f in "$DEVLIB"/*.la \
         "$DEVLIB"/libglib-2.0.a "$DEVLIB"/libgio-2.0.a "$DEVLIB"/libgobject-2.0.a \
         "$DEVLIB"/libgthread-2.0.a "$DEVLIB"/libgmodule-2.0.a \
         "$DEVLIB"/libtiff.a "$DEVLIB"/liblzma.a; do
  [ -e "$f" ] || continue
  mv "$f" "$QUAR/"
done
# ... 运行 finish / conan create ...
mv "$QUAR"/* "$DEVLIB"/   # 恢复（best effort）
rmdir "$QUAR"
```

要点：
1. **必须先拿全局锁再隔离**——锁保证窗口内没有其它重任务依赖这些文件。
2. **按报错扩隔离面**：第一轮只隔离 `*.la`（libtool 层命中）；若 ld 继续命中
   `~/usr/local/lib/*.a`（静态库 shadow，特征是报错里 `in archive /storage/.../usr/local/lib/libxxx.a`），
   再把对应 `.a` 家族加进来。
3. **恢复放 finally 语义**（trap/顺序执行均可），隔离清单写入 `logs/quarantined-files.txt` 留痕。

## 适用范围

- 共享真机上 autotools/libtool 包的 shadow CI/本地构建；`~/usr/local/lib` 存在
  非当前任务产生的 `.la`/`.a`（历史实验残留）。
- **不适用**：交叉构建（WSL/Windows 宿主，本机没有该污染源）；污染文件在 conan 包
  内部的情况（那是 `DRAFT-libfreefare-*` / `DRAFT-libxmu-*-la-shadow-synth` 的领地）。

## 输入 / 输出

- 输入：链接期报错中出现 `~/usr/local/lib`（或 `/storage/Users/<user>/usr/local/lib`）下的
  `.la`/`.a` 绝对路径；设备全局锁。
- 输出：链接期不再命中遗留文件；`~/usr/local/lib` 文件集合在跑前跑后完全一致。

## 示例（xmedcon 实测）

- r11→r12：隔离 `*.la` 后，`clang: no such file or directory: ~/usr/local/lib/libtiff.so、
  liblzma.so` 消失（libtiff.la 的 dependency_libs 不再被展开）。
- r12→r13：继续报 `undefined symbol: pcre2_* in archive ~/usr/local/lib/libglib-2.0.a`
  （glib-2.88 静态库、无 pcre2），把 glib 全家 `.a` 加入隔离后链接通过。
- 全程 `mv` 恢复，未删除任何共享文件。

## 查重边界（2026-10-16，全库 3289 条草稿扫描）

| 既有条目 | 差异 |
|---|---|
| DRAFT-libfreefare-0.4.0-published-la-stale-thirdparty-abs-path | 那是**依赖 conan 包自带** `.la` 的 dependency_libs 硬编码（删依赖包内引用即可）；本条污染源在**设备共享目录**，不属任何 conan 包 |
| DRAFT-libxmu-1.3.1.1-conan-deps-lack-libtool-la-shadow-synth | 那是依赖**缺** `.la`（合成 shadow 目录补 .la）；本条是设备目录**多**出坏 `.la/.a`（隔离移除） |
| DRAFT-ohos-la-libdir-hardcode | 那是 `.la` 内 `libdir='//lib'` 硬编码；本条不涉及 .la 内容改写 |
| ld 静态库 shadow 本身（优先 .a） | 无既有条目覆盖"设备遗留 .a 抢占 -l 解析"这一形态 |
