# readline 8.2 编译进度

**日期**: 2026-07-15
**状态**: ✅ 完成

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 source | ✅ | 官方源码 ftp.gnu.org |
| Step 2 patches | ✅ | 0001-port-for-ohos + 0002-fix-shlib-termcap-link |
| Step 3 configure | ✅ | --with-curses=yes --disable-shared --enable-static |
| Step 4 make | ✅ | CFLAGS="-fPIC -O2" |
| Step 5 install | ✅ | autotools.install() |
| Step 6 conan-init | ✅ | conanfile.py + conandata.yml + test_package/ |
| Step 7 conan-verify | ✅ | conan create 通过 |
| Step 8 finish | ✅ | W2结构+W3编译验证通过 |
| Step 9 submit | ✅ | PR 提交 |

## 发现与知识

1. **CFLAGS=-fPIC 必须设置**: readline 静态库 (libreadline.a) 默认不带 -fPIC，OHOS 上链接到共享库会报 `R_AARCH64_ADR_PREL_PG_HI21` 重定位错误。通过 `tc.extra_cflags.append("-fPIC")` 在 Conan 配方中设置。
2. **TERMCAP_LIB 传递修复**: `shlib/Makefile.in` 中共享库链接命令缺少 `$(TERMCAP_LIB)`，导致链接时找不到 ncurses 符号。补丁 `0002-fix-shlib-termcap-link.patch` 修复此问题。
3. **config.guess/config.sub OHOS 适配**: 需在 3 处添加 ohos 支持：`linux-ohos*` maybe_os 白名单、`ohos*` 系统类型列表、`linux-ohos*` kernel-os 验证。
4. **R6 违规修复**: 删除了 6 个修改生成文件的补丁（Makefile, configure, shlib/Makefile），仅保留修改源文件的补丁（Makefile.in, config.guess, config.sub）。

## 代码质量修复记录 (2026-07-15)

### P0 修复
- [P0] 创建 conanfile.py（Autotools 配方，含 ncurses 依赖、-fPIC、--with-curses）
- [P0] 创建 conandata.yml（官方 URL + sha256 + 补丁声明）
- [P0] 创建 test_package/（conanfile.py + CMakeLists.txt + test.c + MANIFEST.yml）

### P1 修复
- [P1] 删除 R6 违规补丁：0001-Makefile.patch, 0002-configure.patch, 0003-shlib-Makefile.patch
- [P1] 删除重复补丁：0004-shlib-Makefile.in.patch (与 0002 重复), 0005/0006 (与 0001 重复)
- [P1] 修复 manifest.yaml：status: success → built，字段格式对齐模板
- [P1] 更新 notes.md：补全步骤状态，记录修复内容
---

**编译结束**: 2026-07-15 18:10
**最终状态**: built
