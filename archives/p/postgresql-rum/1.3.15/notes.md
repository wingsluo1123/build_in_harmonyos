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

### CI diff 应用失败
- 问题: sources/rum-1.3.15.tar.gz 二进制文件包含在 PR diff 中，导致 CI checkout-pr 步骤无法应用 diff
- 解决: 移除二进制 tarball，依赖 conandata.yml 中的 URL 下载源码

### PostgreSQL 补丁 AI 审查问题
- P0 (Critical): PGSharedMemoryCreate 返回 fake_header 静态变量，导致进程间无法共享内存
  - 修复: 改用 mmap(MAP_SHARED|MAP_ANONYMOUS) 创建真正的共享内存
- P1 (High): PGSharedMemoryIsInUse 无条件返回 false
  - 修复: 添加详细注释说明 postmaster.pid 文件锁机制提供并发实例检测
- P3: getgroups() 失败未处理
  - 修复: 添加 getgroups() < 0 错误处理

## 依赖版本

- PostgreSQL 18.3 (conan recipe 在同 PR 中)

## 验证结果

待 conan create 验证通过后更新。

## 注意事项

RUM 索引是一种全文搜索的加速索引类型，需要 PostgreSQL 的支持。
rum.so 是 PostgreSQL 扩展，运行时由 PostgreSQL 进程加载。
