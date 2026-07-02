# perl-object-pad

Object::Pad - simple syntax for lexical field-based objects.

## 软件信息

- **官网**: https://metacpan.org/dist/Object-Pad
- **源码**: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Object-Pad-0.821.tar.gz
- **许可证**: Artistic-1.0-Perl
- **分类**: perl
- **作者**: PEVANS (Paul Evans)

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.821-r0 | built | 2026-06-29 | 编译成功, 99.5%测试通过 |

## 运行依赖

- perl 5.42.0
- XS::Parse::Keyword
- XS::Parse::Sublike

## 编译依赖

- musl (提供标准 C 库头文件)
- clang 18.1.8 (aarch64-unknown-linux-ohos)
- XS::Parse::Keyword (XS依赖)
- XS::Parse::Sublike (XS依赖)

## 使用说明

Object::Pad 提供了 Perl 的面向对象语法糖，使用 `class`、`field`、`method` 关键字实现词法字段对象。

### 安装

预编译包安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/` 目录。

HNP 包: `perl-object-pad.hnp` (166KB, 含Pad.so + XS依赖 + .pm文件)

### 注意事项

由于 SELinux HMDFS 限制，XS 模块需要安装到系统目录 `/data/service/hnp` 才能正常加载。

Object::Pad 是纯 XS 模块，无 PurePerl fallback，必须加载 Pad.so 才能使用。

### 已知限制

1. **SELinux HMDFS 限制**: 用户目录下的 .so 文件无法加载，需安装到系统目录
2. **XS::Parse::Sublike ABI 版本不匹配**: 当前安装版本(ABI v4)与编译目标(ABI v3)不一致，导致 async 相关功能不可用
3. **可选依赖缺失**: Syntax::Keyword::Dynamically、Devel::MAT、Test::MemoryGrowth、Test::Pod 未安装

---

*OpenHarmony 编译归档 · 2026-07-02*
