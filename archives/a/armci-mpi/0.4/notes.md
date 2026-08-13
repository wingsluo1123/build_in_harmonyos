# armci-mpi 0.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-13
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/pmodels/armci-mpi/archive/refs/tags/v0.4.tar.gz`
2. 解压到 work 目录
3. 运行 autogen.sh 生成 configure（通过 perl/bash 显式调用 aclocal/libtoolize/autoheader/autoconf/automake）
4. 修补 umask 077 → 022（HarmonyOS setgid 限制）
5. 运行 configure（CC=clang + CFLAGS/LDFLAGS 传递 MPI 路径，不使用 mpicc wrapper）
6. make -j1
7. make install DESTDIR
8. conan create + conan-verify 全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络问题 | 使用 git clone --depth 1 获取源码 |
| 2 | init-build 嵌套源码提升 bug | 脚本 bug | 手动从 .orig 重新解压 |
| 3 | config.status umask 077 权限错误 | HarmonyOS setgid 目录限制 | 修补 umask 077 → 022 |
| 4 | HMDFS 内核无法执行 /storage/ 下脚本 shebang | HMDFS 限制 (E217) | 通过 perl/bash 显式调用工具 |
| 5 | aclocal 的 @am_AUTOM4TE@ 未解析 | AUTOM4TE 环境变量未设置 | 设置 AUTOM4TE 指向 autom4te |
| 6 | autom4te 模块路径不正确 | PERL5LIB 未指向 autoconf share | 设置 PERL5LIB |
| 7 | automake 缺少 m4/ltmain.sh | libtoolize 未自动复制 | 手动从 libtool share 目录复制 |
| 8 | mpicc wrapper 无法从 /storage/ 执行 | HMDFS shebang 限制 | 使用 CC=clang + CFLAGS/LDFLAGS 传递 MPI 路径 |
| 9 | configure.ac 中 MPICC 覆盖 CC=clang | configure.ac 逻辑 | 不传递 MPICC 参数 |
| 10 | conftest 运行时找不到 libmpi.so | LD_LIBRARY_PATH 未设置 | 添加 LD_LIBRARY_PATH 指向 mpich lib |

## 源码修改

18 个补丁文件（patches/0001-0018）由 finish 的 refresh-patch --auto 自动生成，
修改 autotools 生成文件（Makefile.in, ltmain.sh, aclocal.m4, libtool.m4,
config.guess, config.sub 等）以支持 OHOS 平台。build() 通过 autogen
重新生成这些文件，补丁作为变更记录保留。

## 依赖版本

- mpich/5.0.1（从 ohpcd 制品仓获取）
- clang/clang++ 15.0.4（系统编译器）
- libtool, autoconf, automake（系统工具）

## 验证结果

conan-verify 全部通过（G1-G4 + L2/L4/L5）:
- G1 配方完整性: PASS
- G2 conan create: PASS
- G3 系统同名库隔离: PASS
- G4 产物完整性: PASS
- L2 smoke test: PASS
- L4 安全扫描: PASS
- L5 产物基线: PASS

## 注意事项

- HMDFS shebang 限制是核心平台问题（E217），所有 /storage/ 下的脚本都受影响
- mpicc wrapper 在 HMDFS 上不可执行，必须使用 CC=clang 直接编译
- 不要传递 MPICC 参数，否则 configure.ac 会覆盖 CC
- umask 077 会导致 config.status 权限错误，必须修补为 022

---

**编译结束**: 2026-08-13 10:44
**最终状态**: published
