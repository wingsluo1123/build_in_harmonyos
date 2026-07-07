# E212: Rust on OHOS — 构建环境准备

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

## 环境准备

### 1. harmonybrew

所有工具链通过 harmonybrew 安装（rustup 不支持 HarmonyOS）。

```bash
git clone --depth=1 https://atomgit.com/Harmonybrew/brew.git ~/.harmonybrew/Homebrew
mkdir -p ~/.harmonybrew/bin
ln -sf ~/.harmonybrew/Homebrew/bin/brew ~/.harmonybrew/bin/brew
export PATH=~/.harmonybrew/bin:$PATH
```

### 2. 工具链安装

```bash
brew install rust              # Rust 工具链 (rustc/cargo)
brew install ohos-sdk          # C 编译器 (clang/ld.lld) + libc++
brew install llvm-gcc-compat   # cc → clang 符号链接
```

### 3. crates.io 镜像（国内 CI 必备）

```toml
# ~/.cargo/config.toml
[source.crates-io]
replace-with = "ustc"

[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
```

### 4. 环境变量

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

---

## CI 脚本编写

### 三段式构建流程

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

### Step 1: `_ensure_cargo()`

安装/发现 Rust 工具链，配置 crates.io 镜像。

```python
def _ensure_cargo(self):
    """Detect or install Rust toolchain via harmonybrew."""
    home = os.path.expanduser("~")
    cert_pem = os.path.join(home, "usr", "local", "ssl", "cert.pem")
    if os.path.exists(cert_pem):
        os.environ["SSL_CERT_FILE"] = cert_pem
        os.environ["REQUESTS_CA_BUNDLE"] = cert_pem

    self._setup_cargo_mirror(home)

    if shutil.which("cargo"):
        return

    # 1. 检查 existing harmonybrew cargo
    harmonybrew_bin = os.path.join(home, ".harmonybrew", "bin")
    harmonybrew_cargo = os.path.join(harmonybrew_bin, "cargo")
    if os.path.isfile(harmonybrew_cargo) and os.access(harmonybrew_cargo, os.X_OK):
        self._add_path(harmonybrew_bin)
        return

    # 2. 检查 ~/.cargo/bin
    cargo_bin_dir = os.path.join(home, ".cargo", "bin")
    cargo_bin = os.path.join(cargo_bin_dir, "cargo")
    if os.path.isfile(cargo_bin) and os.access(cargo_bin, os.X_OK):
        self._add_path(cargo_bin_dir)
        return

    # 3. 安装 harmonybrew + brew install rust
    # ... Git clone harmonybrew + ln -sf brew + brew install rust ...

    raise Exception("cargo still not found after brew install rust")

def _add_path(self, p):
    os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

def _setup_cargo_mirror(self, home):
    """Configure USTC crates.io mirror."""
    cargo_dir = os.path.join(home, ".cargo")
    config_path = os.path.join(cargo_dir, "config.toml")
    if os.path.isfile(config_path):
        return
    os.makedirs(cargo_dir, exist_ok=True)
    with open(config_path, "w") as f:
        f.write(
            '[source.crates-io]\n'
            'replace-with = "ustc"\n'
            '\n'
            '[source.ustc]\n'
            'registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"\n'
            '\n'
            '[net]\n'
            'git-fetch-with-cli = true\n'
            '\n'
            '[http]\n'
            'multiplexing = false\n'
        )
```

> ⚠️ **PATH 陷阱**: `shutil.which("cargo")` 返回后本方法直接 return，不会把 `~/.harmonybrew/bin` 加入 PATH。后续若用 `self.run("rustc ...")` 会在 conan shell 中找不到 `rustc`（Python 进程与 conan shell 的 PATH 不一致）。**解法**: 见 Step 3。

### Step 2: `_ensure_cc()`

确保 `cc` 命令在 PATH 中。`rustc` 在链接时需要调 `cc`（PATH 中的命令），不是读取 `CC` 环境变量。

```python
def _ensure_cc(self):
    """Ensure a C compiler/linker (cc) is available in PATH."""
    if shutil.which("cc"):
        return

    clang_path = self._find_clang()
    if not clang_path and shutil.which("brew"):
        self.run("brew install ohos-sdk")
        self.run("brew install llvm-gcc-compat")
        harmonybrew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if harmonybrew_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = harmonybrew_bin + os.pathsep + os.environ.get("PATH", "")
        clang_path = self._find_clang()

    if clang_path:
        os.environ["CC"] = clang_path
        os.environ["CXX"] = clang_path.replace("clang", "clang++")
        cc_bindir = os.path.join(self.source_folder, "._cc_bin")
        os.makedirs(cc_bindir, exist_ok=True)
        cc_link = os.path.join(cc_bindir, "cc")
        if not os.path.exists(cc_link):
            os.symlink(clang_path, cc_link)
        os.environ["PATH"] = cc_bindir + os.pathsep + os.environ.get("PATH", "")
    else:
        self.output.warning("No C compiler found; build may fail")

def _find_clang(self):
    """Locate clang binary. Returns path or None."""
    clang = shutil.which("clang")
    if clang:
        return clang
    import glob
    home = os.path.expanduser("~")
    for cellar in glob.glob(os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk", "*", "native", "llvm")):
        candidate = os.path.join(cellar, "bin", "clang")
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    candidate = os.path.join(home, ".harmonybrew", "bin", "clang")
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return None
```

**角色分工**:

| 包 | 作用 |
|----|------|
| `ohos-sdk` | 提供 `clang`/`clang++`/`ld.lld` + `libc++_shared` |
| `llvm-gcc-compat` | 提供 `cc` → `clang`、`gcc` → `clang` 等符号链接 |

### Step 3: `_fix_libstdcxx()`

`rustc` 默认给每个链接命令添加 `-lstdc++`，但 OHOS 只有 `libc++`。在 rustc sysroot target lib 目录（已在 linker 默认 `-L` 搜索路径中）写入转发脚本。

```python
def _fix_libstdcxx(self):
    """Redirect -lstdc++ → -lc++_shared in rustc sysroot target lib dir."""
    import subprocess
    rustc = shutil.which("rustc")          # 用 Python PATH，不是 self.run
    if not rustc:
        self.output.warning("rustc not found; -lstdc++ fix skipped")
        return
    try:
        result = subprocess.run([rustc, "--print", "sysroot"],
                                capture_output=True, text=True, check=True)
        sysroot = result.stdout.strip()
    except Exception as e:
        self.output.warning(f"Cannot determine rustc sysroot: {e}")
        return

    target = "aarch64-unknown-linux-ohos"
    lib_dir = os.path.join(sysroot, "lib", "rustlib", target, "lib")
    if not os.path.isdir(lib_dir):
        self.output.warning(f"rustc target lib dir not found: {lib_dir}")
        return

    so_file = os.path.join(lib_dir, "libstdc++.so")
    if not os.path.exists(so_file):
        with open(so_file, "w") as f:
            f.write("INPUT(-lc++_shared)\n")

    a_file = os.path.join(lib_dir, "libstdc++.a")
    if not os.path.exists(a_file):
        with open(a_file, "w") as f:
            f.write("INPUT(-lc++_static -lc++abi)\n")
```

### 手动修复（简单场景）

不写 conanfile.py 时，可直接命令行执行：

```bash
OHOS_LIB_DIR=$(find ~/.harmonybrew -path "*/llvm/lib/aarch64-linux-ohos" -type d | head -1)
echo 'INPUT(-lc++_shared)' > "$OHOS_LIB_DIR/libstdc++.so"
echo 'INPUT(-lc++_static -lc++abi)' > "$OHOS_LIB_DIR/libstdc++.a"
export RUSTFLAGS="-L $OHOS_LIB_DIR -C link-arg=-L$OHOS_LIB_DIR"
cargo build --release
```

## 验证

```bash
cargo build --release 2>&1 | grep "Finished"
```

## 关系
- **相似**: E050 (HMDFS symlink issue) — related but different root cause
- **原则**: P003 (platform compatibility)

## 来源
- 编译事件: ouch latest (2026-07-03 / 2026-07-06)
- 作者: Agent 80FE / AtomCode (deepseek-v4-flash)
