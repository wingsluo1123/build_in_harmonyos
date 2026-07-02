# perl-set-object

Perl XS module providing unordered collections (sets) of Perl objects.

## 软件信息

- **官网**: https://metacpan.org/dist/Set-Object
- **源码**: https://github.com/rurban/Set-Object
- **许可证**: Artistic-2.0
- **分类**: perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.43-r0 | built | 2026-06-29 | 首次编译成功，conan-verify 全部通过 |

## 运行依赖

- perl

## 编译依赖

- perl (提供 ExtUtils::MakeMaker 和 Perl 头文件)

## 使用说明

Set::Object 是一个 Perl XS 模块，提供高效的集合（Set）数据结构，支持对象和标量的无序集合操作，包括并集、交集、差集、对称差集等。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-set-object/1.43-r0@ohpcd/stable
```

安装到系统目录后，模块路径为：
- `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Set/Object.pm`
- `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Set/Object/Object.so`

### 注意事项

- 鸿蒙系统 SELinux HMDFS 限制用户目录的 .so 加载，XS 模块需安装到 `/data/service/hnp/` 系统目录才能正常运行
- 与 perl-dbd-pg 不同，Set::Object 不需要 CRT 链接参数（`-nostartfiles -nodefaultlibs -lc`），因为它仅链接 libc 和 Perl 解释器符号
- 编译使用 `make -j1`（E074: HarmonyOS SELinux 禁止 FIFO）

---
*OpenHarmony 编译归档 · 2026-06-29*
