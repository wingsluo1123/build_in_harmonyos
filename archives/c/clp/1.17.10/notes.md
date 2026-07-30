# clp 1.17.10 适配笔记

## 基本信息
- 软件: clp (COIN-OR Linear Programming)
- 版本: 1.17.10
- 构建系统: autotools
- 依赖: CoinUtils/2.11.10, Osi/0.108.9

## 关键问题
### E072: config.sub 不识别 ohos 三元组
替换 config.sub/config.guess 为支持 ohos 的版本

### 依赖链
CoinUtils → Osi → Clp

## 编译命令
./configure --prefix=$DEFAULT_PREFIX CC=clang CXX=clang++ --enable-static --disable-shared
make -j1
make install
