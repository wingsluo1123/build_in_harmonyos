# DRAFT-worker-meson-launcher-shim-python-c-argv0：worker 的 meson 启动器失效；修复 shim 必须用 python3 -m mesonbuild.mesonmain

> Status: **Draft**（待审核 promote）| severity: `2` | category: `environment, meson, toolchain, python, shell` | Updated: 2026-10-15
> 对应: `knowledge/drafts/DRAFT-worker-meson-launcher-shim-python-c-argv0.kv`

---

## 触发面

- trigger_tool: `conan|conan create|meson|ninja|meson compile`
- phase: `configure|compilation`

**匹配关键词**：meson, shim, launcher, python -c, argv0, meson_command, symbolextractor, ERROR 127, broken-worker-shadow, el2 bundle python, PATH

## 错误签名（error_signature）

```text
meson: inaccessible or not found|meson.* Error 127|/bin/sh: .*build.*/-c: inaccessible or not found|Failed to run.*symbolextractor
```

## 根因（root_cause）

两个叠加问题：

1. **启动器失效**：worker 的 `/storage/Users/currentUser/usr/local/bin/meson`
   被改名为 `meson.broken-worker-shadow`——其 shebang 指向
   `/data/storage/el1/bundle/libs/arm64/python/bin/python3`，而该 el2 bundle python
   在会话中已不存在，于是 conan 调 meson 报 *meson: inaccessible or not found*
   （Error 127）。`~/.scratch/bin/meson` 是同一 shebang 的失效 shim。
2. **shim 写法陷阱**：若自建 shim 写成
   `python3 -c 'import sys; from mesonbuild import mesonmain; sys.exit(mesonmain.main())' "$@"`，
   meson 记录的 `mesonlib.meson_command` 的 `argv[0]` 会变成 `-c`。meson 生成
   `shared_library` 目标时会用 `get_build_command()` **自我重入**执行内部
   `--internal symbolextractor`，ninja 以构建目录为 cwd 去 exec `"<builddir>/-c"`
   → `inaccessible or not found`（Error 127）。

典型现象：编译、链接全部成功，只在 *Generating symbol file ...* 一步失败，且报错中的
可执行文件路径形如 `<builddir>/-c`。

## 影响范围（affected_scope）

el2 bundle python 被移除/不可用的 OHOS worker 上，任何 meson 驱动的 conan 包
（glibmm / gtkmm / gtk / pango / gdk-pixbuf 等）。

## 推荐方案（rec_approach: `shim-python-m-mesonmain`）

在 PATH 前排目录（本 worker 为 `/storage/Users/currentUser/usr/local/bin`，它被
`ci/conan/profiles/ohos-aarch64` 的 `[buildenv] PATH=+(path)...` 前置）放一个 shim：

```sh
#!/bin/sh
export PYTHONPATH=/storage/Users/currentUser/usr/local/lib/python3.12/site-packages${PYTHONPATH:+:$PYTHONPATH}
exec /storage/Users/currentUser/usr/local/bin/python3 -m mesonbuild.mesonmain "$@"
```

关键点：**必须用 `-m mesonbuild.mesonmain`**（`argv[0]` 为真实脚本路径，meson 自我
重入可用）；**禁止 `python -c`**（`argv[0]="-c"` → `<builddir>/-c`）。

属 worker 环境修复：不入仓库、不改任何配方。

## 验证方式（verification_cmd）

```text
meson --version           # 正常输出版本号，如 1.12.1
conan create <某 meson 包> ... --build=missing
# 期望：Generating symbol file 步骤不再报 Error 127
```

## 兜底（fallback）

绕过 conan 的 meson 调用，手动 `meson setup/compile`；或把
`python3 -m mesonbuild.mesonmain` 包装成 PATH 内脚本。

## 关联

- 该环境缺陷曾使 gtkmm 3.24.11 适配的 glibmm 依赖重建连续失败 2 轮（本机 meson 不可用
  → 修 shim → `python -c` 写法导致 symbolextractor 127 → 改 `-m` 后恢复）。
