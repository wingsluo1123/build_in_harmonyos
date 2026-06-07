# graphviz 15.0.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：`ohc-run.py init-build graphviz 15.0.0`
2. 设置环境变量：
   - TMPDIR=/storage/Users/currentUser/tmp
   - CC=clang, CXX=clang++
   - LD_LIBRARY_PATH 包含 OHOS SDK 的 llvm/lib 目录（解决 lld 依赖 libxml2 问题）
3. 执行 configure：`./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | clang 编译器链接失败，lld 需要 libxml2.so.16 | OHOS SDK 的 lld 动态链接到 libxml2，但默认 LD_LIBRARY_PATH 不包含 SDK lib 目录 | 添加 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` 到 LD_LIBRARY_PATH |
| 2 | configure 失败：`sort: stat failed: -: Permission denied` | SELinux 平台限制，无法访问管道临时文件 | **平台限制，无法绕过** |
| 3 | configure 失败：`can't create ./conf*/subs1.awk: Permission denied` | SELinux 平台限制，configure 脚本无法创建临时文件 | **平台限制，无法绕过** |

## 平台限制说明

**SELinux 限制**：
- configure 脚本内部使用管道和临时文件（如 `sort -`），被 SELinux 阻止
- 无法通过环境变量 TMPDIR/TEMP/TMP 绕过，因为这是 configure 脚本的内部实现
- 按照 SKILL.md §7 Gotchas 指导，已尝试使用 $TMPDIR，但仍受限于 configure 内部管道操作
- 此限制影响所有基于 autotools 的软件编译

**建议方案**：
- 等待平台 SELinux 策略更新
- 或使用其他构建系统（cmake/meson）替代 autotools

## 源码修改

无补丁生成，编译在 configure 阶段失败。

## 依赖版本

- clang 15.0.4 (OHOS SDK)
- libxml2 2.15.3（已安装，但通过 OHOS SDK 内置版本解决 lld 依赖）

## 验证结果

```bash
# configure 失败，无法继续编译
configure: error: C compiler cannot create executables
sort: stat failed: -: Permission denied
```

## 交付物

无编译产物。

## 注意事项

- **R10 铁律**：临时文件应使用 $TMPDIR，但 configure 内部管道操作不受此控制
- 此问题属于 E002 类错误模式的延伸，建议记录为新的知识条目
## E011/E080 解决方案应用记录（2026-05-30 第三轮修复）

### 问题：libtool HMDFS 兼容性
- 错误：`libltdlcS.c:39:39: error: use of undeclared identifier 'dlopen_LTX_get_vtable'`
- 根因：libtool 在 HMDFS 上生成预加载符号表时符号定义缺失

### 应用方案
1. **禁用 LT_DLPREOPEN**：修改 libltdl/Makefile
   - `sed -i 's/LT_DLPREOPEN = -dlpreopen dlopen.la/LT_DLPREOPEN = /g' Makefile`
   - 成功编译 libltdl

2. **修复 UTIL_API 可见性**：修改 lib/util/api.h
   - 添加 PUBLIC 定义：`#define PUBLIC __attribute__((visibility("default")))`
   - 修改 UTIL_API 为 PUBLIC，解决静态库符号隐藏问题

3. **修复 libwebp 依赖**：修改 plugin/webp/Makefile
   - 添加 `-lsharpyuv` 到 WEBP_LIBS

4. **修复 gvpr 依赖**：修改 cmd/gvpr/Makefile
   - 添加 `libexpr_C.la`, `libast_C.la`, `libsfio_C.la` 等依赖

### 结果
- ✅ Configure 成功（E011 方案）
- ✅ Make 成功（禁用 LT_DLPREOPEN + 修复可见性 + 修复依赖）
- ✅ DESTDIR 安装成功
- ❌ 本地运行验证失败（运行时库加载问题）

### 运行时问题
- dot_builtins 运行时找不到共享库（libgvc.so.7 等）
- fontconfig 符号问题（cairo 需要 fontconfig）
- 这是 HMDFS 运行时限制，不影响静态编译产物

### 源码修改记录（R6 铁律）
1. `libltdl/Makefile`：移除 LT_DLPREOPEN
2. `lib/util/api.h`：添加 PUBLIC 定义，修改 UTIL_API
3. `plugin/webp/Makefile`：添加 sharpyuv 依赖
4. `cmd/gvpr/Makefile`：添加完整的静态库依赖链

### 知识沉淀
- HMDFS 上 libtool 预加载机制（LT_DLPREOPEN）无法正常工作
- 静态库符号可见性问题：PRIVATE 符号在跨库链接时会隐藏
- autotools 项目在 HMDFS 上需要手动修复依赖传播


## 预编译包限制说明（2026-05-30 第四轮修复尝试）

### 发现的问题

1. **符号链接缺失**
   - 预编译包中有 `libgvc.so.7.0.10`，但缺少 `libgvc.so.7` 符号链接
   - 缺少 `dot` -> `dot_builtins` 符号链接
   - 缺少插件库符号链接

2. **系统打包限制**
   - HarmonyOS 系统限制导致 tar 无法读取符号链接文件
   - 所有打包工具（tar、pax、Python tarfile）都报 "Permission denied"
   - 无法在当前环境下创建包含符号链接的预编译包

3. **外部依赖库缺失**
   - libfontconfig.so.1（cairo 需要）
   - libpangocairo-1.0.so.0
   - libpango-1.0.so.0
   - libpcre2-8.so.0
   - libffi.so.8
   - libc++_shared.so

### 建议解决方案

1. 在 OpenHarmony 编译服务器（无 SELinux 限制）上重新打包
2. 补充缺失的外部依赖库到 lib/external 目录
3. 使用相对路径符号链接（$ORIGIN）

### 当前状态

- 编译产物已生成（status: built）
- 符号链接模板已保存（~/tmp/test-graphviz-pkg/）
- 需要在无限制环境重新打包后才能 published


## ELF 签名问题发现（2026-05-30 最终分析）

### 问题：动态链接器无法加载库
**根因**：P-SIGN-001 - HarmonyOS 动态链接器校验 ELF 签名

**解决方案**：
1. 移除旧签名：`llvm-objcopy --remove-section .codesign <file>`
2. 重新签名：`binary-sign-tool sign -inFile <file> -outFile <file> -selfSign 1`
3. 签名后动态链接器可以加载库 ✅

### 新问题：缺少 soft-float 符号
**错误**：`__subtf3: symbol not found`
**根因**：编译时未链接 compiler-rt 运行时库
**符号类型**：128-bit floating point 运算（soft-float）
**影响**：libgvplugin_neato_layout.so.8 等插件库

### 解决方案
重新编译需要添加编译选项：
- `-rtlib=compiler-rt` 或
- 链接包含 soft-float 函数的库

### 当前状态
- 编译产物已生成 ✅
- ELF 签名已修复 ✅
- 动态链接可加载 ✅
- 运行时符号缺失 ❌（需要重新编译）

### 建议
在 OpenHarmony 编译服务器上重新编译，使用正确的运行时库配置。


---

## 第五轮编译尝试（2026-05-30 11:28）

### 目标
解决运行时 `__subtf3` 符号缺失问题，重新编译并添加 compiler-rt 运行时库。

### 问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | config.guess 不识别 OHOS | 缺少 OHOS 平台检测逻辑 | **修改 config.guess**：添加 OHOS 检测（通过 `uname -s` 和目录 `/data/service/hnp/ohos-sdk.org`） | ✅ |
| 2 | config.sub 不接受 `aarch64-unknown-linux-ohos` | `linux-ohos` Kernel-OS 组合未定义 | **修改 config.sub**：在 kernel-os 验证中添加 `linux-ohos*` | ✅ |
| 3 | clang 链接失败：lld 需要 libxml2.so.16 | OHOS SDK 的 lld 动态链接 libxml2，但动态链接器无法加载 | **使用 GNU ld**：添加 `-fuse-ld=bfd` 到 CFLAGS/LDFLAGS | ✅ |
| 4 | configure 无法运行编译测试程序 | SELinux 限制：编译的测试程序无法执行 | **平台限制**：HMDFS/SELinux 阻止执行 | ❌ |

### config.guess 修改详情

在文件开头添加 OHOS 平台检测（跳过临时文件创建）：

```bash
# OpenHarmony detection - skip temp file creation (SELinux compatible)
UNAME_SYSTEM=`(uname -s) 2>/dev/null` || UNAME_SYSTEM=unknown
if test "$UNAME_SYSTEM" = "OHOS" || test -d /data/service/hnp/ohos-sdk.org; then
    UNAME_MACHINE=`(uname -m) 2>/dev/null` || UNAME_MACHINE=aarch64
    echo "${UNAME_MACHINE}-unknown-linux-ohos"
    exit 0
fi
```

**关键点**：
- 通过 `uname -s` 检测 OHOS 系统
- 或通过 OHOS SDK 目录存在性检测
- 直接输出平台类型，避免创建临时文件（SELinux 兼容）
- 返回格式：`aarch64-unknown-linux-ohos`

### config.sub 修改详情

修改两个位置：

1. **OS 列表**：在有效 OS 列表中添加 `ohos*`
   ```bash
   gnu* | android* | bsd* | ... | ohos* | ...
   ```

2. **Kernel-OS 组合验证**：添加 `linux-ohos*`
   ```bash
   linux-gnu* | linux-dietlibc* | ... | linux-ohos* | ...
   ```

### 编译器链接器配置

**问题**：OHOS SDK 的 lld 动态链接到 libxml2.so.16，但动态链接器无法加载该库（即使 LD_LIBRARY_PATH 已设置）。

**解决方案**：使用 GNU ld（bfd）代替 lld
```bash
export CFLAGS="-fPIC -O2 -rtlib=compiler-rt -fno-exceptions -fuse-ld=bfd"
export LDFLAGS="-fuse-ld=bfd -rtlib=compiler-rt"
```

**验证结果**：
- ✅ clang 可以使用 `-fuse-ld=bfd` 编译简单程序
- ✅ 生成的可执行文件可以执行（需要 ELF 签名）

### 编译流程尝试

```bash
export TMPDIR=$HOME/tmp
export LD_LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib:/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib"
export CC=clang
export CXX=clang++
export CFLAGS="-fPIC -O2 -rtlib=compiler-rt -fno-exceptions -fuse-ld=bfd"
export LDFLAGS="-fuse-ld=bfd -rtlib=compiler-rt"

./configure --prefix=/storage/Users/currentUser/usr/local
```

**结果**：
- ✅ 平台识别成功：`aarch64-unknown-linux-ohos`
- ✅ 编译器测试成功：生成 a.out
- ❌ 执行测试程序失败：`configure: error: cannot run C compiled programs`
- 错误原因：SELinux 阻止执行编译的程序

### SELinux 平台限制

**现象**：
- configure 编译的测试程序无法执行
- 错误：`cannot run C compiled programs`

**根因**：
- HMDFS/SELinux 策略阻止执行动态生成的 ELF 文件
- 这是 autotools configure 的标准流程，无法绕过

**影响**：
- 所有基于 autotools 的软件在当前环境无法完成 configure
- configure 必须执行编译测试程序来验证编译器功能

**建议**：
- 在 OpenHarmony 编译服务器（无 SELinux 限制）上重新编译
- 或等待平台 SELinux 策略更新

### 待应用的完整编译配置

在无 SELinux 限制的环境中，使用以下配置重新编译：

```bash
export TMPDIR=$HOME/tmp
export CC=clang
export CXX=clang++
export CFLAGS="-fPIC -O2 -rtlib=compiler-rt -fno-exceptions -fuse-ld=bfd"
export LDFLAGS="-fuse-ld=bfd -rtlib=compiler-rt"

./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos
make -j2
make install DESTDIR=$TEST_PREFIX

# 应用 E011/E080 补丁（如需要）
# 禁用 LT_DLPREOPEN, 修复 UTIL_API 可见性, 修复依赖传播

# 完成收尾
python3 $SKILL_ROOT/scripts/ohc-run.py package graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py finish graphviz 15.0.0 published
```

### 知识沉淀建议

本轮发现的新知识模式：

1. **E081: config.guess/config.sub OHOS 平台识别**
   - 问题：GNU config 不识别 OHOS
   - 解决：添加 uname -s 和目录检测逻辑
   - 适用：所有 autotools 项目

2. **E082: OHOS SDK lld libxml2 依赖问题**
   - 问题：lld 动态链接 libxml2，但无法加载
   - 解决：使用 `-fuse-ld=bfd` 绕过
   - 适用：使用 OHOS SDK clang 的所有编译

### 当前状态

- config.guess/config.sub 已修复 ✅
- 编译器链接问题已解决 ✅
- compiler-rt 运行时库配置已准备 ✅
- configure 因 SELinux 限制无法完成 ❌
- 需要在无限制环境重新编译 ⚠️
---

## 第六轮质量审核修复（2026-05-31）

### 问题：知识图谱引用冲突
- E081/E082/E083 已有正式条目（非 OHOS 平台相关）
- 正确引用：E007（config.guess OHOS 识别）

### 修复内容
1. 更新 manifest.yaml 知识引用（E007, E008）
2. 删除 draft 目录中冲突的草稿（E081-draft-*, E082-draft-*, E083-draft-*）
3. 创建 test-report.md 记录测试跳过原因
4. 补充 compile_date 字段

---

## 状态降级说明（2026-05-31 13:45）

### 质量门禁判定

| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | ✅ PASS | 有编译产物 |
| G2 功能可用性 | ❌ FAIL | 运行时库加载失败（缺少 __subtf3 等 soft-float 符号） |
| G3 可移植性 | ⚠️ WARN | SELinux 平台限制阻塞编译流程 |
| G4 档案完整性 | ✅ PASS | manifest 完整，文档齐全 |

### 降级原因

根据 SKILL.md 质量门禁标准：
- **G2 功能可用性 FAIL** = 编译失败
- 运行时无法正常使用（库加载失败）
- SELinux 限制导致编译流程不完整

因此将状态从 built 降级为 **failed**。

**失败原因**:
1. SELinux/HMDFS 平台限制阻塞 configure 流程（无法执行测试程序）
2. 运行时库加载失败（缺少 __subtf3 等 soft-float 符号）
3. G2 功能可用性门禁 FAIL

**建议方案**:
在无 SELinux 限制的 OpenHarmony 编译服务器上使用以下配置重新编译：

```bash
export TMPDIR=$HOME/tmp
export CC=clang
export CXX=clang++
export CFLAGS="-fPIC -O2 -rtlib=compiler-rt -fno-exceptions -fuse-ld=bfd"
export LDFLAGS="-fuse-ld=bfd -rtlib=compiler-rt"

./configure --prefix=$DEFAULT_PREFIX
make -j2
make check
make install DESTDIR=$TEST_PREFIX

# 完成收尾
python3 $SKILL_ROOT/scripts/ohc-run.py package graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py finish graphviz 15.0.0 published
```

**保留价值**:
虽然编译失败，但归档保留以下价值：
1. config.guess/config.sub OHOS 平台检测方案（E007）
2. SELinux/HMDFS 平台限制记录（E008）
3. compiler-rt 运行时库配置方案
4. 详细的失败分析供后续参考
---

## 第七轮编译尝试（2026-05-31 16:15）

### 目标
遵守 R15 铁律，不使用 --build/--host/--target 参数，使用正确的 config.guess/config.sub 补丁重新编译。

### 问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | config.guess 不识别 OHOS | 缺少 HarmonyOS 检测分支 | **应用 0002-config.guess-ohos.patch** | ✅ |
| 2 | config.sub 不接受 ohos-linux | kernel-OS 组合验证缺失 | **应用 0003-config.sub-ohos.patch** | ✅ |
| 3 | configure 成功识别平台 | 补丁有效 | `checking build system type... aarch64-unknown-linux-ohos` | ✅ |
| 4 | config.status 创建临时文件失败 | SELinux/HMDFS 平台限制 | **无法绕过** | ❌ |

### 关键成果

**✅ config.guess/config.sub 补丁验证成功**：
- 使用 patch-autotools-ohos.pl 脚本自动补丁
- 手动修复 config.sub kernel-OS 组合验证（添加 linux-ohos*）
- configure 正确识别平台：`aarch64-unknown-linux-ohos`
- 大部分检测通过，直到 config.status 阶段

**❌ SELinux/HMDFS 平台限制阻塞**：
- 错误：`./confKbMOGD/subs1.awk: Permission denied`
- 根因：HMDFS/SELinux 策略阻止创建和执行临时文件
- 这是 autotools configure 的标准流程，无法绕过

### 生成的补丁文件

1. **0002-config.guess-ohos.patch**：添加 HarmonyOS 系统识别
2. **0003-config.sub-ohos.patch**：添加 ohos-linux triplet 和 kernel-OS 组合验证

### 验证平台识别

```bash
$ ./config/config.guess
aarch64-unknown-linux-ohos

$ ./config/config.sub aarch64-unknown-linux-ohos
aarch64-unknown-linux-ohos
```

### 知识沉淀

- **R15 铁律遵守**：不使用 --build/--host/--target 参数 ✅
- **E007 解决方案验证**：patch-autotools-ohos.pl + 手动修复 kernel-OS 组合 ✅
- **E008 平台限制确认**：SELinux/HMDFS 阻塞 configure 流程 ❌

### 建议

在无 SELinux 限制的 OpenHarmony 编译服务器上使用以下补丁重新编译：

```bash
export TMPDIR=$HOME/tmp
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig

# 应用补丁
patch -p1 < archives/g/graphviz/15.0.0/patches/0002-config.guess-ohos.patch
patch -p1 < archives/g/graphviz/15.0.0/patches/0003-config.sub-ohos.patch

./configure --prefix=$DEFAULT_PREFIX
make -j2
make check
make install DESTDIR=$TEST_PREFIX

# 完成收尾
python3 $SKILL_ROOT/scripts/ohc-run.py package graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py finish graphviz 15.0.0 published
```
---

## 第八轮编译尝试（2026-05-31 16:30）

### 目标
遵守 R15 铁律，使用 `-fuse-ld=bfd` 绕过 lld libxml2 依赖问题，重新编译。

### 关键发现

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | lld 需要 libxml2.so.16 | OHOS SDK 的 lld 动态链接 libxml2，但动态链接器无法加载 | **使用 `-fuse-ld=bfd`** | ✅ |
| 2 | config.guess 正确识别 OHOS | 已应用 OHOS 平台检测补丁 | 无需额外修改 | ✅ |
| 3 | 编译器测试程序无法执行 | HMDFS/SELinux 阻止执行动态生成的 ELF 文件 | **平台限制，无法绕过** | ❌ |

### 编译流程验证

1. **编译器可以编译**：使用 `-fuse-ld=bfd` 绕过 lld libxml2 问题 ✅
   ```bash
   clang -fPIC -O2 -fuse-ld=bfd -o test test.c  # 成功生成 a.out
   ```

2. **编译产物无法执行**：SELinux/ELF 签名验证阻止 ❌
   ```
   ./conftest: Permission denied (RC=126)
   ```

3. **ELF 签名后仍无法执行**：HMDFS 文件系统限制 ❌
   ```bash
   binary-sign-tool sign -inFile test -outFile test_signed -selfSign 1
   ./test_signed: Permission denied (RC=126)  # 仍无法执行
   ```

### 根因分析

**E008 平台限制（HMDFS/SELinux）**：
- HMDFS 文件系统的 SELinux 策略阻止执行动态生成的 ELF 文件
- 这是 autotools configure 的标准流程（必须执行编译测试程序）
- 无法通过环境变量或签名绕过

### 与之前失败的对比

| 轮次 | 失败原因 | 是否遵守 R15 |
|------|---------|------------|
| 第五轮 | 使用 `--build=aarch64-unknown-linux-ohos` | ❌ 违反 R15 |
| 第六轮 | SELinux 限制 + 运行时库加载失败 | ✅ |
| 第七轮 | config.status 创建临时文件失败 | ✅ |
| 第八轮 | 编译测试程序无法执行（即使已签名） | ✅ |

### 结论

graphviz 15.0.0 在当前 HMDFS/SELinux 环境下无法编译：
- autotools configure 必须执行编译测试程序
- HMDFS 文件系统 SELinux 策略阻止执行动态生成的 ELF 文件
- 这是 E008 平台限制，不是软件本身的问题

### 建议方案

在无 SELinux 限制的 OpenHarmony 编译服务器上使用以下配置重新编译：

```bash
export TMPDIR=$HOME/tmp
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$HOME/usr/local/share/pkgconfig"
export CC=clang
export CXX=clang++
export CFLAGS="-fPIC -O2"
export LDFLAGS="-fuse-ld=bfd"

./configure --prefix=$DEFAULT_PREFIX  # 不使用 --build/--host/--target（遵守 R15）
make -j2
make check
make install DESTDIR=$TEST_PREFIX

# 完成收尾
python3 $SKILL_ROOT/scripts/ohc-run.py package graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build graphviz 15.0.0
python3 $SKILL_ROOT/scripts/ohc-run.py finish graphviz 15.0.0 published
```

### 知识沉淀

**成功验证的方案**：
1. **E007**：config.guess/config.sub OHOS 平台识别 ✅
2. **使用 GNU ld 绕过 lld libxml2 问题** ✅

**发现的平台限制**：
1. **E008**：HMDFS/SELinux 阻止执行动态生成的 ELF 文件
   - 影响：所有 autotools 项目无法完成 configure
   - 适用：在 HMDFS 文件系统上的所有编译
---

**编译结束**: 2026-06-07 13:12
**最终状态**: failed
