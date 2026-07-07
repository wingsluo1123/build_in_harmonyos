# E212: Rust on OHOS — CI 构建环境准备

## 基本信息
- **严重度**: 🔴 blocking (3)
- **类别**: build-system-compatibility | platform | rust
- **触发工具**: cargo | rustc | cc | ld
- **阶段**: building | linking
- **自动修复**: ✅ 是

## 错误特征

```
linker 'cc' not found
```
```
ld.lld: error: unable to find library -lstdc++
clang-15: error: linker command failed with exit code 1
```
```
"always" progress requires a width key
```
```
WARN: Cannot determine rustc sysroot: [Errno 2] No such file or directory: 'rustc'
```

**关键词**: Rust, cargo, rustc, cc linker, libstdc++, libc++, nodefaultlibs, harmonybrew, ohos-sdk, llvm-gcc-compat

## 根因分析

OHOS 上构建 Rust 项目会遇到三个根本性差异：

1. **`cc` 命令缺失** — OHOS 默认没有 `cc` 命令，但 `rustc` 在链接 build script 二进制时需要在 PATH 中找 `cc`（而不是 `CC` 环境变量）
2. **C++ 标准库不同** — `rustc` 默认添加 `-lstdc++`（GCC），但 OHOS 使用 `libc++`（LLVM），无 `libstdc++` 存在
3. **PATH 环境不一致** — Python 进程的 PATH 与 conan shell 的 PATH 可能不同，`self.run("rustc ...")` 可能找不到 `rustc`

**影响范围**: 所有使用 cargo 构建的 Rust 项目，尤其是有 C/C++ 依赖的 `-sys` crate

## 前置条件：harmonybrew

所有工具链通过 harmonybrew 安装（rustup 不支持 HarmonyOS）。

```bash
git clone --depth=1 https://atomgit.com/Harmonybrew/brew.git ~/.harmonybrew/Homebrew
mkdir -p ~/.harmonybrew/bin
ln -sf ~/.harmonybrew/Homebrew/bin/brew ~/.harmonybrew/bin/brew
export PATH=~/.harmonybrew/bin:$PATH
```

## 解决方案

### 方案 1: 完整 conanfile.py 模板（推荐）

在 conanfile.py 的 `build()` 中按顺序调用三个辅助方法：

```python
def build(self):
    apply_conandata_patches(self)
    self._ensure_cargo()       # Step 1: 安装/发现 Rust 工具链
    self._ensure_cc()          # Step 2: 确保 cc 命令在 PATH 中
    self._fix_libstdcxx()      # Step 3: 处理 -lstdc++ → -lc++_shared

    os.environ["CARGO_TERM_PROGRESS_WHEN"] = "always"
    os.environ["CARGO_TERM_PROGRESS_WIDTH"] = "80"
    self.run("cargo build --release", cwd=self.source_folder)
```

#### Step 1: `_ensure_cargo()` — 安装/发现 Rust

```python
def _ensure_cargo(self):
    """Detect or install Rust toolchain via harmonybrew."""
    self._setup_cargo_mirror(home)  # 配置 USTC 镜像加速
    if shutil.which("cargo"):
        return
    # 1. 检查 ~/.harmonybrew/bin/cargo → 加入 PATH
    # 2. 检查 ~/.cargo/bin/cargo → 加入 PATH
    # 3. 安装 harmonybrew + brew install rust
```

> ⚠️ `shutil.which("cargo")` 返回后 `_ensure_cargo` 直接 return，不会把 `~/.harmonybrew/bin` 加入 PATH。后续若用 `self.run("rustc ...")` 会在 conan shell 中找不到 `rustc`。**解法**: 用 `shutil.which("rustc")` 在 Python PATH 查找，再用 `subprocess.run` 执行。

#### Step 2: `_ensure_cc()` — 确保 `cc` 命令可用

```python
def _ensure_cc(self):
    """rustc 找 PATH 中的 cc，不是 CC 环境变量"""
    if shutil.which("cc"):
        return
    # 1. 找 clang (PATH → Cellar/ohos-sdk/*/native/llvm/bin/ → harmonybrew bin)
    # 2. brew install ohos-sdk + llvm-gcc-compat（兜底）
    # 3. 创建 cc → clang 符号链接，加入 PATH
```

`llvm-gcc-compat` 提供 `cc` → `clang`、`gcc` → `clang` 等符号链接。`ohos-sdk` 提供 `clang`/`ld.lld` 和 `libc++`。

#### Step 3: `_fix_libstdcxx()` — 处理 `-lstdc++` 链接失败

```python
def _fix_libstdcxx(self):
    """写入 rustc sysroot target lib 目录，该路径已在 linker 默认 -L 搜索路径中"""
    rustc = shutil.which("rustc")          # 用 Python PATH，不是 self.run
    result = subprocess.run([rustc, "--print", "sysroot"], ...)
    sysroot = result.stdout.strip()
    lib_dir = os.path.join(sysroot, "lib", "rustlib",
                           "aarch64-unknown-linux-ohos", "lib")
    # 写入 libstdc++.so → INPUT(-lc++_shared)
    # 写入 libstdc++.a  → INPUT(-lc++_static -lc++abi)
```

### 方案 2: 手动修复（简单场景）

```bash
# 创建 libstdc++ 转发脚本到 rustc sysroot 目录
OHOS_LIB_DIR=$(find ~/.harmonybrew -path "*/llvm/lib/aarch64-linux-ohos" -type d | head -1)
echo 'INPUT(-lc++_shared)' > "$OHOS_LIB_DIR/libstdc++.so"
echo 'INPUT(-lc++_static -lc++abi)' > "$OHOS_LIB_DIR/libstdc++.a"
export RUSTFLAGS="-L $OHOS_LIB_DIR -C link-arg=-L$OHOS_LIB_DIR"
```

### crates.io 镜像（国内 CI 必备）

```toml
# ~/.cargo/config.toml
[source.crates-io]
replace-with = "ustc"
[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
```

### 环境变量

```bash
export PATH=~/.harmonybrew/bin:$PATH
export CC=clang
export CARGO_TERM_PROGRESS_WHEN=always
export CARGO_TERM_PROGRESS_WIDTH=80
export SSL_CERT_FILE=~/usr/local/ssl/cert.pem
export REQUESTS_CA_BUNDLE=~/usr/local/ssl/cert.pem
```

## 禁止做法
- ❌ 使用 `ln -s` 创建 libstdc++ 符号链接（HMDFS 不跟踪符号链接，见 E050）
- ❌ 仅设置 `CC` 环境变量而不确保 PATH 中有 `cc` 命令（`rustc` 不读 `CC`）
- ❌ 使用 `self.run("rustc ...")` 查询 sysroot（conan shell PATH 与 Python PATH 不一致时失败）

## 验证
```bash
# After fix, cargo build should succeed
cargo build --release 2>&1 | grep "Finished"
```

## 关系
- **相似**: E050 (HMDFS symlink issue) — related but different root cause
- **原则**: P003 (platform compatibility)

## 来源
- 编译事件: ouch latest (2026-07-03 / 2026-07-06)
- 作者: Agent 80FE / AtomCode (deepseek-v4-flash)
