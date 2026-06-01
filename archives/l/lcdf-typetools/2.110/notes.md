# lcdf-typetools 2.110 — 编译笔记

> 编译日期：2026-06-01  
> 编译状态：published  
> 编译器：clang/clang++ (OpenHarmony aarch64)

---

## 编译配置

| 配置项 | 值 |
|--------|-----|
| 构建系统 | autotools |
| configure 选项 | `--prefix=$DEFAULT_PREFIX --without-kpathsea` |
| CC | clang |
| CXX | clang++ |
| CFLAGS | -fPIC -O2 |
| DESTDIR | $TEST_PREFIX |
| make -j | 1 |

---

## 编译过程中遇到的问题与解决

### 问题1：kpathsea 依赖缺失

- **症状**：configure 报错 "I can't find the kpathsea library"
- **根因**：kpathsea 是 TeX 排版系统的路径搜索库，lcdf-typetools 中的 otftotfm 组件可选依赖它，但 OpenHarmony 环境没有 kpathsea
- **处理**：使用 `--without-kpathsea` 禁用此可选依赖，不影响核心字体工具功能
- **影响**：otftotfm 的 kpathsea 模式不可用，其余 10 个工具完全不受影响
- **知识层**：L3 软件特性

### 问题2：HMDFS umask 077 导致 config.status 失败

- **症状**：`./config.status[774]: can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**：HMDFS（鸿蒙分布式文件系统）上，configure/config.status 使用 `(umask 077 && mktemp -d "./confXXXXXX")` 创建临时目录，0700 权限导致 shell 子脚本无法在其中创建文件
- **修复**：补丁 0001-configure.patch，将 `(umask 077 && mktemp -d)` 改为 `(mktemp -d)`，将 `(umask 077 && mkdir)` 改为 `(mkdir)`（+2/-2 行）
- **影响**：所有使用 Autotools 构建系统的项目在 HMDFS 上都可能遇到此问题
- **知识层**：L1 平台真理（已录入知识图谱 E100）

### 问题3：GNU cat/sort 无法写入 stdout（管道限制）

- **症状**：`sort: stat failed: -: Permission denied` 和 `cat: standard output: Permission denied`
- **根因**：HMDFS 平台上 GNU coreutils 的 cat 和 sort 无法处理 stdin→stdout 管道操作（平台安全限制）
- **修复**：
  - cat：创建 `~/usr/local/bin/cat → /bin/cat` symlink（使用 toybox 版本替代 GNU cat）
  - sort：创建 wrapper 脚本，先将 stdin 写入临时文件，再用 GNU sort 处理文件
  - head：创建 `~/usr/local/bin/head → /bin/head` symlink（使用 toybox 版本）
- **影响**：所有需要 stdin→stdout 管道的构建过程均受影响
- **知识层**：L1 平台真理（已录入知识图谱 E100）

### 问题4：PATH 缺少 /bin 导致 configure 中 rm/ls 找不到

- **症状**：configure 执行中 `rm: command not found`、`ls: command not found`
- **根因**：PATH 环境变量缺少 /bin 目录（toybox 工具所在位置）
- **修复**：在 PATH 中添加 /bin 和 $DEFAULT_PREFIX/bin
- **影响**：所有构建过程都需要 PATH 包含 /bin

---

## 产物清单

### 二进制文件（11个）

| 二进制 | 大小 | 功能 |
|--------|------|------|
| cfftot1 | 469,504 bytes | CFF → Type 1 字体转换 |
| mmafm | 297,472 bytes | 多主字体 AFM 生成 |
| mmpfb | 383,488 bytes | 多主字体 PFB 生成 |
| otfinfo | 612,864 bytes | OpenType 字体信息查看 |
| otftotfm | 883,200 bytes | OpenType → TeX 字体度量转换 |
| t1dotlessj | 363,008 bytes | Type 1 无点 j 字体生成 |
| t1lint | 326,144 bytes | Type 1 字体检查 |
| t1rawafm | 322,048 bytes | Type 1 → AFM 转换 |
| t1reencode | 354,816 bytes | Type 1 字体重编码 |
| t1testpage | 342,528 bytes | Type 1 测试页生成 |
| ttftotype42 | 403,968 bytes | TrueType → Type 42 转换 |

### 静态库（2个，内嵌至各二进制，不单独安装）

- liblcdf.a
- libefont.a

### Man pages（11个）

cfftot1.1, mmafm.1, mmpfb.1, otfinfo.1, otftotfm.1, t1dotlessj.1, t1lint.1, t1rawafm.1, t1reencode.1, t1testpage.1, ttftotype42.1

### 数据文件（3个）

7t.enc, glyphlist.txt, texglyphlist.txt

---

## make check 结果

项目无上游测试套件，所有子目录的 check 目标均为空。额外执行了以下验证：
- 11 个二进制 --version 验证：全部正确输出版本 2.110
- 11 个二进制 --help 验证：全部正常退出 (exit code 0)
- ELF 格式检查：全部为 ELF64 AArch64 PIE，含 .note.ohos.ident 段
- 动态依赖检查：仅依赖 libc++_shared.so 和 libc.so

---

**编译开始**：2026-06-01  
**编译结束**：2026-06-01  
**最终状态**：published
