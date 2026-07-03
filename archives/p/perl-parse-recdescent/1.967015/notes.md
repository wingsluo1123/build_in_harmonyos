# 适配笔记 — perl-parse-recdescent 1.967015

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | Parse::RecDescent |
| 版本 | 1.967015 |
| 类型 | 纯 Perl 模块 (ExtUtils::MakeMaker) |
| 源码 | https://cpan.metacpan.org/authors/id/J/JT/JTBRAUN/Parse-RecDescent-1.967015.tar.gz |
| SHA256 | 1943336a4cb54f1788a733f0827c0c55db4310d5eae15e542639c9dd85656e37 |

## 编译过程

### 1. 下载与初始化
- 通过 MetaCPAN API 获取下载 URL
- 使用 `curl -kL` 下载源码包 (SSL 证书验证失败，鸿蒙平台已知问题)
- `ohc-run.py init-build --no-download` 初始化（手动放置源码包）

### 2. 构建
```bash
perl Makefile.PL
make
make install DESTDIR=$TEST_PREFIX
```

纯 Perl 模块，无 C 编译步骤。`perl Makefile.PL` 生成标准 Makefile，`make` 仅复制 .pm 文件到 blib 目录。

### 3. 测试
```bash
make test
```
结果: 13 个测试文件，122 个测试全部通过 (PASS)
- t/00.load.t, t/01.basics.t, t/autotree.t 等
- 2 个测试因缺少可选依赖跳过 (Test::Pod, Test::Warn)

### 4. Conan 配方
- `ohc-run.py conan-init` 生成的是 autotools 模板，需手动修改为纯 Perl 模块模式
- 参考已有配方 `perl-net-ip` 的 conanfile.py 结构
- 关键修改：
  - `build()`: 使用 `self.run("perl Makefile.PL")` 替代 autotools configure
  - `package()`: 使用 `make install DESTDIR` + glob 查找 .pm 文件
  - `package_info()`: `libs=[]`（纯 Perl 无编译库），设置 PERL5LIB 环境变量
  - 移除 `generate()` 中的 `-static` 链接标志（不适用）
- conandata.yml: 填入实际 SHA256
- test_package: 创建 test.pl 验证模块加载和简单解析器功能

### 5. 验证
- `ohc-run.py conan-verify`: G1-G4 全部通过，L2/L4/L5 检查通过
- G2 (conan create) 干净构建验证通过

## 问题与解决

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 下载 SSL 证书验证失败 | 鸿蒙平台 CA 证书问题 | 使用 `curl -kL` 下载 |
| conan-init 生成 autotools 模板 | 自动检测构建系统为 autotools | 手动改写为纯 Perl 模块模式 |
| conandata.yml SHA256 占位符 | 自动生成时未计算 | 手动 sha256sum 并填入 |

## 状态
- 编译状态: built
- conan-verify: PASS
- 分支: feat/perl-parse-recdescent-1.967015
