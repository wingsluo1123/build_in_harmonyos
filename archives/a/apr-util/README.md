# APR-Util (Apache Portable Runtime Utility)

APR-Util 是 APR 的伴随库，提供额外的实用工具接口。

## 版本信息
- 当前版本: 1.6.3
- 发布日期: 2023-11-06
- 官网: https://apr.apache.org/

## 描述
APR-Util 提供了 APR 之外的补充功能：

- DBD (Database abstraction)
- DSO (Dynamic Shared Object)
- Cryptographic routines
- URI parsing
- XML parsing (via expat)
- DBM (Database Manager)

## 编译状态
- 鸿蒙难度: 🟡 (中等)
- 构建系统: autotools
- 编译器: clang

## 依赖
- apr/1.7.6
- expat/2.7.1

## 已知问题
- E007: config.guess 需要补丁支持 HarmonyOS
- E011: configure umask 需要修改
- E072: config.sub 需要支持 ohos-linux triplet + ohos* OS name + linux-ohos* validation

## 使用方式
```bash
# 链接 APR-Util
gcc myapp.c -I/path/to/apr-util/include/apr-1 -L/path/to/apr-util/lib -laprutil-1 -lapr-1

# 使用 pkg-config
gcc myapp.c $(pkg-config --cflags --libs apr-util-1)
```
