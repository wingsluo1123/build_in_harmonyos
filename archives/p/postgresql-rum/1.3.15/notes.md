# postgresql-rum 1.3.15 适配笔记

## 编译环境
- 构建系统: PGXS (PostgreSQL Extension Build System)
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 PostgreSQL 扩展构建系统 (PGXS) 编译，依赖 PostgreSQL 服务器端开发文件。
通过 `make USE_PGXS=1 PG_CONFIG=<pg_config_path>` 构建 rum.so 共享库。

## 遇到的问题与解决方案

### CI 编译失败: PGShmemHeader 结构体字段名变更 (P0)
- 问题: 补丁中 `InternalIpcMemoryCreate` 的 OHOS 分支使用了 `->length` 字段，但 PostgreSQL 18.3 的 `PGShmemHeader` 结构体没有 `length` 成员，实际字段名为 `totalsize`
- 根因: 补丁在 `InternalIpcMemoryCreate` 中初始化了共享内存头部，但头部初始化应由 `PGSharedMemoryCreate` 在调用 `InternalIpcMemoryCreate` 之后完成
- 修复: 移除 `InternalIpcMemoryCreate` OHOS 分支中的头部初始化代码，仅保留 mmap 创建和清理回调注册。头部初始化由 `PGSharedMemoryCreate` 使用正确的字段名（`totalsize`、`creatorPID`、`dsm_control`、`device`、`inode`、`freeoffset`）完成

### getgroups() 主 GID 遗漏 (P0, AI Review)
- 问题: `getgroups()` 只返回附加组（supplementary groups），不包含主 GID。当目录属组等于用户主 GID 时，所有权检查会错误失败
- 修复: 在 `getgroups()` 遍历之前先检查 `getegid() == dir_gid`

### pg_mode_mask 注释不准确 (P2, AI Review)
- 问题: 注释称 "avoids group/other permissions" 与 `umask(0)` 的实际效果相反
- 修复: 修正注释描述 `umask(0)` 的真实语义——不屏蔽任何权限位

### test_rum.sh 空壳测试 (P3, AI Review, R34)
- 问题: 测试仅检查 rum.so 文件是否存在，未验证共享库导出的扩展入口符号
- 修复: 添加 `nm -D` 检查 `_PG_init` 符号是否存在

### CI diff 应用失败
- 问题: sources/rum-1.3.15.tar.gz 二进制文件包含在 PR diff 中，导致 CI checkout-pr 步骤无法应用 diff
- 解决: 移除二进制 tarball，依赖 conandata.yml 中的 URL 下载源码

### PostgreSQL 补丁 AI 审查问题
- P0 (Critical): PGSharedMemoryCreate 返回 fake_header 静态变量
  - 修复: 改用 mmap(MAP_SHARED|MAP_ANONYMOUS) 创建真正的共享内存
- P1 (High): PGSharedMemoryIsInUse 无条件返回 false
  - 说明: CreateLockFile() 通过 flock() 检查 postmaster.pid 提供并发实例检测，在此函数被调用之前已完成
- P3: getgroups() 失败未处理
  - 修复: 添加 getgroups() < 0 错误处理

## R8 规则豁免说明 (#ifdef __OHOS__)

PostgreSQL 18.3 补丁中使用 `#ifdef __OHOS__` 的场景及其无法使用 configure-time 检测的原因：

1. **SysV 共享内存 (sysv_shmem.c)**: `shmget` 系统调用在 OHOS 上触发 SIGSYS（未实现的系统调用），无法通过 configure 探测，因为 configure 阶段不会调用 `shmget`
2. **shm_open (initdb.c, dsm_impl.h)**: 同样触发 SIGSYS，无法通过 configure 探测
3. **hmdfs 文件系统行为 (miscinit.c, file_perm.c, pgmkdirp.c, initdb.c)**: hmdfs 对 umask、mkdir 权限的处理与标准文件系统不同，属于编译期无法检测的运行时文件系统行为
4. **getpwuid 回退 (username.c, fe-auth.c)**: OHOS 用户可能不在 /etc/passwd 中，属于运行时环境差异
5. **Unix 域套接字 (pg_config_manual.h, pg_regress.c)**: OHOS 不支持 Unix-domain sockets（bind 返回 EPERM），属于内核功能限制

以上场景均涉及 OHOS 平台的内核级限制或文件系统行为差异，无法通过 POSIX 接口适配或 configure 阶段探测解决，因此申请 R8 规则豁免。

## 依赖版本

- PostgreSQL 18.3 (conan recipe 在同 PR 中)

## 验证结果

PostgreSQL 补丁已修复编译错误（PGShmemHeader 字段名），待 conan create 验证通过后更新状态。

## 注意事项

RUM 索引是一种全文搜索的加速索引类型，需要 PostgreSQL 的支持。
rum.so 是 PostgreSQL 扩展，运行时由 PostgreSQL 进程加载。
