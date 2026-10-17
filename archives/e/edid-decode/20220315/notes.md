# edid-decode 20220315 适配笔记

## 编译环境
- 构建系统: makefile（上游单文件 Makefile，无 configure）
- 编译日期: 2026-10-08
- 编译器: clang / clang++（`tools.build:compiler_executables` 注入）
- 状态: built

## 源码

- 上游官方仓库：`https://git.linuxtv.org/edid-decode.git/`（linuxtv cgit，**无 tag、无正式 release**，`git ls-remote` 只有 `refs/heads/master`）。
- 本轮目标提交：`cb74358c289650322d91af60cb48a9d984509fd2`（2022-03-15，即 Debian `0.1~git20220315.cb74358c2896` 对应的上游快照）。
- **取源实测（分开记录）**：
  - 上游 cgit 快照 `https://git.linuxtv.org/edid-decode.git/snapshot/edid-decode-<ref>.{tar.gz,tar.xz,tar.bz2,zip}` → **HTTP 400**，正文 `Unsupported snapshot format`（该 cgit 实例未开放 snapshot，四种格式 + `master` 全部 400）；`https://linuxtv.org/git/edid-decode.git` → **404**。
  - 上游仓库本身可达：`https://git.linuxtv.org/edid-decode.git` → **200**；`git ls-remote` rc=0。
  - **采用 Debian pool 快照（备选，如实披露）**：`https://deb.debian.org/debian/pool/main/e/edid-decode/edid-decode_0.1~git20220315.cb74358c2896.orig.tar.xz` → **HTTP 200 / 105488 B**，`sha256=3cb9903663d71b571480ec5cfd88c4c8dd3e77d352b3e2533c3426d61ae296b2`（本地实测），内容为上游 commit 的 `git archive` 导出（顶层目录 `edid-decode-0.1~git20220315.cb74358c2896/`）。
  - 未使用任何镜像前缀。

## 编译步骤

1. `get()` 下载并 `strip_root=True` 解包。
2. `make -j1 CXX=<conf 中的 cxx>`：上游 Makefile 一次性 `$(CXX) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) $(WARN_FLAGS) -g $(sha) $(date) -o edid-decode <9 个 .cpp> -lm`。
3. `package()` 把 `edid-decode` 复制到 `bin/`、`edid-decode.1` 复制到 `share/man/man1/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 cgit 快照 URL 全部 400 | 该 cgit 实例未开放 snapshot（`Unsupported snapshot format`） | 改用 Debian pool 的 git-snapshot orig 包（同一上游 commit），并在正文如实披露 |
| 2 | `make install` 无法执行 | OpenHarmony 设备镜像没有 `install(1)`（`command -v install` 为空，`/data/service/hnp/bin` 亦无） | 配方 `package()` 用 conan `copy()` 放置二进制与 man 页，不调用上游 install 目标 |
| 3 | `make check` 不存在 | 该快照 Makefile 只有 `all`/`clean`/`install` 目标；`test/` 只有 18 个 `.test` 输入样本与 README，无 runner | 以 `test_package` 消费者测试替代，PR 正文按「上游无自动化测试」模板报清点证据 |
| 4 | `$(sha)`/`$(date)` 为空 | Makefile 用 `test -d .git` 守卫，归档包无 `.git` | 无需处理：`-DSHA=`/`-DDATE=` 为空，程序走 `edid-decode SHA: not available` 分支 |

## 源码修改

无补丁（`patches: []`）。

## 依赖版本

无编译期依赖（仅 libm，Makefile 自带 `-lm`）。

## 验证结果

```bash
# 消费者测试（conan create 的 test_package 阶段）
python3 test_package/test_edid_decode.py <package>/bin/edid-decode test_package/fixtures
# → 3 个上游 EDID 样本解码通过，断言通过
```

## 注意事项

- `test_package/fixtures/` 内的 3 个 `.test` 文件是上游 `test/` 目录的原始样本（纯文本十六进制），仅作消费者测试输入。
---

**编译结束**: 2026-10-08 20:49
**最终状态**: built
