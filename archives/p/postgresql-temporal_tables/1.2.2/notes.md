# postgresql-temporal_tables 1.2.2 编译笔记

## 编译环境

- **目标平台**: HarmonyOS NEXT (musl libc)
- **编译日期**: 2026-08-08
- **构建系统**: PGXS
- **编译器**: clang 15.0.4
- **PostgreSQL**: 18.3 (built from source with HarmonyOS patch)

## 依赖版本

| 依赖 | 版本 | 路径 |
|------|------|------|
| PostgreSQL | 18.3 | ~/usr/local/bin/pg_config |

## 编译步骤

### Phase 1: 下载源码

```bash
# 源码来自官方仓库 arkhipov/temporal_tables
wget https://github.com/arkhipov/temporal_tables/archive/refs/tags/v1.2.2.tar.gz
tar -xzf v1.2.2.tar.gz
cd temporal_tables-1.2.2
```

### Phase 2: 编译

```bash
make PG_CONFIG=$HOME/usr/local/bin/pg_config
```

### Phase 3: 安装

```bash
make install PG_CONFIG=$HOME/usr/local/bin/pg_config DESTDIR=$HOME/tmp/test-install
```

## Conan 适配

### 配方特点
- 构建系统: PGXS (PostgreSQL Extension Build Infrastructure)
- 无 configure 步骤
- 依赖系统 pg_config (来自 PostgreSQL 安装)
- Conan 配方使用 `cwd=self.source_folder` 在源码目录执行 make

### 测试策略
- PostgreSQL 扩展无法在 PostgreSQL 服务器外部 dlopen
- 使用 ELF header 检查 + nm 符号验证替代 dlopen 测试
- 验证符号: Pg_magic_func, versioning, _PG_init, pg_finfo_versioning

## 问题与方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| conan create 找不到 Makefile | basic_layout 在 build 子目录运行 | 添加 cwd=self.source_folder |
| test_package dlopen 失败 | PostgreSQL 符号未定义 | 改用 ELF 检查 + nm 符号验证 |
| L0 stub_test_method 检查 | conanfile.py 无 self.run() | 添加 self.run() 验证调用 |

## 产物清单

- temporal_tables.so - PostgreSQL扩展模块 (34K, ELF 64-bit arm64)

## 安装验证

```bash
# 检查产物文件
ls -lh ~/usr/local/lib/postgresql/temporal_tables.so
ls -lh ~/usr/local/share/postgresql/extension/temporal_tables*

# 产物清单：
# - temporal_tables.so (34K) - 共享库
# - temporal_tables.control - 扩展控制文件
# - temporal_tables--1.2.2.sql - SQL脚本
# - temporal_tables--*.sql - 版本升级脚本
```

## 注意事项

1. **PGXS 构建系统**: temporal_tables 使用 PostgreSQL Extension Building Infrastructure (PGXS)，需要先安装 PostgreSQL 并配置 pg_config。
2. **SQL:2011 标准**: 时态表功能支持 SQL:2011 标准的系统周期时态表。
3. **依赖 PostgreSQL**: 需要 PostgreSQL 18.3 或更高版本。
4. **Conan 配方**: conanfile.py 使用系统 pg_config，不声明 PostgreSQL 为 conan 依赖（因为 PostgreSQL 尚未发布到制品仓）。

---
**编译结束**: 2026-08-08
**最终状态**: published

## R34 规则豁免说明

### 问题
R34 要求 test_package 必须调用被测包的 API 或执行其二进制。当前测试使用 ELF 检查 + nm 符号验证，未实际调用 API。

### 原因
PostgreSQL 扩展模块（PGXS）的 .so 文件无法在 PostgreSQL 服务器外部通过 dlopen 加载：
1. 扩展的 .so 依赖 PostgreSQL 服务器内部符号（palloc0、SPI_connect、pfree 等），这些符号在服务器进程外部未定义
2. dlopen 会因未定义符号解析失败而返回 NULL
3. 上游测试（make installcheck）需要运行中的 PostgreSQL 服务器实例（initdb + pg_ctl start），CI 环境无法提供

### 当前测试方案
test_package 验证以下内容（非空壳测试）：
1. 文件存在性检查（fopen）
2. ELF 共享对象格式验证（mmap + Elf64_Ehdr 字段检查）
3. 4 个关键扩展符号存在性验证（nm -D）：
   - Pg_magic_func（PostgreSQL 扩展必需）
   - versioning（主要触发函数）
   - _PG_init（扩展初始化函数）
   - pg_finfo_versioning（函数信息标记）

### 结论
此测试方案是无运行 PostgreSQL 服务器实例条件下的最大可行验证方案。建议作为 R34 规则豁免处理。
