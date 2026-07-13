# pth 2.0.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4 / clang++ 15.0.4 (OpenHarmony SDK)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

```bash
source $SKILL_ROOT/.build-context-pth-2.0.7
cd $BUILD_SRC_DIR
umask 022

# 1. 替换过旧的 config.guess/config.sub
cp /storage/Users/currentUser/usr/local/share/automake-1.16/config.guess .
cp /storage/Users/currentUser/usr/local/share/automake-1.16/config.sub .

# 2. 修复 configure: Linux braindead 检测 + /tmp 路径 + umask
# 3. 修复 shtool: umask 077 → 022
# (以上修改通过补丁在 Conan 构建时自动应用)

# 4. 配置
./configure --prefix=$DEFAULT_PREFIX --disable-shared

# 5. 编译 (必须 -j1, HMDFS 不支持 mkfifo)
make -j1

# 6. 安装
make install DESTDIR=$TEST_PREFIX

# 7. 测试
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 无法识别 aarch64-unknown-linux-ohos | 原始文件为 2003 年版本，不含 OpenHarmony 识别 | 替换为 automake 1.17 版本 (Copyright 2023) |
| 2 | configure 将 OpenHarmony 误判为 "braindead Linux"，选择 sjljlx 变体 (需 GLIBC jmp_buf) | configure 的 Linux 检测在缺少 /usr/include/features.h 时覆盖了正确的 sjlj 结果 | 修改 configure 逻辑: 不在缺少 features.h 时覆盖 sjlj 检测结果 |
| 3 | configure 写入 /tmp/autoconf.$$ 失败 | OpenHarmony 的 /tmp 是只读文件系统 | 将 `/tmp/autoconf.$$` 改为 `${TMPDIR:-/tmp}/autoconf.$$` |
| 4 | shtool 创建临时目录失败 | HMDFS 文件系统上 umask 077 导致 mkdir 后文件不可访问 | 将 shtool 中 umask 077 改为 umask 022 |
| 5 | Conan 构建时 pth_p.h 找不到 | conandata.yml 中 base_path=source_subfolder 与 basic_layout 不匹配 | 改为 base_path="." |
| 6 | Conan 构建时 make 在 build-release 子目录运行，shtool 相对路径失效 | basic_layout 默认 build 目录为子目录 | 设置 self.folders.build="." 和 self.folders.generators="." 实现原地构建 |
| 7 | make -j20 时 pth_p.h 未生成就开始编译 pth_uctx.c | HMDFS 不支持 mkfifo (make jobserver)，并行构建时 shtool scpp 与编译竞态 | 使用 make -j1 强制串行构建 |
| 8 | make install -j20 时目录创建与文件安装顺序冲突 | 并行安装时 shtool install 在 mkdir 之前执行 | 使用 install -j1 强制串行安装 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | 替换为 automake 1.17 版本，支持 aarch64-unknown-linux-ohos |
| config.sub | 替换为 automake 1.17 版本 |
| configure | (1) Linux braindead 检测: 缺少 features.h 时不覆盖 sjlj 结果; (2) /tmp/autoconf.$$ → ${TMPDIR:-/tmp}/autoconf.$$; (3) umask 077 → 022 |
| shtool | umask 077 → 022 (影响 scpp 生成 pth_p.h) |

## 依赖版本

无外部依赖。pth 是自包含的用户空间线程库。

## 验证结果

```
make check 退出码: 0
Pth: OK: aarch64-unknown-linux-ohos | sjlj/ssjlj/sas | down | 2.0.7

conan-verify: 8/8 门禁通过 (G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS)
```

## 注意事项

1. **必须使用 make -j1**: HMDFS 文件系统不支持 mkfifo，make 的 jobserver 机制无法工作，并行构建会导致 pth_p.h 生成与源码编译的竞态条件。
2. **umask 必须为 022**: HMDFS 上 umask 077 会导致临时目录创建后无法访问。
3. **in-source 构建**: pth 的 Makefile 使用相对路径 (./shtool)，Conan 配方必须设置 build folder 为源码目录。
4. **mctx 配置**: OpenHarmony 无 makecontext/swapcontext，但支持 sigsetjmp/siglongjmp 和 sigaltstack，configure 正确检测为 sjlj/ssjlj/sas。

---

**编译结束**: 2026-06-26 05:34
**最终状态**: published
