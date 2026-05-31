# gpgme 1.24.0 系统安装归档

## 来源

系统已安装 gpgme 1.24.0（预编译包或之前编译），比任务要求版本(1.23.2)更新，直接使用。

## 安装信息

- 安装日期: 2026-05-31
- 安装方式: 预编译包或系统安装
- 状态: published

## 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| libgpgme.so.11.33.0 | 473KB | 主库文件 |
| libgpgme.so | - | 符号链接 |
| libgpgme.so.11 | - | 符号链接 |
| gpgme.h | 98KB | 头文件 |
| gpgme.pc | 383B | pkg-config 文件 |
| gpgme-glib.pc | 400B | GLib 绑定 pkg-config |

## pkg-config 验证

```bash
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion gpgme    # 1.24.0
pkg-config --libs gpgme          # -L~/usr/local/lib -lgpgme
pkg-config --cflags gpgme        # -I~/usr/local/include
```

## 依赖

| 软件 | 版本 | 状态 |
|------|------|------|
| libgpg-error | 1.50 | 已安装 |
| libassuan | 3.0.2 | 已安装 |

## 注意事项

- 系统版本比任务要求版本更新，满足需求
- 编译依赖 gpgme 的软件时需设置 `PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig`
- 无可执行文件（gpgme 是纯库，无命令行工具）

---

*归档创建: 2026-05-31*