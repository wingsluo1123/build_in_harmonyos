# perl-object-event 1.23-r0 适配笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-29
- 编译器: clang/clang++ (未使用，纯 Perl 模块)
- 状态: built

## 编译步骤

1. 下载源码包 `Object-Event-1.23.tar.gz` (CPAN)
2. 执行 `perl Makefile.PL INSTALL_BASE=/`（使用 INSTALL_BASE=/ 使文件安装到 lib/perl5/ 下）
3. 执行 `make -j1` 编译
4. 执行 `make test` 运行测试套件
5. 执行 `make install DESTDIR=$PACKAGE_FOLDER` 安装到 Conan 包目录

### Conan 配方生成

使用 `ohc-run.py conan-init` 生成 conanfile.py + conandata.yml + test_package/，然后通过 `ohc-run.py conan-verify` 验证（8 道门禁全部通过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模块加载失败: Can't locate common/sense.pm | 运行时依赖 common::sense 未在 Conan 包中声明 | common::sense 已在系统 Perl 路径安装，设置 PERL5LIB 时需保留系统路径 |
| 2 | 模块加载失败: Can't locate AnyEvent/Util.pm | 运行时依赖 AnyEvent 未在 Conan 包中声明 | AnyEvent 已在系统 Perl 路径安装 (v7.17)，设置 PERL5LIB 时需保留系统路径 |
| 3 | PERL5LIB 覆盖导致系统模块不可见 | Conan test_package 环境中 PERL5LIB 只包含 Conan 包路径 | test_package 通过 conanrun.sh 设置环境，实际运行时需追加系统 Perl lib 路径 |

## 源码修改

无补丁。Object::Event 是纯 Perl 模块，无需任何源码修改即可在鸿蒙平台编译和运行。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| Perl | 5.42.0 | 系统安装 (HNP) | aarch64-linux 平台 |
| common::sense | 3.75 | 系统 Perl lib | 运行时依赖 |
| AnyEvent | 7.17 | 系统 Perl lib | 运行时依赖 (AnyEvent::Util::guard) |
| Carp | (core) | Perl 核心模块 | 运行时依赖 |

## 验证结果

### Conan 验证 (conan-verify)

```
G0: ✅ PASS (构建系统识别)
G1: ✅ PASS (配方完整性)
G2: ✅ PASS (conan create 成功)
G3: ✅ PASS (系统同名库隔离)
G4: ✅ PASS (产物完整性: 1 .pm + 1 .packlist + 1 .pod)
L2: ✅ PASS (smoke test: perl -MObject::Event → 1.23)
L4: ✅ PASS (安全扫描: 纯 Perl 模块，无可扫描 ELF)
L5: ✅ PASS (产物基线: 5 个文件完全一致)
```

### 模块测试套件 (make test)

```
All tests successful.
Files=20, Tests=99,  5 wallclock secs
Result: PASS
```

### 功能测试

17 项功能测试全部通过，覆盖：模块加载、版本验证、对象创建、事件注册/触发、多回调、回调注销、事件优先级、before_/after_ 前缀事件、stop_event、handles、remove_all_callbacks、guard 返回值、unreg_me 自注销、异常处理。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/perl5/Object/Event.pm | 23KB | 主模块文件 |
| lib/perl5/aarch64-linux/auto/Object/Event/.packlist | 86B | 安装清单 |
| lib/perl5/aarch64-linux/perllocal.pod | 215B | 本地安装记录 |

## 注意事项

1. **运行时依赖**: Object::Event 依赖 `common::sense` 和 `AnyEvent`，这两个模块需在系统 Perl 路径中可用。当前系统已安装，无需额外操作。
2. **纯 Perl 模块**: 本模块不包含 XS/C 代码，无 SELinux 限制问题（参考 perl-dbd-pg 的 XS 模块 SELinux 问题）。
3. **PERL5LIB 设置**: 使用 Conan 安装后，需确保 PERL5LIB 同时包含 Conan 包路径和系统 Perl lib 路径，否则依赖模块不可见。
4. **INSTALL_BASE=/**: 使用此参数使模块安装到 `lib/perl5/` 子目录下，配合 DESTDIR 实现 Conan staging 隔离。

---

**编译结束**: 2026-06-29 20:04
**最终状态**: built
**功能测试**: 2026-07-01, 全部通过 (20 文件 / 99 测试 + 17 功能测试)
