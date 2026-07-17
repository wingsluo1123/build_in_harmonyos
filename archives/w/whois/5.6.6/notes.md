# whois 5.6.6 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: published

## 编译步骤

whois 使用简单的 Makefile 构建，不需要 configure 步骤：

1. 下载源码（从 GitHub 官方源 rfc1036/whois）
2. 生成 version.h：`perl make_version_h.pl debian/changelog > version.h`
3. 编译：`make whois CC=clang AR=llvm-ar RANLIB=llvm-ranlib -j1`
4. Staging 安装：`make install-whois prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
5. 验证：`whois --help` 显示 Usage 信息

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tools.build:compiler_executables:c conf 不存在 | Conan 版本差异，不支持子键访问 | 改用 dict 方式获取 compiler_executables |
| 2 | make_version_h.pl 找不到 | basic_layout 将构建目录设为子目录 | 使用 self.source_folder 绝对路径 |
| 3 | whois --help 退出码为 1 | 上游设计，--help 非标准退出码 | test.sh 改为检查输出内容而非退出码 |
| 4 | mkpasswd 编译失败 | 缺少 getpass 函数（OHOS 平台限制） | 只构建 whois 目标，跳过 mkpasswd |

## 源码修改

无补丁。需要在 build() 方法中生成 version.h 文件（由 make_version_h.pl 脚本生成）。

## 依赖版本

无 Conan 依赖。libidn2 为可选系统库，不在 Conan 配方中声明。

## 验证结果

conan create + conan-verify 全部通过：
- G1: 配方完整性 ✅
- G2: conan create 干净构建 ✅
- G3: 系统同名库隔离 ✅
- G4: 产物完整性 ✅
- L2/L4/L5: smoke test / 安全扫描 / 基线对比 ✅

## 注意事项

1. whois 使用 Makefile 构建，不是 autotools，无需 configure 步骤
2. 需要运行 `make_version_h.pl` 生成 version.h，否则编译失败
3. libidn2 是可选依赖，Makefile 自动检测，未安装时跳过
4. mkpasswd 编译失败（缺少 getpass 函数），但 whois 本体编译成功
5. whois --help 退出码为 1（非标准），测试需检查输出内容
---

**编译结束**: 2026-07-15 18:04
**最终状态**: published
