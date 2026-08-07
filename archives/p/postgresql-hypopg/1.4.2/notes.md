# postgresql-hypopg 1.4.2 适配笔记

## 编译环境
- 构建系统: pgxs (PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-08-08
- 编译器: clang
- 状态: built

## 编译步骤

1. **下载源码**: 从 GitHub 下载 HypoPG/hypopg 1.4.2 tarball
   - URL: https://api.github.com/repos/HypoPG/hypopg/tarball/1.4.2

2. **编译**: 使用 PGXS 构建系统
   ```bash
   make PG_CONFIG=<pg_config_path>
   ```

3. **安装**: 安装到 staging 目录
   ```bash
   make install DESTDIR=$TEST_PREFIX PG_CONFIG=<pg_config_path>
   ```

4. **质量门禁**: 通过 conan create 验证
   - G2: conan create 成功
   - W3: 本地 CI 模拟通过
   - test_package: test_hypopg.sh 验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | URL 搜索失败 | 脚本不支持 GitHub API URL 格式 | 手动查询 GitHub API，获取 tarball URL |
| 2 | 依赖缺失 | PostgreSQL 不在 conan 制品仓 | 先适配 PostgreSQL 18.3 conan 配方 |

## 源码修改

无补丁，使用原始源码编译。

## 依赖版本

- PostgreSQL 18.3 (提供 pg_config 和 PGXS 构建系统)

## 验证结果

```bash
# 安装产物验证
hypopg.so (PostgreSQL 扩展共享库)
hypopg.control (扩展控制文件)
hypopg--*.sql (版本迁移 SQL 文件)
```

## 注意事项

1. **构建系统**: hypopg 使用 PGXS (PostgreSQL Extension Building Infrastructure)
2. **依赖**: 必须先安装 PostgreSQL (pg_config 命令)
3. **验证**: PostgreSQL 扩展通过 ELF/符号/控制文件验证

---
**编译结束**: 2026-08-08
**最终状态**: built
