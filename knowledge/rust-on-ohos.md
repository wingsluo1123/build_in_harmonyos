# Rust 在 OHOS 上的 CI 构建准备

> 基于 `ouch` 适配实战（PR #1651）总结 · 2026-07-06

## 1. 前置条件：harmonybrew

所有工具链通过 harmonybrew 安装（rustup 不支持 HarmonyOS）。

```bash
# 安装 harmonybrew（CI 镜像未预装时）
git clone --depth=1 https://atomgit.com/Harmonybrew/brew.git ~/.harmonybrew/Homebrew
mkdir -p ~/.harmonybrew/bin
ln -sf ~/.harmonybrew/Homebrew/bin/brew ~/.harmonybrew/bin/brew
export PATH=~/.harmonybrew/bin:$PATH
```

## 2. 工具链安装

按顺序执行：

```bash
brew install rust            # Rust 工具链 (rustc/cargo)
brew install ohos-sdk        # C 编译器 (clang/ld.lld) + libc++
brew install llvm-gcc-compat # cc → clang 符号链接
```

## 3. 典型 conanfile.py 结构

```python
def build(self):
    # 步骤 1: 确保 Rust 工具链
    self._ensure_cargo()
    # 步骤 2: 确保 C 编译器 (cc) 在 PATH 中
    self._ensure_cc()
    # 步骤 3: 处理 -lstdc++ → -lc++_shared 适配
    self._fix_libstdcxx()

    os.environ["CARGO_TERM_PROGRESS_WHEN"] = "always"
    os.environ["CARGO_TERM_PROGRESS_WIDTH"] = "80"
    self.run("cargo build --release", cwd=self.source_folder)
```

## 4. 关键方法实现

### 4.1 `_ensure_cargo()` — 安装/发现 Rust

```python
def _ensure_cargo(self):
    # 1. shutil.which("cargo") → 已有则返回
    # 2. 检查 ~/.harmonybrew/bin/cargo
    # 3. 检查 ~/.cargo/bin/cargo
    # 4. brew install rust
```

> ⚠️ `shutil.which("cargo")` 返回后 `_ensure_cargo` 会直接 return，不会把 `~/.harmonybrew/bin` 加入 PATH。后续代码若有 `self.run("rustc ...")` 可能在 conan shell 中找不到 `rustc`。
>
> **解法**：用 `shutil.which("rustc")` 在 Python PATH 中查找，再用 `subprocess.run` 执行，不要用 `self.run`。

### 4.2 `_ensure_cc()` — 确保 `cc` 命令可用

```python
def _ensure_cc(self):
    # rustc 找的是 PATH 中的 cc 命令，不是 CC 环境变量
    if shutil.which("cc"):
        return
    # 1. 找 clang (PATH → Cellar → harmonybrew bin)
    # 2. brew install ohos-sdk + llvm-gcc-compat（兜底）
    # 3. 创建 cc → clang 符号链接加入 PATH
```

### 4.3 `_fix_libstdcxx()` — 处理 `-lstdc++` 链接失败

```python
def _fix_libstdcxx(self):
    # rustc 默认添加 -lstdc++，但 OHOS 使用 libc++
    # 解法：在 rustc sysroot target lib 目录写入转发脚本
    #
    # rustc --print sysroot  → ~/.harmonybrew/Cellar/rust/1.96.1
    # 写入目标路径:
    #   <sysroot>/lib/rustlib/aarch64-unknown-linux-ohos/lib/libstdc++.so
    # 内容: INPUT(-lc++_shared)
    #
    # 这个路径已在 linker 的默认 -L 搜索路径中，无需额外传参
    
    rustc = shutil.which("rustc")  # 用 Python PATH，不是 self.run
    result = subprocess.run([rustc, "--print", "sysroot"], ...)
    sysroot = result.stdout.strip()
    lib_dir = os.path.join(sysroot, "lib", "rustlib", "aarch64-unknown-linux-ohos", "lib")
    # 写入 libstdc++.so 转发脚本
```

## 5. 避坑清单

| # | 错误 | 原因 | 解法 |
|---|------|------|------|
| 1 | `"always" progress requires a width key` | 设置 `CARGO_TERM_PROGRESS_WHEN=always` 时缺 `width` | `CARGO_TERM_PROGRESS_WIDTH=80` |
| 2 | `linker 'cc' not found` | `rustc` 在 PATH 中找不到 `cc` 命令 | 创建 `cc → clang` 符号链接并加入 PATH（仅设 `CC` 环境变量无效） |
| 3 | `unable to find library -lstdc++` | OHOS 无 libstdc++（使用 libc++） | sysroot target lib 目录写入 `libstdc++.so → INPUT(-lc++_shared)` 转发脚本 |
| 4 | `self.run("rustc ...")` 找不到 rustc | Python 进程 PATH 与 conan shell PATH 不一致 | 用 `shutil.which("rustc")` + `subprocess.run()` 替代 `self.run()` |
| 5 | RUSTFLAGS 的 `-L` 参数不生效 | RUSTFLAGS 可能被忽略或截断 | 直接写入 sysroot lib 目录（已在 linker 默认搜索路径中） |

## 6. crates.io 镜像（国内 CI 必备）

```toml
# ~/.cargo/config.toml
[source.crates-io]
replace-with = "ustc"

[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"

[net]
git-fetch-with-cli = true

[http]
multiplexing = false
```

## 7. 环境变量速查

```bash
export PATH=~/.harmonybrew/bin:$PATH
export CC=clang          # 对 cc crate 有效（对 rustc 无效，但无害）
export CXX=clang++
export SSL_CERT_FILE=~/usr/local/ssl/cert.pem
export REQUESTS_CA_BUNDLE=~/usr/local/ssl/cert.pem
export CARGO_TERM_PROGRESS_WHEN=always
export CARGO_TERM_PROGRESS_WIDTH=80
```
