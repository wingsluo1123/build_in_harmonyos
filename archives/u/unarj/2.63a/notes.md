# unarj 2.63a 适配笔记

## 编译环境
- 构建系统: makefile (simple Makefile, no configure)
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built

## 源码
- URL: https://www.ibiblio.org/pub/Linux/utils/compress/unarj-2.63a.tar.gz
- SHA256: d197ae60d06c1e11e3579fc0afa8c2f7d328b9d7e063d7c0124cb2346810a764

## 编译步骤
```bash
make CC=clang CFLAGS="-fPIC -O2 -Wall -DUNIX" -j1
```

## 适配说明
- unarj 是一个纯命令行工具，非库文件
- 源码来自 ibiblio 公共存档（原始 sourceforge URL 404）
- Makefile 使用 gcc，需覆盖为 clang
- CFLAGS 需添加 -DUNIX 以启用 POSIX 代码路径
- 无依赖，仅依赖标准 C 库
- 编译产生大量 C 旧式声明警告，但不影响功能

## 依赖版本
- 无第三方依赖，仅依赖标准 C 库（musl libc）

## 验证结果
```
conan create archives/u/unarj/2.63a -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 结果: G2 PASS (conan create 成功), G3 PASS, G4 PASS
# test_package: PASS (unarj binary runs and prints usage info)
```

## 源码修改
无补丁，无源码修改

## COMPLETED
