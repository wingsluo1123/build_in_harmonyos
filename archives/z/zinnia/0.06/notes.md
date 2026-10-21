# zinnia 0.06 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-15
- 编译器: clang/clang++ (15.0.4)
- 状态: built
- 目标平台: aarch64-linux-ohos (HarmonyOS PC)

## 编译步骤
```bash
# Step 2 手动编译（探索性编译）
source .build-context-zinnia-0.06
cd $BUILD_SRC_DIR
export CC=clang CXX=clang++ CFLAGS="-fPIC -O2"
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check  # 通过（上游无注册 C/C++ 测试）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess(2008) 无 HarmonyOS 识别 | 手动修改 config.guess 添加 `*:HarmonyOS:*:*)` 分支输出 `aarch64-unknown-linux-ohos` |
| 2 | config.sub 不识别 linux-ohos | config.sub(2009) 无 OHOS 支持 | 三处补丁：KERNEL-OS 列表、os 列表、`-linux-ohos*` 分支（patch-autotools-ohos.pl 因锚点缺失未全生效，手动补齐） |
| 3 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS umask 077 权限陷阱（E011/E046） | `sed -i 's/umask 077/umask 022/g' configure config.status` |
| 4 | trainer.cpp:106 make_pair 编译错误 | 新版 libc++ 完美转发 make_pair 拒绝显式模板实参绑定 const 左值 | 去掉显式模板实参：`std::make_pair(y, fn)` |
| 5 | lang-preflight 误判 python | lang_detect._manifest_scan 将子目录 python/setup.py basename 误纳入顶层 manifest；顶层实为 autotools C++（configure.in/Makefile.am + 24 个 .cpp/.h） | 如实记录误判证据；按真实语言 C++ 继续适配（R47 边界规则：绑定目录不算主体） |

## 源码修改
- config.guess: 添加 HarmonyOS 系统识别分支（输出 aarch64-unknown-linux-ohos）
- config.sub: 添加 linux-ohos 三元组支持（3 处）
- configure/config.status: umask 077 → 022（HMDFS 权限陷阱规避）
- trainer.cpp: `std::make_pair<std::string, FeatureNode*>(y, fn)` → `std::make_pair(y, fn)`（C++11 兼容修复）

## 依赖版本
- 无第三方依赖（纯 C++ 库，仅依赖 libc/libc++_shared/libm）
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18)

## 验证结果
```bash
# 编译验证
$ ./configure --prefix=$DEFAULT_PREFIX   # 通过
$ make -j2                                # 通过
$ make install DESTDIR=$TEST_PREFIX      # 通过
$ make check                             # 通过（返回 0）

# 产物
# libzinnia.so.0.0.0 / libzinnia.a / libzinnia.so / libzinnia.so.0
# 工具: zinnia / zinnia_learn / zinnia_convert
# 头文件: zinnia.h（根 + include/zinnia/）
# pkgconfig: zinnia.pc

# 工具运行验证
$ LD_LIBRARY_PATH=... ./zinnia --help   # 正常输出用法
```

## 上游测试清点与实测（R51 三步法）
1. **上游测试清点**：zinnia 0.06 无 C/C++ 测试目录（无 test/，Makefile.am 无 TESTS 注册）；仅有 perl/test.pl、ruby/test.rb、python/test.py 语言绑定测试与 sdk/example.{c,cpp} 示例（非注册测试）。
2. **实际运行**：`make check` 实际执行（返回 0，上游无注册测试目标，故无 C/C++ 测试可跑）。
3. **回填**：C/C++ 测试通过率 N/A（0/0 注册测试，上游确无 C/C++ 测试，附清点证据如上）。

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| libzinnia.so.0.0.0 | ~200KB | 动态库 |
| libzinnia.a | ~490KB | 静态库 |
| zinnia/zinnia_learn/zinnia_convert | ~19KB each | 命令行工具 |

## 注意事项
- lang-preflight 工具对"子目录绑定 setup.py"存在误判缺陷（R47），本次以真实语言 C++ 继续，需在 feedback 中反馈。
- libzinnia.so 动态依赖 libc++_shared.so / libc.so，属 OHOS 系统库，无污染风险。
- R38: 构建产物含命令行工具（zinnia/zinnia_learn/zinnia_convert），需在软件级目录创建 commands.json。
---

**编译结束**: 2026-10-15 22:32
**最终状态**: published
