# ARMCI-MPI — OpenHarmony 编译档案

## 软件简介
ARMCI-MPI 是 ARMCI (Aggregate Remote Memory Copy Interface) 的 MPI 实现，使用 MPI 单边通信 (RMA) 提供远程内存访问原语。来自 pmodels 组织（MPICH 同一团队）。

## OHOS 适配要点
- Autotools 构建，GitHub tag tarball 不含预生成 configure，需先运行 autogen.sh
- **HMDFS shebang 限制 (E217)**: /storage/ 下的脚本 shebang 无法被内核 execve，需通过 `perl /path/to/tool` 或 `bash /path/to/tool` 显式调用
- configure.ac 中 MPICC 会覆盖 CC，不要传递 MPICC 参数
- mpicc wrapper 无法从 /storage/ 执行，改用 `CC=clang` + `CFLAGS/LDFLAGS` 传递 MPI 路径
- umask 077 导致 config.status 权限错误，需修补为 umask 022
- 18 个补丁修复 autotools 生成文件的平台兼容性 (config.guess/sub, ltmain.sh, libtool.m4 等)

## 可用版本
- **0.4** (2024 release): 首次适配，静态库 libarmci.a，依赖 mpich/5.0.1
