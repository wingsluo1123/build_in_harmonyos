# bashdb 5.2-1.2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-22
- 包类型: 纯 bash 脚本（无可执行二进制）
- 状态: built

## 依赖
- bash/5.3（已发布到 ohpcd，status: published, build_date: 2026-04-13）

## 编译步骤
```bash
# bash 5.3 路径由 Conan 依赖提供
./configure --prefix=$TEST_PREFIX \
    --with-bash=$BASH_PREFIX/bin/bash \
    --build=aarch64-unknown-linux-gnu
make -j$(nproc)
make install
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 拒绝 bash 5.3 | case 语句只匹配 5.0/5.1/5.2 | 补丁 0001：添加 `'5.3'` 到 case 分支，更新错误消息 |
| 2 | configure 找到旧版 bash | PATH 中可能有系统自带 bash | `--with-bash` 指定 bash/5.3 依赖的 bin/bash 路径 |
| 3 | config.guess 不识别 OHOS | uname -s 返回 HarmonyOS | `--build=aarch64-unknown-linux-gnu` 强制 triplet |
| 4 | 源码无法从 SourceForge 下载 | 中国地区 sourceforge.net 被屏蔽 | conandata.yml URL 列表添加 MacPorts distfiles 镜像 fallback |

## 源码下载
- 官方源: https://downloads.sourceforge.net/project/bashdb/bashdb/5.2-1.2.0/bashdb-5.2-1.2.0.tar.bz2
- 镜像源: https://distfiles.macports.org/bashdb/bashdb-5.2-1.2.0.tar.bz2
- SHA256: 96fe0c8ffc12bc478c9dc41bb349ae85135da71b692069b8b7f62b27967ce534
- 大小: 603654 字节

## 验证结果
- `bashdb --version` ✅ (预期输出 bashdb 5.2-1.2.0)
- 纯脚本包，无 NEEDED 依赖

## 注意事项
- 运行时需要 bash/5.3 已安装
- bashdb 通过 `bash --debugger` 或直接 `bashdb` 调用
