# libpq - PostgreSQL 客户端库

## 软件简介

libpq 是 PostgreSQL 的前端库，提供 C 语言 API 用于连接 PostgreSQL 数据库服务器并执行查询。它是 PostgreSQL 客户端应用程序的核心组件。

**官方主页**: https://www.postgresql.org/

**许可证**: PostgreSQL License（类似 MIT/BSD，宽松自由）

## 鸿蒙PC适配状态

| 版本 | 状态 | 构建系统 | 补丁数 | 适配质量 |
|------|------|---------|--------|---------|
| 17.2 | built | autotools | 3 | 高 |

**适配特点**:
- 静态库版本（无 RUNPATH 问题，天然可移植）
- 无外部依赖（--without-readline --without-zlib --without-icu）
- 已通过质量门禁 G1-G4

## 使用方法

### 安装

```bash
# 使用预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libpq 17.2
```

### 编译链接

```bash
# 设置 pkg-config 路径
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# 使用 pkg-config 编译
clang your_app.c $(pkg-config --cflags --libs libpq) -o your_app
```

### API 示例

```c
#include <libpq-fe.h>
#include <stdio.h>

int main() {
    PGconn *conn = PQconnectdb("dbname=test");
    if (PQstatus(conn) != CONNECTION_OK) {
        fprintf(stderr, "Connection failed: %s\n", PQerrorMessage(conn));
        PQfinish(conn);
        return 1;
    }
    
    printf("libpq version: %ld\n", PQlibVersion());
    PQfinish(conn);
    return 0;
}
```

## 依赖关系

**无外部依赖**（静态库版本已禁用 readline/zlib/ICU）

## 平台适配说明

### 关键适配点

1. **平台识别**: 需要 config.guess/config.sub 补丁识别 HarmonyOS
2. **临时目录**: configure 使用 $HOME/tmp 替代只读的 /tmp
3. **静态库方案**: 避免动态库 RUNPATH 硬编码问题

### 补丁文件

| 补丁 | 说明 |
|------|------|
| 0001-config.guess-harmonyos.patch | 添加 HarmonyOS 平台识别 |
| 0002-config.sub-ohos.patch | 添加 linux-ohos 内核识别 |
| 0003-configure-tmpdir.patch | 修复临时目录权限问题 |

## 相关资源

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/current/libpq.html)
- [鸿蒙PC适配笔记](./17.2/notes.md)
- [质量门禁报告](./17.2/reports/)