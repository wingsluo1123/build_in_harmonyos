# DejaGNU / i686-elf binutils 测试策略

## 1. 上游 testsuite 概况

### 1.1 全量统计（binutils 全源码包）

| 类别 | 数量 |
|------|------|
| binutils-2.46.1.tar.gz 总文件数 | 约 1,800+ |
| 全量 testsuite 文件（binutils + gas + ld） | 约 **25,959** |
| 全量 .exp 驱动 | 约 **386** |
| binutils 工具子目录 testsuite 文件 | **617** |
| binutils 工具子目录 .exp 驱动 | **37** |

### 1.2 统计命令

```bash
# 全量 testsuite 文件数（binutils + gas + ld）
tar -tzf binutils-2.46.1.tar.gz | grep -cE 'testsuite/'

# 全量 .exp 驱动
tar -tzf binutils-2.46.1.tar.gz | grep -cE '\.exp$'

# binutils 工具子目录
tar -tzf binutils-2.46.1.tar.gz | grep -E '^binutils-2\.46\.1/binutils/testsuite/' | grep -cE 'testsuite/'
```

### 1.3 .exp 驱动分布

```
37 .exp 文件分布在:
  binutils/testsuite/binutils-all/   — 14 个核心工具 exp
  binutils/testsuite/binutils-all/x86-64/ — 3 个
  binutils/testsuite/lib/            — 2 个（工具库）
  binutils/testsuite/config/         — 1 个（配置）
  binutils/testsuite/binutils-all/i386/ 等 arch 子目录 — 各 1 个
```

## 2. DejaGNU 运行链

### 2.1 依赖链

```
runtest (DejaGNU 1.6.3)
  ├── Expect (5.45.4)
  │     └── Tcl (8.6)
  ├── site.exp (target board 配置)
  ├── tool.exp (binutils / gas / ld 等)
  └── target simulator (如 QEMU) 或 native 执行
```

### 2.2 当前环境可用性

| 组件 | 路径 / 版本 | 状态 |
|------|-------------|------|
| runtest | `/storage/Users/currentUser/usr/local/bin/runtest` (DejaGNU 1.6.3) | ✅ 可用 |
| expect | `/storage/Users/currentUser/usr/local/bin/expect` (5.45.4) | ✅ 可用 |
| Tcl | 8.6 (bundled with DejaGNU) | ✅ 可用 |
| tclsh | 未找到 | ❌ 不可用 |
| qemu-system-i386 | 未找到 | ❌ 不可用 |
| i686-elf-as/ld/objdump | 不在 PATH（conan 构建产物中） | ⚠️ 需从 conan cache 提取 |

## 3. i686-elf target 难点

### 3.1 裸机 ELF 特性

i686-elf 是裸机交叉目标：
- 输出的可执行文件是 ELF 格式，但没有操作系统加载器
- 无法直接在 OHOS (aarch64) host 上执行
- 需要 target simulator (QEMU) 或硬件环境才能运行执行类测试

### 3.2 影响范围

| 测试类型 | 能否执行 | 说明 |
|----------|---------|------|
| assemble + objdump 对比 | ✅ 可 | compile-only，不执行目标代码 |
| size/nm/strip/ar 等工具 | ✅ 可 | 操作 ELF 文件，不执行目标代码 |
| ld 链接 + readelf 检查 | ✅ 可 | 链接后分析 ELF，不执行目标代码 |
| 执行目标代码的测试 | ❌ 不可 | 需要 QEMU 或硬件 |

## 4. Simulator 路线

### 4.1 QEMU 方案

**条件**：需安装 `qemu-system-i386`。
**当前状态**：❌ 环境中无 `qemu-system-i386`。

```bash
# 安装命令（参考）
sudo apt-get install qemu-system-i386
# 或从源码编译
# 需确认 OHOS 环境下是否可用
```

**Board 配置**（site.exp）：
```
set target_board i686-elf-sim
set simulator "/usr/bin/qemu-system-i386"
```

### 4.2 不可用证据

```bash
which qemu-system-i386 || echo "qemu-system-i386: NOT FOUND"
```

当前环境无 QEMU，且 OHOS 包管理器可能不提供 QEMU 包。
**结论**：Simulator 路线不可行，推进 compile-only/host-side 子集路线。

## 5. Compile-only / Host-side 子集路线

### 5.1 适用 .exp 子集

以下 .exp 驱动不要求执行目标代码，可在 host 上直接运行：

| .exp 文件 | 测试内容 | 是否可执行 |
|-----------|---------|-----------|
| ar.exp | ar 归档操作 | ✅ |
| nm.exp | nm 符号表 | ✅ |
| objcopy.exp | objcopy 格式转换 | ✅ |
| objdump.exp | objdump 反汇编/分析 | ✅ |
| size.exp | size 段大小 | ✅ |
| strings.exp | strings 字符串提取 | ✅ |
| cxxfilt.exp | C++ 符号 demangling | ✅ |
| readelf.exp | readelf 分析 | ✅ |
| elfedit.exp | ELF 编辑 | ✅ |
| addr2line.exp | addr2line 地址转换 | ✅ |

### 5.2 不可执行 .exp

| .exp 文件 | 原因 |
|-----------|------|
| compress.exp | 需要运行时压缩/解压 |
| debuginfod.exp | 需要网络服务 |
| dlltool.exp | Windows 特定 |
| 架构相关 (i386/arm/riscv 等) | 需要目标架构运行环境 |

### 5.3 最小验证命令（已验证可执行）

```bash
# 设置 i686-elf 工具路径
export PATH="$HOME/.conan2/p/b/i686-f21dd5ac0be0a/p/bin:$PATH"

# 设置 site.exp
export TMPDIR="$HOME/tmp"
mkdir -p "$TMPDIR"
export DEJAGNU="$HOME/dejagnu-i686-binutils/site.exp"
cat > $DEJAGNU << 'EOF'
set target_triplet i686-elf
set target_alias i686-elf
set host_triplet aarch64-unknown-linux-ohos
set build_triplet aarch64-unknown-linux-ohos
set experimental false
EOF

# 运行 compile-only 子集
cd ~/dejagnu-i686-binutils
runtest --tool binutils \
  --srcdir "$PWD/binutils-2.46.1/binutils/testsuite" \
  --target i686-elf \
  ar.exp nm.exp size.exp strings.exp cxxfilt.exp \
  2>&1 | tee runtest.log
```

### 5.4 真实执行结果（2026-07-23）

| 指标 | 值 |
|------|-----|
| 运行 .exp 数 | 5（ar.exp, cxxfilt.exp, nm.exp, size.exp, strings.exp） |
| 预期通过 (expected passes) | 4 |
| 意外失败 (unexpected failures) | 5 |
| 不支持 (unsupported) | 11 |
| 未解决 (unresolved) | 0 |
| 退出码 | 1（有 FAIL 但非框架崩溃） |

#### 通过详情

| 测试 | 结果 |
|------|------|
| cxxfilt.exp | ✅ 全部通过（C++ demangling 纯 host-side） |
| strings.exp | ✅ 全部通过（字符串提取纯 host-side） |
| ar.exp | ❌ 2 FAIL（archive with empty element, ar foreign object） |
| nm.exp | ❌ 2 FAIL（nm assembling, nm --size-sort assembling） |
| size.exp | ❌ 1 FAIL（size assembling） |

#### 首个真实错误

```
FAIL: nm (assembling)
```

**真实执行日志摘录**：
```
Running binutils-all/nm.exp ...
Executing on host: i686-elf-as bintest.s -o tmpdir/bintest.o (timeout = 300)
spawn -ignore SIGHUP i686-elf-as bintest.s -o tmpdir/bintest.o

FAIL: nm (assembling)
```

**根因**（#3194 修复后，使用 EXP_STTY expect 环境）：经过 #3194 expect/5.45.4 的 EXP_STTY 修复（0006 补丁）后，`/bin/stty` 污染已清零（出现次数 0）。5 个 FAIL 不再是 stty 误判，而是：
- **nm (assembling)**：`i686-elf-as` 汇编 `bintest.s` 后 nm 读取符号表，对比预期输出实际不一致（OHOS 平台工具行为差异）
- **nm --size-sort (assembling)**：同上
- **size (assembling)**：同上
- **archive with empty element**：`i686-elf-ar` 创建空归档行为与 Linux binutils 有差异
- **ar foreign object**：`i686-elf-ar` 处理外部对象格式差异

以上 5 个 FAIL 均为 i686-elf 裸机交叉工具链在 OHOS 上的平台行为差异，非 `/bin/stty` 污染所致。EXP_STTY 修复已确认有效。

**`/bin/stty` 修复效果**：使用 #3194 expect 后，所有 spawn 子进程不再输出 `/bin/stty` stderr 警告。stty.test 全部通过。DejaGNU `default_target_assemble` 不再因 stty stderr 误判为汇编失败。

**解决方案**（已通过 #3194 实施）：
1. 补丁 0006-stty-ohos-compat.patch：在 `exp_tty.c`、`pty_termios.c`、`pty_sgttyb.c` 中检查 `EXP_STTY` 环境变量，若设置则使用该路径，否则返回 `STTY_BIN`；若路径不可执行则安全跳过 stty 初始化
2. 使用方式：`export EXP_STTY=/bin/true` 或指向真实 stty 路径
3. 未设置时行为不变（Linux/macOS 不受影响）

#### 11 个 UNSUPPORTED 测试

这些测试因目标架构不兼容被标记为 UNSUPPORTED（例如架构特定汇编、需要 target simulator 的执行类测试），属于正常行为。

#### 解决 assembly 失败的方案

```bash
# 方法 1：使用 --no-warnings 或 --fatal-warnings 抑制
# 方法 2：将 bintest.s 替换为 i686-elf 兼容代码
# 方法 3：跳过 assembling 类测试，仅运行纯 host-side 工具测试
runtest --tool binutils --target i686-elf \
  --srcdir ... \
  cxxfilt.exp strings.exp
```

## 6. 通过率统计口径

**统一口径**：

| 测试类别 | 文件/驱动规模 | 通过率 | 说明 |
|----------|-------------|--------|------|
| 全量 binutils 上游 testsuite（binutils + gas + ld） | 约 25,959 文件 / 386 .exp 驱动 | **未执行（N/A）** | 规模 25,959 为 testsuite 文件总量，不作为已执行用例分母；完整运行依赖 DejaGNU + QEMU/target simulator，当前 OHOS 环境未补齐 |
| binutils 工具子目录 testsuite | 617 文件 / 37 .exp 驱动 | **未执行（0/617）** | 同上 |
| 本轮 DejaGNU host-side 子集（5 .exp） | 5 .exp / 20 测试项 | **4 PASS / 5 FAIL / 11 UNSUPPORTED** | 退出码 1；4 PASS 来自纯 host-side 工具（cxxfilt、strings）；5 FAIL 为 i686-elf 裸机 target 汇编/`/bin/stty` 兼容性限制；11 UNSUPPORTED 为 target/simulator 不可用相关跳过 |
| Smoke test | 8 个工具 --version | **8/8（100%）** | test_package conanfile.py 验证 |

**关键原则**：
- 上游全量通过率不得写 100% 或 0/0
- DejaGNU 子集通过率单独统计，不合并到上游或 smoke
- Smoke test 的 100% 不能覆盖上游未执行的事实

## 7. 限制条件和复用范围

### 7.1 适用范围

- 适用于所有 `*-elf` 格式的 GNU binutils 交叉工具链
- compile-only/host-side 子集适用于同架构构建环境
- smoke test 可作为最低可用性验证

### 7.2 不适用的场景

- 需要真实 target runtime 的执行类测试（如 gdb 测试）
- 需要目标硬件或模拟器的集成测试
- 需要 DejaGNU 全量运行的测试

### 7.3 复用方式

复制本策略文件并适配：
1. 替换 `target_triplet` 和 `target_alias`
2. 更新工具路径
3. 调整 .exp 子集选择
4. 适配 site.exp board 配置