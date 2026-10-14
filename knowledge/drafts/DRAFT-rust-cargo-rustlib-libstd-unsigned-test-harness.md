# DRAFT-rust-cargo-rustlib-libstd-unsigned-test-harness：cargo 前置的未签名 libstd 遮蔽签名副本，proc-macro 测试 harness exit 127

> 草稿（pending-editor-review）。对应 kv：`knowledge/drafts/DRAFT-rust-cargo-rustlib-libstd-unsigned-test-harness.kv`
> 触发事件：`archives/t/typeshare/1.13.4` HarmonyOS PC 适配（2026-10-13），`conan create` 第 1 轮 rc=101。

## 背景

在 HarmonyOS 上以 conan 构建 Rust workspace 时，`cargo test --workspace` 会为**每个 proc-macro crate**
生成一个以 `prefer-dynamic` 链接的单元测试 harness。这类 harness 与普通 lib/bin 测试目标不同：它的
`DT_NEEDED` 只列 `libstd-<hash>.so` 与 `libc.so`，且不带 `RUNPATH`，因此运行期必须由
`LD_LIBRARY_PATH` 提供 Rust 标准库动态库。

本图已有条目覆盖了"未签名工具链二进制无法 execve"（`DRAFT-below-ohos-unsigned-rust-toolchain`）
与"搬移工具链二进制会破坏 rustc 的 sysroot 推导"（`DRAFT-13336-rainfrog-...`），但都未覆盖
**cargo 主动把 sysroot 的 `lib/rustlib/<target>/lib` 前置进搜索路径**这一行为，以及由此产生的
"未签名副本遮蔽已签名副本"。

## 现象

```
     Running unittests src/lib.rs (target/release/deps/typeshare_annotation-e7f6f049d69ac091)
Error loading shared library libstd-6cb83eb787a5e858.so: (needed by .../typeshare_annotation-e7f6f049d69ac091)
Error relocating .../typeshare_annotation-e7f6f049d69ac091: _RNvNtCscXlqXfLctsd_3std2rt19lang_start_internal: symbol not found
Error relocating .../typeshare_annotation-e7f6f049d69ac091: _RNvNtCsd1oV3Xf3bd2_5alloc5alloc18handle_alloc_error: symbol not found
...
error: test failed, to rerun pass `-p typeshare-annotation --lib`
Caused by:
  process didn't exit successfully: `.../typeshare_annotation-e7f6f049d69ac091` (exit status: 127)
```

特征：
- 同一 workspace 的**其它 5 个测试目标全部通过**（lib/bin 目标静态链接 libstd），只有 proc-macro
  crate 的 harness 崩溃 → 与"平台不支持"或"用例失败"明显不同；
- 报错文案是 `Error loading shared library`（加载期），而不是 `error: test failed: assertion`（用例期）；
- 符号名是 `_RNv…`（Rust mangled），指向 libstd/alloc/core。

## 根因

1. **harness 的动态链接形态**：`readelf -d target/release/deps/<proc_macro_crate>-*` →
   `NEEDED [libstd-<hash>.so]`、`NEEDED [libc.so]`，无 `RUNPATH`。
2. **cargo 的前置行为**：cargo 启动测试进程时会把 sysroot 的
   `lib/rustlib/<target>/lib` 目录（libstd 所在处）**前置**到 `LD_LIBRARY_PATH`。
   实测探针（在 `CARGO_TARGET_<TRIPLE>_RUNNER` 指向的 wrapper 里打印 `$LD_LIBRARY_PATH`）：
   ```
   PROBE LD_LIBRARY_PATH=[.../target/release, .../target/release/deps,
     <toolchain>/lib/rustlib/aarch64-unknown-linux-ohos/lib,      <-- cargo 前置
     <toolchain>/lib, ...]
   ```
3. **签名门禁**：`<toolchain>/lib/rustlib/...` 属于只读工具链载荷（conan 的
   `rust-toolchain/1.97.1` 包；配方为省下 ~500MB 复制量，只对 cargo/rustc/librustc_driver
   复制+自签名，其余目录走软链接）。该目录里的 `libstd-<hash>.so` **未签名**，
   HarmonyOS 拒绝加载未签名共享库 → cargo 前置的这份副本遮蔽了配方放在 `<toolchain>/lib/`
   的已签名副本。

**判据（一行）**：同一 harness 手工以 `LD_LIBRARY_PATH=<toolchain>/lib` 运行输出
`0 tests, 0 benchmarks`（正常），以 `LD_LIBRARY_PATH=<toolchain>/lib/rustlib/<target>/lib`
运行则复现同一报错 → 既排除"文件不存在"，也排除 noexec 挂载。

## 诊断

```bash
# 1) harness 是否动态依赖 libstd（且无 RUNPATH）
readelf -d target/release/deps/<crate>-* | grep -E "NEEDED|RUNPATH"

# 2) 复现：指向未签名副本
LD_LIBRARY_PATH=<toolchain>/lib/rustlib/aarch64-unknown-linux-ohos/lib \
    target/release/deps/<crate>-* --list        # -> Error loading shared library libstd-...

# 3) 对照：指向已签名副本
LD_LIBRARY_PATH=<build>/rust-toolchain/lib \
    target/release/deps/<crate>-* --list        # -> 0 tests, 0 benchmarks

# 4) 签名标记（未签名 0 / 已签名 >=1）
strings -a <libstd.so> | grep -c codesign
ls -l <rustlib>/libstd-*.so <signed>/libstd-*.so   # 两者字节数不同（签名追加数据）
```

## 修复（首选，可直接复用）

`conanfile.py` 内两处改动，均为**构建环境适配**，不改上游源码：

```python
# 1) _prepare_signed_toolchain()：把 rustlib/<target>/lib 下所有 .so 一并复制+自签名
rustlib_lib = os.path.join(src_lib, "rustlib", self._ohos_target(), "lib")
if os.path.isdir(rustlib_lib):
    for name in sorted(os.listdir(rustlib_lib)):
        if name.endswith(".so"):
            dylib_srcs.append(os.path.join(rustlib_lib, name))

# 2) _prepare_test_runner()：用 cargo target runner 把已签名目录前置
runner = os.path.join(self.build_folder, "ohos-test-runner.sh")   # 路径必须无空格
with open(runner, "w", encoding="utf-8", newline="\n") as fh:
    fh.write('#!/bin/sh\n'
             'export LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"\n'
             'exec "$@"\n' % env["LD_LIBRARY_PATH"])
os.chmod(runner, 0o755)
var = "CARGO_TARGET_%s_RUNNER" % self._ohos_target().upper().replace("-", "_")
env[var] = runner
```

要点：
- 自签名副本**平铺**进 `<toolchain>/lib`（不依赖加载器搜索子目录）；
- runner 的作用是把已签名目录**排到 cargo 自身顺序之前**，否则 cargo 的前置目录仍会遮蔽；
- runner 路径**不能含空格**：cargo 以空白切分 runner 值，含空格会报
  `could not execute process ... (never executed)`；
- 交付二进制静态链接 libstd，不受影响（`readelf -d bin/typeshare` → 仅 `NEEDED libc.so`）。

## 禁止（实测踩过的错误方向）

| 方向 | 为什么错 | 后果 |
|------|----------|------|
| `--test-threads=1` / 排除 proc-macro crate | 掩盖而非修复；被测用例仍在，漏测（违反 R51） | 覆盖虚高，真实用户仍撞上 |
| `chmod 777 libstd-*.so` | 失败根因是缺 OHOS 代码签名，与 POSIX mode 无关 | 反复调权限，问题依旧 |
| 只把系统库目录塞进 `LD_LIBRARY_PATH` | 系统 lib 目录没有该 libstd-<hash>.so | 从"库找不到"变成"符号找不到" |

## 验证证据

- 修复前：`cargo test --workspace --all-features --tests` → rc=101，唯一失败目标
  `typeshare-annotation`（exit status 127）。
- 修复后：rc=0，6 个目标全 `ok`，**386 用例通过 / 0 失败 / 0 跳过**；`-p typeshare-annotation --lib`
  输出 `test result: ok. 0 passed; 0 failed; 0 ignored`（该 crate 无 `#[test]`，harness 正常执行即证据）。
- `conan create` EXIT=0；`conan-verify` G0-G4 PASS；`finish` W3 本地 CI PASS。
- 日志：typeshare 任务工作区 `logs/conan_create_5.log`、`logs/upstream_cargo_test.log`。

## 适用边界

- 适用于任何含 proc-macro crate 的 Rust workspace；不含 proc-macro 的纯 lib/bin 项目不会触发。
- 需要工具链包（或任何 sysroot）内的 `libstd-*.so` 处于"只读、未签名"状态——即
  `tool_requires rust-toolchain` 这类预编译工具链包的标准形态。
- 若改用 harmonybrew 预签名 bottle 作为工具链来源，则 `<toolchain>/lib/rustlib/...` 已是签名件，
  本问题不出现；但配方仍需自行处理 `cargo` 的 DT_NEEDED（libssl/libcrypto/libz）。

## Provenance

- 触发任务：`archives/t/typeshare/1.13.4`（Rust CLI，cargo workspace：annotation/core/lib/cli）
- 工具链：`rust-toolchain/1.97.1`（tool_requires，宿主与目标同为 `aarch64-unknown-linux-ohos`）
- 记录日期：2026-10-13
- 作者：7527 (OpenDesk agent)
