# lp_solve 5.5.2.14 适配笔记

## 编译环境
- 构建系统: custom（自定义 Makefile，原始使用 ccc shell 脚本）
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 链接器: GNU ld.bfd 2.45（⭐ 必须，lld 因 libxml2 依赖缺失不可用）
- 平台: OpenHarmony aarch64 (HongMeng Kernel 1.12.0)
- 状态: published

## 编译步骤

lp_solve 没有标准的 configure/make/cmake 构建系统，而是使用自定义的 `ccc` shell 脚本编译。
为适配 OpenHarmony，我们创建了完整的 Makefile：

1. **init-build**: 手动处理源码解压（tarball 含嵌套 `lp_solve/lp_solve/` 目录，自动解压失败）
2. **创建 Makefile**: 基于 `lpsolve55/ccc` 和 `lp_solve/ccc` 脚本的编译逻辑编写
3. **关键编译参数**: `CC=clang CFLAGS="-fPIC -O2" LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd"`
4. **编译**: `make all` — 构建 liblpsolve55.a、liblpsolve55.so、lp_solve 可执行文件
5. **安装**: `make install DESTDIR=$TEST_PREFIX` → `make install` (本地)
6. **打包**: `ohc-run.py package lp_solve 5.5.2.14`
7. **验证**: lp_solve -h 确认版本，求解测试模型验证功能
8. **收尾**: `ohc-run.py finish lp_solve 5.5.2.14 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| P1 | init-build 解压失败 | tarball 内含嵌套目录 `lp_solve/lp_solve/`，Python tarfile 的子目录提升逻辑与同名子目录冲突 | 手动解压 tarball，逐一 `mv` 提升子目录内容，用 `--no-download` 继续 init-build |
| P2 | 源码无标准构建标记文件 | lp_solve 没有 configure/Makefile/CMakeLists.txt | 创建占位 Makefile 使 init-build 识别目录为有效，后覆盖为完整 Makefile |
| P3 | Flex/Bison 前缀不匹配 | `PARM` 宏使用 `yyget_extra(yyscanner)`，但生成的 flex 头文件 `lp_rlp.h` 使用 `lp_yy*` 前缀 | 编译 `lp_rlp.c` 时添加 `-Dyyscanner=lp_yyscanner -Dyyget_extra=lp_yyget_extra -Dyylex=lp_yylex` 等 13 个前缀映射 |
| P4 | Bison Token 定义缺失 | `lp_rlp.h` 的 inline 函数使用 bison tokens (INF=262 等)，但 tokens 仅在 `lp_rlp.c` 中定义，`lp_rlp.h` 包含于 token 定义之前 | 创建 `lp_rlp_tokens.h` 条件定义头文件；修改 `lp_rlp.c` 在 `#include "lp_rlp.h"` 前插入 token enum/defines |
| P5 | lld 不可用 | lld 依赖 libxml2.so.16，该库缺失导致 lld 无法启动 | ⭐ 必须使用 GNU ld: `LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd"` |
| P6 | 头文件安装不完整 | 初始 Makefile 仅安装 7 个头文件，但 `lp_lib.h` 依赖多个内部头文件 | 扩展 install 目标包含 33 个头文件（含 bfp/、shared/、colamd/ 子目录头文件） |

## 源码修改

| 文件 | 类型 | 说明 |
|------|------|------|
| Makefile | 新增 | 完整的 OpenHarmony 适配 Makefile（含编译规则、install 目标、flex/bison 前缀映射） |
| lp_rlp.c | 修改 | 在 `#include "lp_rlp.h"` 前插入 bison token enum/defines，使 flex inline 函数可用 tokens |
| lp_rlp_tokens.h | 新增 | 条件定义 bison token 常量的头文件（#ifndef 守卫防止与 lp_rlp.c 中的 enum 冲突） |

补丁文件：
- 0001-Makefile.patch
- 0002-lp_rlp.h.patch（被 0003-lp_rlp.c.patch 替代）
- 0003-lp_rlp_tokens.h.patch

## 依赖版本

- clang 15.0.4 (系统预装)
- GNU ld.bfd 2.45 (/data/service/hnp/bin/ld.bfd)
- musl libc (系统 libc)
- 无额外库依赖（lp_solve 自包含 LUSOL、COLAMD 等）

## 验证结果

```bash
# 版本确认
$ lp_solve -h | head -2
Usage of ... lp_solve version 5.5.2.14

# LP 模型求解
$ lp_solve test_model.lp
Value of objective function: 10.00000000
x1=6, x2=4  ✅

# MIP 模型求解
$ lp_solve test_mip.lp
Value of objective function: 180.00000000
x1=20, x2=60  ✅

# 共享库 API
$ ./test_lib
版本号: 5.5.2.14  ✅
make_lp/set_obj/add_constraint/solve/delete_lp  ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lp_solve-5.5.2.14-ohos-aarch64.tar.gz | 2219 KB | 预编译包（ELF已签名） |
| lp_solve-5.5.2.14-ohos-aarch64-debug.tar.gz | 735 KB | Debug 符号包 |

## 注意事项

1. ⭐ 必须使用 GNU ld (ld.bfd) 替代 lld，lld 因 libxml2 依赖缺失不可用
2. `lpsolve.h` 包含 `windows.h`，跨平台用户应使用 `lp_lib.h` 作为 API 入口
3. G0 干净构建验证存在已知问题：源码 tarball 嵌套 `lp_solve/lp_solve/` 目录导致补丁路径不匹配
4. lp_solve 无标准测试套件（make check），采用模型求解和 API 调用验证

---
**编译结束**: 2026-06-09
**最终状态**: published
---

**编译结束**: 2026-06-09 16:24
**最终状态**: published

## 代码质量检查与 CI 构建验证 (2026-07-14)

### 质量检查 (quality_check.py)
- 结果: 0 错误、0 警告 ✓

### CI 构建验证 (conan-verify) 修复记录

| # | 门禁 | 问题 | 修复 |
|---|------|------|------|
| C1 | G1 | conanfile.py 缺失 | 创建 Makefile 构建配方 |
| C2 | G1 | conandata.yml 缺失 | 创建含 source URL + sha256 + 3 补丁引用 |
| C3 | G1 | test_package/ 缺失 | 创建 conanfile.py + CMakeLists.txt + test_lp_solve.c + MANIFEST.yml |
| C4 | G1 | commands.json 缺失 | 创建软件级元数据 |
| C5 | G1 | manifest.yaml 字段错误 | 修正 build_system=makefile, system=makefile, 补充 sha256 |
| C6 | G2 | 补丁 0001 源路径 `--- a/Makefile` | 改为 `--- /dev/null`（新文件补丁格式） |
| C7 | G2 | Conan 2.29.1 不支持 `conf.get("tools.build:compiler_executables:c")` | 改用 `os.environ.get("CC")` 获取编译器路径 |
| C8 | G2 | `basic_layout` 导致源码在 src/ 子目录 | 自定义 `layout()` 使 source/build 同目录 |
| C9 | G2 | yacc 隐式规则重新生成 lp_rlp.c 导致 token 未定义 | 使用 `make -r` 禁用隐式规则 |
| C10 | G2 | 0004 补丁在 lp_rlp.h include tokens 导致宏/enum 冲突 | 删除 0004 补丁 |
| C11 | G2 | test_package `get_var()` 不存在于 API | 改用 `get_var_primalresult()` |
| C12 | G2 | CMakeLists.txt 缺少 `enable_testing()` 和 `add_test()` | 添加 CMake test target 注册 |

### 最终验证结果
- G1 (配方完整性): PASS ✓
- G2 (conan create): PASS ✓
- G3 (系统同名库隔离): PASS ✓
- G4 (产物完整性): PASS ✓
- L2 (平台功能矩阵): PASS ✓
- L4 (静态安全扫描): PASS ✓
- L5 (产物基线对比): PASS ✓
- **Verdict: PASS** — 可标记 status: published
