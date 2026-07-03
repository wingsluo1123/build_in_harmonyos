# E212: Rust linker defaults to -lstdc++ on OHOS but system only has libc++

## 基本信息
- **严重度**: 🔴 blocking (3)
- **类别**: build-system-compatibility | platform | rust
- **触发工具**: cargo | rustc | cc | ld
- **阶段**: linking
- **自动修复**: ✅ 是

## 错误特征
```
ld.lld: error: unable to find library -lstdc++
clang-15: error: linker command failed with exit code 1
```

**关键词**: lstdc++, libc++, rust, cargo, ld.lld, linker, ohos, aarch64-unknown-linux-ohos

## 根因分析
The Rust compiler for the `aarch64-unknown-linux-ohos` target defaults to linking C++ code with `-lstdc++` (GCC's C++ standard library). However, OHOS uses `libc++` (LLVM's C++ standard library) instead. No `libstdc++` exists on the system, causing the linker to fail.

This affects any Rust project that has C/C++ dependencies (e.g., `-sys` crates that compile C/C++ code like `libbzip3-sys`, `unrar-ng-sys`, `zstd-sys`).

## 解决方案

### 推荐方案: create-libstdcxx-linker-script
Create `libstdc++.so` and `libstdc++.a` linker scripts in the OHOS SDK lib directory that redirect to libc++:

```bash
OHOS_LIB_DIR=$(find ~/.harmonybrew -path "*/llvm/lib/aarch64-linux-ohos" -type d | head -1)
echo 'INPUT(-lc++_shared)' > "$OHOS_LIB_DIR/libstdc++.so"
echo 'INPUT(-lc++_static -lc++abi)' > "$OHOS_LIB_DIR/libstdc++.a"
export RUSTFLAGS="-L $OHOS_LIB_DIR -C link-arg=-L$OHOS_LIB_DIR"
```

### 回退方案: set-rustflags-cpp-lib
Explicitly tell the linker to use libc++ instead of libstdc++:
```bash
export RUSTFLAGS="-C link-arg=-lc++ -C link-arg=-lc++abi"
```

## 禁止做法
- ❌ Using `ln -s` to create libstdc++ symlinks (HMDFS does not track symlinks properly, see E050)
- **原因**: HMDFS file system does not properly track symlinks
- **后果**: Linker still cannot find libstdc++ even after creating symlink

## 验证
```bash
# After fix, cargo build should succeed
cargo build --release 2>&1 | grep "Finished"
```

## 关系
- **相似**: E050 (HMDFS symlink issue) — related but different root cause
- **原则**: P003 (platform compatibility)

## 来源
- 编译事件: ouch latest (2026-07-03)
- 作者: Agent 80FE
