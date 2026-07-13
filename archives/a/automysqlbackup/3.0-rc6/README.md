# automysqlbackup 3.0-rc6 — OpenHarmony 编译归档

## 软件简介

automysqlbackup 是一个纯 Bash 脚本工具，用于自动备份 MySQL 数据库。
本版本 3.0-rc6 无需 C/C++ 编译，"编译"过程即安装脚本文件到目标系统。

- **主页**: https://sourceforge.net/projects/automysqlbackup/
- **许可证**: GPL-2.0
- **构建系统**: custom (纯脚本安装)

## 归档内容

```
archives/a/automysqlbackup/3.0-rc6/
├── conanfile.py          # Conan 2.x 配方
├── conandata.yml         # 源码下载信息 + SHA256
├── manifest.yaml         # 归档清单
├── notes.md              # 适配笔记
├── README.md             # 本文件
├── packaging/            # 打包产物（空）
├── patches/              # 补丁文件（无）
├── test_package/
│   └── conanfile.py      # Conan 测试包
└── reports/
    ├── conan-verify-report.md          # conan-verify 官方报告
    ├── conan-create.log                # ohos-aarch64 profile 失败日志
    ├── conan-create-standard-profile.log  # 标准 profile 成功日志
    ├── manual-install-check.log        # 手动安装验证日志
    └── test-report.md                  # 综合测试报告
```

## 编译状态

**状态**: `built`

- 手动安装验证: ✅ 通过 (md5 校验 + 语法检查 + 功能测试)
- Conan 配方完整性 (G1): ✅ 通过
- Conan create + test (标准 Profile): ✅ 通过
- Conan create (ohos-aarch64 Profile): ❌ 失败 (profile `os.cpu.arch` 兼容性问题)

## 源码信息

- **下载 URL**: https://downloads.sourceforge.net/project/automysqlbackup/AutoMySQLBackup/AutoMySQLBackup%20VER%203.0/automysqlbackup-v3.0_rc6.tar.gz
- **SHA256**: 889e064d086b077e213da11e937ea7242a289f9217652b9051c157830dc23cc0
- **压缩格式**: tar.gz
- **解压根目录**: 无 (strip_root=False)

## Conan 配方关键字段

| 字段 | 值 |
|------|-----|
| name | automysqlbackup |
| version | 3.0-rc6 |
| settings | os, compiler, build_type, arch |
| requirements | 无外部依赖 (R27 合规) |
| generate | BUILD_SHARED_LIBS=OFF (R26 静态链接标记) |
| package_info.libs | ["automysqlbackup"] |
| package_info.bindirs | ["bin"] |

## 安装路径

| 文件 | 安装路径 |
|------|----------|
| automysqlbackup | $PREFIX/bin/automysqlbackup |
| automysqlbackup.conf | /etc/automysqlbackup/automysqlbackup.conf |
| LICENSE | /etc/automysqlbackup/LICENSE |
| README | /etc/automysqlbackup/README |
