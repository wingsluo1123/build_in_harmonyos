# Kyoto Cabinet

**类别**: Key-Value Database
**官网**: https://dbmx.net/kyotocabinet/（fallabs.com 已 404，dbmx.net 为官方权威镜像）
**描述**: 高性能键值存储数据库，支持多种数据库类型（HashDB/TreeDB/PolyDB/ForestDB）

---

## 已编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.2.80 | built | 2026-10-14 | 上游 make check 512 条命令全量通过 |

---

## 功能特性

- **HashDB**: 基于哈希表的键值存储
- **TreeDB**: 基于B+树的有序键值存储
- **PolyDB**: 多态数据库（自动适配类型）
- **ForestDB**: 文档数据库（支持分层结构）

---

## 使用场景

- 缓存系统
- 配置存储
- 会话管理
- 元数据索引

---

## 构建与测试

- Conan 2 配方（HarmonyOS PC AArch64，musl，clang 15）：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
- 依赖：zlib/1.3.1（压缩，上游默认开启）
- 上游测试：`make check` 512 条命令、11 个子目标（配方 build() 内串行运行）
- test_package：27 项断言（文件 HashDB：创建/写入/读取/覆盖/删除/迭代/重开/持久化/非法路径/损坏输入）
- 补丁：`0001-configure-umask-hmdfs.patch`（configure 临时目录 umask 077→022，HMDFS 兼容）

## 注意事项

1. ForestDB 数据库文件是目录结构，删除时需使用 `rm -rf`
2. 测试套件执行时间较长（约540秒），须 `-j1` 串行（共享 casket* 测试库文件）
3. 上游 Makefile 无 VPATH，必须源内构建
4. 支持 C++ API 和命令行工具（17 个 CLI：kc*test / kc*mgr / kclangctest）

---

*最后更新: 2026-10-14*