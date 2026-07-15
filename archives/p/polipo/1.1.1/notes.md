# polipo 1.1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 1. 源码下载
从 GitHub 下载 polipo-1.1.1.tar.gz：
```bash
# 官方源: https://github.com/jech/polipo/archive/refs/tags/polipo-1.1.1.tar.gz
python3 $SKILL_ROOT/scripts/ohc-run.py init-build polipo 1.1.1 --url=https://github.com/jech/polipo/archive/refs/tags/polipo-1.1.1.tar.gz
```

### 2. 编译
Polipo 是纯 Makefile 项目，无 configure 脚本：
```bash
source .build-context-polipo-1.1.1
cd $BUILD_SRC_DIR
make polipo -j1
```

### 3. 安装到 staging 目录
```bash
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/bin
cp polipo $TEST_PREFIX$DEFAULT_PREFIX/bin/
```

### 4. 验证
```bash
$TEST_PREFIX$DEFAULT_PREFIX/bin/polipo -h
$TEST_PREFIX$DEFAULT_PREFIX/bin/polipo -v
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | makeinfo 缺失 | texinfo 包未安装 | 跳过文档生成，不影响二进制构建 |
| 2 | md5.c 编译警告 | 旧式 C 函数定义 | 非致命，忽略 |
| 3 | conan create build() 失败 | make 在 build 子目录执行，找不到 Makefile | 使用 `make -C {self.source_folder}` |
| 4 | package_info() buildenv_info 不存在 | Conan 2.x _Component 无此属性 | 移除 buildenv_info，仅保留 bindirs |

## 源码修改

无补丁，纯 Makefile 项目无需修改源码。

## 依赖版本

- 无外部依赖
- 仅需标准 C 库（musl）

## 验证结果

```
$ polipo -h
polipo [ -h ] [ -v ] [ -x ] [ -c filename ] [ -- ] [ var=val... ]
  -h: display this message.
  -v: display the list of configuration variables.
  -x: perform expiry on the disk cache.
  -c: specify the configuration file to use.

$ file polipo
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

$ readelf -d polipo
NEEDED: libc.so
FLAGS: BIND_NOW
FLAGS_1: NOW PIE
```

## Conan 配方验证

- G1 (Recipe completeness): PASS
- G2 (conan create): PASS
- G3 (System lib isolation): PASS
- G4 (Product integrity): PASS
- L2 (Smoke test): PASS
- L4 (Security scan): PASS
- L5 (Baseline): PASS

## 注意事项

1. polipo 已停止维护（2014 年最后版本）
2. 运行时警告（主机名、缓存目录）属于配置问题
3. 可用于测试/学习，生产环境建议用更现代的代理

**编译结束**: 2026-07-15 20:02
**最终状态**: built
